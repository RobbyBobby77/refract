# Publishing Refract on Flathub

The manifest here is ready for Flathub: every source is pinned (the build runs offline), the
AppStream metadata validates, and `flatpak-builder-lint` reports only the two errors explained
below. Flathub builds from a release tag on GitHub, using its own copy of the manifest.

## Before the first submission

1. **Make the GitHub repository public.** Flathub clones the source, fetches the screenshots from
   it and checks that the app ID `io.github.RobbyBobby77.Refract` belongs to
   `github.com/RobbyBobby77/refract` — the linter's `appid-url-not-reachable` error goes away
   once it's public.
2. **Tag the release** that Flathub should build (the version in `refract/__init__.py` and the
   newest `<release>` in `../io.github.RobbyBobby77.Refract.metainfo.xml` must match it):

   ```sh
   git tag refract-v1.1.0 && git push github refract-v1.1.0
   ```

3. **Write the Flathub manifest** for that tag, then build and lint it exactly as Flathub will:

   ```sh
   ./flathub-manifest.sh refract-v1.1.0          # -> flathub/
   cd flathub
   flatpak run org.flatpak.Builder --force-clean --sandbox --user --install-deps-from=flathub \
       --ccache --mirror-screenshots-url=https://dl.flathub.org/media/ --repo=repo \
       builddir io.github.RobbyBobby77.Refract.yml
   flatpak run --command=flatpak-builder-lint org.flatpak.Builder manifest io.github.RobbyBobby77.Refract.yml
   flatpak run --command=flatpak-builder-lint org.flatpak.Builder repo repo
   ```

   Expect exactly one linter error once the repository is public:
   `finish-args-flatpak-spawn-access` (see below). While it's still private you'll also see
   `appid-url-not-reachable`, `appstream-missing-screenshots` and
   `appstream-screenshots-not-mirrored-in-ostree`, which all come from GitHub refusing access.
   (This whole sequence was rehearsed from a local clone: the git + submodule checkout and the
   offline build work.)

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
