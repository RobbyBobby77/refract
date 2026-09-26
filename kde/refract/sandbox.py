"""Running inside Flatpak.

The Flatpak build keeps Refract's UI in the sandbox, but a system monitor has
to look at the real system: magpie, systemctl, journalctl, kill and the
programs Refract opens run on the host through `flatpak-spawn --host` (as in
Mission Center's Flatpak). Outside Flatpak every helper here is a no-op.
"""

from __future__ import annotations

import configparser
import glob
import os
import sysconfig
from functools import cache
from pathlib import Path

IN_FLATPAK = Path("/.flatpak-info").exists()


@cache
def _instance() -> dict[str, str]:
    info = configparser.ConfigParser(interpolation=None)
    try:
        info.read("/.flatpak-info")
        return dict(info["Instance"])
    except (configparser.Error, KeyError):
        return {}


def host(argv: list[str], *, watch: bool = False, env: dict[str, str] | None = None) -> list[str]:
    """`argv` to run on the host, with extra `env`. With `watch`, the host
    process is stopped when Refract exits (for helpers, not for programs the
    user opens). Outside Flatpak `env` is ignored: pass it to subprocess."""
    if not IN_FLATPAK:
        return argv
    return ["flatpak-spawn", "--host", "--directory=/", *(["--watch-bus"] if watch else []),
            *(f"--env={k}={v}" for k, v in (env or {}).items()), *argv]


def host_path(path: str | Path) -> Path:
    """A host file path as it appears in here. With the host-os permission
    the host's /usr is mounted at /run/host/usr; the home folders the manifest
    grants (Pictures, wallpapers…) keep their paths."""
    p = Path(path)
    if not IN_FLATPAK:
        return p
    if p == Path("/etc/os-release"):
        return Path("/run/host/os-release")
    if p.parts[1:2] == ("usr",):
        return Path("/run/host") / p.relative_to("/")
    return p


def outside_path(path: str | Path) -> str:
    """The host's name for one of our own files (under /app or /usr)."""
    real = os.path.realpath(path)
    info = _instance()
    for prefix, key in (("/app/", "app-path"), ("/usr/", "runtime-path")):
        if real.startswith(prefix) and info.get(key):
            return info[key] + real[len(prefix) - 1:]
    return real


def magpie_command(magpie: Path, hw_db: Path | None) -> list[str]:
    """Command line that starts magpie on the host.

    magpie was built against the Flatpak runtime, whose glibc may be newer than
    the host's, so it runs under the runtime's own dynamic loader and libraries
    (the same files the sandbox uses, read from their location on the host).
    """
    arch = sysconfig.get_config_var("MULTIARCH") or f"{os.uname().machine}-linux-gnu"
    loader = next(iter(sorted(glob.glob(f"/usr/lib/{arch}/ld-linux*.so.*"))), None)
    if loader is None:
        return host([outside_path(magpie)], watch=True)
    libs = ":".join(outside_path(d) for d in ("/app/lib", f"/usr/lib/{arch}") if os.path.isdir(d))
    env = {"LD_PRELOAD": ""} | ({"MC_MAGPIE_HW_DB": outside_path(hw_db)} if hw_db else {})
    return host([_named(outside_path(loader), "magpie"), "--library-path", libs, outside_path(magpie)],
                watch=True, env=env)


def _named(program: str, name: str) -> str:
    """Run `program` under another name: a process is named after the file it
    was started from, so without this magpie would show up as "ld-linux-x86-64".
    The link lives in the directory shared with the host (dangling in here)."""
    shared = socket_dir()
    if shared is None:
        return program
    link = os.path.join(shared, name)
    try:
        if os.path.islink(link) or os.path.exists(link):
            os.unlink(link)
        os.symlink(program, link)
    except OSError:
        return program
    return link


def socket_dir() -> str | None:
    """A directory with the same path inside and outside the sandbox."""
    app_id = os.environ.get("FLATPAK_ID")
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if IN_FLATPAK and app_id and runtime and os.path.isdir(f"{runtime}/app/{app_id}"):
        return f"{runtime}/app/{app_id}"
    return None
