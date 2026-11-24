"""Select the native backend without importing another platform's modules."""
import sys

if sys.platform == "win32":
    from .windows import (
        AppResolver, ProcessSampler, SystemSampler, list_services,
        process_details, service_action, service_logs, signal_process,
    )
else:
    from .collectors import SystemSampler
    from .processes import AppResolver, ProcessSampler, process_details, signal_process
    from .services import list_services, service_action, service_logs
