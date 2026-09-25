"""Fast process snapshots and desktop application grouping."""
from __future__ import annotations

import configparser
import os
import pwd
import re
import signal
import subprocess
import time
from pathlib import Path

from .collectors import _read, _entries

_PAGE = os.sysconf('SC_PAGE_SIZE')
_HZ = os.sysconf('SC_CLK_TCK')
_STATE = {'R':'Running','S':'Sleeping','D':'Disk sleep','T':'Stopped','t':'Stopped',
          'Z':'Zombie','X':'Dead','I':'Idle','P':'Parked'}
_BACKGROUND = ('org.kde.kalendarac', 'org.kde.xwaylandvideobridge',
               'org.kde.kdeconnect.daemon', 'polkit', 'xdg-desktop-portal')
_APP_COMPONENT = re.compile(r'^app-(.+)\.(?:scope|service)$')


def _app_id(cgroup: str) -> str | None:
    matches = [_APP_COMPONENT.match(p) for p in cgroup.split('/')]
    found = next((m.group(1) for m in reversed(matches) if m), None)
    if not found:
        return None
    for prefix in ('flatpak-', 'gnome-', 'kde-'):
        if found.startswith(prefix):
            found = found[len(prefix):]
            break
    found = re.sub(r'@.*$', '', found)
    found = re.sub(r'-\d+$', '', found)
    return re.sub(r'\\x2d', '-', found) or None


def _uid_name(uid: int, cache: dict[int,str]) -> str:
    if uid not in cache:
        try:
            cache[uid] = pwd.getpwuid(uid).pw_name
        except KeyError:
            cache[uid] = str(uid)
    return cache[uid]


def _process_gpu(pid: int, prior: dict[tuple[int,int],tuple[int,int]], elapsed: float,
                 known_fds: set[str] | None) -> tuple[float | None,int | None,dict[tuple[int,int],tuple[int,int]],set[str]]:
    """Read DRM fdinfo, deduplicating duplicated descriptors by client id."""
    clients: dict[int,tuple[int,int]] = {}
    paths = ([Path(f'/proc/{pid}/fdinfo')/fd for fd in known_fds]
             if known_fds is not None else _entries(f'/proc/{pid}/fdinfo'))
    found_fds = set()
    for path in paths:
        try:
            text = path.read_text(errors='replace')
        except OSError:
            continue
        match = re.search(r'^drm-client-id:\s*(\d+)',text,re.M)
        if not match:
            continue
        found_fds.add(path.name)
        client = int(match[1])
        engines = sum(int(v) for v in re.findall(r'^drm-engine-[^:]+:\s*(\d+)\s+ns',text,re.M))
        memory = re.search(r'^drm-(?:memory|total)-vram:\s*(\d+)\s+KiB',text,re.M)
        clients[client] = (engines,int(memory[1])*1024 if memory else 0)
    if not clients:
        return None,None,{},found_fds
    fresh = {(pid,cid): vals for cid,vals in clients.items()}
    gpu = sum(max(0,vals[0]-prior.get((pid,cid),vals)[0]) for cid,vals in clients.items())/(elapsed*1e7)
    return min(100.,gpu),sum(v[1] for v in clients.values()),fresh,found_fds


class ProcessSampler:
    """Read all visible processes and compute per process rates."""

    def __init__(self) -> None:
        self._prev: dict[int,tuple[int,int,int]] = {}
        self._gpu_prev: dict[tuple[int,int],tuple[int,int]] = {}
        self._gpu_cached: dict[int,tuple[float | None,int | None]] = {}
        self._drm_fds: dict[int,set[str]] = {}
        self._tick = 0
        self._last = time.monotonic()
        self._uid_cache: dict[int,str] = {}
        self._boot = time.time() - float((_read('/proc/uptime') or '0').split()[0])
        self._logical = os.cpu_count() or 1
        self._my_uid = os.getuid()
        self._fixed: dict[int,tuple] = {}
        self._io_denied: set[int] = set()

    def _read_fixed(self, proc: Path, comm: str) -> tuple:
        """Per-process data that is constant for the process lifetime."""
        try:
            argv = (proc/'cmdline').read_bytes().split(b'\0')
            cmdline = ' '.join(x.decode(errors='replace') for x in argv if x)
        except OSError:
            argv,cmdline = [],''
        try:
            exe = os.readlink(proc/'exe')
        except OSError:
            exe = None
        name = comm
        if len(comm)>=15:
            candidate = os.path.basename((exe or '').removesuffix(' (deleted)')) or (os.path.basename(os.fsdecode(argv[0])) if argv and argv[0] else '')
            if candidate.startswith(comm) or len(candidate)>len(comm):
                name = candidate
        try:
            cg = next((line[3:] for line in (proc/'cgroup').read_text().splitlines() if line.startswith('0::')),'')
        except OSError:
            cg = ''
        try:
            uid = proc.stat().st_uid
        except OSError:
            uid = -1
        return name, cmdline, exe, cg, uid, _app_id(cg)

    def sample(self) -> list[dict]:
        """Return visible processes; CPU is percent of the entire machine."""
        now = time.monotonic()
        elapsed = max(now-self._last,1e-6)
        self._last = now
        self._tick += 1
        rows = []
        new_prev = {}
        new_fixed = {}
        new_gpu = {}
        gpu_cache = {}
        drm_fds = {}
        for proc in _entries('/proc'):
            if not proc.name.isdigit():
                continue
            pid = int(proc.name)
            try:
                raw = (proc/'stat').read_text(errors='replace')
                comm = raw[raw.index('(')+1:raw.rindex(')')]
                parts = raw[raw.rindex(')')+2:].split()
                ppid, state = int(parts[1]),_STATE.get(parts[0],parts[0])
                ticks = int(parts[11])+int(parts[12])
                nice, threads, start = int(parts[16]),int(parts[17]),int(parts[19])
                st = (proc/'statm').read_text().split()
                rss, shared = int(st[1])*_PAGE,int(st[2])*_PAGE
            except (OSError,ValueError,IndexError):
                continue
            # cmdline/exe/cgroup/owner rarely change for a running process:
            # read them once per (pid, start time, comm). exec() keeps the pid
            # and start time but renames the process, which refreshes the entry.
            fixed = self._fixed.get(pid)
            if fixed is None or fixed[0] != (start, comm):
                fixed = ((start, comm), *self._read_fixed(proc, comm))
            new_fixed[pid] = fixed
            _, name, cmdline, exe, cg, uid, app_id = fixed
            read = write = 0
            if pid not in self._io_denied:
                try:
                    io = dict((k.strip(),int(v)) for k,v in (line.split(':',1) for line in (proc/'io').read_text().splitlines() if ':' in line))
                    read,write = io.get('read_bytes',0),io.get('write_bytes',0)
                except PermissionError:
                    self._io_denied.add(pid)
                except (OSError,ValueError):
                    pass
            previous = self._prev.get(pid)
            if previous and previous[2] == start:
                cpu = min(100.,max(0,ticks-previous[0])/_HZ/elapsed*100/self._logical)
                rbps = max(0,read-previous[1])/elapsed
                wbps = max(0,write-previous[3])/elapsed if len(previous)>3 else 0.
            else:
                cpu,rbps,wbps = 0.,0.,0.
            new_prev[pid] = (ticks,read,start,write)
            if uid == self._my_uid:
                if self._tick % 2:
                    known = self._drm_fds.get(pid) if self._tick % 10 != 1 else None
                    gpu,gmem,clients,fds = _process_gpu(pid,self._gpu_prev,elapsed*2,known)
                    new_gpu.update(clients)
                    gpu_cache[pid] = gpu,gmem
                    drm_fds[pid] = fds
                else:
                    gpu,gmem = self._gpu_cached.get(pid,(None,None))
                    gpu_cache[pid] = gpu,gmem
                    drm_fds[pid] = self._drm_fds.get(pid,set())
            else:
                gpu,gmem = None,None
            rows.append({'pid':pid,'ppid':ppid,'name':name,'cmdline':cmdline,'exe':exe,
                         'user':_uid_name(uid,self._uid_cache),'state':state,'threads':threads,
                         'nice':nice,'start_time':self._boot+start/_HZ,'cpu':cpu,
                         'memory':max(0,rss-shared),'shared_memory':shared,
                         'disk_read_bps':rbps,'disk_write_bps':wbps,'gpu':gpu,
                         'gpu_memory':gmem,'cgroup':cg,'app_id':app_id,'start_ticks':start})
        self._prev = new_prev
        self._fixed = new_fixed
        self._io_denied &= new_fixed.keys()
        if self._tick % 2:
            self._gpu_prev = new_gpu
        self._gpu_cached = gpu_cache
        self._drm_fds = drm_fds
        return rows


class AppResolver:
    """Resolve systemd application scopes to desktop entries."""

    def __init__(self) -> None:
        home = Path.home()/'.local/share'
        dirs = [home] + [Path(x) for x in os.environ.get('XDG_DATA_DIRS','/usr/local/share:/usr/share').split(':')]
        dirs += [Path('/var/lib/flatpak/exports/share'),home/'flatpak/exports/share']
        self._dirs = list(dict.fromkeys(dirs))
        self._index: dict[str,dict] = {}
        self._basename: dict[str,dict] = {}
        self._wmclass: dict[str,dict] = {}
        self._scanned = 0.

    def _scan(self) -> None:
        now = time.monotonic()
        if self._scanned and now-self._scanned < 30:
            return
        self._scanned = now
        index = {}
        basename = {}
        wmclass = {}
        lang = os.environ.get('LC_ALL') or os.environ.get('LC_MESSAGES') or os.environ.get('LANG','C')
        lang = lang.split('.')[0]
        for directory in self._dirs:
            root = directory/'applications'
            if not root.is_dir():
                continue
            for file in root.rglob('*.desktop'):
                desktop_id = str(file.relative_to(root)).replace('/','-')[:-8]
                key = desktop_id.lower()
                if key in index:
                    continue
                parser = configparser.ConfigParser(interpolation=None,strict=False)
                parser.optionxform = str
                try:
                    parser.read(file,encoding='utf-8')
                    entry = parser['Desktop Entry']
                    name = next((entry[f'Name[{tag}]'] for tag in (lang,lang.split('_')[0]) if f'Name[{tag}]' in entry),entry.get('Name',''))
                except (OSError,configparser.Error,KeyError):
                    continue
                if not name or entry.get('Hidden','false').lower()=='true':
                    continue
                row = {'id':desktop_id,'name':name,'icon':entry.get('Icon','')}
                index[key] = row
                basename.setdefault(desktop_id.lower().split('.')[-1],row)
                if entry.get('StartupWMClass'):
                    wmclass.setdefault(entry['StartupWMClass'].lower(),row)
        self._index,self._basename,self._wmclass = index,basename,wmclass

    def resolve(self, processes: list[dict]) -> list[dict]:
        """Group matching application processes and sum their live measurements."""
        self._scan()
        groups: dict[str,list[dict]] = {}
        for process in processes:
            app_id = process.get('app_id')
            if not app_id or any(b in app_id.lower() for b in _BACKGROUND):
                continue
            key = app_id.lower().removesuffix('.desktop')
            desktop = self._index.get(key) or self._basename.get(key) or self._wmclass.get(key)
            if desktop:
                groups.setdefault(desktop['id'],[]).append(process)
        result = []
        for desktop_id,procs in groups.items():
            entry = self._index[desktop_id.lower()]
            by_pid = {p['pid']:p for p in procs}
            def depth(p: dict) -> int:
                n, seen = 0,set()
                while p['ppid'] in by_pid and p['ppid'] not in seen:
                    seen.add(p['pid'])
                    p = by_pid[p['ppid']]
                    n += 1
                return n
            ordered = sorted(procs,key=lambda p:(depth(p),p['start_time']))
            def total(field: str):
                return sum(p.get(field) or 0 for p in procs)
            gpu_values = [p['gpu'] for p in procs if p.get('gpu') is not None]
            gpu_mem = [p['gpu_memory'] for p in procs if p.get('gpu_memory') is not None]
            result.append({'id':entry['id'],'name':entry['name'],'icon':entry['icon'],
                           'pids':[p['pid'] for p in ordered],'cpu':total('cpu'),
                           'memory':total('memory'),'shared_memory':total('shared_memory'),
                           'disk_read_bps':total('disk_read_bps'),'disk_write_bps':total('disk_write_bps'),
                           'gpu':sum(gpu_values) if gpu_values else None,
                           'gpu_memory':sum(gpu_mem) if gpu_mem else None})
        return sorted(result,key=lambda p:p['name'].casefold())


def _start_ticks(pid: int) -> int | None:
    raw = _read(f'/proc/{pid}/stat')
    try:
        return int(raw[raw.rindex(')')+2:].split()[19]) if raw else None
    except (ValueError,IndexError):
        return None


def signal_process(pid: int, sig: str, start_ticks: int | None = None) -> tuple[bool,str]:
    """Signal one process, using polkit authorization only when necessary.

    With `start_ticks` the process identity is verified first, so a PID that
    was recycled while a confirmation dialog was open is left alone. A pidfd
    pins the process between that check and the signal.
    """
    if sig not in {'TERM','KILL','STOP','CONT'} or not isinstance(pid,int) or pid<=0:
        return False,'Invalid PID or signal'
    signum = getattr(signal,'SIG'+sig)
    try:
        pidfd = os.pidfd_open(pid)
    except ProcessLookupError:
        return False,'The process has already exited'
    except OSError:
        pidfd = None
    try:
        if start_ticks is not None and _start_ticks(pid) != start_ticks:
            return False,'The process has already exited'
        if pidfd is not None:
            signal.pidfd_send_signal(pidfd,signum)
        else:
            os.kill(pid,signum)
        return True,''
    except ProcessLookupError:
        return False,'The process has already exited'
    except PermissionError:
        try:
            result = subprocess.run(['pkexec','kill',f'-{sig}',str(pid)],capture_output=True,text=True,timeout=60)
            return result.returncode==0,result.stderr.strip()
        except (OSError,subprocess.TimeoutExpired) as error:
            return False,str(error)
    except OSError as error:
        return False,str(error)
    finally:
        if pidfd is not None:
            os.close(pidfd)


def process_details(pid: int) -> dict:
    """Return extended process data; unavailable fields are None."""
    keys = ('ppid','name','exe','cmdline','cwd','user','state','threads','nice','start_time',
            'cgroup','open_files','memory_rss','memory_shared','memory_swap')
    data = {'pid':pid,**dict.fromkeys(keys)}
    try:
        raw = _read(f'/proc/{pid}/stat')
        if not raw:
            return data
        data['name'] = raw[raw.index('(')+1:raw.rindex(')')]
        parts = raw[raw.rindex(')')+2:].split()
        data.update(ppid=int(parts[1]),state=_STATE.get(parts[0],parts[0]),nice=int(parts[16]),
                    threads=int(parts[17]),start_time=time.time()-float((_read('/proc/uptime') or '0').split()[0])+int(parts[19])/_HZ)
        statm = (_read(f'/proc/{pid}/statm') or '').split()
        if len(statm)>2:
            data['memory_rss'],data['memory_shared'] = int(statm[1])*_PAGE,int(statm[2])*_PAGE
        status = _read(f'/proc/{pid}/status') or ''
        swap = re.search(r'^VmSwap:\s*(\d+)',status,re.M)
        data['memory_swap'] = int(swap[1])*1024 if swap else None
        uid = re.search(r'^Uid:\s*(\d+)',status,re.M)
        data['user'] = _uid_name(int(uid[1]),{}) if uid else None
        for field,link in (('exe','exe'),('cwd','cwd')):
            try:
                data[field] = os.readlink(f'/proc/{pid}/{link}')
            except OSError:
                pass
        try:
            cmd = Path(f'/proc/{pid}/cmdline').read_bytes()
            data['cmdline'] = ' '.join(x.decode(errors='replace') for x in cmd.split(b'\0') if x)
        except OSError:
            pass
        data['cgroup'] = next((line[3:] for line in (_read(f'/proc/{pid}/cgroup') or '').splitlines() if line.startswith('0::')),None)
        try:
            data['open_files'] = len(os.listdir(f'/proc/{pid}/fd'))
        except OSError:
            pass
    except (OSError,ValueError,IndexError):
        pass
    return data
