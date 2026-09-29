#!/usr/bin/env python3
"""apkfs — Professor X (FS)

Same simple UX as ApkPatcher:
  apkfs -i app.apk
  apkfs -i app.apks
  apkfs app.apk          # positional also works

Full auto · Termux no-root · fast defaults
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
        description=f"apkfs v{__version__} — {BRAND} · auto APK lab (ApkPatcher-style -i)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
examples (same spirit as ApkPatcher -i):
  apkfs -i app.apk
  apkfs -i app.apks
  apkfs app.apk
  apkfs -i /sdcard/Download/app.apk -c cert.pem
  apkfs -i app.apk --boom
  apkfs -i app.apk --fast
  apkfs doctor

default -i AUTO pack (like ApkPatcher -i — no extra flags needed):
  SSL/VPN/NSC · ads remove · LVL/signature/Play Store support · Flutter/PairIP if detected · sign
  auto APKEditor fallback if apktool fails
  output: <name>_Patched.apk  (next to input)
  spaces OK:  apkfs -i Numberbox.apk  |  apkfs -i "Number Box.apk"

{BRAND}
""",
    )

    p.add_argument("-V", "--version", action="version", version=f"apkfs {__version__} · {BRAND}")

    sub = p.add_subparsers(dest="command")

    # Classic ApkPatcher-style
    p.add_argument("-i", dest="input", help="APK / APKS / APKM / XAPK (FULL AUTO)")
    # positional APK handled by argv preprocess → -i
    p.add_argument("-m", dest="merge", help="Merge split APK only (.apks/.apkm/.xapk)")
    p.add_argument("-c", dest="certs", nargs="*", help="Proxy CA cert(s) .pem/.crt")
    p.add_argument("-a", "--apkeditor", action="store_true", help="Use APKEditor (fallback decompiler)")
    p.add_argument("-u", "--unsigned", action="store_true", help="Keep unsigned / CRC path")
    p.add_argument("-e", action="store_true", dest="emulator", help="Emulator jar set")
    p.add_argument("-f", action="store_true", dest="force_flutter", help="Force Flutter SSL pack")
    p.add_argument("-p", action="store_true", dest="force_pairip", help="Force PairIP pack")
    p.add_argument("-x", action="store_true", dest="corex", help="PairIP CoreX (with pairip)")
    p.add_argument("-P", action="store_true", dest="purchase", help="Client purchase/premium heuristics")
    p.add_argument("-rmads", action="store_true", dest="rmads_flag", help=argparse.SUPPRESS)
    p.add_argument("-rmss", action="store_true", dest="rmss_flag", help=argparse.SUPPRESS)
    p.add_argument("-rmusb", action="store_true", dest="rmusb_flag", help=argparse.SUPPRESS)

    p.add_argument("--dry-run", action="store_true", help="Detect + plan only")
    p.add_argument("--fast", action="store_true", help="Faster decompile (only-main-classes; may miss secondary dex)")
    p.add_argument("--boom", action="store_true", help="Super pack + client unlock")
    p.add_argument("--unlock", action="store_true", help="Client unlock heuristics")
    p.add_argument("--no-support", action="store_true", help="Skip LVL/signature support pack")
    p.add_argument("--no-ads", action="store_true", help="Keep ads")
    p.add_argument("--no-usb-ss", action="store_true", help="Skip USB/screenshot patches")
    p.add_argument("--quiet", action="store_true", help="Less auto-plan chatter (classic engine logs)")
    p.add_argument("--report-dir", type=str, help="Report folder")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose")
    p.add_argument("-C", "--credits", action="store_true", help="Credits")
    p.add_argument("--experimental", action="store_true", help="Experimental strategies")

    sub.add_parser("doctor", help="Check Java / Termux / jars")
    sub.add_parser("setup", help="Termux one-shot setup")

    sp = sub.add_parser("pairip", help="PairIP-focused auto")
    sp.add_argument("-i", dest="input", required=True)
    sp.add_argument("--corex", action="store_true")
    sp.add_argument("-c", dest="certs", nargs="*")
    sp.add_argument("-v", "--verbose", action="store_true")
    sp.add_argument("--fast", action="store_true")

    sm = sub.add_parser("manual", help="Raw engine flags")
    sm.add_argument("engine_args", nargs=argparse.REMAINDER)

    return p


def _join_spaced_apk_argv(argv: list[str]) -> list[str]:
    """
    ApkPatcher-friendly: allow unquoted spaces in APK path.
      apkfs -i Number Box.apk
      apkfs Number Box.apk
    joins consecutive non-flag tokens until an apk/apks/apkm/xapk suffix.
    """
    _ext = (".apk", ".apks", ".apkm", ".xapk")
    out: list[str] = []
    i = 0
    n = len(argv)
    while i < n:
        a = argv[i]
        # after -i / -m / -c take following tokens
        if a in ("-i", "-m") and i + 1 < n:
            out.append(a)
            i += 1
            parts = [argv[i]]
            i += 1
            while i < n and not argv[i].startswith("-"):
                parts.append(argv[i])
                joined = " ".join(parts)
                if joined.lower().endswith(_ext):
                    i += 1
                    break
                # if single token already has ext, stop
                if parts[-1].lower().endswith(_ext):
                    i += 1
                    break
                i += 1
            out.append(" ".join(parts))
            continue
        if a == "-c":
            out.append(a)
            i += 1
            # certs: keep taking until flag or end (no space-join needed usually)
            while i < n and not argv[i].startswith("-"):
                out.append(argv[i])
                i += 1
            continue
        out.append(a)
        i += 1

    # bare path with spaces at start: Number Box.apk → -i Number Box.apk
    if out and not out[0].startswith("-") and out[0] not in ("doctor", "setup", "pairip", "manual"):
        # collect until ext
        parts = [out[0]]
        j = 1
        while j < len(out) and not out[j].startswith("-") and out[j] not in ("doctor", "setup", "pairip", "manual"):
            parts.append(out[j])
            j += 1
        joined = " ".join(parts)
        if joined.lower().endswith(_ext) or any(parts[-1].lower().endswith(e) for e in _ext):
            rest = out[j:]
            out = ["-i", joined, *rest]
        elif not out[0].startswith("-") and Path(out[0]).suffix.lower() in _ext:
            out = ["-i", out[0], *out[1:]]
    return out


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # ApkPatcher-style: bare APK path → -i ; join spaced names
    _ext = (".apk", ".apks", ".apkm", ".xapk")
    if argv:
        a0 = argv[0]
        if not a0.startswith("-") and a0.lower().endswith(_ext):
            argv = ["-i", a0, *argv[1:]]
        elif (
            not a0.startswith("-")
            and a0 not in ("doctor", "setup", "pairip", "manual")
            and any(a0.lower().endswith(e) or Path(a0).suffix.lower() in _ext for e in _ext)
        ):
            argv = ["-i", a0, *argv[1:]]
    argv = _join_spaced_apk_argv(argv)

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

    # Resolve input: -i OR positional OR pairip
    input_path = None
    if args.command == "pairip":
        input_path = args.input
    else:
        input_path = args.input

    if getattr(args, "merge", None):
        from apkfs.auto.pipeline import run_auto
        from apkfs.termux_env import resolve_user_path
        if getattr(args, "fast", False):
            import os
            os.environ["APKFS_FAST"] = "1"
        return run_auto(resolve_user_path(args.merge), merge_only=True, verbose=bool(args.verbose), quiet=bool(getattr(args, "quiet", False)))

    if args.command == "pairip" or input_path:
        from apkfs.auto.pipeline import run_auto
        from apkfs.termux_env import resolve_user_path
        import os

        if getattr(args, "fast", False):
            os.environ["APKFS_FAST"] = "1"
        if getattr(args, "quiet", False):
            os.environ["APKFS_QUIET_PLAN"] = "1"

        certs = []
        for c in (getattr(args, "certs", None) or []):
            try:
                certs.append(resolve_user_path(c))
            except FileNotFoundError:
                certs.append(Path(c).expanduser())

        try:
            apk = resolve_user_path(input_path)
        except FileNotFoundError as e:
            print(f"\n  ✘ {e}\n")
            return 2

        # Classic force flags → engine via plan extras
        force = {
            "flutter": bool(getattr(args, "force_flutter", False)),
            "pairip": bool(getattr(args, "force_pairip", False) or args.command == "pairip"),
            "purchase": bool(getattr(args, "purchase", False)),
            "emulator": bool(getattr(args, "emulator", False)),
        }

        return run_auto(
            apk,
            certs=certs or None,
            dry_run=bool(getattr(args, "dry_run", False)),
            force_corex=bool(getattr(args, "corex", False)),
            use_apkeditor=bool(getattr(args, "apkeditor", False)),
            keep_unsigned=bool(getattr(args, "unsigned", False)),
            no_ads=bool(getattr(args, "no_ads", False)),
            no_usb_ss=bool(getattr(args, "no_usb_ss", False)),
            boom=bool(getattr(args, "boom", False)),
            unlock=bool(getattr(args, "unlock", False) or getattr(args, "purchase", False)),
            no_support=bool(getattr(args, "no_support", False)),
            experimental=bool(getattr(args, "experimental", False)),
            report_dir=Path(args.report_dir) if getattr(args, "report_dir", None) else None,
            verbose=bool(getattr(args, "verbose", False)),
            quiet=bool(getattr(args, "quiet", False)),
            force_flags=force,
        )

    parser.print_help()
    print(f"\n  {BRAND} — like ApkPatcher:\n")
    print("    apkfs -i app.apk")
    print("    apkfs -i app.apks")
    print("    apkfs app.apk\n")
    return 2


def cmd_doctor() -> int:
    print_banner()
    print("  ▶ doctor\n")
    import shutil, subprocess
    from apkfs.termux_env import apkfs_home, is_termux
    from pathlib import Path

    ok = True
    print(f"  {'✔' if is_termux() else '·'} termux   : {'yes (no root)' if is_termux() else 'desktop OK'}")
    print(f"  ✔ home    : {apkfs_home()}")
    java = shutil.which("java")
    if java:
        r = subprocess.run([java, "-version"], capture_output=True, text=True)
        print(f"  ✔ java     : {(r.stderr or r.stdout).splitlines()[0]}")
    else:
        print("  ✘ java     : missing — pkg install openjdk-17")
        ok = False
    for tool in ("aapt2", "aapt", "unzip", "radare2"):
        print(f"  {'✔' if shutil.which(tool) else '·'} {tool:8} : {shutil.which(tool) or 'optional'}")
    tools = apkfs_home() / "tools"
    for jar in ("APKTool.jar", "APKEditor.jar", "ApkSig.jar"):
        jp = tools / jar
        print(f"  {'✔' if jp.exists() and jp.stat().st_size > 50000 else '·'} {jar:16} : {'ok' if jp.exists() else 'auto on first -i'}")
    print(f"\n  quick:  apkfs -i /sdcard/Download/app.apk\n  {BRAND}\n")
    return 0 if ok else 1


def cmd_setup() -> int:
    print_banner()
    from apkfs.termux_env import ensure_termux_pkgs, is_termux, apkfs_home
    import subprocess
    ensure_termux_pkgs(log=print)
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "requests", "r2pipe", "asn1crypto", "multiprocess"])
    print(f"  ✔ home={apkfs_home()}")
    print("  next: termux-setup-storage && apkfs -i /sdcard/Download/app.apk\n")
    return 0


def cmd_manual(engine_args: list[str]) -> int:
    args = engine_args[1:] if engine_args and engine_args[0] == "--" else engine_args
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
