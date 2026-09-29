#!/usr/bin/env python3
"""apkfs — Professor X (FS) · fully automatic APK lab suite CLI.

Termux / no-root friendly — same spirit as original ApkPatcher:
  pkg install python openjdk-17 aapt2
  apkfs -i /sdcard/Download/app.apk
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from apkfs import __version__
from apkfs.brand.banner import BRAND, print_banner


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="apkfs",
        description=f"apkfs v{__version__} — {BRAND} · fully automatic APK lab suite (Termux OK, no root)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
examples (Termux / phone, no root):
  termux-setup-storage
  apkfs -i /sdcard/Download/app.apk
  apkfs -i app.apk
  apkfs -i app.apks
  apkfs -i app.apk -c /sdcard/HttpCanary/certs/HttpCanary.pem
  apkfs -i app.apk --dry-run
  apkfs doctor
  apkfs pairip -i app.apk

{BRAND}
""",
    )

    p.add_argument("-V", "--version", action="version", version=f"apkfs {__version__} · {BRAND}")

    sub = p.add_subparsers(dest="command")

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

    sub.add_parser("doctor", help="Check Java / Termux pkgs / jars")

    sp = sub.add_parser("pairip", help="PairIP-focused workflow (auto flags)")
    sp.add_argument("-i", dest="input", required=True, help="APK path")
    sp.add_argument("--corex", action="store_true")
    sp.add_argument("-c", dest="certs", nargs="*")
    sp.add_argument("-v", "--verbose", action="store_true")

    sm = sub.add_parser("manual", help="Manual engine flags (legacy power-user mode)")
    sm.add_argument("engine_args", nargs=argparse.REMAINDER, help="Args passed to engine")

    si = sub.add_parser("setup", help="Termux one-shot setup (pkg + pip deps, no root)")

    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.credits:
        from apkfs.engine.Utils.Credits import Credits

        Credits()
        return 0

    if args.command == "doctor":
        return cmd_doctor()

    if args.command == "setup":
        return cmd_setup()

    if args.command == "manual":
        return cmd_manual(args.engine_args)

    if args.command == "pairip":
        from apkfs.auto.pipeline import run_auto
        from apkfs.termux_env import resolve_user_path

        return run_auto(
            resolve_user_path(args.input),
            certs=[resolve_user_path(c) for c in (args.certs or [])],
            force_corex=bool(args.corex),
            experimental=True,
            verbose=bool(args.verbose),
        )

    if args.merge:
        from apkfs.auto.pipeline import run_auto
        from apkfs.termux_env import resolve_user_path

        return run_auto(resolve_user_path(args.merge), merge_only=True, verbose=bool(args.verbose))

    if args.input:
        from apkfs.auto.pipeline import run_auto
        from apkfs.termux_env import resolve_user_path

        certs = []
        for c in args.certs or []:
            try:
                certs.append(resolve_user_path(c))
            except FileNotFoundError:
                certs.append(Path(c).expanduser())

        try:
            apk = resolve_user_path(args.input)
        except FileNotFoundError as e:
            print(f"\n  ✘ {e}\n")
            return 2

        return run_auto(
            apk,
            certs=certs or None,
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
    print(f"\n  {BRAND} — Termux:  apkfs -i /sdcard/Download/YourApp.apk\n")
    return 2


def cmd_doctor() -> int:
    print_banner()
    print("  ▶ doctor (Termux / no-root check)\n")
    import shutil
    import subprocess

    from apkfs.termux_env import apkfs_home, is_termux

    ok = True
    print(f"  {'✔' if is_termux() else '·'} termux   : {'yes (no root needed)' if is_termux() else 'not detected (desktop OK)'}")
    print(f"  ✔ home    : {apkfs_home()}")
    print(f"  ✔ tools   : {apkfs_home() / 'tools'}")

    java = shutil.which("java")
    if java:
        r = subprocess.run([java, "-version"], capture_output=True, text=True)
        ver = (r.stderr or r.stdout).splitlines()[0] if (r.stderr or r.stdout) else "?"
        print(f"  ✔ java     : {ver}")
    else:
        print("  ✘ java     : NOT FOUND")
        if is_termux():
            print("             fix: pkg install openjdk-17")
        else:
            print("             fix: install OpenJDK 11+")
        ok = False

    for tool, fix in (
        ("aapt2", "pkg install aapt2"),
        ("aapt", "pkg install aapt"),
        ("unzip", "pkg install unzip"),
        ("radare2", "pkg install radare2   # only if Flutter apps"),
        ("termux-wake-lock", "pkg install termux-api  # optional"),
    ):
        path = shutil.which(tool)
        mark = "✔" if path else "·"
        print(f"  {mark} {tool:16} : {path or fix}")

    # jars
    tools = apkfs_home() / "tools"
    for jar in ("APKTool.jar", "APKEditor.jar", "ApkSig.jar"):
        jp = tools / jar
        if jp.exists() and jp.stat().st_size > 50_000:
            print(f"  ✔ {jar:16} : {jp.stat().st_size // 1024} KB")
        else:
            print(f"  · {jar:16} : will auto-download on first run → {jp}")

    try:
        import requests  # noqa: F401
        print("  ✔ requests : ok")
    except ImportError:
        print("  ✘ requests : pip install requests")
        ok = False

    # storage
    if is_termux():
        sd = Path_shared()
        print(f"  {'✔' if sd else '·'} storage  : {sd or 'run: termux-setup-storage'}")

    print(f"\n  {BRAND} doctor done")
    print("  quick start:  apkfs -i /sdcard/Download/app.apk\n")
    return 0 if ok else 1


def Path_shared():
    from pathlib import Path
    for p in (Path.home() / "storage" / "shared", Path("/sdcard"), Path("/storage/emulated/0")):
        if p.exists():
            return str(p)
    return None


def cmd_setup() -> int:
    print_banner()
    print("  ▶ Termux setup (no root)\n")
    from apkfs.termux_env import ensure_termux_pkgs, is_termux, apkfs_home

    if not is_termux():
        print("  · Not Termux — only ensuring pip deps / home dir")
    notes = ensure_termux_pkgs(log=lambda m: print(m))
    for n in notes:
        print(f"    {n}")

    import subprocess
    pkgs = ["requests", "r2pipe", "asn1crypto", "multiprocess"]
    print("  → pip install deps")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", *pkgs])
    print(f"  ✔ APKFS_HOME={apkfs_home()}")
    print("\n  next:")
    print("    termux-setup-storage")
    print("    apkfs doctor")
    print("    apkfs -i /sdcard/Download/YourApp.apk\n")
    print(f"  🧠⚡  {BRAND}  ⚡🧠\n")
    return 0


def cmd_manual(engine_args: list[str]) -> int:
    args = engine_args
    if args and args[0] == "--":
        args = args[1:]
    if not args:
        print("usage: apkfs manual -- -i /sdcard/Download/app.apk -f -p")
        return 2
    # resolve -i path if present
    try:
        from apkfs.termux_env import resolve_user_path
        out = []
        i = 0
        while i < len(args):
            out.append(args[i])
            if args[i] in ("-i", "-m", "-c") and i + 1 < len(args):
                # path may have spaces already joined by engine CLI; try resolve single token
                try:
                    out.append(str(resolve_user_path(args[i + 1])))
                except Exception:
                    out.append(args[i + 1])
                i += 2
                continue
            i += 1
        args = out
    except Exception:
        pass

    sys.argv = ["apkfs", *args]
    from apkfs.engine.APKFS_MAIN import apkfs_main

    try:
        apkfs_main()
        return 0
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 0


if __name__ == "__main__":
    raise SystemExit(main())
