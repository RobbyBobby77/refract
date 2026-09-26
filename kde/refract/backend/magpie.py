"""Data from Mission Center's own engine, magpie.

magpie speaks protobuf over nng; the small `refract-bridge` helper (Rust,
kde/magpie-bridge) relays that as JSON lines. This module turns magpie's
replies into the same dict schemas the pure-Python collectors produce, so the
UI doesn't care which engine is running. Anything magpie doesn't report (CPU
core count, per-core clocks, drivers…) still comes from the Python collectors'
static information.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from .. import sandbox

log = logging.getLogger(__name__)

_PKG = Path(__file__).resolve().parent.parent
_REPO_KDE = _PKG.parent
_SEARCH = (
    (_PKG / "native" / "refract-bridge", _PKG / "native" / "magpie"),
    (_REPO_KDE / "magpie-bridge" / "target" / "release" / "refract-bridge",
     _REPO_KDE.parent / "subprojects" / "magpie" / "target" / "release" / "magpie"),
)

_DISK_KIND = {0: "HDD", 1: "SSD", 2: "NVMe", 3: "eMMC", 4: "SD", 5: "iSCSI",
              6: "Floppy", 7: "Optical", 8: "USB"}
_NET_KIND = {9: ("wifi", "Wi-Fi"), 8: ("ethernet", "Ethernet"), 7: ("vpn", "VPN"),
             1: ("other", "Bluetooth"), 2: ("other", "Bridge"), 3: ("other", "Docker"),
             4: ("other", "InfiniBand"), 5: ("other", "Multipass"), 6: ("other", "Virtual"),
             10: ("other", "Mobile Broadband")}
_PROC_STATE = {0: "Running", 1: "Sleeping", 2: "Disk sleep", 3: "Zombie", 4: "Stopped",
               5: "Tracing", 6: "Dead", 7: "Wake kill", 8: "Waking", 9: "Parked", 10: "Unknown"}
_BATTERY_STATE = {1: "Charging", 2: "Discharging", 3: "Empty", 4: "Full",
                  5: "Not charging", 6: "Not charging"}
_BATTERY_TECH = {1: "Li-ion", 2: "Li-polymer", 3: "LiFePO4", 4: "Lead acid",
                 5: "NiCd", 6: "NiMH"}
_VENDORS = {0x1002: "AMD", 0x10DE: "NVIDIA", 0x8086: "Intel", 0x5143: "Qualcomm", 0x13B5: "ARM"}
_MK_TO_C = -273150
_SLOW_EVERY = 3        # fans/batteries: refresh every Nth system sample
_APPS_EVERY = 5        # app list (membership only): every Nth process sample


def find_binaries() -> tuple[Path, Path] | None:
    """(bridge, magpie) if both were built/installed, else None."""
    for bridge, magpie in _SEARCH:
        if bridge.exists() and magpie.exists():
            return bridge, magpie
    return None


def _dig(obj: Any, *path: str) -> Any:
    for key in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


class MagpieClient:
    """One running bridge (and magpie) process. Not thread-safe by itself;
    calls are serialised with a lock because the services poller and the
    sampler thread may both use it."""

    def __init__(self, bridge: Path, magpie: Path) -> None:
        # Mission Center's hardware database (network adapter names), if built.
        hw_db = next((f for f in (magpie.parent / "hw.db", _REPO_KDE / "native" / "build" / "hw.db")
                      if f.exists()), None)
        env = dict(os.environ)
        if sandbox.IN_FLATPAK:
            command = sandbox.magpie_command(magpie, hw_db)
            if sandbox.socket_dir():
                env["REFRACT_SOCKET_DIR"] = sandbox.socket_dir()
        else:
            command = [str(magpie)]
            if hw_db:
                env.setdefault("MC_MAGPIE_HW_DB", str(hw_db))
        self._proc = subprocess.Popen(
            [str(bridge), *command], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1, env=env)
        self._lock = threading.Lock()

    def call(self, body: dict[str, Any]) -> dict[str, Any] | None:
        """Send one request; returns the response body, or None on failure."""
        with self._lock:
            if self._proc.poll() is not None:
                return None
            try:
                self._proc.stdin.write(json.dumps({"body": body}) + "\n")
                self._proc.stdin.flush()
                line = self._proc.stdout.readline()
            except (OSError, ValueError):
                return None
        if not line:
            return None
        try:
            reply = json.loads(line).get("body") or {}
        except ValueError:
            return None
        if "error" in reply:
            log.debug("magpie error: %s", reply["error"])
            return None
        return reply

    def close(self) -> None:
        try:
            self._proc.stdin.close()
            self._proc.wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            self._proc.kill()


class MagpieSystemSampler:
    """Drop-in replacement for collectors.SystemSampler backed by magpie."""

    def __init__(self, client: MagpieClient, fallback) -> None:
        self._client = client
        self._fallback = fallback          # collectors.SystemSampler, for static bits
        self._static: dict[str, Any] | None = None
        self._hwmon_names: dict[int, str] = {}
        self._net_drivers: dict[str, str | None] = {}
        self._gpu_drivers: dict[str, str | None] = {}
        # Fans and batteries change slowly: refresh them every few samples
        # (each magpie request triggers a refresh on its side).
        self._ticks = 0
        self._fans: list[dict[str, Any]] = []
        self._batteries: list[dict[str, Any]] = []

    # -- static ---------------------------------------------------------------
    def static_info(self) -> dict[str, Any]:
        if self._static is not None:
            return self._static
        info = dict(self._fallback.static_info())
        cpu = _dig(self._client.call({"get_cpu": {}}), "cpu", "response", "cpu") or {}
        if cpu:
            khz = cpu.get("base_freq_khz")
            info.update({
                "cpu_name": cpu.get("name") or info.get("cpu_name"),
                "sockets": cpu.get("socket_count") or info.get("sockets"),
                "base_mhz": khz / 1000 if khz else info.get("base_mhz"),
                "virtualization": cpu.get("virtualization_technology") or info.get("virtualization"),
                "is_vm": bool(cpu.get("is_virtual_machine")),
                "cache": {"L1d": cpu.get("l1_combined_cache_bytes"), "L1i": None,
                          "L2": cpu.get("l2_cache_bytes"), "L3": cpu.get("l3_cache_bytes")},
                "cpu_driver": cpu.get("frequency_driver") or info.get("cpu_driver"),
                "energy_preference": cpu.get("power_preference") or info.get("energy_preference"),
            })
        about = _dig(self._client.call({"get_about": {}}), "about", "response", "about_info") or {}
        if about:
            os_info, de, dev = about.get("os_info") or {}, about.get("de_info") or {}, about.get("device_info") or {}
            info["os_name"] = os_info.get("pretty_name") or info.get("os_name")
            info["hostname"] = dev.get("hostname") or info.get("hostname")
            if de.get("desktop_environment"):
                info["desktop"] = " ".join(x for x in (de.get("desktop_environment"), de.get("version")) if x)
            info["device"] = " ".join(x for x in (dev.get("vendor"), dev.get("model")) if x) or None
        info["engine"] = "magpie"
        self._static = info
        return info

    # -- live -------------------------------------------------------------------
    def sample(self) -> dict[str, Any]:
        c = self._client
        if self._ticks % _SLOW_EVERY == 0:
            self._fans = [self._fan(f) for f in _dig(c.call({"get_fans": {}}), "fans", "response", "fans", "fans") or []]
            self._batteries = [self._battery(b) for b in _dig(c.call({"get_battery": {}}),
                                                               "batteries", "response", "batteries", "batteries") or []
                               if b.get("kind") in (None, 2)]
        self._ticks += 1
        return {
            "timestamp": time.monotonic(),
            "cpu": self._cpu(_dig(c.call({"get_cpu": {}}), "cpu", "response", "cpu") or {}),
            "memory": self._memory(_dig(c.call({"get_memory": {"kind": 1}}),
                                        "memory", "response", "memory_info", "response", "memory") or {}),
            "disks": [self._disk(d) for d in _dig(c.call({"get_disks": {"request": {"disks": {}}}}),
                                                   "disks", "response", "disks", "disks") or []],
            "network": [self._net(n) for n in (_dig(c.call({"get_connections": {}}),
                                                    "connections", "response", "connections", "connections") or {}).values()],
            "gpus": [self._gpu(gid, g) for gid, g in sorted((_dig(c.call({"get_gpus": {}}),
                                                                  "gpus", "response", "gpus", "gpus") or {}).items())],
            "fans": self._fans,
            "batteries": self._batteries,
        }

    def _cpu(self, cpu: dict[str, Any]) -> dict[str, Any]:
        return {
            "usage": cpu.get("total_usage_percent"),
            "kernel_usage": cpu.get("kernel_usage_percent"),
            "per_core": cpu.get("core_usage_percent") or [],
            "freq_mhz": cpu.get("current_frequency_mhz"),
            "per_core_freq_mhz": None,
            "processes": cpu.get("total_process_count"),
            "threads": cpu.get("total_thread_count"),
            "handles": cpu.get("total_handle_count"),
            "uptime_s": cpu.get("uptime_seconds"),
            "temperature_c": cpu.get("temperature_celsius"),
            "governor": cpu.get("frequency_governor"),
            "power_w": cpu.get("power_draw_w"),
        }

    @staticmethod
    def _memory(m: dict[str, Any]) -> dict[str, Any]:
        if not m:
            return {}
        total, available = m.get("mem_total", 0), m.get("mem_available", 0)
        return {
            "total": total, "used": total - available, "available": available,
            "free": m.get("mem_free", 0),
            "cached": m.get("cached", 0) + m.get("s_reclaimable", 0),
            "buffers": m.get("buffers", 0), "dirty": m.get("dirty", 0),
            "shared": m.get("sh_mem", 0),
            "committed": m.get("committed", 0), "commit_limit": m.get("commit_limit", 0),
            "swap_total": m.get("swap_total", 0),
            "swap_used": m.get("swap_total", 0) - m.get("swap_free", 0),
            "compressed": m.get("zram_compr_size") or None,
        }

    @staticmethod
    def _disk(d: dict[str, Any]) -> dict[str, Any]:
        parts = []
        for p in (d.get("partitions") or {}).values():
            for mount in p.get("mountpoints") or []:
                parts.append({"device": p.get("devname"), "mountpoint": mount,
                              "fstype": p.get("filesystem") or "", "total": p.get("size") or 0,
                              "used": p.get("used") or 0})
        parts.sort(key=lambda p: p["mountpoint"])
        mk = d.get("temperature_milli_k")
        return {
            "id": d["id"], "model": d.get("model"),
            "type": _DISK_KIND.get(d.get("kind"), "Unknown"),
            "capacity": d.get("capacity_bytes"), "formatted": d.get("formatted_bytes"),
            "system_disk": bool(d.get("is_system")), "removable": bool(d.get("ejectable")),
            "read_bps": d.get("rx_speed_bytes_ps"), "write_bps": d.get("tx_speed_bytes_ps"),
            "read_total": d.get("rx_bytes_total"), "write_total": d.get("tx_bytes_total"),
            "busy_percent": d.get("busy_percent"), "avg_response_ms": d.get("response_time_ms"),
            "temperature_c": (mk + _MK_TO_C) / 1000 if mk else None,
            "serial": d.get("serial_number") or None, "wwn": d.get("world_wide_name") or None,
            "rotation_rpm": d.get("rotation_rate"),
            "partitions": parts,
        }

    def _net(self, n: dict[str, Any]) -> dict[str, Any]:
        kind, name = _NET_KIND.get(n.get("kind"), ("other", "Network"))
        wifi = n.get("wireless_connection") or {}
        iface = n["id"]
        if iface not in self._net_drivers:
            try:
                self._net_drivers[iface] = os.path.basename(os.readlink(f"/sys/class/net/{iface}/device/driver"))
            except OSError:
                self._net_drivers[iface] = None
        speed = n.get("max_speed_bytes_ps")
        bitrate = wifi.get("bitrate_kbps")
        return {
            "id": iface, "kind": kind, "name": name, "up": n.get("state") == 8,
            "rx_bps": n.get("rx_rate_bytes_ps"), "tx_bps": n.get("tx_rate_bytes_ps"),
            "rx_total": n.get("rx_total_bytes"), "tx_total": n.get("tx_total_bytes"),
            "mac": (n.get("hw_address") or "").lower() or None,
            "ipv4": [n["ipv4_address"]] if n.get("ipv4_address") else [],
            "ipv6": [n["ipv6_address"]] if n.get("ipv6_address") else [],
            "link_speed_mbps": int(speed * 8 / 1_000_000) if speed else None,
            "driver": self._net_drivers[iface], "device_name": n.get("device_name"),
            "ssid": wifi.get("ssid"), "signal_percent": wifi.get("signal_strength_percent"),
            "frequency_mhz": wifi.get("frequency_mhz"),
            "bitrate_mbps": bitrate // 1000 if bitrate else None,
        }

    def _gpu(self, gid: str, g: dict[str, Any]) -> dict[str, Any]:
        vendor = _VENDORS.get(g.get("vendor_id"), f"0x{g.get('vendor_id', 0):04x}")
        name = g.get("device_name") or "GPU"
        if gid not in self._gpu_drivers:
            try:
                self._gpu_drivers[gid] = os.path.basename(os.readlink(f"/sys/bus/pci/devices/{gid}/driver"))
            except OSError:
                self._gpu_drivers[gid] = None
        display = name
        for prefix in ("AMD ", "NVIDIA ", "Intel "):
            display = display.removeprefix(prefix)
        vram, shared = g.get("total_memory"), g.get("total_shared_memory")
        version = lambda v: ".".join(str(x) for x in (v.get("major"), v.get("minor"), v.get("patch")) if x is not None) if v else None  # noqa: E731
        gen, lanes = g.get("pcie_gen"), g.get("pcie_lanes")
        return {
            "id": gid, "name": display,
            "vendor": vendor, "driver": self._gpu_drivers[gid], "driver_version": None,
            "usage": g.get("utilization_percent"),
            "vram_used": g.get("used_memory"), "vram_total": vram,
            "gtt_used": g.get("used_shared_memory"), "gtt_total": shared,
            "temperature_c": g.get("temperature_c"),
            "power_w": g.get("power_draw_watts"), "power_cap_w": g.get("max_power_draw_watts"),
            "clock_mhz": g.get("clock_speed_mhz"), "clock_max_mhz": g.get("max_clock_speed_mhz"),
            "mem_clock_mhz": g.get("memory_speed_mhz"), "mem_clock_max_mhz": g.get("max_memory_speed_mhz"),
            "encode": g.get("encoder_percent"), "decode": g.get("decoder_percent"),
            "encode_decode_shared": bool(g.get("encode_decode_shared")),
            "pcie": f"PCIe {gen}.0 x{lanes}" if gen and lanes else None,
            "opengl": version(g.get("opengl_version")), "vulkan": version(g.get("vulkan_version")),
            "fan_percent": g.get("fan_speed_percent"),
            "integrated": (vendor == "Intel" and "arc" not in name.lower())
                          or (vendor == "AMD" and (vram or 0) <= 4 * 1024**3 and bool(shared)),
        }

    def _fan(self, f: dict[str, Any]) -> dict[str, Any]:
        hw = f.get("hwmon_index", 0)
        if hw not in self._hwmon_names:
            try:
                self._hwmon_names[hw] = Path(f"/sys/class/hwmon/hwmon{hw}/name").read_text().strip()
            except OSError:
                self._hwmon_names[hw] = f"hwmon{hw}"
        mk, pwm = f.get("temp_amount"), f.get("pwm_percent")
        return {
            "id": f"hwmon{hw}:{f.get('fan_index')}", "name": self._hwmon_names[hw],
            "label": f.get("fan_label"), "rpm": f.get("rpm", 0),
            "pwm_percent": pwm * 100 if pwm is not None else None,
            "temperature_c": (mk + _MK_TO_C) / 1000 if mk else None,
            "max_rpm": f.get("max_rpm"),
        }

    @staticmethod
    def _battery(b: dict[str, Any]) -> dict[str, Any]:
        state = _BATTERY_STATE.get(b.get("state"), "Unknown")
        wh = lambda v: v / 1000 if v else None  # noqa: E731  (mWh → Wh)
        remaining = b.get("time_to_full") if state == "Charging" else b.get("time_to_empty")
        return {
            "id": b.get("name"), "model": b.get("model"), "manufacturer": b.get("vendor"),
            "technology": _BATTERY_TECH.get(b.get("technology")),
            "percent": (b.get("percentage") or 0) * 100, "state": state,
            "power_w": abs(b["power"]) if b.get("power") is not None else None,
            "energy_now_wh": wh(b.get("energy")), "energy_full_wh": wh(b.get("energy_full")),
            "energy_design_wh": wh(b.get("energy_full_design")),
            "health_percent": b["capacity"] * 100 if b.get("capacity") is not None else None,
            "cycles": b.get("charge_cycles"), "voltage_v": b.get("voltage"),
            "time_remaining_s": remaining or None,
            "ac_online": state in ("Charging", "Full", "Not charging"),
            "temperature_c": b.get("temp"),
            "charge_limit": b.get("charge_end_threshold"),
        }


class MagpieProcessSampler:
    """Drop-in replacement for ProcessSampler + AppResolver backed by magpie."""

    def __init__(self, client: MagpieClient) -> None:
        self._client = client
        self._logical = os.cpu_count() or 1
        self._owners: dict[int, tuple[str, str]] = {}   # pid -> (name, user)
        self._users: dict[int, str] = {}
        self._icons: dict[str, str] = {}
        self._apps: list[dict[str, Any]] = []
        self._resolves = 0
        self._icon_dir = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "refract" / "icons"

    def _lookup_owners(self, procs: list[tuple[int, str]]) -> None:
        """Fill in owners for processes not seen before (pid reuse: name changed)."""
        new = [(pid, name) for pid, name in procs
               if pid not in self._owners or self._owners[pid][0] != name]
        if not new:
            return
        if sandbox.IN_FLATPAK:
            # /proc in here only shows the sandbox: ask the host, one call for all.
            try:
                out = subprocess.run(
                    sandbox.host(["stat", "-c", "%U %n", *(f"/proc/{pid}" for pid, _ in new)]),
                    capture_output=True, text=True, timeout=5).stdout
            except (OSError, subprocess.TimeoutExpired):
                return
            users = {int(path.rsplit("/", 1)[1]): user
                     for user, _, path in (line.partition(" ") for line in out.splitlines())
                     if path.startswith("/proc/") and path[6:].isdigit()}
            for pid, name in new:
                if pid in users:
                    self._owners[pid] = (name, users[pid])
            return
        import pwd
        for pid, name in new:
            try:
                uid = os.stat(f"/proc/{pid}").st_uid
            except OSError:
                continue
            if uid not in self._users:
                try:
                    self._users[uid] = pwd.getpwuid(uid).pw_name
                except KeyError:
                    self._users[uid] = str(uid)
            self._owners[pid] = (name, self._users[uid])

    def sample(self) -> list[dict[str, Any]]:
        reply = _dig(self._client.call({"get_processes": {"request": {"process_map": {}}}}),
                     "processes", "response", "processes", "processes") or {}
        self._lookup_owners([(p["pid"], p.get("name") or "") for p in reply.values()])
        rows = []
        for p in reply.values():
            stats = p.get("usage_stats") or {}
            pid = p["pid"]
            gpu_mem = stats.get("gpu_memory_usage")
            rows.append({
                "pid": pid, "ppid": p.get("parent", 0), "name": p.get("name") or "?",
                "cmdline": " ".join(p.get("cmd") or []), "exe": p.get("exe") or None,
                "user": self._owners.get(pid, ("", ""))[1],
                "state": _PROC_STATE.get(p.get("state"), "Unknown"),
                "threads": p.get("task_count", 0), "nice": None, "start_time": None,
                # magpie reports percent of one core; the UI uses the whole machine
                "cpu": (stats.get("cpu_usage") or 0.0) / self._logical,
                "memory": stats.get("memory_usage", 0), "shared_memory": 0,
                "disk_read_bps": stats.get("disk_usage") or 0.0, "disk_write_bps": 0.0,
                "network_bps": stats.get("network_usage") or 0.0,
                "gpu": stats.get("gpu_usage"), "gpu_memory": gpu_mem or None,
                "cgroup": "", "app_id": None, "start_ticks": None,
            })
        live = {r["pid"] for r in rows}
        self._owners = {pid: v for pid, v in self._owners.items() if pid in live}
        return rows

    def resolve(self, processes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Which processes belong to which app changes rarely, and asking magpie
        # costs it a second full process scan — so only now and then. Usage is
        # summed from the fresh process list either way.
        if self._resolves % _APPS_EVERY == 0 or not self._apps:
            self._apps = _dig(self._client.call({"get_apps": {}}), "apps", "response", "apps", "apps") or []
        self._resolves += 1
        apps = self._apps
        missing = [a["id"] for a in apps if a["id"] not in self._icons]
        if missing:
            self._fetch_icons(missing)
        by_pid = {p["pid"]: p for p in processes}
        out = []
        for a in apps:
            members = [by_pid[pid] for pid in a.get("pids") or [] if pid in by_pid]
            if not members:
                continue
            for m in members:
                m["app_id"] = a["id"]
            total = lambda k: sum(m.get(k) or 0 for m in members)  # noqa: E731
            gpus = [m["gpu"] for m in members if m.get("gpu") is not None]
            gmem = [m["gpu_memory"] for m in members if m.get("gpu_memory")]
            out.append({
                "id": a["id"], "name": a.get("name") or a["id"], "icon": self._icons.get(a["id"], ""),
                "pids": [m["pid"] for m in members],
                "cpu": total("cpu"), "memory": total("memory"), "shared_memory": 0,
                "disk_read_bps": total("disk_read_bps"), "disk_write_bps": 0.0,
                "gpu": sum(gpus) if gpus else None, "gpu_memory": sum(gmem) if gmem else None,
            })
        return sorted(out, key=lambda a: a["name"].casefold())

    def _fetch_icons(self, ids: list[str]) -> None:
        pairs = _dig(self._client.call({"get_apps_icons": {"app_ids": ids}}),
                     "app_icons", "response", "values", "pairs") or {}
        for app_id in ids:
            icon = (pairs.get(app_id) or {}).get("icon") or {}
            if "id" in icon:
                self._icons[app_id] = icon["id"]
            elif "data" in icon and icon["data"]:
                data = bytes(icon["data"])
                ext = ".png" if data.startswith(b"\x89PNG") else ".svg" if b"<svg" in data[:4096] else ".img"
                self._icon_dir.mkdir(parents=True, exist_ok=True)
                path = self._icon_dir / f"{app_id}{ext}"
                path.write_bytes(data)
                self._icons[app_id] = str(path)
            else:
                self._icons[app_id] = ""
