from __future__ import annotations

import json
import shutil
import sys
import time
from argparse import Namespace
from pathlib import Path
from typing import Any

from apkfs.auto.detect import detect
from apkfs.auto.plan import Plan, build_plan
from apkfs.brand.banner import footer, print_banner
from apkfs.termux_env import is_termux, wake_lock


def run_auto(
    apk: Path,
    *,
    certs: list[Path] | None = None,
    dry_run: bool = False,
    merge_only: bool = False,
    force_corex: bool = False,
    use_apkeditor: bool = False,
    keep_unsigned: bool = False,
    no_ads: bool = False,
    no_usb_ss: bool = False,
    experimental: bool = False,
    report_dir: Path | None = None,
    verbose: bool = False,
) -> int:
    """
    One-shot fully automatic pipeline.
    User-facing entry:  apkfs -i app.apk
    Termux / no-root safe.
    """
    t0 = time.time()
    print_banner()

    if is_termux():
        print("  · platform : Termux (no root)")
        wake_lock(True)

    apk = apk.expanduser().resolve()
    print(f"  ▶ input : {apk}")

    # 1) Detect
    print("\n  ▶ stage : DETECT")
    det = detect(apk)
    for line in det.summary_lines():
        print(f"    {line}")
    for n in getattr(det, "notes", []) or []:
        print(f"    note: {n}")

    # 2) Plan
    print("\n  ▶ stage : AUTO-PLAN")
    plan = build_plan(
        det,
        certs=certs,
        merge_only=merge_only,
        force_corex=force_corex,
        enable_ads=not no_ads,
        enable_usb_ss=not no_usb_ss,
        experimental=experimental,
    )
    if use_apkeditor:
        plan.engine_flags["APKEditor"] = True
        plan.strategies.append("decompiler: APKEditor")
    if keep_unsigned:
        plan.engine_flags["unsigned_apk"] = True
        plan.strategies.append("keep unsigned / CRC path")

    for line in plan.lines():
        print(f"    {line}")
    for r in plan.reasons:
        print(f"    why: {r}")

    # Report early
    report_dir = (report_dir or apk.parent / f"{apk.stem}_apkfs_report").resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "brand": "Professor X (FS)",
        "tool": "apkfs",
        "input": str(apk),
        "detection": {
            "package": det.package,
            "is_split": det.is_split,
            "abis": det.abis,
            "flutter": det.has_flutter,
            "pairip": det.has_pairip,
            "okhttp": det.has_okhttp,
            "unity": det.has_unity,
            "arm64": det.has_arm64,
            "ads": getattr(det, "has_ads", False),
            "ad_sdks": getattr(det, "ad_sdks", []),
            "trackers": getattr(det, "has_trackers", False),
        },
        "plan": {
            "strategies": plan.strategies,
            "warnings": plan.warnings,
            "confidence": plan.confidence,
            "engine_flags": _jsonable(plan.engine_flags),
        },
    }
    (report_dir / "plan.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n    report : {report_dir / 'plan.json'}")

    if dry_run:
        print("\n  ✔ dry-run complete — no APK written")
        wake_lock(False)
        footer(time.time() - t0)
        return 0

    if merge_only:
        return _run_merge_only(apk, report_dir, t0)

    # 3) Execute via engine with synthesized flags (fully auto)
    print("\n  ▶ stage : PATCH + BUILD")
    print("    engine : apkfs legacy core (auto-driven)")
    try:
        code = _execute_engine(apk, plan, verbose=verbose)
    except SystemExit as e:
        code = int(e.code) if isinstance(e.code, int) else 1
    except Exception as e:
        print(f"  ✘ engine error: {e}")
        report["error"] = str(e)
        (report_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        footer(time.time() - t0)
        return 1

    report["exit_code"] = code
    report["seconds"] = round(time.time() - t0, 2)
    (report_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    if code == 0:
        print("\n  ✔ apkfs auto finished")
        if is_termux():
            print("  · output usually next to your APK on /sdcard/…")
    else:
        print(f"\n  ! engine exited with code {code}")

    wake_lock(False)
    footer(time.time() - t0)
    return code


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_jsonable(x) for x in obj]
    if isinstance(obj, Path):
        return str(obj)
    return obj


def _run_merge_only(apk: Path, report_dir: Path, t0: float) -> int:
    # Use engine Anti_Split via light argv simulation
    print("\n  ▶ stage : MERGE ONLY")
    argv_backup = sys.argv[:]
    try:
        sys.argv = ["apkfs", "-m", str(apk)]
        from apkfs.engine.APKFS_MAIN import apkfs_main

        apkfs_main()
        code = 0
    except SystemExit as e:
        code = int(e.code) if isinstance(e.code, int) else 0
    except Exception as e:
        print(f"  ✘ merge failed: {e}")
        code = 1
    finally:
        sys.argv = argv_backup
    footer(time.time() - t0)
    return code


def _execute_engine(apk: Path, plan: Plan, verbose: bool = False) -> int:
    """
    Build argv for the battle-tested engine and run it.
    Auto mode translates plan → flags so user never types them.
    """
    flags = plan.engine_flags
    argv = ["apkfs", "-i", str(apk)]

    def add(flag: str, cond: bool = True) -> None:
        if cond:
            argv.append(flag)

    add("-a", bool(flags.get("APKEditor")))
    add("-e", bool(flags.get("For_Emulator")))
    add("-u", bool(flags.get("unsigned_apk")))
    add("-f", bool(flags.get("Flutter")))
    add("-p", bool(flags.get("Pairip")))
    add("-x", bool(flags.get("Hook_CoreX")))
    add("-rmss", bool(flags.get("Remove_SS")))
    add("-rmusb", bool(flags.get("Remove_USB")))
    add("-rmads", bool(flags.get("Remove_Ads")))
    add("-r", bool(flags.get("Random_Info")))
    add("-pkg", bool(flags.get("Spoof_PKG")))
    add("-P", bool(flags.get("Purchase")))
    add("-A", bool(flags.get("AES_Logs")))
    add("-A2", bool(flags.get("Algorithm")))
    add("-t", bool(flags.get("TG_Patch")))
    add("-pine", bool(flags.get("Pine_Hook")))

    certs = flags.get("CA_Certificate")
    if certs:
        argv.append("-c")
        argv.extend(list(certs))

    skip = flags.get("Skip_Patch") or []
    if skip:
        argv.append("-skip")
        argv.extend(list(skip))

    if flags.get("Android_ID"):
        argv.extend(["-D", str(flags["Android_ID"])])

    if verbose:
        print(f"    argv  : {' '.join(argv)}")

    argv_backup = sys.argv[:]
    try:
        sys.argv = argv
        # Import after argv set — engine parses on call
        from apkfs.engine.APKFS_MAIN import apkfs_main

        apkfs_main()
        return 0
    except SystemExit as e:
        code = e.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        return 1
    finally:
        sys.argv = argv_backup
