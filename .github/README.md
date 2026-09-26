<p align="center">
  <img src="https://github.com/RobbyBobby77/refract/raw/main/kde/branding/banner.png" alt="Refract — your system at a glance, in Liquid Glass, for KDE Plasma" width="900"/>
</p>

<p align="center">
  <b>A system monitor for KDE Plasma, designed the way Apple would have made it.</b><br/>
  CPU · memory · disks · network · GPU · fans · battery · apps · services
</p>

<p align="center">
  <a href="#install"><img alt="KDE Plasma 6" src="https://img.shields.io/badge/KDE%20Plasma-6-1D99F3?style=flat-square&logo=kde&logoColor=white"/></a>
  <img alt="Qt 6 + QML" src="https://img.shields.io/badge/Qt%206-QML-41CD52?style=flat-square&logo=qt&logoColor=white"/>
  <a href="#credits--licence"><img alt="GPL-3.0-or-later" src="https://img.shields.io/badge/licence-GPL--3.0--or--later-A37BFF?style=flat-square"/></a>
  <a href="#credits--licence"><img alt="Based on Mission Center" src="https://img.shields.io/badge/based%20on-Mission%20Center-FF5A82?style=flat-square"/></a>
</p>

<p align="center">
  <img src="https://github.com/RobbyBobby77/refract/raw/main/kde/screenshots/performance-dark.png" alt="Refract's Performance page: a glass sidebar of live device graphs beside CPU utilization, stats and processor details" width="900"/>
</p>

## Why Refract

- **Liquid Glass, for real.** The sidebar, toolbar, menus and sheets are a refractive glass material
  — frosted, bent at the edges, catching the light — floating over a window that shows your
  desktop through KWin's own blur. Not a blur-and-opacity imitation.
- **Everything, live.** Every CPU core, memory composition, each disk and volume, Wi‑Fi and
  Ethernet, GPU utilization, memory, clocks, power and video engines, fans and batteries — each
  with a smooth, GPU-rendered graph and a live sparkline in the sidebar.
- **Apps and processes that make sense.** Apps are grouped the way you think of them, with
  live CPU, memory, disk and GPU use, heat shading, search, a process tree, and Stop · Quit ·
  Force Quit (safe against recycled process IDs).
- **Services, too.** System and user systemd services: status, startup type, memory, start /
  stop / restart / enable / disable, and the journal.
- **Light on your machine.** Data comes from Mission Center's efficient Rust engine, and Refract
  eases off whenever its window isn't on screen — the graphs keep recording, everything else rests.
- **At home on KDE.** Your icon theme, your accent colour, your wallpaper, System Settings
  shortcuts, and native Wayland window handling — or KDE's own title bar if you prefer.

<table>
  <tr>
    <td><img src="https://github.com/RobbyBobby77/refract/raw/main/kde/screenshots/apps-dark.png" alt="Apps page with a selected app and the floating action bar"/></td>
    <td><img src="https://github.com/RobbyBobby77/refract/raw/main/kde/screenshots/gpu-dark.png" alt="GPU page with utilization, memory and video-engine graphs"/></td>
  </tr>
  <tr>
    <td><img src="https://github.com/RobbyBobby77/refract/raw/main/kde/screenshots/services-dark.png" alt="Services page listing systemd units"/></td>
    <td><img src="https://github.com/RobbyBobby77/refract/raw/main/kde/screenshots/memory-light.png" alt="Memory page in light mode"/></td>
  </tr>
  <tr>
    <td><img src="https://github.com/RobbyBobby77/refract/raw/main/kde/screenshots/settings-light.png" alt="Settings sheet"/></td>
    <td><img src="https://github.com/RobbyBobby77/refract/raw/main/kde/screenshots/about-dark.png" alt="About Refract"/></td>
  </tr>
</table>

## Install

Refract runs on KDE Plasma 6 (developed and tested on Wayland). Install the dependencies from your distribution
so PySide6 and Kirigami share the same Qt:

| Distribution | Packages |
|---|---|
| Fedora | `python3-pyside6 python3-psutil python3-dbus kf6-kirigami` |
| Arch | `pyside6 python-psutil python-dbus kirigami` |
| openSUSE | `python3-pyside6 python3-psutil python3-dbus-python kf6-kirigami` |
| Debian / Ubuntu | `python3-pyside6.qtquick python3-pyside6.qtquickcontrols2 python3-psutil python3-dbus qml6-module-org-kde-kirigami` |

For the see-through glass window and Mission Center's data engine, also install a build
toolchain (Fedora names shown):

```sh
sudo dnf install cmake gcc-c++ qt6-qtbase-devel kf6-kwindowsystem-devel \
                 rust cargo gcc pkgconf-pkg-config libdrm-devel mesa-libgbm-devel systemd-devel
```

Then:

```sh
git clone --recurse-submodules https://github.com/RobbyBobby77/refract.git
cd refract/kde
./install.sh            # installs for your user under ~/.local — no root needed
```

Launch **Refract** from your application launcher, or run `refract`. To update, pull and run
`./install.sh` again; to remove it, `./install.sh --uninstall`. Without the toolchain, Refract
still runs — with a solid window background and its built-in data collectors.

**Shortcuts:** <kbd>Ctrl</kbd>+<kbd>1</kbd> / <kbd>2</kbd> / <kbd>3</kbd> switch pages ·
<kbd>Ctrl</kbd>+<kbd>F</kbd> search · <kbd>Ctrl</kbd>+<kbd>,</kbd> settings ·
<kbd>Delete</kbd> quits the selected app · <kbd>Esc</kbd> clears the selection.

## Make it yours

Settings lets you pick light, dark or automatic appearance; a multicolour, single-hue or KDE
accent; Clear or Tinted glass (or Reduce Transparency); a Glass, Wallpaper or Solid window
background; window buttons on the left or right; update speed, graph history and how often the
process list refreshes; decimal or binary units, bits or bytes, °C or °F.

## Under the hood

Refract is written in Python and QML on Qt 6 (PySide6), with Kirigami for KDE integration.
The glass is a custom GLSL material; a small C++ helper asks KWin for blur-behind, and a small
Rust bridge talks to **magpie**, Mission Center's data engine, which Refract uses unmodified.
Details for developers are in [`kde/README.md`](https://github.com/RobbyBobby77/refract/blob/main/kde/README.md) and, for AI agents,
[`AGENTS.md`](https://github.com/RobbyBobby77/refract/blob/main/AGENTS.md).

## Credits & licence

Refract is a modified version of [**Mission Center**](https://missioncenter.io)
([source](https://gitlab.com/mission-center-devs/mission-center)), © the Mission Center
developers. Starting in September 2026 this fork replaced Mission Center's GTK interface with
a new Qt Quick one and added a bridge to its magpie engine. **Refract is an independent project
and is not affiliated with or endorsed by the Mission Center developers.**

Refract is licensed under the **GNU General Public License v3.0 or later**, like Mission Center —
see [`COPYING`](https://github.com/RobbyBobby77/refract/blob/main/COPYING). The Inter typeface is © The Inter Project Authors, under the SIL Open
Font License. The screenshots show KDE's *Nuvole* wallpaper. The original Mission Center app and
its README remain in this repository, unchanged.
