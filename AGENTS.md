# AGENTS.md

This repository is **Refract**, a fork of [Mission Center](https://gitlab.com/mission-center-devs/mission-center).

- **`kde/`** — **Refract**, the fork's app: a KDE / Qt Quick (PySide6 + QML) system monitor with
  its own build, install and test tooling. This is where the fork's work happens.
  **Read [`kde/AGENTS.md`](kde/AGENTS.md) before changing anything there.**
- Everything else (`src/`, `resources/`, `data/`, `meson.build`, …) is the upstream GTK4 /
  libadwaita app in Rust. Leave it untouched unless a task is explicitly about it, so the
  fork keeps merging cleanly with upstream.
- `subprojects/magpie` (Mission Center's data engine) and `subprojects/graph-widget` are
  upstream submodules — don't commit changes inside them. Fetch them with
  `git submodule update --init --recursive`.

Remotes: `origin` is upstream on GitLab (read-only); `github` is the fork
(`RobbyBobby77/refract`, branch `liquid-glass-kde`).
