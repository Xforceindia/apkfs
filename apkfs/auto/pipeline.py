from __future__ import annotations

import hashlib
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
    # ApkPatcher-parity: extras OFF unless requested
    want_ads: bool = False,
    want_usb_ss: bool = False,
    want_support: bool = False,
    no_ads: bool = False,
    no_usb_ss: bool = False,
    boom: bool = False,
    unlock: bool = False,
    no_support: bool = False,
    experimental: bool = False,
    report_dir: Path | None = None,
    verbose: bool = False,
    quiet: bool = False,
    force_flags: dict | None = None,
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
        enable_ads=bool(want_ads or boom) and not no_ads,
        enable_usb_ss=bool(want_usb_ss or boom) and not no_usb_ss,
        enable_support=bool(want_support or boom) and not no_support,
        enable_unlock=unlock or boom,
        boom=boom,
        experimental=experimental,
    )
    force_flags = force_flags or {}
    if force_flags.get("flutter"):
        plan.engine_flags["Flutter"] = True
        if "Flutter" not in str(plan.strategies):
            plan.strategies.append("Flutter SSL (forced -f)")
    if force_flags.get("pairip"):
        plan.engine_flags["Pairip"] = True
        plan.engine_flags["unsigned_apk"] = plan.engine_flags.get("unsigned_apk", False)  # no-root default signed
        plan.strategies.append("PairIP pack (forced -p)")
    if force_flags.get("purchase"):
        plan.engine_flags["Purchase"] = True
        plan.engine_flags["Support_Unlock"] = True
        plan.strategies.append("Purchase heuristics (forced -P)")
    if force_flags.get("emulator"):
        plan.engine_flags["For_Emulator"] = True

    if use_apkeditor:
        plan.engine_flags["APKEditor"] = True
        plan.strategies.append("decompiler: APKEditor")
    if keep_unsigned:
        plan.engine_flags["unsigned_apk"] = True
        plan.strategies.append("keep unsigned / CRC path")

    if not quiet:
        for line in plan.lines():
            print(f"    {line}")
        for r in plan.reasons:
            print(f"    why: {r}")
    else:
        print(f"    auto → {len(plan.strategies)} steps · conf {plan.confidence:.0%}")
        for s in plan.strategies[:8]:
            print(f"      • {s}")

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
            "billing": getattr(det, "has_billing", False),
            "lvl": getattr(det, "has_lvl", False),
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

    # LuckPatcher-style safety: always backup original next to report
    try:
        bak = report_dir / f"{apk.stem}.original{apk.suffix}"
        if not bak.exists():
            shutil.copy2(apk, bak)
            h = hashlib.sha256(apk.read_bytes()).hexdigest()[:16]
            print(f"\n  ✔ backup  : {bak.name}  sha256={h}…")
            report["backup"] = str(bak)
            report["input_sha256_16"] = h
    except Exception as e:
        print(f"  ! backup failed: {e}")

    if merge_only:
        return _run_merge_only(apk, report_dir, t0)

    # 3) Execute via engine with synthesized flags (fully auto)
    print("\n  ▶ stage : PATCH + BUILD")
    print("    engine : apkfs legacy core (auto-driven)")
    try:
        code = _execute_engine(apk, plan, verbose=verbose)
    except SystemExit as e:
        # Mirror _execute_engine: string exit() was often a success log line
        c = e.code
        if c is None:
            code = 0
        elif isinstance(c, int):
            code = c
        else:
            msg = str(c).lower()
            code = 1 if any(x in msg for x in ("fail", "error", "✘", "not found", "not exist")) else 0
    except Exception as e:
        print(f"  ✘ engine error: {e}")
        report["error"] = str(e)
        (report_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        footer(time.time() - t0)
        return 1

    # 3b) Auto APKEditor fallback when apktool rebuild fails (exit 42)
    if code == 42 and not plan.engine_flags.get("APKEditor"):
        print("  ! apktool path failed — AUTO fallback → APKEditor (-a)")
        print("  · note: big APKs: apktool+aapt2 may sit quiet a while; fallback avoids dead-end")
        plan.engine_flags["APKEditor"] = True
        plan.strategies.append("AUTO fallback: APKEditor (-a) after apktool fail")
        report["auto_a_fallback"] = True
        try:
            code = _execute_engine(apk, plan, verbose=verbose)
            if code == 0:
                print("  ✔ AUTO -a fallback succeeded")
        except SystemExit as e:
            c = e.code
            if c is None:
                code = 0
            elif isinstance(c, int):
                code = c
            else:
                msg = str(c).lower()
                code = 1 if any(x in msg for x in ("fail", "error", "✘", "not found", "not exist")) else 0
        except Exception as e:
            print(f"  ✘ AUTO -a fallback error: {e}")
            code = 1

    report["exit_code"] = code
    report["seconds"] = round(time.time() - t0, 2)
    # Support pack may stash stats via env (engine → auto bridge)
    try:
        import os
        raw = os.environ.pop("APKFS_SUPPORT_STATS", "") or ""
        if raw:
            report["support_stats"] = json.loads(raw)
    except Exception:
        pass
    try:
        from apkfs.engine.Patch.Support_Pack import support_score
        used_support = bool(plan.engine_flags.get("Support_Pack") or plan.engine_flags.get("Purchase"))
        if used_support or report.get("support_stats"):
            report["working_score"] = support_score(
                {
                    "pairip": det.has_pairip,
                    "flutter": det.has_flutter,
                    "has_ads": getattr(det, "has_ads", False),
                    "billing": getattr(det, "has_billing", False),
                    "lvl": getattr(det, "has_lvl", False),
                },
                report.get("support_stats"),
            )
            ws = report["working_score"]
            print(f"\n  ▶ working score : {ws['score'].upper()}  ({ws['hits']} support hits)")
            for rsn in ws.get("reasons", []):
                print(f"      · {rsn}")
            print(f"      · {ws.get('note')}")
        else:
            report["working_score"] = {
                "score": "ok",
                "hits": 0,
                "reasons": ["ApkPatcher-parity core (SSL/VPN/NSC); Support_Pack not enabled"],
                "note": "Add --support or --boom for LVL/installer score. PairIP lib uses unsigned path.",
            }
            print("\n  ▶ mode : ApkPatcher-parity core (SSL/NSC/Flutter) — no Support_Pack")
            print("      · extras: -rmads -rmss -rmusb --support | super: --boom")
    except Exception as e:
        report["working_score_error"] = str(e)
    (report_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    if code == 0:
        # Classic ApkPatcher-style tip: output next to input as *_Patched.apk
        stem = apk.stem
        parent = apk.parent
        candidates = sorted(parent.glob(f"{stem}*_Patched.apk")) + sorted(parent.glob(f"{stem}*Patched*.apk"))
        out = candidates[-1] if candidates else parent / f"{stem}_Patched.apk"
        print(f"\n  ✔ DONE")
        print(f"  ✔ Final APK  ︻デ═一  {out}")
        print(f"  · report     {report_dir}")
        if is_termux():
            print("  · install: allow unknown apps, then open the *_Patched.apk")
    else:
        print(f"\n  ! engine exited with code {code}")
        print("  · tip: retry with  apkfs -i app.apk -a   (APKEditor) or  --fast")

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
        code = e.code
        if code is None:
            code = 0
        elif isinstance(code, int):
            code = code
        else:
            msg = str(code).lower()
            code = 1 if any(x in msg for x in ("fail", "error", "✘", "not found")) else 0
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
    add("--Support_Pack", bool(flags.get("Support_Pack")))
    add("--Support_Unlock", bool(flags.get("Support_Unlock")))
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
    import os
    quiet_was = os.environ.get("APKFS_QUIET")
    # Avoid engine wiping the auto banner / clearing Termux scrollback
    os.environ["APKFS_QUIET"] = "1"
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
        # Engine historically used exit("message") on success paths —
        # treat non-int as success unless message looks like a hard error.
        msg = str(code).lower()
        if any(x in msg for x in ("fail", "error", "✘", "not found", "not exist")):
            return 1
        return 0
    finally:
        sys.argv = argv_backup
        if quiet_was is None:
            os.environ.pop("APKFS_QUIET", None)
        else:
            os.environ["APKFS_QUIET"] = quiet_was
