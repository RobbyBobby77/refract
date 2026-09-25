"""List models exposed to QML.

All models here are *positional*: every refresh rewrites rows in place and only
grows or shrinks the tail. Live tables re-sort every tick, so emitting row moves
would make the view jump around; instead QML tracks the selection by key.
"""

from __future__ import annotations

from typing import Any, Iterable

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    Qt,
    Signal,
    Slot,
)


class RowModel(QAbstractListModel):
    """A list of dict rows with a fixed set of roles."""

    ROLES: tuple[str, ...] = ()

    countChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[dict[str, Any]] = []
        self._role_ids = {Qt.UserRole + 1 + i: name for i, name in enumerate(self.ROLES)}

    def roleNames(self) -> dict[int, QByteArray]:
        return {rid: QByteArray(name.encode()) for rid, name in self._role_ids.items()}

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._rows):
            return None
        name = self._role_ids.get(role)
        if name is None:
            return None
        return self._rows[index.row()].get(name)

    def _count(self) -> int:
        return len(self._rows)

    count = Property(int, _count, notify=countChanged)

    @Slot(int, result="QVariantMap")
    def get(self, row: int) -> dict[str, Any]:
        if 0 <= row < len(self._rows):
            return dict(self._rows[row])
        return {}

    @Slot(str, result=int)
    def rowOf(self, key: str) -> int:
        for i, r in enumerate(self._rows):
            if r.get("key") == key:
                return i
        return -1

    def _apply(self, rows: list[dict[str, Any]]) -> None:
        old, new = len(self._rows), len(rows)
        if new > old:
            self.beginInsertRows(QModelIndex(), old, new - 1)
            self._rows = rows
            self.endInsertRows()
        elif new < old:
            self.beginRemoveRows(QModelIndex(), new, old - 1)
            self._rows = rows
            self.endRemoveRows()
        else:
            self._rows = rows
        if min(old, new) > 0:
            self.dataChanged.emit(self.index(0), self.index(min(old, new) - 1))
        if old != new:
            self.countChanged.emit()


# --------------------------------------------------------------------------
# Sidebar devices
# --------------------------------------------------------------------------

def _fan_title(label: str | None, i: int) -> str:
    """'cpu_fan' -> 'CPU Fan'; unlabeled sensors become 'Fan N'."""
    if not label:
        return f"Fan {i}"
    words = label.replace("_", " ").replace("-", " ").split()
    return " ".join(w.upper() if w.lower() in ("cpu", "gpu", "pch", "vrm") else w.capitalize() for w in words)


class DeviceModel(RowModel):
    ROLES = (
        "key", "kind", "devId", "ordinal", "title", "detail",
        "usage", "v1", "v2", "v3", "series", "series2", "colorName", "maxValue",
    )

    def update(self, snap: dict[str, Any], static: dict[str, Any]) -> None:
        rows: list[dict[str, Any]] = []
        cpu = snap.get("cpu") or {}
        rows.append({
            "key": "cpu", "kind": "cpu", "devId": "cpu", "ordinal": 0,
            "title": "CPU", "detail": static.get("cpu_name") or "",
            "usage": cpu.get("usage"), "v1": cpu.get("freq_mhz"), "v2": None, "v3": None,
            "series": "cpu", "series2": "", "colorName": "blue", "maxValue": 100.0,
        })
        mem = snap.get("memory") or {}
        total = mem.get("total") or 0
        rows.append({
            "key": "memory", "kind": "memory", "devId": "memory", "ordinal": 0,
            "title": "Memory", "detail": "",
            "usage": (mem.get("used", 0) / total * 100.0) if total else None,
            "v1": mem.get("used"), "v2": total, "v3": None,
            "series": "mem", "series2": "", "colorName": "purple", "maxValue": 100.0,
        })
        for i, d in enumerate(snap.get("disks") or []):
            rows.append({
                "key": f"disk:{d['id']}", "kind": "disk", "devId": d["id"], "ordinal": i,
                "title": f"Disk {i}", "detail": d.get("type") or "",
                "usage": d.get("busy_percent"), "v1": d.get("read_bps"), "v2": d.get("write_bps"),
                "v3": None, "series": f"disk.{d['id']}.busy", "series2": "",
                "colorName": "green", "maxValue": 100.0,
            })
        for i, n in enumerate(snap.get("network") or []):
            rows.append({
                "key": f"net:{n['id']}", "kind": "network", "devId": n["id"], "ordinal": i,
                "title": n.get("name") or n["id"], "detail": n["id"],
                "usage": None, "v1": n.get("rx_bps"), "v2": n.get("tx_bps"), "v3": None,
                "series": f"net.{n['id']}.rx", "series2": f"net.{n['id']}.tx",
                "colorName": "orange", "maxValue": -1.0,
            })
        for i, g in enumerate(snap.get("gpus") or []):
            rows.append({
                "key": f"gpu:{g['id']}", "kind": "gpu", "devId": g["id"], "ordinal": i,
                "title": f"GPU {i}", "detail": g.get("name") or "",
                "usage": g.get("usage"), "v1": g.get("temperature_c"), "v2": None, "v3": None,
                "series": f"gpu.{g['id']}.usage", "series2": "",
                "colorName": "pink", "maxValue": 100.0,
            })
        for i, f in enumerate(snap.get("fans") or []):
            rows.append({
                "key": f"fan:{f['id']}", "kind": "fan", "devId": f["id"], "ordinal": i,
                "title": _fan_title(f.get("label"), i), "detail": f.get("name") or "",
                "usage": f.get("pwm_percent"), "v1": f.get("rpm"), "v2": None, "v3": None,
                "series": f"fan.{f['id']}.rpm", "series2": "",
                "colorName": "cyan", "maxValue": -1.0,
            })
        for i, b in enumerate(snap.get("batteries") or []):
            rows.append({
                "key": f"bat:{b['id']}", "kind": "battery", "devId": b["id"], "ordinal": i,
                "title": "Battery", "detail": b.get("state") or "",
                "usage": b.get("percent"), "v1": b.get("power_w"), "v2": None, "v3": None,
                "series": f"bat.{b['id']}.percent", "series2": "",
                "colorName": "mint", "maxValue": 100.0,
            })
        self._apply(rows)


# --------------------------------------------------------------------------
# Apps & processes
# --------------------------------------------------------------------------

_NUMERIC = {"pid", "cpu", "memory", "disk", "gpu", "gpuMemory", "threads", "sharedMemory"}


def _proc_row(p: dict[str, Any], key: str, depth: int, icon: str = "") -> dict[str, Any]:
    return {
        "key": key, "kind": "process", "depth": depth,
        "expandable": False, "expanded": False,
        "name": p.get("name") or "?", "icon": icon, "pid": p.get("pid"),
        "cpu": p.get("cpu") or 0.0, "memory": p.get("memory") or 0,
        "sharedMemory": p.get("shared_memory") or 0,
        "disk": (p.get("disk_read_bps") or 0.0) + (p.get("disk_write_bps") or 0.0),
        "gpu": p.get("gpu"), "gpuMemory": p.get("gpu_memory"),
        "user": p.get("user") or "", "state": p.get("state") or "",
        "threads": p.get("threads") or 0, "cmdline": p.get("cmdline") or "",
        "count": 0, "pids": [p.get("pid")], "starts": [p.get("start_ticks")],
    }


class ProcessModel(RowModel):
    ROLES = (
        "key", "kind", "depth", "expandable", "expanded", "name", "icon", "pid",
        "cpu", "memory", "sharedMemory", "disk", "gpu", "gpuMemory", "user", "state",
        "threads", "cmdline", "count", "pids",
    )

    sortChanged = Signal()
    filterChanged = Signal()
    treeModeChanged = Signal()
    selectionChanged = Signal()
    statsChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._procs: list[dict[str, Any]] = []
        self._apps: list[dict[str, Any]] = []
        self._sort_col = "cpu"
        self._sort_asc = False
        self._filter = ""
        self._tree = False
        self._expanded: set[str] = set()
        self._collapsed: set[str] = set()
        self._selected = ""
        self._selected_info: dict[str, Any] = {}
        self._app_count = 0
        self._proc_count = 0

    # -- properties -------------------------------------------------------
    def _get_sort_col(self) -> str:
        return self._sort_col

    def _get_sort_asc(self) -> bool:
        return self._sort_asc

    def _get_filter(self) -> str:
        return self._filter

    def _set_filter(self, text: str) -> None:
        if text != self._filter:
            self._filter = text
            self.filterChanged.emit()
            self._rebuild()

    def _get_tree(self) -> bool:
        return self._tree

    def _set_tree(self, v: bool) -> None:
        if v != self._tree:
            self._tree = v
            self.treeModeChanged.emit()
            self._rebuild()

    def _get_selected(self) -> str:
        return self._selected

    def _get_selected_info(self) -> dict[str, Any]:
        return self._selected_info

    def _get_app_count(self) -> int:
        return self._app_count

    def _get_proc_count(self) -> int:
        return self._proc_count

    sortColumn = Property(str, _get_sort_col, notify=sortChanged)
    sortAscending = Property(bool, _get_sort_asc, notify=sortChanged)
    filterText = Property(str, _get_filter, _set_filter, notify=filterChanged)
    treeMode = Property(bool, _get_tree, _set_tree, notify=treeModeChanged)
    selectedKey = Property(str, _get_selected, notify=selectionChanged)
    selectedInfo = Property("QVariantMap", _get_selected_info, notify=selectionChanged)
    appCount = Property(int, _get_app_count, notify=statsChanged)
    processCount = Property(int, _get_proc_count, notify=statsChanged)

    # -- slots ------------------------------------------------------------
    @Slot(str)
    def sortBy(self, column: str) -> None:
        if column == self._sort_col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = column
            self._sort_asc = column in ("name", "pid", "user")
        self.sortChanged.emit()
        self._rebuild()

    @Slot(str)
    def toggleExpanded(self, key: str) -> None:
        if key.startswith("section:") or (self._tree and key.startswith("proc:")):
            target = self._collapsed
        else:
            target = self._expanded
        if key in target:
            target.discard(key)
        else:
            target.add(key)
        self._rebuild()

    @Slot(str)
    def select(self, key: str) -> None:
        self._selected = key
        self._refresh_selection()
        self.selectionChanged.emit()

    # -- data -------------------------------------------------------------
    def update(self, procs: list[dict[str, Any]], apps: list[dict[str, Any]]) -> None:
        self._procs = procs
        self._apps = apps
        if self._app_count != len(apps) or self._proc_count != len(procs):
            self._app_count, self._proc_count = len(apps), len(procs)
            self.statsChanged.emit()
        self._rebuild()

    def _sort_key(self, row: dict[str, Any]):
        v = row.get(self._sort_col)
        if self._sort_col in _NUMERIC:
            return v if isinstance(v, (int, float)) else -1
        return str(v or "").casefold()

    def _sorted(self, rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(rows, key=self._sort_key, reverse=not self._sort_asc)

    def _matches(self, p: dict[str, Any], needle: str) -> bool:
        return (needle in (p.get("name") or "").casefold()
                or needle == str(p.get("pid"))
                or needle in (p.get("cmdline") or "").casefold())

    def _rebuild(self) -> None:
        needle = self._filter.strip().casefold()
        by_pid = {p["pid"]: p for p in self._procs}
        rows: list[dict[str, Any]] = []

        # Apps -------------------------------------------------------------
        app_rows: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
        for a in self._apps:
            pids = [pid for pid in a.get("pids") or [] if pid in by_pid]
            if not pids:
                continue
            key = f"app:{a['id']}"
            icon = a.get("icon") or ""
            children = [_proc_row(by_pid[pid], f"{key}/{pid}", 1, icon) for pid in pids]
            name_hit = not needle or needle in (a.get("name") or "").casefold()
            child_hits = [c for c in children if needle and self._matches(c, needle)]
            if not name_hit and not child_hits:
                continue
            main = by_pid[pids[0]]
            gpu_vals = [c["gpu"] for c in children if c["gpu"] is not None]
            gmem_vals = [c["gpuMemory"] for c in children if c["gpuMemory"] is not None]
            row = {
                "key": key, "kind": "app", "depth": 0,
                "expandable": True,
                "expanded": key in self._expanded or bool(needle and child_hits and not name_hit),
                "name": a.get("name") or a["id"], "icon": icon, "pid": main.get("pid"),
                "cpu": a.get("cpu") or 0.0, "memory": a.get("memory") or 0,
                "sharedMemory": a.get("shared_memory") or 0,
                "disk": (a.get("disk_read_bps") or 0.0) + (a.get("disk_write_bps") or 0.0),
                "gpu": sum(gpu_vals) if gpu_vals else None,
                "gpuMemory": sum(gmem_vals) if gmem_vals else None,
                "user": main.get("user") or "", "state": main.get("state") or "",
                "threads": sum(c["threads"] for c in children),
                "cmdline": main.get("cmdline") or "", "count": len(children),
                "pids": pids, "starts": [by_pid[pid].get("start_ticks") for pid in pids],
            }
            shown = children if name_hit else child_hits
            app_rows.append((row, self._sorted(shown)))

        app_rows.sort(key=lambda t: self._sort_key(t[0]), reverse=not self._sort_asc)
        rows.append(self._section("apps", "Apps", len(app_rows)))
        if "section:apps" not in self._collapsed:
            for row, children in app_rows:
                rows.append(row)
                if row["expanded"]:
                    rows.extend(children)

        # Processes ----------------------------------------------------------
        procs = self._procs
        if needle:
            procs = [p for p in procs if self._matches(p, needle)]
        if self._tree and not needle:
            proc_rows = self._tree_rows(procs, by_pid)
        else:
            proc_rows = self._sorted(_proc_row(p, f"proc:{p['pid']}", 0) for p in procs)
        rows.append(self._section("procs", "Processes", len(procs)))
        if "section:procs" not in self._collapsed:
            rows.extend(proc_rows)

        self._apply(rows)
        self._refresh_selection()

    def _section(self, sid: str, title: str, count: int) -> dict[str, Any]:
        key = f"section:{sid}"
        return {
            "key": key, "kind": "section", "depth": 0, "expandable": True,
            "expanded": key not in self._collapsed, "name": title, "icon": "",
            "pid": None, "cpu": None, "memory": None, "sharedMemory": None, "disk": None,
            "gpu": None, "gpuMemory": None, "user": "", "state": "", "threads": 0,
            "cmdline": "", "count": count, "pids": [], "starts": [],
        }

    def _tree_rows(self, procs: list[dict[str, Any]], by_pid: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
        children: dict[int, list[dict[str, Any]]] = {}
        roots: list[dict[str, Any]] = []
        for p in procs:
            if p.get("ppid") in by_pid and p.get("ppid") != p["pid"]:
                children.setdefault(p["ppid"], []).append(p)
            else:
                roots.append(p)
        out: list[dict[str, Any]] = []

        def walk(p: dict[str, Any], depth: int) -> None:
            key = f"proc:{p['pid']}"
            row = _proc_row(p, key, depth)
            kids = children.get(p["pid"], [])
            row["expandable"] = bool(kids)
            row["expanded"] = bool(kids) and key not in self._collapsed
            row["count"] = len(kids)
            out.append(row)
            if row["expanded"] and depth < 64:
                for kid in self._sorted(kids):
                    walk(kid, depth + 1)

        for r in self._sorted(roots):
            walk(r, 0)
        return out

    def _refresh_selection(self) -> None:
        info: dict[str, Any] = {}
        if self._selected:
            for r in self._rows:
                if r["key"] == self._selected:
                    info = dict(r)
                    break
        if info != self._selected_info:
            self._selected_info = info
            self.selectionChanged.emit()


# --------------------------------------------------------------------------
# Services
# --------------------------------------------------------------------------

class ServiceModel(RowModel):
    ROLES = (
        "key", "name", "description", "loadState", "activeState", "subState",
        "enabledState", "pid", "memory", "user",
    )

    sortChanged = Signal()
    filterChanged = Signal()
    selectionChanged = Signal()
    statsChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._services: list[dict[str, Any]] = []
        self._sort_col = "name"
        self._sort_asc = True
        self._filter = ""
        self._selected = ""
        self._selected_info: dict[str, Any] = {}
        self._stats = {"total": 0, "running": 0, "failed": 0}
        self._loaded = False

    def _get_sort_col(self) -> str:
        return self._sort_col

    def _get_sort_asc(self) -> bool:
        return self._sort_asc

    def _get_filter(self) -> str:
        return self._filter

    def _set_filter(self, text: str) -> None:
        if text != self._filter:
            self._filter = text
            self.filterChanged.emit()
            self._rebuild()

    def _get_selected(self) -> str:
        return self._selected

    def _get_selected_info(self) -> dict[str, Any]:
        return self._selected_info

    def _get_stats(self) -> dict[str, Any]:
        return self._stats

    def _get_loaded(self) -> bool:
        return self._loaded

    sortColumn = Property(str, _get_sort_col, notify=sortChanged)
    sortAscending = Property(bool, _get_sort_asc, notify=sortChanged)
    filterText = Property(str, _get_filter, _set_filter, notify=filterChanged)
    selectedKey = Property(str, _get_selected, notify=selectionChanged)
    selectedInfo = Property("QVariantMap", _get_selected_info, notify=selectionChanged)
    stats = Property("QVariantMap", _get_stats, notify=statsChanged)
    loaded = Property(bool, _get_loaded, notify=statsChanged)

    @Slot(str)
    def sortBy(self, column: str) -> None:
        if column == self._sort_col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = column
            self._sort_asc = column in ("name", "description", "activeState", "enabledState")
        self.sortChanged.emit()
        self._rebuild()

    @Slot(str)
    def select(self, key: str) -> None:
        self._selected = key
        self._refresh_selection()
        self.selectionChanged.emit()

    def reset(self) -> None:
        """Forget the current listing (e.g. while switching system/user)."""
        self._services = []
        self._loaded = False
        self._selected = ""
        self.statsChanged.emit()
        self._rebuild()
        self.selectionChanged.emit()

    def update(self, services: list[dict[str, Any]]) -> None:
        self._services = services
        stats = {
            "total": len(services),
            "running": sum(1 for s in services if s.get("active_state") == "active"),
            "failed": sum(1 for s in services if s.get("active_state") == "failed"),
        }
        self._loaded = True
        self._stats = stats
        self.statsChanged.emit()
        self._rebuild()

    def _rebuild(self) -> None:
        needle = self._filter.strip().casefold()
        rows = []
        for s in self._services:
            if needle and needle not in s["name"].casefold() and needle not in (s.get("description") or "").casefold():
                continue
            scope = "user" if s.get("user") else "system"
            rows.append({
                "key": f"svc:{scope}:{s['name']}", "name": s["name"],
                "description": s.get("description") or "",
                "loadState": s.get("load_state") or "",
                "activeState": s.get("active_state") or "",
                "subState": s.get("sub_state") or "",
                "enabledState": s.get("enabled_state") or "",
                "pid": s.get("pid"), "memory": s.get("memory"),
                "user": bool(s.get("user")),
            })
        col = self._sort_col

        def key(r: dict[str, Any]):
            v = r.get(col)
            if col in ("pid", "memory"):
                return v if isinstance(v, (int, float)) else -1
            return str(v or "").casefold()

        rows.sort(key=key, reverse=not self._sort_asc)
        self._apply(rows)
        self._refresh_selection()

    def _refresh_selection(self) -> None:
        info: dict[str, Any] = {}
        if self._selected:
            for r in self._rows:
                if r["key"] == self._selected:
                    info = dict(r)
                    break
        if info != self._selected_info:
            self._selected_info = info
            self.selectionChanged.emit()
