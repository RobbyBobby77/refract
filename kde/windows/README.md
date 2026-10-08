# Refract for Windows

Refract's Qt Quick interface runs natively on 64-bit Windows 10 and 11. The Windows
backend uses psutil, Windows performance counters, DXGI, and the Service Control
Manager; no KDE installation, Linux environment, Rust build, or submodule checkout
is needed. Tested on Windows 11 x64.

## Portable application

Extract **Refract-Windows-x64.zip**, keep the whole `Refract` folder together, and
double-click **Refract.exe**. Python is included. Preferences are stored per user
under `HKEY_CURRENT_USER\Software\Refract\Refract`.

Normal monitoring works without administrator rights. Windows can deny access to
protected processes and service controls; run the executable as administrator if
you intend to manage those. Refract reports permission errors and does not request
elevation automatically. On Windows, **End Process** and **Force Quit** both
terminate immediately and show a confirmation; they cannot request a graceful
application quit. Suspend/resume works for processes you have access to.

## Run from source

Install 64-bit Python 3.10 or newer. From the repository's root, in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\kde\windows\run.ps1
powershell -ExecutionPolicy Bypass -File .\kde\windows\run.ps1 --theme light --page apps
```

The script creates `kde/.venv` and installs the Windows dependencies on its first
run. Use `-Python C:\path\to\python.exe` to select an interpreter. If you already
have an environment, install `kde/windows/requirements.txt` into it, set
`PYTHONPATH` to the absolute `kde` directory, then run `python -m refract`.

## Build and verify

```powershell
powershell -ExecutionPolicy Bypass -File .\kde\windows\build.ps1
$env:PYTHONPATH = (Resolve-Path .\kde).Path
.\kde\.venv\Scripts\python.exe -m unittest discover -s .\kde\tests -v
.\kde\.venv\Scripts\python.exe .\kde\tools\drive.py --smoke --out .\windows-shots
```

The build produces `kde/windows/dist/Refract-Windows-x64.zip`. `build.ps1` accepts
`-OutputDirectory` and bundles QML, shaders, fonts, icons, and dependency notices.
The GitHub Windows workflow builds and uploads the same archive. The smoke test
uses temporary INI preferences, visits all available devices, Apps, Services, and
their sheets, and fails on QML warnings.

## Windows coverage

- CPU and per-core use, speed, process/thread/handle counts, and uptime.
- Memory use and available/cache/commit/page-file statistics.
- Disk read/write rates, active time, response time, and mounted volume capacities.
  Physical capacity is the sum of mounted volumes; unallocated space is excluded.
  Rates depend on Windows disk performance counters being enabled. Missing counters
  leave rates unavailable while volume information remains visible.
- Network use, link speed, addresses, and adapter names.
- WDDM GPU use and dedicated/shared memory use, with DXGI names and budgets.
- Battery percentage, charging state, and remaining discharge time.
- Processes, window-based application grouping, details, terminate, suspend/resume.
- Windows services, automatic/manual/disabled startup, and start/stop/restart controls.
  Logs show recent Service Control Manager events in the System event log.
- Desktop wallpaper tinting, settings links, clipboard, and file/URL opening.

CPU/GPU temperatures, fan sensors, GPU clocks/power, per-process GPU use, open-file
counts, Wi-Fi
SSID/radio details, detailed battery health, CPU cache/virtualization metadata, and
Linux memory categories have no collector in this port. Unavailable values display
as dashes. Process pause state reflects pauses issued by Refract; external pauses
may not be reflected in the table. Windows has one service scope, so the Linux
System/User selector is hidden. KWin desktop blur is unavailable; the in-window
glass rendering and wallpaper/opaque background modes remain available.

The fast process collector batches Windows NT process snapshots (also used by
psutil). It validates the returned layout and falls back to documented
Toolhelp/psutil calls if a future Windows version changes that API; the fallback
can be slower on machines with many protected processes.

## License and sources

Refract is GPL-3.0-or-later; see `COPYING.txt` in the portable distribution and
`COPYING` at the repository root. Source and build scripts:
[RobbyBobby77/refract](https://github.com/RobbyBobby77/refract).
Qt/PySide, psutil, and the bundled Inter fonts retain their respective licenses
and notices. Portable action icons are original Refract assets.
