"""The QObject facade QML talks to (exposed as the `Monitor` context property).

Sampling happens on a worker thread; results are delivered to the GUI thread
through queued signals, where they are turned into rolling graph histories
(`Series`) and list models.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback
from typing import Any

from PySide6.QtCore import (
    Property,
    QEvent,
    QFileSystemWatcher,
    QObject,
    QThread,
    QTimer,
    Signal,
    Slot,
    QUrl,
)
from PySide6.QtGui import QGuiApplication, QDesktopServices

from .models import DeviceModel, ProcessModel, ServiceModel
from . import sandbox, wallpaper

log = logging.getLogger(__name__)

HISTORY = 300  # samples kept per series; graphs show the most recent N
_VISIBILITY_EVENTS = (QEvent.Type.Expose, QEvent.Type.Show, QEvent.Type.Hide,
                      QEvent.Type.WindowActivate, QEvent.Type.WindowDeactivate,
                      QEvent.Type.WindowStateChange)
NO_DATA = float("nan")  # history that hasn't been sampled yet; graphs skip it


class Series(QObject):
    """Rolling history of one metric."""

    changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._values: list[float] = [NO_DATA] * HISTORY

    def push(self, value: float | None, notify: bool = True) -> None:
        self._values.append(float(value) if value is not None else NO_DATA)
        del self._values[0]
        if notify:
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
        self._proc_interval = 2000   # ms; the process table needn't follow every tick
        self._ticks = 0
        self._timer: QTimer | None = None
        self._sys = self._procs = self._apps = None
        self._magpie = None
        self._magpie_misses = 0

    @Slot()
    def start(self) -> None:
        self._use_magpie() or self._use_python()
        try:
            self.staticReady.emit(self._sys.static_info())
        except Exception:  # noqa: BLE001 - never let the sampler thread die
            self.failed.emit(traceback.format_exc())
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self._interval)
        self._tick()

    def _use_magpie(self) -> bool:
        """Mission Center's own engine, when it has been built (build-native.sh)."""
        if sys.platform == "win32":
            return False
        from .backend import magpie
        from .backend.collectors import SystemSampler

        binaries = magpie.find_binaries() if os.environ.get("MC_ENGINE") != "python" else None
        if not binaries:
            return False
        self._magpie = magpie.MagpieClient(*binaries)
        self._sys = magpie.MagpieSystemSampler(self._magpie, SystemSampler())
        self._procs = self._apps = magpie.MagpieProcessSampler(self._magpie)
        log.info("data engine: magpie (%s)", binaries[1])
        return True

    def _use_python(self) -> bool:
        from .backend import AppResolver, ProcessSampler, SystemSampler

        if self._magpie is not None:
            self._magpie.close()
            self._magpie = None
        self._sys = SystemSampler()
        self._procs = ProcessSampler()
        self._apps = AppResolver()
        log.info("data engine: %s", "Windows" if sys.platform == "win32" else "built-in Python collectors")
        return True

    @Slot()
    def stop(self) -> None:
        if self._timer:
            self._timer.stop()
        if self._sys is not None and hasattr(self._sys, "close"):
            self._sys.close()
        if self._magpie is not None:
            self._magpie.close()

    @Slot(int)
    def setInterval(self, ms: int) -> None:
        self._interval = max(250, ms)
        if self._timer:
            self._timer.setInterval(self._interval)

    @Slot(int)
    def setProcessInterval(self, ms: int) -> None:
        self._proc_interval = max(0, ms)

    @Slot(bool)
    def setWantProcesses(self, want: bool) -> None:
        changed = want and not self._want_procs
        self._want_procs = want
        if changed and self._procs is not None:
            self._sample_processes()

    def _tick(self) -> None:
        try:
            snap = self._sys.sample()
            if self._magpie is not None and not snap["cpu"].get("per_core"):
                # magpie/bridge stopped answering: fall back after a few tries
                self._magpie_misses += 1
                if self._magpie_misses >= 3:
                    log.warning("magpie is not responding; switching to the Python collectors")
                    self._use_python()
                    self.staticReady.emit(self._sys.static_info())
                return
            self._magpie_misses = 0
            self.systemReady.emit(snap)
        except Exception:  # noqa: BLE001
            self.failed.emit(traceback.format_exc())
        self._ticks += 1
        every = max(1, round(self._proc_interval / self._interval))
        if self._want_procs and self._ticks % every == 0:
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
        from .backend import list_services

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
    processIntervalChanged = Signal()
    wallpaperChanged = Signal()
    actionFinished = Signal(str, bool, str)       # title, ok, message
    logsReady = Signal(str, str)                  # unit, text
    _wallpaperFound = Signal(object)              # (light, dark) URLs, from a worker thread

    # cross-thread requests to the worker
    _reqInterval = Signal(int)
    _reqProcessInterval = Signal(int)
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
        self._on_screen = True
        self._stale = False
        self._notify = True
        self._window: QObject | None = None
        self._process_interval = 2000
        if sandbox.IN_FLATPAK:
            # The sandbox can't watch Plasma's config. Look again (off the UI
            # thread: it takes host calls) at startup and whenever the window is
            # activated, e.g. after changing the wallpaper in System Settings.
            self._wallpapers = ("", "")
            self._wallpaper_checked = 0.0
            self._wallpaperFound.connect(self._on_wallpaper_found)
            self._refresh_wallpaper()
        else:
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
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.started.connect(self._worker.start)
        self._worker.staticReady.connect(self._on_static)
        self._worker.systemReady.connect(self._on_system)
        self._worker.processesReady.connect(self._on_processes)
        self._worker.failed.connect(lambda tb: log.error("sampler failure:\n%s", tb))
        self._reqInterval.connect(self._worker.setInterval)
        self._reqProcessInterval.connect(self._worker.setProcessInterval)
        self._reqProcesses.connect(self._worker.setWantProcesses)
        self._reqStop.connect(self._worker.stop)

        self._svc_thread = QThread(self)
        self._svc_worker = ServiceWorker()
        self._svc_worker.moveToThread(self._svc_thread)
        self._svc_thread.finished.connect(self._svc_worker.deleteLater)
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
        # Off screen (minimized, other desktop) the history keeps growing, but
        # nothing in the UI is told until the window is back.
        self._record(snap, notify=self._on_screen)
        if self._on_screen:
            self._devices.update(snap, self._static)
            self._ready = True
            self.sampled.emit()
        else:
            self._stale = True

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
        s.push(value, self._notify)

    def _record(self, snap: dict[str, Any], notify: bool = True) -> None:
        self._notify = notify
        self._record_values(snap)

    def _record_values(self, snap: dict[str, Any]) -> None:
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
            self._update_wants()
            self.pageChanged.emit()

    def _update_wants(self) -> None:
        self._reqProcesses.emit(self._on_screen and self._page == "apps")
        self._reqServices.emit(self._on_screen and self._page == "services", self._services_user)

    def _get_process_interval(self) -> int:
        return self._process_interval

    def _set_process_interval(self, ms: int) -> None:
        if ms != self._process_interval:
            self._process_interval = ms
            self._reqProcessInterval.emit(ms)
            self.processIntervalChanged.emit()

    processInterval = Property(int, _get_process_interval, _set_process_interval,
                               notify=processIntervalChanged)

    # -- on-screen tracking ------------------------------------------------------
    def watch(self, window: QObject) -> None:
        """Follow whether `window` can be seen; minimized or on another desktop
        it isn't exposed (KWin suspends it), and then sampling for the tables
        pauses and the UI stops updating."""
        self._window = window
        window.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self._window and event.type() in _VISIBILITY_EVENTS:
            QTimer.singleShot(0, self._check_on_screen)
            if sandbox.IN_FLATPAK and event.type() == QEvent.Type.WindowActivate:
                self._refresh_wallpaper()
        return False

    def _check_on_screen(self) -> None:
        w = self._window
        # Being focused always counts as visible, in case a compositor never
        # re-sends an expose after restoring the window.
        on = bool(w.isExposed() or w.isActive())
        if on == self._on_screen:
            return
        self._on_screen = on
        self._update_wants()
        if on and self._stale:
            self._stale = False
            for s in self._series.values():
                s.changed.emit()
            self._devices.update(self._snap, self._static)
            self._ready = True
            self.sampled.emit()

    activePage = Property(str, _get_page, _set_page, notify=pageChanged)

    def _get_services_user(self) -> bool:
        return self._services_user

    def _set_services_user(self, user: bool) -> None:
        if user != self._services_user:
            self._services_user = user
            # Drop the other scope's rows at once so no action can target them.
            self._services.reset()
            self._reqServices.emit(self._on_screen and self._page == "services", user)
            self.servicesUserChanged.emit()

    servicesUser = Property(bool, _get_services_user, _set_services_user, notify=servicesUserChanged)

    def _watch_wallpaper_config(self) -> None:
        path = str(wallpaper.CONFIG)
        if path not in self._wallpaper_watch.files() and wallpaper.CONFIG.exists():
            self._wallpaper_watch.addPath(path)

    @Slot(str)
    def _on_wallpaper_config(self, _path: str) -> None:
        self._watch_wallpaper_config()
        self._on_wallpaper_found(wallpaper.resolve())

    def _refresh_wallpaper(self) -> None:
        now = time.monotonic()
        if now - self._wallpaper_checked < 5:
            return
        self._wallpaper_checked = now
        threading.Thread(target=lambda: self._wallpaperFound.emit(wallpaper.resolve()), daemon=True).start()

    @Slot(object)
    def _on_wallpaper_found(self, urls: tuple[str, str]) -> None:
        urls = tuple(urls)
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
        from .backend import process_details

        try:
            return process_details(pid) or {}
        except Exception:  # noqa: BLE001
            log.exception("process_details(%s)", pid)
            return {}

    @Slot("QVariantList", "QVariantList", str, str)
    def signalProcesses(self, pids: list[int], starts: list[int | None], sig: str, title: str) -> None:
        """Signal processes; `starts` (start times) guard against recycled PIDs."""
        from .backend import signal_process

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
        from .backend import service_action

        def run() -> None:
            ok, err = service_action(name, action, user)
            self.actionFinished.emit(f"{action.capitalize()} {name}", ok, err)
            self._reqRefreshServices.emit()

        threading.Thread(target=run, daemon=True).start()

    @Slot(str, bool)
    def requestLogs(self, name: str, user: bool) -> None:
        from .backend import service_logs

        def run() -> None:
            self.logsReady.emit(name, service_logs(name, user))

        threading.Thread(target=run, daemon=True).start()

    @Slot(str, "QVariantList")
    def launch(self, program: str, args: list[str]) -> None:
        """Start a helper program (System Settings modules, file manager…)."""
        if sys.platform == "win32":
            if program == "xdg-open" and args:
                target = str(args[0])
                url = QUrl.fromLocalFile(target) if os.path.exists(target) else QUrl(target)
            elif program == "systemsettings":
                page = "network" if "kcm_networkmanagement" in args else "powersleep"
                url = QUrl("ms-settings:" + page)
            else:
                self.actionFinished.emit(program, False, "This helper is unavailable on Windows")
                return
            if not QDesktopServices.openUrl(url):
                self.actionFinished.emit(program, False, "Could not open the requested location")
            return
        if sandbox.IN_FLATPAK:
            threading.Thread(target=self._launch_on_host, args=(program, args), daemon=True).start()
            return
        if shutil.which(program) is None:
            self.actionFinished.emit(program, False, f"{program} is not installed")
            return
        subprocess.Popen([program, *map(str, args)], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _launch_on_host(self, program: str, args: list[str]) -> None:
        try:
            found = subprocess.run(sandbox.host(["sh", "-c", 'command -v "$1"', "sh", program]),
                                   capture_output=True, timeout=5).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            found = False
        if not found:
            self.actionFinished.emit(program, False, f"{program} is not installed")
            return
        subprocess.Popen(sandbox.host([program, *map(str, args)]), start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
