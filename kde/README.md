# Refract — developer guide

This folder is **Refract**, a Liquid Glass system monitor for KDE Plasma forked from
[Mission Center](https://gitlab.com/mission-center-devs/mission-center). For what it looks like and
how to install it, see the [project page](../.github/README.md); this page is about how it's built.
AI agents: start with [`AGENTS.md`](AGENTS.md).

## Design notes

- **Liquid Glass** (`shaders/glass.frag`) is a real refractive material, not a blur + opacity.
  The window's content is rendered into a layer; glass surfaces sample it at their screen position
  (derived in the vertex stage), frost it with a mip-biased golden-spiral blur, bend it through a
  convex rim (with slight chromatic dispersion), boost vibrancy, and add a specular hairline that
  catches light on opposite edges.
- Following Apple's guidance, glass is reserved for the **navigation layer** — sidebar, toolbar
  controls, the floating action bar, menus and sheets. Content sits on quieter translucent cards
  (`shaders/panel.frag`) so it stays legible.
- The window **background** is glass too: a neutral translucent tint over KWin's blur of whatever is
  behind the window (`native/`, `effects.py`), like a macOS window. "Wallpaper" (a subtle tint from
  the Plasma wallpaper) and "Solid" are alternatives; without KWin's blur it falls back to solid.
- Apple system colours, concentric corner radii, Inter / Inter Display typography with tabular
  figures, "traffic light" window controls, capsule controls and spring animations.
- Settings: appearance (auto/light/dark), accent colour (multicolour or one hue), Clear vs Tinted
  glass, Reduce Transparency, update interval, graph history, units, and an option to use KDE's own
  window decorations instead of the custom chrome.

## Data engine

When built, Refract runs Mission Center's own collector, **magpie** (`../subprojects/magpie`), exactly
as the GTK app does. `magpie-bridge/` is a small Rust helper that starts magpie on a private nng
socket and relays its protobuf IPC as JSON lines; `backend/magpie.py` maps the replies onto the UI.
That brings nvtop-based GPU data (encode/decode, per-process GPU use for every vendor), SMART-capable
disk info, battery history and Mission Center's app detection, at a fraction of the CPU cost.
Without the native build, pure-Python collectors (`backend/collectors.py`, `processes.py`) take over;
services always use systemd over D-Bus. Settings → Performance shows which engine is running.

## Running from a checkout

Install the runtime and (optional) build dependencies listed on the [project page](../.github/README.md#install)
— or let `./install.sh --deps` install them with your distribution's package manager — then:

```sh
./build-native.sh                # optional: KWin blur helper + magpie + refract-bridge + hw.db
./bin/refract                    # run from the checkout
./install.sh                     # install for your user (~/.local); builds the native parts if it can
python3 tools/drive.py --smoke   # UI smoke test: every page, sheet and device; fails on QML errors
python3 tools/screenshots.py dark && python3 tools/screenshots.py light   # README screenshots
```

Useful flags: `--page apps|services`, `--device memory|disk:nvme0n1|net:wlp…`,
`--theme light|dark`, `--screenshot out.png`.

## Flatpak

`flatpak/build.sh` builds Refract as a Flatpak and writes `flatpak/refract.flatpak`, a single-file
bundle that installs on any distribution and fetches KDE's runtime from Flathub
(`--install` also installs it for you). It sets up flatpak-builder and the SDKs if needed;
build files go to `~/.cache/refract-flatpak`.

- The UI runs in the sandbox on `org.kde.Platform` 6.11 with Qt's PySide6 BaseApp;
  `flatpak/install-app.sh` builds and installs everything into `/app` in the same layout as
  `install.sh`.
- A system monitor has to see the real system, so — like Mission Center's Flatpak — magpie runs
  **on the host** through `flatpak-spawn --host`. It was built against the runtime, so it runs under
  the runtime's own dynamic loader and libraries, read from their host location in
  `/.flatpak-info`; that makes it independent of the host's glibc. The bridge stays in the sandbox
  and they meet on a socket in `$XDG_RUNTIME_DIR/app/<app id>`, which both sides can see.
- `/proc` in the sandbox only shows the sandbox, and signals can't cross it: process owners,
  process details, Stop/Quit/Force Quit, `systemctl`, `journalctl` and the programs Refract opens
  all run on the host too. `refract/sandbox.py` has the helpers (`host()`, `host_path()`); outside
  Flatpak they change nothing.

## Layout

```
refract/            the app (Python package)
  app.py            bootstrap: fonts, QML engine, screenshot mode
  bridge.py         Monitor: sampler threads → graph histories + models for QML
  models.py         sidebar devices, apps/process tree, services (positional list models)
  wallpaper.py      finds the Plasma wallpaper
  effects.py        KWin blur-behind via the native helper
  sandbox.py        Flatpak: running commands and finding files on the host
  backend/          magpie adapter + fallback collectors for /proc, /sys, NetworkManager, systemd
  qml/Refract/      design system (Theme, Glass*, Card, Graph…) and pages
  shaders/          GLSL sources + compiled .qsb packs (./build-shaders.sh to rebuild)
  fonts/            Inter (SIL OFL)
bin/refract         launcher for a source checkout
branding/           icon, banner and social-preview generators and the brand guide
native/             C++ helper wrapping KWindowEffects (blur-behind)
magpie-bridge/      Rust JSON bridge to magpie
flatpak/            Flatpak manifest, build.sh (→ refract.flatpak), install-app.sh
tools/              drive.py (UI smoke test), screenshots.py (README images), patch-via-git.sh
```

The original Mission Center GTK application in the repository root is untouched.

## Credits & licence

Refract is a modified version of **Mission Center**, © the Mission Center developers
([gitlab.com/mission-center-devs](https://gitlab.com/mission-center-devs/mission-center)). This
fork (from September 2026) replaces the GTK frontend with a new Qt Quick one and adds the bridge
to Mission Center's magpie engine, which is used unmodified. Refract is an independent project and
is not affiliated with or endorsed by the Mission Center developers.

Like Mission Center, Refract is licensed under the **GPL-3.0-or-later** (see [`COPYING`](../COPYING)).
Inter is © The Inter Project Authors, under the SIL Open Font License
(`refract/fonts/Inter-LICENSE.txt`).

Working on the code (or pointing an AI agent at it)? See [`AGENTS.md`](AGENTS.md).
