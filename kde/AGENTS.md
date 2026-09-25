# AGENTS.md — Mission Center, Liquid Glass edition (`kde/`)

A KDE / Qt Quick frontend for Mission Center with an Apple "Liquid Glass" look.
Python (PySide6) + QML, data from Mission Center's Rust engine **magpie** via a small
Rust bridge, with pure-Python collectors as a fallback. Everything for this edition lives
in `kde/`; the upstream GTK app in the repo root is untouched and must stay that way.

## Layout

```
kde/
  missioncenter-glass        run from the checkout (sets PYTHONPATH)
  install.sh                 per-user install to ~/.local (+ --uninstall); builds native parts
  build-native.sh            KWin blur helper (C++) + magpie + bridge (Rust)
  build-shaders.sh           GLSL -> .qsb (compiled packs are committed)
  tools/drive.py             UI test harness / smoke test (see Verifying)
  tools/patch-via-git.sh     stands in for GNU patch when building magpie's nvtop
  native/                    libmcglass.so: C ABI over KWindowEffects (blur-behind)
  magpie-bridge/             mc-glass-bridge: magpie protobuf/nng <-> JSON lines on stdio
  missioncenter_kde/
    app.py                   Session: fonts, engine, context properties, screenshot mode
    bridge.py                Monitor (QML `Monitor`): sampler threads -> Series + models
    models.py                DeviceModel, ProcessModel, ServiceModel (positional)
    effects.py               WindowEffects (QML `WindowEffects`): KWin blur via ctypes
    wallpaper.py             current Plasma wallpaper (plasmashell D-Bus, KConfig fallback)
    backend/magpie.py        magpie client + adapters to the snapshot schema
    backend/collectors.py    Python fallback: CPU/mem/disk/net/GPU/fans/battery
    backend/processes.py     Python fallback: processes/apps; also signal_process, process_details
    backend/services.py      systemd over D-Bus (always used; magpie's list is thinner)
    qml/MissionCenter/       all QML (flat dir; qmldir declares Theme/Prefs/Fmt singletons)
    shaders/                 glass.vert/frag, panel.frag, backdrop.frag (+ .qsb)
```

Data flow: `SamplerWorker` (QThread) calls `sample()` each tick -> queued signal ->
`Monitor._on_system` pushes values into `Series` histories and updates `DeviceModel`.
Processes are sampled only while the Apps page is visible; services poll on their own
thread (`ServiceWorker`, a full listing takes ~0.7 s). QML reads `Monitor.cpu`,
`Monitor.disks`, `Monitor.series("disk.nvme0n1.read")`, etc. The snapshot dict schema is
the contract between backends and UI: magpie.py must produce exactly what collectors.py
produces (see the `_cpu/_memory/_disk/...` mappers).

## Commands

```sh
cd kde
./missioncenter-glass [--page apps|services] [--device KEY] [--theme light|dark]
./build-native.sh          # after editing native/ or magpie-bridge/
./build-shaders.sh         # after editing any shaders/*.vert|*.frag — commit the .qsb too
./install.sh               # refresh the user's installed copy (~/.local/share/missioncenter-glass)
MC_ENGINE=python ./missioncenter-glass   # force the Python collectors
python3 -m missioncenter_kde.backend    # self-test of the Python collectors
```

Runtime deps are distro packages (PySide6, psutil, dbus-python, kf6-kirigami) — never pip
PySide6, its bundled Qt won't match the system Kirigami. Build deps (Fedora):
`cmake gcc-c++ qt6-qtbase-devel kf6-kwindowsystem-devel rust cargo gcc pkgconf-pkg-config
libdrm-devel mesa-libgbm-devel systemd-devel`.

## Verifying a change

1. `python3 -m py_compile` on touched Python files.
2. `python3 tools/drive.py --smoke --out /tmp/shots` — visits every device view, sheet
   and page on the current machine; **exits 1 on any QML warning or JS error**. Look at
   the screenshots of what you changed (they're real renders, not mocks).
3. For targeted checks write a steps file: `[[delay_ms, "js in Main.qml scope", "shot.png"], ...]`
   and run `python3 tools/drive.py steps.json --out /tmp/shots [--theme light]`.
4. Anything involving the see-through window needs a composited capture:
   `spectacle -b -n -f -o /tmp/full.png` while the app is on screen (grabWindow can't see
   KWin's blur).
5. Performance: with the screen on, expect roughly 1–2% of a core for the app plus ~3.5%
   for magpie on Performance, and ~6% for magpie on Apps. Measure per thread via
   `/proc/<pid>/task/*/stat` (utime+stime over 20 s), including the bridge and magpie
   child processes. Measure with the display on: with it off, KWin suspends the window,
   rendering stops and the numbers look better than they are.
6. `./install.sh` so the user's installed app picks up the change; commit and
   `git push github liquid-glass-kde` (the GitHub remote is named `github`).

Qt on Fedora logs to journald when stderr isn't a TTY; set `QT_FORCE_STDERR_LOGGING=1`
to see Qt/scenegraph logs. QML warnings are already routed to Python logging ("QML: …").

## Rules of the design

- **Glass samples the scene.** `GlassSurface` refracts `Theme.glassSource`, the `scene`
  item in Main.qml rendered as a layer. Glass must never be *inside* `scene` (it would
  sample itself) and no ancestor of chrome glass may enable `layer` (screen UVs are derived
  from clip space in glass.vert, assuming OpenGL, which app.py forces). Inside page content
  use `Card`, `PillSegmented`, `PillButton` instead of glass components.
- Pass colours to shaders as `vector4d` (non-premultiplied), not `color` uniforms.
- The scene may be translucent (glass window over KWin blur); glass.frag carries alpha
  through — keep that when editing it.
- Keep fragment shaders branch-free around `texture()` calls: implicit-derivative lookups
  in divergent branches cause visible seams.
- Models are *positional*: rows are rewritten in place and only the tail grows/shrinks, so
  live-sorted tables don't jump. Track selection by `key`, never by row index. Service keys
  include the scope (`svc:user:foo.service`) so system/user units never collide.
- Process actions go through `Monitor.signalProcesses(pids, starts, …)`; `starts` (process
  start ticks) guard against recycled PIDs — keep passing them.
- Heavy or rarely visible views must be lazily instantiated (`Loader`), e.g. the 32-graph
  per-core grid; bindings on hidden items still evaluate every tick.
- Cost control: every magpie request makes magpie refresh that category, so request only
  what's needed — fans/batteries every 3rd sample, the app list every 5th process sample,
  the process table at `Prefs.processInterval` (2 s default). While the window isn't on
  screen (not exposed and not active: minimized, other desktop, display off) `Monitor`
  keeps recording history silently, stops table/service polling and skips UI updates,
  then flushes once it's back (`Monitor.watch`). Keep new periodic work behind the same
  checks.
- Apple semantics: Theme.qml holds the system colours, radii, type; device colours via
  `Theme.deviceColor(name)`. Numbers use `font.features: Theme.tabular`; don't apply it to
  prose (it widens hyphens).

## Gotchas that already cost hours

- `font.pixelSize` is an **int** in QML — `12.5` breaks the whole component.
- Local component names are shadowed by explicit imports: Qt 6.10+ ships a `SearchField`
  in QtQuick.Controls, so ours is `GlassSearchField`. Check new names against Qt types.
- Don't name QML properties `right`, `left`, `index` (a model role called `index` clashes
  with the delegate's), `on…` (reserved for handlers), or reuse an id as a property name
  (`header: header` inside a ListView delegate binds to itself).
- A ShaderEffect uniform named `imageSize` is never filled (stays 0,0). Renamed to
  `pictureSize`. If a uniform looks dead, write a debug shader that outputs it as a colour.
- Python `QVariantList` properties are live references: slicing/iterating them in QML
  re-converts the whole list per element (1.5 ms per graph). Copy into a `var` property
  first (`readonly property var history: series.values`), then slice.
- `QQmlExpression.evaluate()` in PySide returns `(value, isUndefined)`.
- KWin's blur protocol becomes available ~800 ms after startup; effects.py polls.
- configparser mangles KDE's `[Containments][1][Wallpaper]…` group names — use the
  KConfig parser in wallpaper.py (or plasmashell's D-Bus `wallpaper(0)`).
- magpie units: process CPU is % of one core (we divide by logical CPUs), fan PWM is 0–1,
  temperatures are milli-Kelvin, battery percentage/capacity are 0–1, energy is mWh,
  disk rx = read / tx = write. Its first GPU/apps replies are empty while it warms up.
- magpie's build applies nvtop patches with GNU `patch` and ignores failures; without
  `patch`, `MC_PATCH_BINARY=tools/patch-via-git.sh` (build-native.sh sets it) mirrors
  patch's fuzz/reject behaviour. If GPU code fails to compile, check the patches applied.
- A process that `exec`s keeps its PID and start time — the Python process cache keys on
  (start, comm) for that reason.

## Conventions

- Match the surrounding style: typed Python with small helpers and docstrings on public
  API; QML with `required property` delegates and comments only where intent isn't obvious.
- Commit messages: imperative subject, a short body explaining *why*.
- Never modify `subprojects/` (upstream submodules) or the GTK app in the repo root.
