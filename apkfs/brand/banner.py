from __future__ import annotations

import sys
from datetime import datetime

from apkfs import __version__

BRAND = "Professor X (FS)"
TAGLINE = "Fully Automatic APK Lab Suite"
SIGN = "Professor X (FS)"


class _C:
    R = "\033[0m"
    B = "\033[1m"
    D = "\033[2m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YEL = "\033[93m"
    BLU = "\033[94m"
    MAG = "\033[95m"
    CYN = "\033[96m"
    GRY = "\033[90m"
    W = "\033[97m"


def _on() -> bool:
    return sys.stdout.isatty()


def _c(code: str, s: str) -> str:
    return f"{code}{s}{_C.R}" if _on() else s


def print_banner() -> None:
    line = "═" * 62
    print(_c(_C.CYN, line))
    print(
        _c(_C.B + _C.W, "  apkfs")
        + _c(_C.GRY, f"  v{__version__}")
        + _c(_C.D, "  ·  ")
        + _c(_C.MAG + _C.B, BRAND)
    )
    print(_c(_C.GRY, f"  {TAGLINE}"))
    print(_c(_C.CYN, line))
    print(_c(_C.GRY, f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}  ·  one command · full auto"))
    print()


def footer(seconds: float | None = None) -> None:
    print()
    print(_c(_C.CYN, "─" * 62))
    msg = f"  🧠⚡  {SIGN}  ⚡🧠"
    print(_c(_C.MAG + _C.B, msg))
    if seconds is not None:
        print(_c(_C.GRY, f"  time: {seconds:.2f}s"))
    print(_c(_C.CYN, "─" * 62))
    print()
