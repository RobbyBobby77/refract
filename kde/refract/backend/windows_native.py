"""Small, read-only Win32 helpers; no compiler or extra native package needed."""
from __future__ import annotations

import ctypes as C
from ctypes import wintypes as W
import logging

log = logging.getLogger(__name__)


class _Value(C.Union):
    _fields_ = [("double", C.c_double), ("large", C.c_longlong), ("long", W.LONG)]


class _Formatted(C.Structure):
    _anonymous_ = ("value",)
    _fields_ = [("status", W.DWORD), ("value", _Value)]


class _Item(C.Structure):
    _fields_ = [("name", W.LPWSTR), ("value", _Formatted)]


class PerformanceCounters:
    """Locale-independent PDH wildcard counters, sampled on the worker thread."""

    PATHS = {
        "disk_busy": r"\PhysicalDisk(*)\% Idle Time",
        "disk_response": r"\PhysicalDisk(*)\Avg. Disk sec/Transfer",
        "gpu": r"\GPU Engine(*)\Utilization Percentage",
        "gpu_memory": r"\GPU Adapter Memory(*)\Dedicated Usage",
        "gpu_shared": r"\GPU Adapter Memory(*)\Shared Usage",
        "committed": r"\Memory\Committed Bytes",
        "commit_limit": r"\Memory\Commit Limit",
        "cache": r"\Memory\Cache Bytes",
    }

    def __init__(self) -> None:
        self._query = W.HANDLE()
        self._counters: dict[str, W.HANDLE] = {}
        self._lib = C.WinDLL("pdh")
        signatures = {
            "PdhOpenQueryW": [W.LPCWSTR, C.c_size_t, C.POINTER(W.HANDLE)],
            "PdhAddEnglishCounterW": [W.HANDLE, W.LPCWSTR, C.c_size_t, C.POINTER(W.HANDLE)],
            "PdhCollectQueryData": [W.HANDLE],
            "PdhGetFormattedCounterArrayW": [W.HANDLE, W.DWORD, C.POINTER(W.DWORD),
                                              C.POINTER(W.DWORD), C.c_void_p],
            "PdhGetFormattedCounterValue": [W.HANDLE, W.DWORD, C.POINTER(W.DWORD), C.POINTER(_Formatted)],
            "PdhCloseQuery": [W.HANDLE],
        }
        for name, args in signatures.items():
            func = getattr(self._lib, name)
            func.argtypes, func.restype = args, W.DWORD
        if self._lib.PdhOpenQueryW(None, 0, C.byref(self._query)):
            return
        for key, path in self.PATHS.items():
            handle = W.HANDLE()
            status = self._lib.PdhAddEnglishCounterW(self._query, path, 0, C.byref(handle))
            if status == 0:
                self._counters[key] = handle
            else:
                log.debug("counter %s unavailable (0x%x)", key, status)
        self._lib.PdhCollectQueryData(self._query)

    def sample(self) -> dict[str, dict[str, float]]:
        if not self._query or self._lib.PdhCollectQueryData(self._query):
            return {}
        result = {}
        for key, handle in self._counters.items():
            if "*" not in self.PATHS[key]:
                value = _Formatted()
                if self._lib.PdhGetFormattedCounterValue(handle, 0x200, None, C.byref(value)) == 0 and value.status in (0, 1):
                    result[key] = {"": value.double}
                continue
            # Instances may appear between calls. Retry from a fresh size query.
            for _ in range(3):
                size, count = W.DWORD(), W.DWORD()
                status = self._lib.PdhGetFormattedCounterArrayW(handle, 0x200, C.byref(size), C.byref(count), None)
                if status != 0x800007D2 or not size.value:
                    break
                buffer = C.create_string_buffer(size.value)
                status = self._lib.PdhGetFormattedCounterArrayW(handle, 0x200, C.byref(size), C.byref(count), buffer)
                if status == 0:
                    items = C.cast(buffer, C.POINTER(_Item))
                    result[key] = {items[i].name: items[i].value.double for i in range(count.value)
                                   if items[i].value.status in (0, 1)}
                    break
        return result

    def close(self) -> None:
        if self._query:
            self._lib.PdhCloseQuery(self._query)
            self._query = W.HANDLE()


def performance_info() -> dict[str, int]:
    """System process/thread/handle counts from GetPerformanceInfo."""
    class Info(C.Structure):
        _fields_ = [("cb", W.DWORD)] + [(name, C.c_size_t) for name in (
            "CommitTotal", "CommitLimit", "CommitPeak", "PhysicalTotal", "PhysicalAvailable",
            "SystemCache", "KernelTotal", "KernelPaged", "KernelNonpaged", "PageSize",
        )] + [(name, W.DWORD) for name in ("HandleCount", "ProcessCount", "ThreadCount")]

    lib = C.WinDLL("psapi")
    lib.GetPerformanceInfo.argtypes = [C.POINTER(Info), W.DWORD]
    lib.GetPerformanceInfo.restype = W.BOOL
    info = Info()
    info.cb = C.sizeof(info)
    if not lib.GetPerformanceInfo(C.byref(info), info.cb):
        return {}
    return {"processes": info.ProcessCount, "threads": info.ThreadCount, "handles": info.HandleCount,
            "cached": info.SystemCache * info.PageSize, "committed": info.CommitTotal * info.PageSize,
            "commit_limit": info.CommitLimit * info.PageSize}


def visible_processes() -> set[int]:
    """PIDs with visible top-level windows, for application grouping."""
    lib = C.WinDLL("user32")
    callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    lib.EnumWindows.argtypes = [callback_type, W.LPARAM]
    lib.EnumWindows.restype = W.BOOL
    lib.IsWindowVisible.argtypes, lib.IsWindowVisible.restype = [W.HWND], W.BOOL
    lib.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    lib.GetWindowThreadProcessId.restype = W.DWORD
    pids: set[int] = set()

    @callback_type
    def visit(window, _param):
        if lib.IsWindowVisible(window):
            pid = W.DWORD()
            lib.GetWindowThreadProcessId(window, C.byref(pid))
            pids.add(pid.value)
        return True

    lib.EnumWindows(visit, 0)
    return pids


def wallpaper_path() -> str:
    """Current wallpaper via the documented SystemParametersInfo API."""
    lib = C.WinDLL("user32")
    lib.SystemParametersInfoW.argtypes = [W.UINT, W.UINT, C.c_void_p, W.UINT]
    lib.SystemParametersInfoW.restype = W.BOOL
    buffer = C.create_unicode_buffer(32768)
    return buffer.value if lib.SystemParametersInfoW(0x73, len(buffer), buffer, 0) else ""


def process_inventory() -> list[dict]:
    """One Toolhelp snapshot for names, parent PIDs and thread counts.

    Calling psutil.ppid()/num_threads() for every PID takes a fresh system
    process snapshot each time on Windows, making a table refresh quadratic.
    """
    class Entry(C.Structure):
        _fields_ = [("size", W.DWORD), ("usage", W.DWORD), ("pid", W.DWORD),
                    ("heap", C.c_size_t), ("module", W.DWORD), ("threads", W.DWORD),
                    ("parent", W.DWORD), ("priority", W.LONG), ("flags", W.DWORD),
                    ("exe", W.WCHAR * 260)]

    lib = C.WinDLL("kernel32", use_last_error=True)
    lib.CreateToolhelp32Snapshot.argtypes, lib.CreateToolhelp32Snapshot.restype = [W.DWORD, W.DWORD], W.HANDLE
    lib.Process32FirstW.argtypes = lib.Process32NextW.argtypes = [W.HANDLE, C.POINTER(Entry)]
    lib.Process32FirstW.restype = lib.Process32NextW.restype = W.BOOL
    lib.CloseHandle.argtypes, lib.CloseHandle.restype = [W.HANDLE], W.BOOL
    handle = lib.CreateToolhelp32Snapshot(2, 0)
    if handle == C.c_void_p(-1).value:
        raise C.WinError(C.get_last_error())
    rows = []
    try:
        entry = Entry()
        entry.size = C.sizeof(entry)
        found = lib.Process32FirstW(handle, C.byref(entry))
        while found:
            rows.append({"pid": entry.pid, "ppid": entry.parent, "threads": entry.threads, "name": entry.exe})
            found = lib.Process32NextW(handle, C.byref(entry))
    finally:
        lib.CloseHandle(handle)
    return rows


def process_snapshot() -> list[dict]:
    """Batch the same NT process information used by psutil's Windows backend.

    Windows 10/11's SystemProcessInformation layout is stable, but this API
    can change in future Windows versions. Validate all offsets and fall
    back to the documented Toolhelp/psutil APIs if the query fails.
    """
    class UnicodeString(C.Structure):
        _fields_ = [("length", W.USHORT), ("maximum", W.USHORT), ("buffer", C.c_void_p)]

    class ProcessInfo(C.Structure):
        _fields_ = [
            ("next", W.ULONG), ("threads", W.ULONG), ("private_working_set", C.c_longlong),
            ("hard_faults", W.ULONG), ("thread_peak", W.ULONG), ("cycles", C.c_ulonglong),
            ("created", C.c_longlong), ("user", C.c_longlong), ("kernel", C.c_longlong),
            ("name", UnicodeString), ("priority", W.LONG), ("pid", W.HANDLE), ("ppid", W.HANDLE),
            ("handles", W.ULONG), ("session", W.ULONG), ("key", C.c_size_t),
            ("peak_virtual", C.c_size_t), ("virtual", C.c_size_t), ("faults", W.ULONG),
        ] + [(name, C.c_size_t) for name in (
            "peak_working_set", "working_set", "peak_paged_pool", "paged_pool",
            "peak_nonpaged_pool", "nonpaged_pool", "pagefile", "peak_pagefile", "private_pages",
        )] + [(name, C.c_longlong) for name in (
            "reads", "writes", "other_ops", "read_bytes", "write_bytes", "other_bytes",
        )]

    lib = C.WinDLL("ntdll")
    query = lib.NtQuerySystemInformation
    query.argtypes, query.restype = [W.ULONG, C.c_void_p, W.ULONG, C.POINTER(W.ULONG)], W.ULONG
    required = W.ULONG()
    capacity = 1024 * 1024
    for _ in range(5):
        buffer = C.create_string_buffer(capacity)
        status = query(5, buffer, capacity, C.byref(required))
        if status == 0:
            break
        if status != 0xC0000004:
            raise OSError(f"Process snapshot failed (0x{status:x})")
        capacity = max(capacity * 2, required.value + 65536)
        if capacity > 64 * 1024 * 1024:
            raise OSError("Process snapshot exceeds size limit")
    else:
        raise OSError("Process list changed too quickly to sample")
    rows, offset = [], 0
    base, end = C.addressof(buffer), C.addressof(buffer) + required.value
    while offset + C.sizeof(ProcessInfo) <= required.value:
        info = ProcessInfo.from_buffer(buffer, offset)
        name = ""
        if info.name.buffer and info.name.length:
            if not base <= info.name.buffer <= end - info.name.length or info.name.length % 2:
                raise OSError("Invalid process name in snapshot")
            name = C.wstring_at(info.name.buffer, info.name.length // 2)
        rows.append({"pid": info.pid or 0, "ppid": info.ppid or 0, "threads": info.threads,
                     "name": name or "System Idle Process", "created": (info.created - 116444736000000000) / 1e7,
                     "cpu_seconds": (info.user + info.kernel) / 1e7, "memory": info.working_set,
                     "read_bytes": info.read_bytes, "write_bytes": info.write_bytes})
        if info.next == 0:
            return rows
        if info.next < C.sizeof(ProcessInfo) or offset + info.next >= required.value:
            raise OSError("Invalid process offset in snapshot")
        offset += info.next
    raise OSError("Incomplete process snapshot")


def graphics_adapters() -> dict[str, dict]:
    """DXGI adapter names and memory sizes, keyed by the PDH adapter LUID."""
    import uuid

    class Guid(C.Structure):
        _fields_ = [("data", C.c_ubyte * 16)]

    class Luid(C.Structure):
        _fields_ = [("low", W.DWORD), ("high", W.LONG)]

    class Desc(C.Structure):
        _fields_ = [("name", W.WCHAR * 128)] + [(s, W.UINT) for s in ("vendor", "device", "subsystem", "revision")]
        _fields_ += [(s, C.c_size_t) for s in ("dedicated", "system", "shared")]
        _fields_ += [("luid", Luid), ("flags", W.UINT)]

    def method(obj, index, restype, *args):
        vtable = C.cast(obj, C.POINTER(C.POINTER(C.c_void_p))).contents
        return C.WINFUNCTYPE(restype, C.c_void_p, *args)(vtable[index])

    lib = C.WinDLL("dxgi")
    lib.CreateDXGIFactory1.argtypes = [C.POINTER(Guid), C.POINTER(C.c_void_p)]
    lib.CreateDXGIFactory1.restype = W.LONG
    guid = Guid.from_buffer_copy(uuid.UUID("770aae78-f26f-4dba-a829-253c83d1b387").bytes_le)
    factory = C.c_void_p()
    if lib.CreateDXGIFactory1(C.byref(guid), C.byref(factory)) != 0:
        return {}
    rows = {}
    try:
        enum = method(factory, 12, W.LONG, W.UINT, C.POINTER(C.c_void_p))
        for i in range(32):
            adapter = C.c_void_p()
            if enum(factory, i, C.byref(adapter)) != 0:
                break
            try:
                desc = Desc()
                if method(adapter, 10, W.LONG, C.POINTER(Desc))(adapter, C.byref(desc)) == 0 and not desc.flags & 2:
                    key = f"0x{desc.luid.high & 0xffffffff:08x}_0x{desc.luid.low:08x}_0"
                    rows[key] = {"id": key, "name": desc.name,
                                 "vendor": {0x1002: "AMD", 0x10de: "NVIDIA", 0x8086: "Intel"}.get(desc.vendor),
                                 "vram_total": desc.dedicated or None, "gtt_total": desc.shared or None,
                                 "integrated": None}
            finally:
                method(adapter, 2, W.ULONG)(adapter)
    finally:
        method(factory, 2, W.ULONG)(factory)
    return rows
