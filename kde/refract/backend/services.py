"""Systemd service listing and stateless actions."""
from __future__ import annotations

import json
import subprocess
import time

from .. import sandbox

# Per-unit PID/memory lookups are a D-Bus round trip each; cap the total so a
# slow bus can't hold up the poller (or application shutdown).
_DETAIL_BUDGET_S = 1.5


def _fallback(user: bool) -> list[dict]:
    prefix = ['systemctl'] + (['--user'] if user else [])
    try:
        units = subprocess.run(sandbox.host(prefix+['list-units','--type=service','--all','--output=json']),
                               capture_output=True,text=True,timeout=3)
        files = subprocess.run(sandbox.host(prefix+['list-unit-files','--type=service','--output=json']),
                               capture_output=True,text=True,timeout=3)
        loaded = json.loads(units.stdout) if units.returncode==0 else []
        installed = json.loads(files.stdout) if files.returncode==0 else []
    except (OSError,ValueError,subprocess.TimeoutExpired):
        return []
    result = {}
    for item in loaded:
        name = item.get('unit') or item.get('name')
        if not name or not name.endswith('.service') or name.endswith('@.service'):
            continue
        result[name] = {'name':name,'description':item.get('description') or '',
                        'load_state':item.get('load') or 'loaded',
                        'active_state':item.get('active') or 'inactive','sub_state':item.get('sub') or 'dead',
                        'enabled_state':None,'pid':None,'memory':None,'user':user}
    for item in installed:
        name = item.get('unit_file') or item.get('unit') or item.get('name')
        if not name or not name.endswith('.service') or name.endswith('@.service'):
            continue
        row = result.setdefault(name,{'name':name,'description':'','load_state':'not-found',
                                      'active_state':'inactive','sub_state':'dead','enabled_state':None,
                                      'pid':None,'memory':None,'user':user})
        row['enabled_state'] = item.get('state')
    return sorted(result.values(),key=lambda r:r['name'])


def list_services(user: bool = False) -> list[dict]:
    """List loaded and installed systemd services on the chosen bus."""
    try:
        import dbus
        bus = dbus.SessionBus() if user else dbus.SystemBus()
        manager = dbus.Interface(bus.get_object('org.freedesktop.systemd1','/org/freedesktop/systemd1'),
                                 'org.freedesktop.systemd1.Manager')
        units = manager.ListUnits(timeout=2)
        files = manager.ListUnitFiles(timeout=2)
        result = {}
        deadline = time.monotonic() + _DETAIL_BUDGET_S
        for unit in units:
            name = str(unit[0])
            if not name.endswith('.service') or name.endswith('@.service'):
                continue
            row = {'name':name,'description':str(unit[1]),'load_state':str(unit[2]),
                   'active_state':str(unit[3]),'sub_state':str(unit[4]),'enabled_state':None,
                   'pid':None,'memory':None,'user':user}
            result[name] = row
            if str(unit[3]) != 'active' or time.monotonic() > deadline:
                continue
            try:
                obj = bus.get_object('org.freedesktop.systemd1',unit[6],introspect=False)
                props = dbus.Interface(obj,'org.freedesktop.DBus.Properties')
                service_props = props.GetAll('org.freedesktop.systemd1.Service',timeout=0.2)
                pid = int(service_props.get('MainPID',0))
                row['pid'] = pid or None
                unit_props = props.GetAll('org.freedesktop.systemd1.Unit',timeout=0.2)
                memory = int(service_props.get('MemoryCurrent',unit_props.get('MemoryCurrent',2**64-1)))
                row['memory'] = memory if memory != 2**64-1 else None
            except Exception:
                pass
        for path,state in files:
            name = str(path).rsplit('/',1)[-1]
            if not name.endswith('.service') or name.endswith('@.service'):
                continue
            row = result.setdefault(name,{'name':name,'description':'','load_state':'not-found',
                                        'active_state':'inactive','sub_state':'dead','enabled_state':None,
                                        'pid':None,'memory':None,'user':user})
            row['enabled_state'] = str(state)
        return sorted(result.values(),key=lambda row:row['name'])
    except Exception:
        return _fallback(user)


def service_action(name: str, action: str, user: bool = False) -> tuple[bool,str]:
    """Run a requested systemctl action and return success and stderr."""
    if action not in {'start','stop','restart','enable','disable'} or not name or name.startswith('-'):
        return False,'Invalid service or action'
    command = ['systemctl']+(['--user'] if user else [])+[action,name]
    try:
        result = subprocess.run(sandbox.host(command),capture_output=True,text=True,timeout=90)
        return result.returncode==0,result.stderr.strip()
    except (OSError,subprocess.TimeoutExpired) as error:
        return False,str(error)


def service_logs(name: str, user: bool = False, lines: int = 200) -> str:
    """Return recent journal records for one unit."""
    if not name or name.startswith('-'):
        return ''
    try:
        command = ['journalctl']+(['--user'] if user else [])+['-u',name,'-n',str(max(0,int(lines))),
                                                             '--no-pager','-o','short-iso']
        return subprocess.run(sandbox.host(command),capture_output=True,text=True,timeout=10).stdout
    except (OSError,subprocess.TimeoutExpired,ValueError):
        return ''
