"""Run a read-only backend diagnostic."""
import json
import time

from .collectors import SystemSampler
from .processes import ProcessSampler, AppResolver
from .services import list_services


def main() -> None:
    system = SystemSampler()
    processes = ProcessSampler()
    apps = AppResolver()
    print(json.dumps({'static_info':system.static_info()},indent=2,default=str))
    system.sample()
    processes.sample()
    time.sleep(1)
    timings = {}
    start = time.perf_counter()
    snapshot = system.sample()
    timings['sample()'] = (time.perf_counter()-start)*1000
    start = time.perf_counter()
    proc_rows = processes.sample()
    timings['ProcessSampler.sample()'] = (time.perf_counter()-start)*1000
    start = time.perf_counter()
    app_rows = apps.resolve(proc_rows)
    timings['AppResolver.resolve()'] = (time.perf_counter()-start)*1000
    start = time.perf_counter()
    system_services = list_services(False)
    timings['list_services(False)'] = (time.perf_counter()-start)*1000
    start = time.perf_counter()
    user_services = list_services(True)
    timings['list_services(True)'] = (time.perf_counter()-start)*1000
    print(json.dumps({'sample':snapshot,'top_processes':sorted(proc_rows,key=lambda p:p['cpu'],reverse=True)[:10],
                      'apps':[{'id':a['id'],'name':a['name'],'icon':a['icon'],'pids_count':len(a['pids'])} for a in app_rows],
                      'services':{'system_count':len(system_services),'user_count':len(user_services),
                                  'system_examples':system_services[:5],'user_examples':user_services[:5]},
                      'timings_ms':timings},indent=2,default=str))


if __name__ == '__main__':
    main()
