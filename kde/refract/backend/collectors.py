"""Linux system telemetry collectors. No UI dependency."""
from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path

import psutil

from .. import sandbox


def _read(path: str | Path) -> str | None:
    try:
        return Path(path).read_text(errors="replace").strip()
    except (OSError, ValueError):
        return None


def _number(path: str | Path, scale: float = 1) -> float | None:
    try:
        return float(_read(path)) / scale
    except (TypeError, ValueError):
        return None


def _integer(path: str | Path) -> int | None:
    value = _number(path)
    return int(value) if value is not None else None


def _entries(path: str | Path) -> list[Path]:
    try:
        return list(Path(path).iterdir())
    except OSError:
        return []


def _pci_index() -> dict[tuple[str, str], str]:
    result = {}
    for filename in ('/usr/share/hwdata/pci.ids', '/usr/share/misc/pci.ids'):
        try:
            with open(filename, encoding='utf-8', errors='replace') as file:
                vendor = None
                for line in file:
                    if re.match(r'^[0-9a-fA-F]{4}  ', line):
                        vendor = line[:4].lower()
                    elif vendor and re.match(r'^\t[0-9a-fA-F]{4}  ', line):
                        result[(vendor, line[1:5].lower())] = line[7:].strip()
            if result:
                break
        except OSError:
            pass
    return result


def _pretty_pci(name: str) -> str:
    groups = re.findall(r'\[([^]]+)\]', name)
    if groups:
        return groups[-1].split('/')[-1].strip()
    return name


def _cpu_times() -> list[list[int]]:
    text = _read('/proc/stat') or ''
    return [[int(x) for x in line.split()[1:]] for line in text.splitlines()
            if re.match(r'^cpu\d*\s', line)]


def _cpu_percent(old: list[int], new: list[int]) -> tuple[float, float]:
    # Only the first 8 fields: guest and guest_nice are already counted in
    # user and nice, so including them would double-count VM time.
    delta = [max(0, b-a) for a, b in zip(old[:8], new[:8])]
    total = sum(delta)
    if not total:
        return 0.0, 0.0
    idle = delta[3] + (delta[4] if len(delta) > 4 else 0)
    kernel = sum(delta[i] for i in (2, 5, 6) if i < len(delta))
    return min(100., 100 * (total-idle)/total), min(100., 100 * kernel/total)


def _meminfo() -> dict[str, int]:
    result = {}
    for line in (_read('/proc/meminfo') or '').splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            try:
                result[key] = int(value.split()[0]) * 1024
            except (IndexError, ValueError):
                pass
    return result


def _cache_sizes() -> dict[str, int | None]:
    result: dict[str, int | None] = dict.fromkeys(('L1d', 'L1i', 'L2', 'L3'))
    seen = set()
    for cpu in _entries('/sys/devices/system/cpu'):
        if not re.fullmatch(r'cpu\d+', cpu.name):
            continue
        for entry in _entries(cpu / 'cache'):
            if not entry.name.startswith('index'):
                continue
            level, kind = _read(entry/'level'), _read(entry/'type')
            key = {'1': {'Data': 'L1d', 'Instruction': 'L1i'}, '2': {'Unified': 'L2'},
                   '3': {'Unified': 'L3'}}.get(level or '', {}).get(kind or '')
            shared = _read(entry/'shared_cpu_list') or cpu.name
            identity = (key, shared)
            if not key or identity in seen:
                continue
            seen.add(identity)
            size = _read(entry/'size') or ''
            match = re.match(r'(\d+)([KMG]?)', size)
            if match:
                amount = int(match[1]) * {'': 1, 'K': 1024, 'M': 1048576, 'G': 1073741824}[match[2]]
                result[key] = (result[key] or 0) + amount
    return result


def _temperature() -> float | None:
    for preferred in ('k10temp', 'coretemp'):
        for chip in _entries('/sys/class/hwmon'):
            if _read(chip/'name') == preferred:
                for index in range(1, 10):
                    label = (_read(chip/f'temp{index}_label') or '').lower()
                    if 'tctl' in label or 'package' in label or index == 1:
                        value = _number(chip/f'temp{index}_input', 1000)
                        if value is not None:
                            return value
    for zone in _entries('/sys/class/thermal'):
        if zone.name.startswith('thermal_zone'):
            value = _number(zone/'temp', 1000)
            if value is not None and 0 < value < 130:
                return value
    return None


def _disk_parents(device: str, seen: set[str] | None = None) -> set[str]:
    seen = seen or set()
    name = os.path.basename(device)
    if name in seen:
        return set()
    seen.add(name)
    path = Path('/sys/class/block') / name
    if not path.exists():
        return set()
    slaves = _entries(path/'slaves')
    if slaves:
        result = set()
        for slave in slaves:
            result.update(_disk_parents(slave.name, seen))
        return result
    if (path/'partition').exists():
        try:
            return {path.resolve().parent.name}
        except OSError:
            return set()
    return {name}


def _disk_type(name: str, path: Path) -> str:
    if name.startswith('nvme'):
        return 'NVMe'
    if name.startswith('sr'):
        return 'Optical'
    if name.startswith('mmcblk'):
        return 'SD'
    try:
        if 'usb' in str((path/'device').resolve()).lower():
            return 'USB'
    except OSError:
        pass
    rotational = _read(path/'queue/rotational')
    return {'0': 'SSD', '1': 'HDD'}.get(rotational, 'Unknown')


def _hwmon_for(path: Path) -> list[Path]:
    result = []
    for parent in (path/'device', path/'device/device', path):
        result.extend(p for p in _entries(parent/'hwmon') if p.name.startswith('hwmon'))
        result.extend(p for p in _entries(parent) if p.name.startswith('hwmon'))
    return result


def _gpu_clocks(path: Path, filename: str) -> tuple[float | None, float | None]:
    values = []
    current = None
    for line in (_read(path/filename) or '').splitlines():
        match = re.search(r'(\d+(?:\.\d+)?)\s*(MHz|GHz)', line, re.I)
        if match:
            value = float(match[1]) * (1000 if match[2].lower() == 'ghz' else 1)
            values.append(value)
            if '*' in line:
                current = value
    return current, max(values) if values else None


class SystemSampler:
    """Collect current system telemetry; deltas belong to this instance."""

    def __init__(self) -> None:
        self._pci = _pci_index()
        self._static: dict | None = None
        self._previous_cpu = _cpu_times()
        self._previous_disk: dict[str, list[int]] = {}
        self._previous_net: dict[str, tuple[int, int]] = {}
        self._previous_time = time.monotonic()
        self._nm_time = 0.0
        self._nm_cache: dict[str, dict] = {}
        self._net_names: dict[str, str | None] = {}
        self._gpu_static: dict[str, dict] = {}
        self._mounts_time = 0.0
        self._mounts: dict[str, list[dict]] = {}
        self._system_disks: set[str] = set()
        self._nvidia_command = shutil.which('nvidia-smi')
        self._nvidia_process: subprocess.Popen | None = None
        self._nvidia_started = 0.0
        self._nvidia_next = 0.0
        self._nvidia_rows: list[list[str]] = []

    def _nvidia(self, now: float) -> list[list[str]]:
        """Poll nvidia-smi without blocking the sampling deadline."""
        fields = ('name,utilization.gpu,memory.used,memory.total,temperature.gpu,'
                  'power.draw,power.limit,clocks.gr,clocks.max.gr,clocks.mem,'
                  'clocks.max.mem,utilization.encoder,utilization.decoder,driver_version')
        process = self._nvidia_process
        if process is not None and process.poll() is not None:
            try:
                output, _ = process.communicate(timeout=0)
                if process.returncode == 0:
                    self._nvidia_rows = [[x.strip() for x in line.split(',')] for line in output.splitlines()]
                else:
                    self._nvidia_rows = []
            except (OSError, subprocess.TimeoutExpired):
                self._nvidia_rows = []
            self._nvidia_process = None
        elif process is not None and now-self._nvidia_started > 2:
            process.kill()
            process.wait()
            self._nvidia_process = None
            self._nvidia_rows = []
        if self._nvidia_command and self._nvidia_process is None and now >= self._nvidia_next:
            try:
                self._nvidia_process = subprocess.Popen(
                    [self._nvidia_command,f'--query-gpu={fields}','--format=csv,noheader,nounits'],
                    stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
                self._nvidia_started = now
                self._nvidia_next = now+2
            except OSError:
                self._nvidia_next = now+30
        return self._nvidia_rows

    def static_info(self) -> dict:
        """Return cached hardware and operating system metadata."""
        if self._static is not None:
            return self._static
        cpuinfo = _read('/proc/cpuinfo') or ''
        sections = [s for s in cpuinfo.split('\n\n') if s.strip()]
        first = dict(line.split(':', 1) for line in sections[0].splitlines() if ':' in line) if sections else {}
        first = {k.strip(): v.strip() for k, v in first.items()}
        physical = {dict((k.strip(), v.strip()) for k, v in (line.split(':',1) for line in s.splitlines() if ':' in line)).get('physical id') for s in sections}
        cores = set()
        for s in sections:
            fields = dict((k.strip(), v.strip()) for k, v in (line.split(':',1) for line in s.splitlines() if ':' in line))
            cores.add((fields.get('physical id', '0'), fields.get('core id', fields.get('processor'))))
        os_name = None
        for line in (_read(sandbox.OS_RELEASE) or '').splitlines():
            if line.startswith('PRETTY_NAME='):
                os_name = line.partition('=')[2].strip('"')
        desktop = None
        if sandbox.IN_FLATPAK or shutil.which('plasmashell'):
            try:
                desktop = subprocess.run(sandbox.host(['plasmashell','--version']), capture_output=True, text=True, timeout=2).stdout.strip() or None
                if desktop:
                    desktop = desktop.replace('plasmashell', 'KDE Plasma')
            except (OSError, subprocess.TimeoutExpired):
                pass
        cpufreq = Path('/sys/devices/system/cpu/cpu0/cpufreq')
        flags = first.get('flags', '').split()
        self._static = {
            'hostname': socket.gethostname(), 'os_name': os_name or 'Linux', 'kernel': os.uname().release,
            'desktop': desktop, 'cpu_name': first.get('model name', 'Unknown'),
            'sockets': len(physical) or 1, 'cores': len(cores) or os.cpu_count() or 1,
            'logical': os.cpu_count() or len(sections) or 1,
            'base_mhz': _number(cpufreq/'base_frequency', 1000),
            'max_mhz': _number(cpufreq/'cpuinfo_max_freq', 1000),
            'virtualization': 'AMD-V' if 'svm' in flags else 'VT-x' if 'vmx' in flags else None,
            'is_vm': 'hypervisor' in flags, 'cache': _cache_sizes(),
            'cpu_driver': _read(cpufreq/'scaling_driver'),
            'governor': _read(cpufreq/'scaling_governor'),
            'energy_preference': _read(cpufreq/'energy_performance_preference'),
            'memory_total': _meminfo().get('MemTotal', 0),
        }
        return self._static

    def _refresh_mounts(self, now: float) -> None:
        if now - self._mounts_time < 10:
            return
        mounts: dict[str, list[dict]] = {}
        systems = set()
        for line in (_read('/proc/mounts') or '').splitlines():
            parts = line.split()
            if len(parts) < 3 or not parts[0].startswith('/dev/'):
                continue
            device, mount, fstype = parts[:3]
            mount = mount.replace('\\040', ' ')
            parents = _disk_parents(device)
            if mount == '/':
                systems.update(parents)
            try:
                stats = os.statvfs(mount)
                total = stats.f_blocks * stats.f_frsize
                used = (stats.f_blocks - stats.f_bfree) * stats.f_frsize
            except OSError:
                continue
            row = {'device': device, 'mountpoint': mount, 'fstype': fstype, 'total': total, 'used': used}
            for parent in parents:
                mounts.setdefault(parent, []).append(row)
        self._mounts, self._system_disks, self._mounts_time = mounts, systems, now

    def _nm(self, now: float) -> dict[str, dict]:
        if now - self._nm_time < 5:
            return self._nm_cache
        self._nm_time = now
        # Runs on the sampling thread, so every call is short and bounded; a
        # hung NetworkManager must not stall the CPU/memory graphs.
        result = {}
        t = 0.3
        try:
            import dbus
            bus = dbus.SystemBus()
            service = 'org.freedesktop.NetworkManager'
            nm = dbus.Interface(bus.get_object(service, '/org/freedesktop/NetworkManager', introspect=False), service)
            for device_path in nm.GetDevices(timeout=t):
                obj = bus.get_object(service, device_path, introspect=False)
                props = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
                iface = str(props.Get(f'{service}.Device', 'Interface', timeout=t))
                if str(props.Get(f'{service}.Device', 'DeviceType', timeout=t)) != '2':
                    continue
                wifi = f'{service}.Device.Wireless'
                ap_path = str(props.Get(wifi, 'ActiveAccessPoint', timeout=t))
                data: dict = {'bitrate_mbps': int(props.Get(wifi, 'Bitrate', timeout=t)) // 1000 or None}
                if ap_path != '/':
                    ap = dbus.Interface(bus.get_object(service, ap_path, introspect=False), 'org.freedesktop.DBus.Properties')
                    group = f'{service}.AccessPoint'
                    data.update(ssid=bytes(ap.Get(group, 'Ssid', timeout=t)).decode('utf-8','replace'),
                                signal_percent=int(ap.Get(group, 'Strength', timeout=t)),
                                frequency_mhz=int(ap.Get(group, 'Frequency', timeout=t)))
                result[iface] = data
        except Exception:
            return self._nm_cache
        self._nm_cache = result
        return result

    def _gpu_info(self, card: Path) -> dict:
        if card.name in self._gpu_static:
            return self._gpu_static[card.name]
        device = card/'device'
        vendor_id = (_read(device/'vendor') or '').removeprefix('0x').lower()
        device_id = (_read(device/'device') or '').removeprefix('0x').lower()
        vendor = {'1002': 'AMD', '10de': 'NVIDIA', '8086': 'Intel'}.get(vendor_id, vendor_id)
        name = _pretty_pci(self._pci.get((vendor_id, device_id), f'{vendor} GPU'))
        driver_path = device/'driver'
        try:
            driver = driver_path.resolve().name if driver_path.exists() else None
        except OSError:
            driver = None
        info = {'id': card.name, 'name': name, 'vendor': vendor, 'driver': driver,
                'driver_version': _read(Path('/sys/module')/driver/'version') if driver else None,
                'integrated': (vendor == 'Intel' and 'arc' not in name.lower()) or (vendor == 'AMD' and
                               (_integer(device/'mem_info_vram_total') or 0) <= 4*1024**3
                               and (device/'mem_info_gtt_total').exists())}
        self._gpu_static[card.name] = info
        return info

    def sample(self) -> dict:
        """Return one complete system snapshot with rates since the prior call."""
        now = time.monotonic()
        elapsed = max(now - self._previous_time, 1e-6)
        current = _cpu_times()
        percentages = [_cpu_percent(a,b) for a,b in zip(self._previous_cpu,current)]
        self._previous_cpu, self._previous_time = current, now
        cpufreq = Path('/sys/devices/system/cpu')
        freqs = [_number(cpufreq/f'cpu{i}/cpufreq/scaling_cur_freq', 1000) for i in range(self.static_info()['logical'])]
        per_freq = [float(v) for v in freqs] if freqs and all(v is not None for v in freqs) else None
        # process count and total threads are current values, not the cumulative fork counter.
        pid_dirs = [p for p in _entries('/proc') if p.name.isdigit()]
        loadavg = (_read('/proc/loadavg') or '').split()
        try:
            threads = int(loadavg[3].split('/')[1])
        except (IndexError, ValueError):
            threads = 0
        file_nr = (_read('/proc/sys/fs/file-nr') or '').split()
        mem = _meminfo()
        total, available = mem.get('MemTotal',0), mem.get('MemAvailable',0)
        zram = [(_read(z/'mm_stat') or '').split() for z in _entries('/sys/block') if z.name.startswith('zram')]
        compressed = sum(int(v[1]) for v in zram if len(v)>1 and v[1].isdigit()) if zram else None
        cpu = {'usage': percentages[0][0] if percentages else 0., 'kernel_usage': percentages[0][1] if percentages else 0.,
               'per_core': [p[0] for p in percentages[1:]],
               'freq_mhz': sum(per_freq)/len(per_freq) if per_freq else None, 'per_core_freq_mhz': per_freq,
               'processes': len(pid_dirs), 'threads': threads, 'handles': int(file_nr[0]) if file_nr else None,
               'uptime_s': float((_read('/proc/uptime') or '0').split()[0]), 'temperature_c': _temperature(),
               'governor': _read(cpufreq/'cpu0/cpufreq/scaling_governor')}
        memory = {'total': total, 'used': max(0,total-available), 'available': available, 'free': mem.get('MemFree',0),
                  'cached': mem.get('Cached',0)+mem.get('SReclaimable',0), 'buffers': mem.get('Buffers',0),
                  'dirty': mem.get('Dirty',0), 'shared': mem.get('Shmem',0), 'committed': mem.get('Committed_AS',0),
                  'commit_limit': mem.get('CommitLimit',0), 'swap_total': mem.get('SwapTotal',0),
                  'swap_used': mem.get('SwapTotal',0)-mem.get('SwapFree',0), 'compressed': compressed}
        self._refresh_mounts(now)
        disks = []
        for path in _entries('/sys/block'):
            name = path.name
            if name.startswith(('loop','ram','zram','dm-','md','nbd')):
                continue
            stats = [int(v) for v in (_read(path/'stat') or '').split() if v.isdigit()]
            old = self._previous_disk.get(name)
            self._previous_disk[name] = stats
            delta = [max(0,a-b) for a,b in zip(stats,old)] if old else []
            ios = (delta[0]+delta[4]) if len(delta)>9 else 0
            partitions = self._mounts.get(name,[])
            temp = next((v for hw in _hwmon_for(path) if (v:=_number(hw/'temp1_input',1000)) is not None),None)
            disks.append({'id': name, 'model': _read(path/'device/model'), 'type': _disk_type(name,path),
                          'capacity': (_integer(path/'size') or 0)*512,
                          'formatted': sum(p['total'] for p in {p['device']:p for p in partitions}.values()) if partitions else None,
                          'system_disk': name in self._system_disks, 'removable': _read(path/'removable')=='1',
                          'read_bps': delta[2]*512/elapsed if len(delta)>9 else 0.,
                          'write_bps': delta[6]*512/elapsed if len(delta)>9 else 0.,
                          'busy_percent': min(100.,delta[9]/(elapsed*10)) if len(delta)>9 else 0.,
                          'avg_response_ms': (delta[3]+delta[7])/ios if ios else None,
                          'temperature_c': temp, 'partitions': partitions})
        network = []
        nm = self._nm(now)
        try:
            addresses = psutil.net_if_addrs()
        except (OSError, PermissionError):
            addresses = {}
        try:
            counters = psutil.net_io_counters(pernic=True)
        except (OSError, PermissionError):
            counters = {}
            for line in (_read('/proc/net/dev') or '').splitlines()[2:]:
                if ':' not in line:
                    continue
                iface, values = line.split(':', 1)
                fields = values.split()
                if len(fields) >= 9:
                    counters[iface.strip()] = (int(fields[0]), int(fields[8]))
        for path in _entries('/sys/class/net'):
            name = path.name
            if name == 'lo':
                continue
            # Virtual bridges and containers are hidden; active tunnels remain visible.
            virtual = '/devices/virtual/net/' in str(path.resolve())
            up = _read(path/'operstate') == 'up'
            if virtual and not (up and (name.startswith(('tun','tap','wg')))):
                continue
            wireless = (path/'wireless').exists() or name.startswith(('wl','wlan'))
            kind = 'wifi' if wireless else 'vpn' if virtual else 'ethernet' if (path/'device').exists() else 'other'
            human = {'wifi':'Wi-Fi','vpn':'VPN','ethernet':'Ethernet','other':'Network'}[kind]
            c = counters.get(name)
            rx, tx = ((c.bytes_recv,c.bytes_sent) if hasattr(c, 'bytes_recv') else c) if c else (0,0)
            if c is None:
                rx, tx = _integer(path/'statistics/rx_bytes') or 0, _integer(path/'statistics/tx_bytes') or 0
            old = self._previous_net.get(name)
            self._previous_net[name] = rx,tx
            addr = addresses.get(name,[])
            ipv4 = [a.address for a in addr if a.family == socket.AF_INET]
            ipv6 = [a.address.split('%')[0] for a in addr if a.family == socket.AF_INET6]
            device = path/'device'
            if name not in self._net_names:
                ven = (_read(device/'vendor') or '').removeprefix('0x')
                dev = (_read(device/'device') or '').removeprefix('0x')
                self._net_names[name] = self._pci.get((ven,dev))
            speed = _integer(path/'speed')
            driver = device/'driver'
            mac = _read(path/'address')
            network.append({'id': name, 'kind': kind, 'name': human, 'up': up,
                            'rx_bps': max(0,rx-old[0])/elapsed if old else 0.,
                            'tx_bps': max(0,tx-old[1])/elapsed if old else 0.,
                            'rx_total': rx, 'tx_total': tx, 'mac': mac, 'ipv4': ipv4, 'ipv6': ipv6,
                            'link_speed_mbps': speed if speed and speed>0 else None,
                            'driver': driver.resolve().name if driver.exists() else None,
                            'device_name': self._net_names[name],
                            'ssid': nm.get(name,{}).get('ssid'), 'signal_percent': nm.get(name,{}).get('signal_percent'),
                            'frequency_mhz': nm.get(name,{}).get('frequency_mhz'),
                            'bitrate_mbps': nm.get(name,{}).get('bitrate_mbps')})
        gpus = []
        nvidia_rows = self._nvidia(now)
        nvidia_index = 0
        for card in _entries('/sys/class/drm'):
            if not re.fullmatch(r'card\d+',card.name):
                continue
            device = card/'device'
            data = dict(self._gpu_info(card))
            hw = _hwmon_for(card)
            def hw_value(file: str, scale: float = 1) -> float | None:
                return next((v for p in hw if (v:=_number(p/file,scale)) is not None),None)
            clock, clock_max = _gpu_clocks(device,'pp_dpm_sclk')
            mem_clock, mem_max = _gpu_clocks(device,'pp_dpm_mclk')
            if clock is None:
                clock = hw_value('freq1_input',1e6)
            width = _read(device/'current_link_width')
            speed_text = _read(device/'current_link_speed')
            generation = {'2.5':'1.0','5.0':'2.0','8.0':'3.0','16.0':'4.0',
                          '32.0':'5.0','64.0':'6.0'}.get((speed_text or '').split(' ')[0])
            pcie = f'PCIe {generation} x{width}' if width and generation else None
            data.update(usage=_number(device/'gpu_busy_percent'),
                        vram_used=_integer(device/'mem_info_vram_used'), vram_total=_integer(device/'mem_info_vram_total'),
                        gtt_used=_integer(device/'mem_info_gtt_used'), gtt_total=_integer(device/'mem_info_gtt_total'),
                        temperature_c=hw_value('temp1_input',1000),
                        power_w=hw_value('power1_average',1e6) or hw_value('power1_input',1e6),
                        power_cap_w=hw_value('power1_cap',1e6), clock_mhz=clock, clock_max_mhz=clock_max,
                        mem_clock_mhz=mem_clock, mem_clock_max_mhz=mem_max,
                        encode=None,decode=None,pcie=pcie)
            if data['vendor'] == 'NVIDIA':
                fields = nvidia_rows[nvidia_index] if nvidia_index < len(nvidia_rows) else []
                nvidia_index += 1
                def nv(index: int) -> float | None:
                    try:
                        return float(fields[index])
                    except (IndexError, ValueError):
                        return None
                if len(fields) >= 14:
                    data.update(name=fields[0] or data['name'],usage=nv(1),
                                vram_used=int(nv(2)*1048576) if nv(2) is not None else None,
                                vram_total=int(nv(3)*1048576) if nv(3) is not None else None,
                                temperature_c=nv(4),power_w=nv(5),power_cap_w=nv(6),
                                clock_mhz=nv(7),clock_max_mhz=nv(8),mem_clock_mhz=nv(9),
                                mem_clock_max_mhz=nv(10),encode=nv(11),decode=nv(12),
                                driver_version=fields[13] or data['driver_version'])
            gpus.append(data)
        fans = []
        for chip in _entries('/sys/class/hwmon'):
            chip_name = _read(chip/'name') or chip.name
            for fan in _entries(chip):
                match = re.fullmatch(r'fan(\d+)_input', fan.name)
                if not match:
                    continue
                index = match[1]
                rpm = _integer(fan)
                if rpm is None:
                    continue
                pwm = _number(chip/f'pwm{index}')
                fans.append({'id': f'{chip_name}:{index}', 'name': chip_name,
                             'label': _read(chip/f'fan{index}_label'), 'rpm': rpm,
                             'pwm_percent': pwm*100/255 if pwm is not None else None,
                             'temperature_c': _number(chip/f'temp{index}_input',1000) or _number(chip/'temp1_input',1000)})
        ac_values = [_read(p/'online') for p in _entries('/sys/class/power_supply') if _read(p/'type') in ('Mains','USB','USB_C') and (p/'online').exists()]
        ac = any(v=='1' for v in ac_values) if ac_values else None
        batteries = []
        for bat in _entries('/sys/class/power_supply'):
            if _read(bat/'type') != 'Battery' or _read(bat/'scope') == 'Device':
                continue
            state = (_read(bat/'status') or 'Unknown').title()
            energy_now = _number(bat/'energy_now',1e6)
            energy_full = _number(bat/'energy_full',1e6)
            energy_design = _number(bat/'energy_full_design',1e6)
            voltage = _number(bat/'voltage_now',1e6)
            if energy_now is None and voltage is not None:
                charge = _number(bat/'charge_now',1e6)
                energy_now = charge*voltage if charge is not None else None
            if energy_full is None and voltage is not None:
                charge = _number(bat/'charge_full',1e6)
                energy_full = charge*voltage if charge is not None else None
            power = _number(bat/'power_now',1e6)
            if power is None:
                current = _number(bat/'current_now',1e6)
                power = current*voltage if current is not None and voltage is not None else None
            power = abs(power) if power is not None else None
            remaining = ((energy_now if state=='Discharging' else max(0,(energy_full or 0)-(energy_now or 0))) *3600/power
                         if power and energy_now is not None and (state=='Discharging' or energy_full is not None) else None)
            percent = _number(bat/'capacity')
            if percent is None:
                percent = 100*energy_now/energy_full if energy_now is not None and energy_full else 0.
            batteries.append({'id': bat.name, 'model': _read(bat/'model_name'), 'manufacturer': _read(bat/'manufacturer'),
                              'technology': _read(bat/'technology'), 'percent': percent, 'state': state,
                              'power_w': power, 'energy_now_wh': energy_now, 'energy_full_wh': energy_full,
                              'energy_design_wh': energy_design,
                              'health_percent': 100*energy_full/energy_design if energy_full is not None and energy_design else None,
                              'cycles': _integer(bat/'cycle_count'), 'voltage_v': voltage,
                              'time_remaining_s': remaining, 'ac_online': ac})
        return {'timestamp': now, 'cpu': cpu, 'memory': memory, 'disks': disks, 'network': network,
                'gpus': gpus, 'fans': fans, 'batteries': batteries}
