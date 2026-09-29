#!/usr/bin/env python3
"""apkfs — Professor X (FS) · fully automatic APK lab suite CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from apkfs import __version__
from apkfs.brand.banner import BRAND, print_banner


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="apkfs",
        description=f"apkfs v{__version__} — {BRAND} · fully automatic APK lab suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
examples:
  apkfs -i app.apk                 # FULL AUTO (detect → plan → patch → sign)
  apkfs -i app.apks                # auto merge + patch
  apkfs -i app.apk -c burp.pem     # auto + your proxy CA
  apkfs -i app.apk --dry-run       # only detect + plan + report
  apkfs -m app.apks                # merge only
  apkfs doctor                     # check java / jars
  apkfs pairip -i app.apk          # PairIP-focused recovery helper
  apkfs manual -i app.apk -f -p    # legacy manual flags (power users)

{BRAND}
""",
    )

    p.add_argument("-V", "--version", action="version", version=f"apkfs {__version__} · {BRAND}")

    sub = p.add_subparsers(dest="command")

    # default-style top flags also work without subcommand
    p.add_argument("-i", dest="input", help="APK / APKS / APKM / XAPK path (FULL AUTO)")
    p.add_argument("-m", dest="merge", help="Merge split APK only")
    p.add_argument("-c", dest="certs", nargs="*", help="Proxy CA cert paths (.pem/.crt)")
    p.add_argument("--dry-run", action="store_true", help="Detect + plan only, write report")
    p.add_argument("--corex", action="store_true", help="Experimental PairIP CoreX (arm64/split)")
    p.add_argument("--experimental", action="store_true", help="Allow experimental strategies")
    p.add_argument("-a", "--apkeditor", action="store_true", help="Prefer APKEditor decompiler")
    p.add_argument("-u", "--unsigned", action="store_true", help="Keep unsigned / CRC path")
    p.add_argument("--no-ads", action="store_true", help="Do not auto-apply ads patches")
    p.add_argument("--no-usb-ss", action="store_true", help="Skip USB/screenshot lab patches")
    p.add_argument("--report-dir", type=str, help="Where to write plan/report JSON")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose engine argv / logs")
    p.add_argument("-C", "--credits", action="store_true", help="Show credits")

    # doctor
    sub.add_parser("doctor", help="Check Java, jars, environment")

    # pairip helper
    sp = sub.add_parser("pairip", help="PairIP-focused workflow (auto flags)")
    sp.add_argument("-i", dest="input", required=True, help="APK path")
    sp.add_argument("--corex", action="store_true")
    sp.add_argument("-c", dest="certs", nargs="*")
    sp.add_argument("-v", "--verbose", action="store_true")

    # manual legacy passthrough
    sm = sub.add_parser("manual", help="Manual engine flags (legacy power-user mode)")
    sm.add_argument("engine_args", nargs=argparse.REMAINDER, help="Args passed to engine")

    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.credits:
        from apkfs.engine.Utils.Credits import Credits

        Credits()
        return 0

    # subcommand: doctor
    if args.command == "doctor":
        return cmd_doctor()

    # subcommand: manual
    if args.command == "manual":
        return cmd_manual(args.engine_args)

    # subcommand: pairip
    if args.command == "pairip":
        from apkfs.auto.pipeline import run_auto

        return run_auto(
            Path(args.input),
            certs=[Path(c) for c in (args.certs or [])],
            force_corex=bool(args.corex),
            experimental=True,
            no_ads=False,
            verbose=bool(args.verbose),
        )

    # merge only
    if args.merge:
        from apkfs.auto.pipeline import run_auto

        return run_auto(Path(args.merge), merge_only=True, verbose=bool(args.verbose))

    # FULL AUTO — primary UX
    if args.input:
        from apkfs.auto.pipeline import run_auto

        return run_auto(
            Path(args.input),
            certs=[Path(c) for c in (args.certs or [])],
            dry_run=bool(args.dry_run),
            force_corex=bool(args.corex),
            use_apkeditor=bool(args.apkeditor),
            keep_unsigned=bool(args.unsigned),
            no_ads=bool(args.no_ads),
            no_usb_ss=bool(args.no_usb_ss),
            experimental=bool(args.experimental),
            report_dir=Path(args.report_dir) if args.report_dir else None,
            verbose=bool(args.verbose),
        )

    parser.print_help()
    print(f"\n  {BRAND} — try:  apkfs -i YourApp.apk\n")
    return 2


def cmd_doctor() -> int:
    print_banner()
    print("  ▶ doctor\n")
    import shutil
    import subprocess

    ok = True
    java = shutil.which("java")
    if java:
        r = subprocess.run([java, "-version"], capture_output=True, text=True)
        ver = (r.stderr or r.stdout).splitlines()[0] if (r.stderr or r.stdout) else "?"
        print(f"  ✔ java     : {ver}")
    else:
        print("  ✘ java     : NOT FOUND (install OpenJDK 11+)")
        ok = False

    for tool in ("aapt2", "aapt", "keytool", "unzip", "radare2", "r2"):
        path = shutil.which(tool)
        print(f"  {'✔' if path else '·'} {tool:8} : {path or 'optional / missing'}")

    try:
        import requests  # noqa: F401

        print("  ✔ requests : ok")
    except ImportError:
        print("  ✘ requests : missing (pip install requests)")
        ok = False

    # jars appear next to entry script after first run
    print("\n  note: apktool/apkeditor/apksig jars auto-download on first patch run")
    print(f"\n  {BRAND} doctor done")
    return 0 if ok else 1


def cmd_manual(engine_args: list[str]) -> int:
    """Power-user: pass raw engine flags."""
    # strip leading -- if argparse kept them
    args = engine_args
    if args and args[0] == "--":
        args = args[1:]
    if not args:
        print("usage: apkfs manual -- -i app.apk -f -p")
        return 2
    sys.argv = ["apkfs", *args]
    from apkfs.engine.APKFS_MAIN import apkfs_main

    try:
        apkfs_main()
        return 0
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 0


if __name__ == "__main__":
    raise SystemExit(main())
