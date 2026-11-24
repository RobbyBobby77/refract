"""Windows collectors and actions implementing Refract's snapshot contract."""
from __future__ import annotations

import os
import platform
import re
import socket
import subprocess
import time
import winreg
import xml.etree.ElementTree as ET
from pathlib import Path

import psutil

from .windows_native import (
    PerformanceCounters, graphics_adapters, performance_info, process_inventory,
    process_snapshot, visible_processes,
)

_ERRORS = (psutil.Error, OSError, ValueError)
_NO_WINDOW = subprocess.CREATE_NO_WINDOW
_SUSPENDED: set[tuple[int, int]] = set()


def _run(command: list[str], timeout: float = 5) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, errors="replace",
                          timeout=timeout, creationflags=_NO_WINDOW)


def _start_token(created: float) -> int:
    # Epoch milliseconds stay exact in QML's doubles (unlike 64-bit FILETIMEs).
    return int(created * 1000)


def _cpu_name() -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            return winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
    except OSError:
        return platform.processor() or "Processor"


def _gpu_id(instance: str) -> str | None:
    found = re.search(r"luid_(0x[0-9a-f]+_0x[0-9a-f]+)_phys_(\d+)", instance, re.I)
    return f"{found[1]}_{found[2]}".lower() if found else None


class SystemSampler:
    """psutil system rates plus native Windows performance counters."""

    def __init__(self) -> None:
        self._pdh = PerformanceCounters()
        self._previous_time = time.monotonic()
        self._cpu = psutil.cpu_times(percpu=True)
        self._disks = psutil.disk_io_counters(perdisk=True) or {}
        self._net = psutil.net_io_counters(pernic=True) or {}
        self._mounts: list[dict] = []
        self._mounts_time = 0.
        self._static: dict | None = None
        self._gpus = graphics_adapters()

    def close(self) -> None:
        self._pdh.close()

    def static_info(self) -> dict:
        if self._static is None:
            freq = psutil.cpu_freq()
            self._static = {
                "hostname": socket.gethostname(), "os_name": f"Windows {platform.release()}",
                "kernel": platform.version(), "desktop": "Windows", "engine": "windows",
                "cpu_name": _cpu_name(), "sockets": None, "cores": psutil.cpu_count(logical=False),
                "logical": psutil.cpu_count() or 1, "base_mhz": freq.max if freq else None,
                "max_mhz": freq.max if freq else None, "virtualization": None, "is_vm": None,
                "cache": {}, "cpu_driver": None, "governor": None, "energy_preference": None,
                "memory_total": psutil.virtual_memory().total,
            }
        return self._static

    def _volumes(self, now: float) -> list[dict]:
        if now - self._mounts_time >= 10:
            mounts = []
            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                except _ERRORS:
                    continue
                mounts.append({"device": part.device, "mountpoint": part.mountpoint,
                               "fstype": part.fstype, "total": usage.total, "used": usage.used})
            self._mounts, self._mounts_time = mounts, now
        return self._mounts

    def sample(self) -> dict:
        now = time.monotonic()
        elapsed = max(now - self._previous_time, 1e-6)
        counters = self._pdh.sample()
        current = psutil.cpu_times(percpu=True)
        cores, kernel = [], []
        for a, b in zip(self._cpu, current):
            total = max(0., sum(b) - sum(a))
            idle, system = max(0., b.idle - a.idle), max(0., b.system - a.system)
            cores.append(min(100., max(0., 100 * (total-idle)/total)) if total else 0.)
            kernel.append(min(100., 100 * system/total) if total else 0.)
        self._cpu = current
        freq = psutil.cpu_freq()
        info = performance_info()
        cpu = {"usage": sum(cores)/len(cores) if cores else 0.,
               "kernel_usage": sum(kernel)/len(kernel) if kernel else 0., "per_core": cores,
               "freq_mhz": freq.current if freq else None, "per_core_freq_mhz": None,
               "processes": info.get("processes", len(psutil.pids())), "threads": info.get("threads"),
               "handles": info.get("handles"), "uptime_s": max(0., time.time()-psutil.boot_time()),
               "temperature_c": None, "governor": None}
        ram, swap = psutil.virtual_memory(), psutil.swap_memory()
        memory = {"total": ram.total, "used": ram.used, "available": ram.available, "free": ram.free,
                  "cached": info.get("cached"), "buffers": None, "dirty": None, "shared": None,
                  "committed": info.get("committed"), "commit_limit": info.get("commit_limit"),
                  "swap_total": swap.total, "swap_used": swap.used, "compressed": None}
        volumes = self._volumes(now)
        disk_io = psutil.disk_io_counters(perdisk=True) or {}
        disks = []
        for name, values in disk_io.items():
            old = self._disks.get(name)
            number = re.search(r"(\d+)$", name)
            instance = next((s for s in counters.get("disk_busy", {})
                             if number and s.split(" ")[0] == number[1]), None)
            letters = instance.split()[1:] if instance else []
            parts = [p for p in volumes if p["device"].rstrip("\\").casefold() in {l.casefold() for l in letters}]
            busy = counters.get("disk_busy", {}).get(instance)
            response = counters.get("disk_response", {}).get(instance)
            disks.append({"id": name, "model": name, "type": "Disk",
                          "capacity": sum(p["total"] for p in parts) or None,
                          "formatted": sum(p["total"] for p in parts) or None,
                          "system_disk": any(p["device"].rstrip("\\").casefold() == os.environ.get("SystemDrive", "C:").casefold() for p in parts),
                          "removable": None, "read_bps": max(0, values.read_bytes-old.read_bytes)/elapsed if old else 0.,
                          "write_bps": max(0, values.write_bytes-old.write_bytes)/elapsed if old else 0.,
                          "busy_percent": min(100., max(0., 100-busy)) if busy is not None else None,
                          "avg_response_ms": response*1000 if response is not None else None,
                          "temperature_c": None, "partitions": parts})
        # Volume capacity is still useful when disk performance counters are disabled.
        if not disks:
            for p in volumes:
                disks.append({"id": p["device"], "model": p["device"], "type": "Volume",
                              "capacity": p["total"], "formatted": p["total"], "partitions": [p],
                              "read_bps": None, "write_bps": None, "busy_percent": None})
        self._disks = disk_io
        network = []
        addresses, stats = psutil.net_if_addrs(), psutil.net_if_stats()
        net_io = psutil.net_io_counters(pernic=True) or {}
        for name, values in net_io.items():
            addr, state = addresses.get(name, []), stats.get(name)
            if "loopback" in name.casefold():
                continue
            old = self._net.get(name)
            kind = "wifi" if any(s in name.casefold() for s in ("wi-fi", "wifi", "wireless", "wlan")) else "ethernet"
            network.append({"id": name, "name": name, "kind": kind, "up": bool(state and state.isup),
                            "rx_bps": max(0, values.bytes_recv-old.bytes_recv)/elapsed if old else 0.,
                            "tx_bps": max(0, values.bytes_sent-old.bytes_sent)/elapsed if old else 0.,
                            "rx_total": values.bytes_recv, "tx_total": values.bytes_sent,
                            "mac": next((a.address for a in addr if a.family == psutil.AF_LINK), None),
                            "ipv4": [a.address for a in addr if a.family == socket.AF_INET],
                            "ipv6": [a.address.split("%")[0] for a in addr if a.family == socket.AF_INET6],
                            "link_speed_mbps": state.speed if state and state.speed > 0 else None,
                            "driver": None, "device_name": name, "ssid": None, "signal_percent": None,
                            "frequency_mhz": None, "bitrate_mbps": None})
        self._net = net_io
        gpus: dict[str, dict] = {gid: dict(data) for gid, data in self._gpus.items()}
        # Sum processes on the same engine, then use the busiest engine per GPU.
        engines: dict[tuple[str, str], float] = {}
        for instance, value in counters.get("gpu", {}).items():
            gid = _gpu_id(instance)
            if gid and (not self._gpus or gid in self._gpus):
                engine = re.search(r"_eng_(\d+)", instance)
                key = gid, engine[1] if engine else instance
                engines[key] = engines.get(key, 0.) + value
        for field, counter in (("vram_used", "gpu_memory"), ("gtt_used", "gpu_shared")):
            for instance, value in counters.get(counter, {}).items():
                gid = _gpu_id(instance)
                if gid and (not self._gpus or gid in self._gpus):
                    gpus.setdefault(gid, {"id": gid, "name": "Windows graphics adapter"})[field] = int(value)
        for (gid, _engine), usage in engines.items():
            row = gpus.setdefault(gid, {"id": gid, "name": "Windows graphics adapter"})
            row["usage"] = min(100., max(row.get("usage", 0.), usage))
        batteries = []
        battery = psutil.sensors_battery()
        if battery:
            batteries.append({"id": "battery", "model": "System battery", "percent": battery.percent,
                              "state": "Full" if battery.power_plugged and battery.percent >= 100 else "Charging" if battery.power_plugged else "Discharging",
                              "time_remaining_s": battery.secsleft if battery.secsleft >= 0 else None,
                              "ac_online": battery.power_plugged})
        self._previous_time = now
        return {"timestamp": now, "cpu": cpu, "memory": memory, "disks": disks,
                "network": network, "gpus": list(gpus.values()), "fans": [], "batteries": batteries}


class ProcessSampler:
    """Rates keyed by process creation time, so reused PIDs start afresh."""

    def __init__(self) -> None:
        self._previous: dict[tuple[int, int], tuple[float, int, int]] = {}
        self._fixed: dict[tuple[int, int], dict] = {}
        self._last = time.monotonic()
        self._logical = psutil.cpu_count() or 1

    def sample(self) -> list[dict]:
        now = time.monotonic()
        elapsed = max(now-self._last, 1e-6)
        rows, fresh, fixed = [], {}, {}
        attrs = ["pid", "create_time", "cpu_times", "memory_info", "io_counters"]
        try:
            entries = process_snapshot()
        except OSError:
            entries = process_inventory()
        for entry in entries:
            if entry["pid"] == 0:
                continue
            p = {}
            if "created" in entry:
                p["create_time"] = entry["created"]
            else:
                try:
                    p = psutil.Process(entry["pid"]).as_dict(attrs, ad_value=None)
                except _ERRORS:
                    continue
            p.update(entry)
            if p["create_time"] is None:
                continue
            token = _start_token(p["create_time"])
            identity = p["pid"], token
            meta = self._fixed.get(identity)
            if meta is None:
                try:
                    process = psutil.Process(p["pid"])
                    meta = process.as_dict(["exe", "cmdline", "username"], ad_value=None)
                except _ERRORS:
                    meta = {"exe": None, "cmdline": None, "username": None}
            fixed[identity] = meta
            p.update(meta)
            if "cpu_seconds" in entry:
                cpu, io = True, True
                memory_bytes = entry["memory"]
                totals = (entry["cpu_seconds"], entry["read_bytes"], entry["write_bytes"])
            else:
                cpu, memory, io = p["cpu_times"], p["memory_info"], p["io_counters"]
                memory_bytes = memory.rss if memory else None
                totals = ((cpu.user+cpu.system) if cpu else 0., io.read_bytes if io else 0, io.write_bytes if io else 0)
            old = self._previous.get((p["pid"], token))
            fresh[p["pid"], token] = totals
            rows.append({"pid": p["pid"], "ppid": p["ppid"] or 0, "name": p["name"] or str(p["pid"]),
                         "exe": p["exe"], "cmdline": subprocess.list2cmdline(p["cmdline"] or []),
                         "user": p["username"], "state": "Stopped" if identity in _SUSPENDED else "Idle" if p["pid"] == 0 else "Running",
                         "threads": p["threads"], "nice": None, "start_time": p["create_time"],
                         "cpu": min(100., max(0., totals[0]-old[0])/elapsed/self._logical*100) if old and cpu else 0.,
                         "memory": memory_bytes, "shared_memory": None,
                         "disk_read_bps": max(0, totals[1]-old[1])/elapsed if old and io else None,
                         "disk_write_bps": max(0, totals[2]-old[2])/elapsed if old and io else None,
                         "gpu": None, "gpu_memory": None, "cgroup": None, "app_id": None, "start_ticks": token})
        self._previous, self._last = fresh, now
        self._fixed = fixed
        return rows


class AppResolver:
    """Group visible applications and their descendants by executable."""

    def resolve(self, processes: list[dict]) -> list[dict]:
        by_pid = {p["pid"]: p for p in processes}
        visible = visible_processes()
        groups: dict[str, list[dict]] = {}
        for process in processes:
            root = process
            seen = set()
            while root["pid"] not in visible and root["ppid"] in by_pid and root["pid"] not in seen:
                seen.add(root["pid"])
                root = by_pid[root["ppid"]]
            if root["pid"] not in visible:
                continue
            key = (root["exe"] or root["name"]).casefold()
            groups.setdefault(key, []).append(process)
        rows = []
        for key, procs in groups.items():
            root = next((p for p in procs if p["pid"] in visible), procs[0])
            row = {"id": key, "name": Path(root["name"]).stem, "icon": "",
                   "pids": [p["pid"] for p in sorted(procs, key=lambda p: p["start_time"])],
                   "gpu": None, "gpu_memory": None}
            for field in ("cpu", "memory", "shared_memory", "disk_read_bps", "disk_write_bps"):
                row[field] = sum(p.get(field) or 0 for p in procs)
            rows.append(row)
        return sorted(rows, key=lambda r: r["name"].casefold())


def signal_process(pid: int, sig: str, start_ticks: int | None = None) -> tuple[bool, str]:
    """Terminate/suspend/resume with psutil's PID reuse checks and our UI token."""
    if sig not in {"TERM", "KILL", "STOP", "CONT"} or not isinstance(pid, int) or pid <= 0:
        return False, "Invalid PID or action"
    try:
        process = psutil.Process(pid)
        if start_ticks is not None and _start_token(process.create_time()) != start_ticks:
            return False, "The process has already exited"
        {"TERM": process.terminate, "KILL": process.kill, "STOP": process.suspend, "CONT": process.resume}[sig]()
        identity = pid, _start_token(process.create_time())
        if sig == "STOP":
            _SUSPENDED.add(identity)
        else:
            _SUSPENDED.discard(identity)
        return True, ""
    except psutil.NoSuchProcess:
        return False, "The process has already exited"
    except psutil.AccessDenied:
        return False, "Access denied. Run Refract as administrator to manage this process."
    except _ERRORS as error:
        return False, str(error)


def process_details(pid: int) -> dict:
    keys = ("ppid", "name", "exe", "cmdline", "cwd", "user", "state", "threads", "nice", "start_time",
            "cgroup", "open_files", "memory_rss", "memory_shared", "memory_swap")
    data = {"pid": pid, **dict.fromkeys(keys)}
    try:
        process = psutil.Process(pid)
        with process.oneshot():
            for key, getter in (("ppid", process.ppid), ("name", process.name), ("exe", process.exe),
                                ("cmdline", lambda: subprocess.list2cmdline(process.cmdline())), ("cwd", process.cwd),
                                ("user", process.username), ("state", lambda: process.status().title()),
                                ("threads", process.num_threads),
                                ("nice", lambda: process.nice().name.replace("_PRIORITY_CLASS", "").replace("_", " ").title()),
                                ("start_time", process.create_time),
                                ("memory_rss", lambda: process.memory_info().rss)):
                try:
                    data[key] = getter()
                except _ERRORS:
                    pass
        # psutil.open_files() on Windows probes individual handles and may block
        # for seconds. It cannot run in this synchronous GUI detail callback.
    except _ERRORS:
        pass
    return data


def list_services(user: bool = False) -> list[dict]:
    """Windows Service Control Manager inventory; Windows has one service scope."""
    rows = []
    for service in psutil.win_service_iter():
        try:
            data = service.as_dict()
            status = data["status"]
            active = {"running": "active", "paused": "active", "start_pending": "activating",
                      "stop_pending": "deactivating"}.get(status, "inactive")
            startup = {"automatic": "enabled", "manual": "manual", "disabled": "disabled"}.get(data["start_type"], data["start_type"])
            pid = data["pid"]
            memory = None
            if pid:
                try:
                    memory = psutil.Process(pid).memory_info().rss
                except _ERRORS:
                    pass
            rows.append({"name": data["name"], "description": data["display_name"], "load_state": "loaded",
                         "active_state": active, "sub_state": status, "enabled_state": startup,
                         "pid": pid, "memory": memory, "user": False})
        except _ERRORS:
            continue
    return sorted(rows, key=lambda r: r["name"].casefold())


def _wait_service(name: str, status: str, timeout: float = 20) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if psutil.win_service_get(name).status() == status:
            return True
        time.sleep(.2)
    return False


def service_action(name: str, action: str, user: bool = False) -> tuple[bool, str]:
    """Use sc.exe with individual arguments; return SCM permission errors to UI."""
    if action not in {"start", "stop", "restart", "enable", "disable"} or not name or name.startswith("-"):
        return False, "Invalid service or action"
    try:
        psutil.win_service_get(name).name()  # Validate against the SCM before any action.
        if action == "restart":
            if psutil.win_service_get(name).status() != "stopped":
                result = _run(["sc.exe", "stop", name])
                if result.returncode:
                    return False, result.stdout.strip() or result.stderr.strip()
                if not _wait_service(name, "stopped"):
                    return False, "Timed out waiting for the service to stop"
            command = ["sc.exe", "start", name]
        elif action in {"enable", "disable"}:
            command = ["sc.exe", "config", name, "start=", "auto" if action == "enable" else "disabled"]
        else:
            command = ["sc.exe", action, name]
        result = _run(command)
        return result.returncode == 0, "" if result.returncode == 0 else result.stdout.strip() or result.stderr.strip()
    except (*_ERRORS, subprocess.TimeoutExpired) as error:
        return False, str(error)


def service_logs(name: str, user: bool = False, lines: int = 200) -> str:
    """Recent SCM System events for this service (not an application's own log)."""
    try:
        display = psutil.win_service_get(name).display_name()
        result = _run(["wevtutil.exe", "qe", "System", "/q:*[System[Provider[@Name='Service Control Manager']]]",
                       "/rd:true", "/f:xml", f"/c:{min(1000, max(1, int(lines)))}"], timeout=10)
        if result.returncode:
            return result.stderr.strip() or result.stdout.strip()
        root = ET.fromstring("<Events>" + re.sub(r"<\?xml[^>]*\?>", "", result.stdout) + "</Events>")
        ns = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}
        records = []
        for event in root.findall("e:Event", ns):
            values = [d.text or "" for d in event.findall("e:EventData/e:Data", ns)]
            if name not in values and display not in values:
                continue
            stamp = event.find("e:System/e:TimeCreated", ns)
            eid = event.findtext("e:System/e:EventID", "", ns)
            records.append(f"{stamp.get('SystemTime', '') if stamp is not None else ''} · Event {eid}\n" + " · ".join(values))
        return "\n\n".join(records)
    except (*_ERRORS, subprocess.TimeoutExpired, ET.ParseError) as error:
        return str(error)
