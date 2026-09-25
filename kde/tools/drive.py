#!/usr/bin/env python3
"""Drive the real app for testing: run JS steps, take screenshots, and fail on
QML warnings.

    python3 tools/drive.py --smoke [--out DIR] [--theme light|dark]
    python3 tools/drive.py STEPS.json [--out DIR] [app options...]

STEPS.json is a list of [delay_ms, js, png] triples. `js` is evaluated in
Main.qml's scope, so ids such as win, actions, menu, settingsSheet, procSheet,
svcSheet and confirm are reachable, plus Monitor, Prefs and Theme. `png` (a
file name, relative to --out) is saved after the JS ran; use "" to skip.

--smoke visits every device view (whatever this machine has), the per-core
grid, Settings, the Apps page with its menu, details sheet and tree mode, and
the Services page with its details sheet.

Exit status is 1 if any QML warning or JS error was logged. Screenshots come
from QQuickWindow.grabWindow(), which does not include KWin's blur-behind;
use `spectacle -b -n -f -o FILE` for a composited capture.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QCoreApplication, QTimer  # noqa: E402

from missioncenter_kde.app import Session, parse_args  # noqa: E402


class _ProblemCounter(logging.Handler):
    """Counts QML warnings and failed evaluate() calls."""

    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.problems: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if message.startswith("QML:") or message.startswith("evaluate("):
            self.problems.append(message)


def smoke_steps(session: Session) -> list[tuple[int, str, str]]:
    keys = json.loads(session.evaluate(
        "JSON.stringify(Array.from({ length: Monitor.devices.count }, (_, i) => Monitor.devices.get(i).key))") or "[]")
    steps: list[tuple[int, str, str]] = []
    for i, key in enumerate(keys):
        steps.append((200, f"win.device = {json.dumps(key)}", ""))
        steps.append((900, "", f"device-{i:02d}-{key.replace(':', '_')}.png"))
    steps += [
        (200, "win.device = 'cpu'; Prefs.cpuPerCore = true", ""),
        (900, "", "cpu-per-core.png"),
        (200, "Prefs.cpuPerCore = false; settingsSheet.open()", ""),
        (900, "", "settings.png"),
        (200, "settingsSheet.close(); win.page = 'apps'", ""),
        (3000, "Monitor.processes.select(Monitor.processes.get(1).key)", ""),
        (600, "", "apps.png"),
        (200, "actions.processMenu(Monitor.processes.get(1), 400, 400)", ""),
        (900, "", "apps-menu.png"),
        (200, "menu.close(); actions.processDetails(Monitor.processes.get(1))", ""),
        (1200, "", "process-details.png"),
        (200, "procSheet.close(); Prefs.processTree = true", ""),
        (900, "", "apps-tree.png"),
        (200, "Prefs.processTree = false; Monitor.processes.select(''); win.page = 'services'", ""),
        (3500, "", "services.png"),
        (200, "actions.serviceDetails(Monitor.services.get(2))", ""),
        (1500, "", "service-details.png"),
        (200, "svcSheet.close(); win.page = 'performance'", ""),
        (600, "", ""),
    ]
    return steps


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    cli.add_argument("steps", nargs="?", help="JSON steps file (omit with --smoke)")
    cli.add_argument("--smoke", action="store_true", help="visit every page, sheet and device")
    cli.add_argument("--out", help="directory for screenshots (none are saved without it)")
    args, app_args = cli.parse_known_args()
    if not args.smoke and not args.steps:
        cli.error("give a steps file or --smoke")

    out = Path(args.out) if args.out else None
    if out:
        out.mkdir(parents=True, exist_ok=True)

    counter = _ProblemCounter()
    logging.getLogger().addHandler(counter)
    # --screenshot keeps the run from overwriting the user's last page/device.
    session = Session(parse_args(["--size", "1320x860", "--screenshot", "-"] + app_args))
    if session.window is None:
        session.close(1)
        return 1

    def run(steps: list[tuple[int, str, str]]) -> None:
        t = 0
        for delay, js, png in steps:
            t += delay

            def act(js: str = js, png: str = png) -> None:
                if js:
                    session.evaluate(js)
                if png and out:
                    session.screenshot(str(out / png))
                    print("saved", out / png, flush=True)

            QTimer.singleShot(t, act)
        QTimer.singleShot(t + 300, QCoreApplication.quit)

    def start_smoke() -> None:
        try:
            run(smoke_steps(session))
        except Exception as error:  # noqa: BLE001 - a broken harness must fail the run
            counter.problems.append(f"smoke setup failed: {error!r}")
            QCoreApplication.quit()

    if args.smoke:
        QTimer.singleShot(3500, start_smoke)
    else:
        run([tuple(s) for s in json.loads(Path(args.steps).read_text())])

    session.run()
    for problem in counter.problems:
        print("PROBLEM:", problem, file=sys.stderr)
    print(f"{len(counter.problems)} problem(s)")
    return 1 if counter.problems else 0


if __name__ == "__main__":
    sys.exit(main())
