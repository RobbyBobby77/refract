"""The QObject facade QML talks to (exposed as the `Monitor` context property).

Sampling happens on a worker thread; results are delivered to the GUI thread
through queued signals, where they are turned into rolling graph histories
(`Series`) and list models.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import threading
import traceback
from typing import Any

from PySide6.QtCore import (
    Property,
    QFileSystemWatcher,
    QObject,
    QThread,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import QGuiApplication

from .models import DeviceModel, ProcessModel, ServiceModel
from . import wallpaper

log = logging.getLogger(__name__)

HISTORY = 300  # samples kept per series; graphs show the most recent N
NO_DATA = float("nan")  # history that hasn't been sampled yet; graphs skip it


class Series(QObject):
    """Rolling history of one metric."""

    changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._values: list[float] = [NO_DATA] * HISTORY

    def push(self, value: float | None) -> None:
        self._values.append(float(value) if value is not None else NO_DATA)
        del self._values[0]
        self.changed.emit()

    def _get_values(self) -> list[float]:
        return self._values

    def _get_latest(self) -> float:
        return self._values[-1]

    values = Property("QVariantList", _get_values, notify=changed)
    latest = Property(float, _get_latest, notify=changed)

    @Slot(int, result=float)
    def peak(self, points: int) -> float:
        recent = [v for v in self._values[-points:] if v == v]  # drop NaN
        return max(recent, default=0.0)


class SamplerWorker(QObject):
    staticReady = Signal(object)
    systemReady = Signal(object)
    processesReady = Signal(object, object)
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._interval = 1000
        self._want_procs = False
        self._timer: QTimer | None = None
        self._sys = self._procs = self._apps = None

    @Slot()
    def start(self) -> None:
        from .backend.collectors import SystemSampler
        from .backend.processes import AppResolver, ProcessSampler

        self._sys = SystemSampler()
        self._procs = ProcessSampler()
        self._apps = AppResolver()
        try:
            self.staticReady.emit(self._sys.static_info())
        except Exception:  # noqa: BLE001 - never let the sampler thread die
            self.failed.emit(traceback.format_exc())
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self._interval)
        self._tick()

    @Slot()
    def stop(self) -> None:
        if self._timer:
            self._timer.stop()

    @Slot(int)
    def setInterval(self, ms: int) -> None:
        self._interval = max(250, ms)
        if self._timer:
            self._timer.setInterval(self._interval)

    @Slot(bool)
    def setWantProcesses(self, want: bool) -> None:
        changed = want and not self._want_procs
        self._want_procs = want
        if changed and self._procs is not None:
            self._sample_processes()

    def _tick(self) -> None:
        try:
            self.systemReady.emit(self._sys.sample())
        except Exception:  # noqa: BLE001
            self.failed.emit(traceback.format_exc())
        if self._want_procs:
            self._sample_processes()

    def _sample_processes(self) -> None:
        try:
            procs = self._procs.sample()
            apps = self._apps.resolve(procs)
            self.processesReady.emit(procs, apps)
        except Exception:  # noqa: BLE001
            self.failed.emit(traceback.format_exc())



class ServiceWorker(QObject):
    """Polls systemd on its own thread: a full listing takes ~0.7 s, which
    would otherwise stall the graphs."""

    servicesReady = Signal(object)
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._want = False
        self._user = False
        self._timer: QTimer | None = None

    @Slot()
    def start(self) -> None:
        self._timer = QTimer(self)
        self._timer.setInterval(5000)
        self._timer.timeout.connect(self.refresh)
        if self._want:
            self._timer.start()

    @Slot()
    def stop(self) -> None:
        if self._timer:
            self._timer.stop()

    @Slot(bool, bool)
    def setWant(self, want: bool, user: bool) -> None:
        changed = want and (not self._want or user != self._user)
        self._want, self._user = want, user
        if self._timer:
            if want:
                self._timer.start()
            else:
                self._timer.stop()
        if changed:
            self.refresh()

    @Slot()
    def refresh(self) -> None:
        from .backend.services import list_services

        try:
            self.servicesReady.emit(list_services(self._user))
        except Exception:  # noqa: BLE001
            self.failed.emit(traceback.format_exc())


class Monitor(QObject):
    sampled = Signal()
    staticChanged = Signal()
    intervalChanged = Signal()
    pageChanged = Signal()
    servicesUserChanged = Signal()
    wallpaperChanged = Signal()
    actionFinished = Signal(str, bool, str)       # title, ok, message
    logsReady = Signal(str, str)                  # unit, text

    # cross-thread requests to the worker
    _reqInterval = Signal(int)
    _reqProcesses = Signal(bool)
    _reqServices = Signal(bool, bool)
    _reqRefreshServices = Signal()
    _reqStop = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._static: dict[str, Any] = {}
        self._snap: dict[str, Any] = {}
        self._series: dict[str, Series] = {}
        self._interval = 1000
        self._page = "performance"
        self._services_user = False
        self._ready = False
        self._wallpapers = wallpaper.resolve()
        # Follow wallpaper changes. Plasma rewrites its config atomically, which
        # drops the inotify watch, so the path is re-added after every change.
        self._wallpaper_watch = QFileSystemWatcher(self)
        self._wallpaper_watch.fileChanged.connect(self._on_wallpaper_config)
        self._watch_wallpaper_config()

        self._devices = DeviceModel(self)
        self._processes = ProcessModel(self)
        self._services = ServiceModel(self)

        self._thread = QThread(self)
        self._worker = SamplerWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start)
        self._worker.staticReady.connect(self._on_static)
        self._worker.systemReady.connect(self._on_system)
        self._worker.processesReady.connect(self._on_processes)
        self._worker.failed.connect(lambda tb: log.error("sampler failure:\n%s", tb))
        self._reqInterval.connect(self._worker.setInterval)
        self._reqProcesses.connect(self._worker.setWantProcesses)
        self._reqStop.connect(self._worker.stop)

        self._svc_thread = QThread(self)
        self._svc_worker = ServiceWorker()
        self._svc_worker.moveToThread(self._svc_thread)
        self._svc_thread.started.connect(self._svc_worker.start)
        self._svc_worker.servicesReady.connect(self._on_services)
        self._svc_worker.failed.connect(lambda tb: log.error("services failure:\n%s", tb))
        self._reqServices.connect(self._svc_worker.setWant)
        self._reqRefreshServices.connect(self._svc_worker.refresh)
        self._reqStop.connect(self._svc_worker.stop)

        self._thread.start()
        self._svc_thread.start()

    def shutdown(self) -> bool:
        """Stop the sampler threads; False if one is still stuck in a call."""
        self._reqStop.emit()
        stopped = True
        for thread in (self._thread, self._svc_thread):
            thread.quit()
            stopped = thread.wait(5000) and stopped
        return stopped

    # -- worker results -----------------------------------------------------
    @Slot(object)
    def _on_static(self, info: dict[str, Any]) -> None:
        self._static = info
        self.staticChanged.emit()

    @Slot(object)
    def _on_system(self, snap: dict[str, Any]) -> None:
        self._snap = snap
        self._record(snap)
        self._devices.update(snap, self._static)
        self._ready = True
        self.sampled.emit()

    @Slot(object, object)
    def _on_processes(self, procs: list[dict[str, Any]], apps: list[dict[str, Any]]) -> None:
        self._processes.update(procs, apps)

    @Slot(object)
    def _on_services(self, services: list[dict[str, Any]]) -> None:
        self._services.update(services)

    def _push(self, key: str, value: float | None) -> None:
        s = self._series.get(key)
        if s is None:
            s = self._series[key] = Series(self)
        s.push(value)

    def _record(self, snap: dict[str, Any]) -> None:
        cpu = snap.get("cpu") or {}
        self._push("cpu", cpu.get("usage"))
        self._push("cpu.kernel", cpu.get("kernel_usage"))
        self._push("cpu.freq", cpu.get("freq_mhz"))
        self._push("cpu.temp", cpu.get("temperature_c"))
        for i, v in enumerate(cpu.get("per_core") or []):
            self._push(f"cpu.core.{i}", v)

        mem = snap.get("memory") or {}
        total = mem.get("total") or 0
        swap_total = mem.get("swap_total") or 0
        self._push("mem", mem.get("used", 0) / total * 100.0 if total else 0.0)
        self._push("mem.swap", mem.get("swap_used", 0) / swap_total * 100.0 if swap_total else 0.0)

        for d in snap.get("disks") or []:
            k = f"disk.{d['id']}"
            self._push(f"{k}.busy", d.get("busy_percent"))
            self._push(f"{k}.read", d.get("read_bps"))
            self._push(f"{k}.write", d.get("write_bps"))

        for n in snap.get("network") or []:
            k = f"net.{n['id']}"
            self._push(f"{k}.rx", n.get("rx_bps"))
            self._push(f"{k}.tx", n.get("tx_bps"))

        for g in snap.get("gpus") or []:
            k = f"gpu.{g['id']}"
            self._push(f"{k}.usage", g.get("usage"))
            vt, gt = g.get("vram_total"), g.get("gtt_total")
            self._push(f"{k}.vram", (g.get("vram_used") or 0) / vt * 100.0 if vt else 0.0)
            self._push(f"{k}.gtt", (g.get("gtt_used") or 0) / gt * 100.0 if gt else 0.0)
            self._push(f"{k}.power", g.get("power_w"))
            self._push(f"{k}.temp", g.get("temperature_c"))
            self._push(f"{k}.clock", g.get("clock_mhz"))
            self._push(f"{k}.encode", g.get("encode"))
            self._push(f"{k}.decode", g.get("decode"))

        for f in snap.get("fans") or []:
            self._push(f"fan.{f['id']}.rpm", f.get("rpm"))
            self._push(f"fan.{f['id']}.pwm", f.get("pwm_percent"))
            self._push(f"fan.{f['id']}.temp", f.get("temperature_c"))

        for b in snap.get("batteries") or []:
            self._push(f"bat.{b['id']}.percent", b.get("percent"))
            self._push(f"bat.{b['id']}.power", b.get("power_w"))

    # -- properties -----------------------------------------------------------
    def _get(self, section: str, default: Any) -> Any:
        return self._snap.get(section, default)

    staticInfo = Property("QVariantMap", lambda self: self._static, notify=staticChanged)
    cpu = Property("QVariantMap", lambda self: self._get("cpu", {}), notify=sampled)
    memory = Property("QVariantMap", lambda self: self._get("memory", {}), notify=sampled)
    disks = Property("QVariantList", lambda self: self._get("disks", []), notify=sampled)
    network = Property("QVariantList", lambda self: self._get("network", []), notify=sampled)
    gpus = Property("QVariantList", lambda self: self._get("gpus", []), notify=sampled)
    fans = Property("QVariantList", lambda self: self._get("fans", []), notify=sampled)
    batteries = Property("QVariantList", lambda self: self._get("batteries", []), notify=sampled)
    ready = Property(bool, lambda self: self._ready, notify=sampled)
    devices = Property(QObject, lambda self: self._devices, constant=True)
    processes = Property(QObject, lambda self: self._processes, constant=True)
    services = Property(QObject, lambda self: self._services, constant=True)
    wallpaperDark = Property(str, lambda self: self._wallpapers[1], notify=wallpaperChanged)
    wallpaperLight = Property(str, lambda self: self._wallpapers[0], notify=wallpaperChanged)

    def _get_interval(self) -> int:
        return self._interval

    def _set_interval(self, ms: int) -> None:
        if ms != self._interval:
            self._interval = ms
            self._reqInterval.emit(ms)
            self.intervalChanged.emit()

    interval = Property(int, _get_interval, _set_interval, notify=intervalChanged)

    def _get_page(self) -> str:
        return self._page

    def _set_page(self, page: str) -> None:
        if page != self._page:
            self._page = page
            self._reqProcesses.emit(page == "apps")
            self._reqServices.emit(page == "services", self._services_user)
            self.pageChanged.emit()

    activePage = Property(str, _get_page, _set_page, notify=pageChanged)

    def _get_services_user(self) -> bool:
        return self._services_user

    def _set_services_user(self, user: bool) -> None:
        if user != self._services_user:
            self._services_user = user
            # Drop the other scope's rows at once so no action can target them.
            self._services.reset()
            self._reqServices.emit(self._page == "services", user)
            self.servicesUserChanged.emit()

    servicesUser = Property(bool, _get_services_user, _set_services_user, notify=servicesUserChanged)

    def _watch_wallpaper_config(self) -> None:
        path = str(wallpaper.CONFIG)
        if path not in self._wallpaper_watch.files() and wallpaper.CONFIG.exists():
            self._wallpaper_watch.addPath(path)

    @Slot(str)
    def _on_wallpaper_config(self, _path: str) -> None:
        self._watch_wallpaper_config()
        urls = wallpaper.resolve()
        if urls != self._wallpapers:
            self._wallpapers = urls
            self.wallpaperChanged.emit()

    # -- slots ------------------------------------------------------------------
    @Slot(str, result=QObject)
    def series(self, key: str) -> Series:
        s = self._series.get(key)
        if s is None:
            s = self._series[key] = Series(self)
        return s

    @Slot(str)
    def copy(self, text: str) -> None:
        QGuiApplication.clipboard().setText(text)

    @Slot(int, result="QVariantMap")
    def processDetails(self, pid: int) -> dict[str, Any]:
        from .backend.processes import process_details

        try:
            return process_details(pid) or {}
        except Exception:  # noqa: BLE001
            log.exception("process_details(%s)", pid)
            return {}

    @Slot("QVariantList", "QVariantList", str, str)
    def signalProcesses(self, pids: list[int], starts: list[int | None], sig: str, title: str) -> None:
        """Signal processes; `starts` (start times) guard against recycled PIDs."""
        from .backend.processes import signal_process

        def run() -> None:
            errors = []
            for i, pid in enumerate(pids):
                start = starts[i] if i < len(starts) else None
                ok, err = signal_process(int(pid), sig, int(start) if start is not None else None)
                if not ok:
                    errors.append(f"{pid}: {err}")
            self.actionFinished.emit(title, not errors, "\n".join(errors))

        threading.Thread(target=run, daemon=True).start()

    @Slot(str, str, bool)
    def serviceAction(self, name: str, action: str, user: bool) -> None:
        from .backend.services import service_action

        def run() -> None:
            ok, err = service_action(name, action, user)
            self.actionFinished.emit(f"{action.capitalize()} {name}", ok, err)
            self._reqRefreshServices.emit()

        threading.Thread(target=run, daemon=True).start()

    @Slot(str, bool)
    def requestLogs(self, name: str, user: bool) -> None:
        from .backend.services import service_logs

        def run() -> None:
            self.logsReady.emit(name, service_logs(name, user))

        threading.Thread(target=run, daemon=True).start()

    @Slot(str, "QVariantList")
    def launch(self, program: str, args: list[str]) -> None:
        """Start a helper program (System Settings modules, file manager…)."""
        if shutil.which(program) is None:
            self.actionFinished.emit(program, False, f"{program} is not installed")
            return
        subprocess.Popen([program, *map(str, args)], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
