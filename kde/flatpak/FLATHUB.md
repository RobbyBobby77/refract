# Publishing Refract on Flathub

The manifest here is ready for Flathub: every source is pinned (the build runs offline), the
AppStream metadata validates, and `flatpak-builder-lint` reports only the one error explained
below. Flathub builds from a release tag on GitHub, using its own copy of the manifest.

## Status

The repository is public and `refract-v1.1.0` is tagged. `./flathub-manifest.sh refract-v1.1.0`
writes the submission files to `flathub/`; built with Flathub's own settings from GitHub, the
manifest and the built app lint with exactly one error, `finish-args-flatpak-spawn-access`
(see the exception request below). What's left is the pull request.

## Building and linting like Flathub

Flathub builds a tagged release (the version in `refract/__init__.py` and the newest `<release>`
in `../io.github.RobbyBobby77.Refract.metainfo.xml` must match the tag). To check one locally
with Flathub's exact build settings (`flathub-build` mirrors the screenshots and writes full
media URLs, which the repo lint requires):

```sh
./flathub-manifest.sh refract-v1.1.0          # -> flathub/
cd flathub
flatpak run --command=flathub-build org.flatpak.Builder io.github.RobbyBobby77.Refract.yml
flatpak run --command=flatpak-builder-lint org.flatpak.Builder manifest io.github.RobbyBobby77.Refract.yml
flatpak run --command=flatpak-builder-lint org.flatpak.Builder repo repo
```

## Submitting

Follow <https://docs.flathub.org/docs/for-app-authors/submission>: fork
`github.com/flathub/flathub`, create a branch from its **`new-pr`** branch, add
`flathub/io.github.RobbyBobby77.Refract.yml` and `flathub/cargo-sources.json`, and open a pull
request against `new-pr` titled **Add io.github.RobbyBobby77.Refract**.

The linter's `finish-args-flatpak-spawn-access` error needs an exception, which reviewers grant
for system monitors (Mission Center, Resources and JDSystemMonitor have it). Ask for it in the
pull request:

> Refract is a system monitor for KDE Plasma, a fork of Mission Center, and needs the same
> `finish-args-flatpak-spawn-access` exception. In the sandbox `/proc` only lists the sandbox's
> own processes and host processes can't be signalled, so — like Mission Center — its data engine
> (Mission Center's magpie) runs on the host through `flatpak-spawn --host`, and so do the
> commands behind its actions: `kill`/`pkexec` to end processes, `systemctl`/`journalctl` for
> services, `xdg-open`/`systemsettings` for links and settings. It also reads the Plasma wallpaper
> through the host, so apart from `org.freedesktop.Flatpak` it asks only for display access and
> read access to `kdeglobals`.

After the pull request is merged, Flathub creates `github.com/flathub/io.github.RobbyBobby77.Refract`
and invites you to it. Log in to flathub.org with GitHub to verify the app.

## Updating

1. Bump `__version__` in `refract/__init__.py`, add a `<release>` to the metainfo, commit.
2. If magpie or `magpie-bridge/Cargo.lock` changed: `./update-cargo-sources.sh`, commit.
3. Tag and push (`refract-vX.Y.Z`), run `./flathub-manifest.sh refract-vX.Y.Z`, and open a pull
   request with the files from `flathub/` against `flathub/io.github.RobbyBobby77.Refract`.
   The manifest carries `x-checker-data`, so Flathub's bot may open that pull request for you
   when it sees the new tag — check that `cargo-sources.json` didn't need regenerating.
