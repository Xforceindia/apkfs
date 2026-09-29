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


def _norm_name(s: str) -> str:
    """Number Box.apk / numberbox.apk / Number_Box.APK → numberbox.apk"""
    return s.lower().replace(" ", "").replace("_", "").replace("-", "")


def _is_apk_name(name: str) -> bool:
    low = name.lower()
    return low.endswith((".apk", ".apks", ".apkm", ".xapk"))


def _rank_match(cand_name: str, want_name: str) -> tuple:
    """
    Lower tuple = better match.
    Prefer exact → case-fold exact → same stem with fewer space/underscore diffs.
    """
    if cand_name == want_name:
        return (0, 0, cand_name)
    if cand_name.lower() == want_name.lower():
        return (1, 0, cand_name)
    cn, wn = _norm_name(cand_name), _norm_name(want_name)
    if cn != wn:
        return (9, 99, cand_name)
    # both normalize equal — prefer name closer in length / fewer spaces stripped
    space_penalty = abs(cand_name.count(" ") - want_name.count(" "))
    len_penalty = abs(len(cand_name) - len(want_name))
    # prefer no-space cand when want has no spaces (Numberbox vs Number Box)
    want_nospace = " " not in want_name and "_" not in want_name and "-" not in want_name
    if want_nospace and (" " in cand_name or "_" in cand_name):
        space_penalty += 5
    if not want_nospace and (" " not in cand_name):
        # user typed spaces → prefer spaced file
        space_penalty += 2
    return (2, space_penalty + len_penalty, cand_name)


def _best_match(hits: list[Path], want_name: str) -> Path | None:
    if not hits:
        return None
    ranked = sorted(hits, key=lambda h: _rank_match(h.name, want_name))
    return ranked[0]


def resolve_user_path(raw: str) -> Path:
    """
    Make Termux / desktop paths painless (ApkPatcher-style -i):
      Numberbox.apk
      Number Box.apk
      ./app.apk
      /sdcard/Download/app.apk
      ~/storage/shared/Download/app.apk
      Download/app.apk   -> tries common storage roots

    Fuzzy: ignore case + spaces/underscores/dashes in the *filename*
    so  -i Numberbox.apk  also finds  Number Box.apk
    When both exist, prefer the closer name (exact / casefold first).
    """
    raw = (raw or "").strip().strip('"').strip("'")
    if not raw:
        raise FileNotFoundError("empty path")

    p = Path(raw).expanduser()
    if p.exists() and p.is_file():
        return p.resolve()
    if p.exists() and p.is_dir():
        raise FileNotFoundError(f"path is a directory, not an APK: {raw}")

    target_norm = _norm_name(p.name)
    want_name = p.name
    search_names = {p.name, p.name.replace(" ", ""), p.name.replace(" ", "_")}

    def _match_file(cand: Path) -> bool:
        if not cand.is_file():
            return False
        if not _is_apk_name(cand.name):
            return False
        if cand.name == p.name or cand.name in search_names:
            return True
        return _norm_name(cand.name) == target_norm

    def _scan_dir(folder: Path, depth: int = 0):
        """Yield matching APKs under folder (shallow first)."""
        if not folder.is_dir():
            return
        try:
            entries = list(folder.iterdir())
        except OSError:
            return
        files = [e for e in entries if e.is_file()]
        dirs = [e for e in entries if e.is_dir()]
        for e in files:
            if _match_file(e):
                yield e
        if depth < 2:
            for d in dirs:
                # skip huge / hidden
                if d.name.startswith(".") or d.name in ("Android", "obb", "data"):
                    continue
                yield from _scan_dir(d, depth + 1)

    # 1) exact relative to cwd
    cwd_c = Path.cwd() / p
    if cwd_c.exists() and cwd_c.is_file():
        return cwd_c.resolve()

    # 2) fuzzy in cwd — collect + rank (don't return first iterdir hit)
    cwd_hits: list[Path] = []
    seen_cwd: set[str] = set()
    for hit in _scan_dir(Path.cwd(), depth=0):
        try:
            key = str(hit.resolve())
        except OSError:
            key = str(hit)
        if key not in seen_cwd:
            seen_cwd.add(key)
            cwd_hits.append(hit)
    best = _best_match(cwd_hits, want_name)
    if best is not None:
        return best.resolve()

    # 3) absolute missing — try storage roots + fuzzy by filename
    roots = _storage_roots()
    parents_try: list[Path] = []
    if p.is_absolute():
        parents_try.append(p.parent)
    parents_try.extend(roots)
    for root in roots:
        for sub in ("Download", "Downloads", "apk", "APK", "DCIM", ""):
            parents_try.append((root / sub) if sub else root)

    seen: set[str] = set()
    all_hits: list[Path] = []
    for folder in parents_try:
        try:
            key = str(folder.resolve()) if folder.exists() else str(folder)
        except OSError:
            key = str(folder)
        if key in seen:
            continue
        seen.add(key)
        # exact name variants first
        for sn in search_names:
            c = folder / sn
            if c.exists() and c.is_file() and _is_apk_name(c.name):
                all_hits.append(c)
        for hit in _scan_dir(folder, depth=1):
            try:
                hk = str(hit.resolve())
            except OSError:
                hk = str(hit)
            if hk not in {str(x.resolve()) if x.exists() else str(x) for x in all_hits}:
                all_hits.append(hit)

    # dedupe
    dedup: list[Path] = []
    dseen: set[str] = set()
    for h in all_hits:
        try:
            k = str(h.resolve())
        except OSError:
            k = str(h)
        if k not in dseen:
            dseen.add(k)
            dedup.append(h)

    best = _best_match(dedup, want_name)
    if best is not None:
        return best.resolve()

    raise FileNotFoundError(
        f"APK not found: {raw}\n"
        f"  tip: put the file in current dir or /sdcard/Download/\n"
        f"  tip: apkfs -i Numberbox.apk   (spaces/case OK — fuzzy match)\n"
        f"  Termux: termux-setup-storage first"
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
