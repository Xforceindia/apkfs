"""Termux / no-root Android helpers for apkfs."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def is_termux() -> bool:
    prefix = os.environ.get("PREFIX", "")
    if "com.termux" in prefix:
        return True
    if os.path.isdir("/data/data/com.termux/files/usr"):
        return True
    if os.environ.get("TERMUX_VERSION"):
        return True
    if shutil.which("termux-setup-storage") or shutil.which("termux-wake-lock"):
        return True
    return False


def apkfs_home() -> Path:
    base = os.environ.get("APKFS_HOME") or str(Path.home() / ".apkfs")
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    (p / "tools").mkdir(exist_ok=True)
    (p / "work").mkdir(exist_ok=True)
    return p


def resolve_user_path(raw: str) -> Path:
    """
    Make Termux paths painless:
      app.apk
      ./app.apk
      /sdcard/Download/app.apk
      ~/storage/shared/Download/app.apk
      Download/app.apk   -> tries common storage roots
    """
    raw = (raw or "").strip().strip('"').strip("'")
    if not raw:
        raise FileNotFoundError("empty path")

    p = Path(raw).expanduser()
    if p.exists():
        return p.resolve()

    # Absolute missing
    if p.is_absolute():
        # try sdcard alias
        alts = _storage_roots()
        name = p.name
        # if user wrote /sdcard/... but symlink missing
        for root in alts:
            candidate = root / Path(*p.parts[1:]) if p.parts[0] == "/" else root / p.name
            # simpler: search by name under Download
            for sub in ("Download", "Downloads", "DCIM", ""):
                c = (root / sub / name) if sub else (root / name)
                if c.exists():
                    return c.resolve()
        raise FileNotFoundError(f"APK not found: {raw}")

    # Relative — try cwd then storage
    cwd_c = (Path.cwd() / p)
    if cwd_c.exists():
        return cwd_c.resolve()

    for root in _storage_roots():
        for sub in ("Download", "Downloads", "apk", "APK", ""):
            c = (root / sub / p) if sub else (root / p)
            if c.exists():
                return c.resolve()
            c2 = (root / sub / p.name) if sub else None
            if c2 and c2.exists():
                return c2.resolve()

    raise FileNotFoundError(
        f"APK not found: {raw}\n"
        f"  tip (Termux): termux-setup-storage\n"
        f"  then: apkfs -i /sdcard/Download/Your.apk"
    )


def _storage_roots() -> list[Path]:
    roots: list[Path] = []
    home = Path.home()
    candidates = [
        Path("/sdcard"),
        Path("/storage/emulated/0"),
        home / "storage" / "shared",
        home / "storage" / "downloads",
        Path("/storage/emulated/0/Download"),
        Path("/sdcard/Download"),
    ]
    for c in candidates:
        try:
            if c.exists():
                roots.append(c)
        except OSError:
            continue
    # unique
    out: list[Path] = []
    seen = set()
    for r in roots:
        s = str(r.resolve()) if r.exists() else str(r)
        if s not in seen:
            seen.add(s)
            out.append(r)
    return out


def wake_lock(enable: bool = True) -> None:
    """Prevent Termux sleep during long patch (no-op if not Termux)."""
    cmd = "termux-wake-lock" if enable else "termux-wake-unlock"
    bin_path = shutil.which(cmd)
    if not bin_path:
        return
    try:
        subprocess.run([bin_path], check=False, capture_output=True)
    except Exception:
        pass


def ensure_termux_pkgs(log=print) -> list[str]:
    """
    Install required Termux packages if missing (no root — uses `pkg`).
    Returns list of actions taken / problems.
    """
    notes: list[str] = []
    if not is_termux():
        return notes
    if not shutil.which("pkg"):
        notes.append("pkg not found")
        return notes

    need = []
    if not shutil.which("java"):
        need.append("openjdk-17")
    if not (shutil.which("aapt2") or shutil.which("aapt")):
        need.append("aapt2")
    # wget/curl usually present
    if not shutil.which("curl") and not shutil.which("wget"):
        need.append("curl")

    for pkg in need:
        log(f"  → pkg install {pkg}")
        try:
            subprocess.run(
                ["pkg", "install", "-y", pkg],
                check=True,
            )
            notes.append(f"installed {pkg}")
        except Exception as e:
            notes.append(f"failed {pkg}: {e}")
    return notes


def java_cmd() -> list[str]:
    """
    Java launcher with Termux-friendly memory defaults.
    Override: export APKFS_JAVA_OPTS='-Xmx1024m'
    """
    java = shutil.which("java") or "java"
    opts = os.environ.get("APKFS_JAVA_OPTS")
    if opts:
        extra = opts.split()
    elif is_termux():
        # phones: keep heap modest; user can raise
        extra = ["-Xmx512m", "-XX:+UseParallelGC"]
    else:
        extra = []
    return [java, *extra]
