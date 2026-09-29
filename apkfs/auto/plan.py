from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .detect import Detection


@dataclass
class Plan:
    """Fully automatic action plan — user only passed -i."""

    strategies: list[str] = field(default_factory=list)
    engine_flags: dict[str, Any] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    confidence: float = 0.85

    def lines(self) -> list[str]:
        out = [f"confidence : {self.confidence:.0%}"]
        out.append("auto-plan  :")
        for s in self.strategies:
            out.append(f"  • {s}")
        if self.warnings:
            out.append("warnings   :")
            for w in self.warnings:
                out.append(f"  ! {w}")
        return out


def build_plan(
    det: Detection,
    *,
    certs: list[Path] | None = None,
    merge_only: bool = False,
    force_corex: bool = False,
    # ApkPatcher-parity plain -i: SSL/VPN/NSC only. Extras via flags / --boom
    enable_ads: bool = False,
    enable_usb_ss: bool = False,
    enable_support: bool = False,
    enable_unlock: bool = False,
    boom: bool = False,
    experimental: bool = False,
) -> Plan:
    """
    Decide everything automatically.

    Default (ApkPatcher-compatible plain -i):
      merge (if split) → SSL/VPN smali → NSC/cert → Flutter -f if libflutter
      → PairIP -p if libpairipcore (unsigned CRC) → sign otherwise
    Extras (ads/usb/ss/support/unlock) only with flags or --boom
    """
    p = Plan()
    flags: dict[str, Any] = {
        "Flutter": False,
        "Pairip": False,
        "Hook_CoreX": False,
        "CA_Certificate": [str(c) for c in (certs or [])] or None,
        "Remove_SS": enable_usb_ss,
        "Remove_USB": enable_usb_ss,
        "Remove_Ads": enable_ads,
        # LuckPatcher-like support (re-sign friendly). Unlock only via --boom/--unlock
        "Support_Pack": bool(enable_support or boom),
        "Support_Unlock": bool(enable_unlock or boom),
        "Purchase": bool(enable_unlock or boom),
        "AES_Logs": False,
        "Algorithm": False,
        "Random_Info": False,
        "Spoof_PKG": False,
        "TG_Patch": False,
        "Pine_Hook": False,
        "APKEditor": False,
        "For_Emulator": False,
        "unsigned_apk": False,
        "Android_ID": None,
        "Skip_Patch": [],
        "AES_S": False,
        "Load_Modules": None,
    }

    if merge_only:
        p.strategies.append("anti-split merge only")
        p.reasons.append("user asked merge-only")
        p.engine_flags = {"merge_only": True}
        p.confidence = 0.95
        return p

    # Always: MITM lab base
    p.strategies.append("SSL pinning soften (smali TrustManager/OkHttp/HostnameVerifier)")
    p.strategies.append("VPN / proxy / mock-location lab bypasses")
    p.strategies.append("network_security_config + user/system CA trust")
    p.reasons.append("default lab MITM preset")

    if certs:
        p.strategies.append(f"embed {len(certs)} proxy CA cert(s)")
    else:
        p.strategies.append("embed default lab CA + trust user CAs")

    if enable_usb_ss:
        p.strategies.append("screenshot FLAG_SECURE + USB-debug detection soften")
        p.reasons.append("common lab friction removers")

    if enable_ads:
        if getattr(det, "has_ads", False) or getattr(det, "ad_sdks", None):
            sdks = ", ".join(getattr(det, "ad_sdks", [])[:8]) or "generic"
            p.strategies.append(f"AUTO REMOVE ads/trackers ({sdks})")
            p.reasons.append("ads/trackers detected — strip load/show/init call-sites + ad unit ids")
        else:
            p.strategies.append("AUTO REMOVE ads/trackers (best-effort, always-on clean)")
            p.reasons.append("clean pack: neutralize known ad SDK + force-update prompts")
        if getattr(det, "has_trackers", False):
            p.warnings.append("analytics/trackers softened best-effort — not a full privacy suite")

    # Flutter auto
    if det.has_flutter:
        flags["Flutter"] = True
        p.strategies.append("Flutter libflutter.so SSL patch (radare2 patterns)")
        p.reasons.append("detected libflutter.so")
        p.confidence = min(p.confidence, 0.75)
        p.warnings.append("Flutter patterns depend on Dart engine version — may need updates")

    # PairIP auto — ApkPatcher Scan only treats libpairipcore.so as PairIP
    has_pairip_lib = bool(getattr(det, "has_pairip_lib", False) or (
        det.has_pairip and any("libpairipcore" in (n or "").lower() for n in getattr(det, "native_libs", []))
    ))
    if not has_pairip_lib and det.has_pairip:
        p.warnings.append(
            "pairip dex/app-class markers without libpairipcore.so — plain -i skips -p (ApkPatcher-same)"
        )
    if has_pairip_lib:
        flags["Pairip"] = True
        p.reasons.append("detected libpairipcore.so")
        if force_corex or (experimental and det.has_arm64 and det.is_split):
            flags["Hook_CoreX"] = True
            flags["unsigned_apk"] = False
            p.strategies.append("PairIP CoreX hook (arm64) — signed install")
            p.warnings.append("CoreX is unstable — app may crash; server integrity still applies")
            p.confidence = min(p.confidence, 0.45)
        else:
            # ApkPatcher: -p without -x → unsigned CRC (VM / MultiApp)
            flags["unsigned_apk"] = True
            p.strategies.append("PairIP soft (-p): unsigned CRC APK (VM / Multi_App) — ApkPatcher-same")
            p.warnings.append("PairIP unsigned: install in VM/MultiApp; or try -p -x CoreX on arm64")
            p.confidence = min(p.confidence, 0.55)

    if det.is_split:
        p.strategies.insert(0, "anti-split merge (.apks/.apkm/.xapk → apk)")
        if flags.get("Hook_CoreX"):
            p.reasons.append("CoreX requires split input for base.apk dump")

    if det.has_okhttp:
        p.reasons.append("okhttp markers present — certificate pinner patterns prioritized")


    if boom:
        flags["Support_Pack"] = True
        flags["Support_Unlock"] = True
        flags["Purchase"] = True
        if enable_ads:
            flags["Remove_Ads"] = True
        flags["Remove_SS"] = True
        flags["Remove_USB"] = True
        p.strategies.insert(0, "BOOM super mode (LP-style modified APK pack)")
        p.strategies.append("Support pack: LVL / signature / Play Store installer source")
        p.strategies.append("Client unlock heuristics (isPremium / BillingClient / LVL)")
        p.reasons.append("boom: SSL + clean ads + LVL/signature support + client unlock heuristics")
        p.warnings.append("BOOM unlock is CLIENT-SIDE only — online IAP / Play Integrity still server-enforced")
        p.warnings.append("Always keep original APK backup; test patched build before uninstalling original")
        p.confidence = min(p.confidence, 0.55)
    else:
        if flags.get("Support_Pack"):
            p.strategies.append("Support pack: LVL / signature / Play Store installer source (re-sign friendly)")
            p.reasons.append("LuckPatcher-like modified-APK support so re-signed apps keep running")
            if getattr(det, "has_installer_check", False):
                p.strategies.append("AUTO: spoof install source as Play Store (getInstaller + InstallSourceInfo)")
                p.reasons.append("app checks installer/Play Store source — client-side spoof enabled")
                p.warnings.append("Installer spoof is client-side only; adb install -i com.android.vending is stronger on-device")
        if flags.get("Support_Unlock"):
            p.strategies.append("Client unlock heuristics (isPremium / BillingClient state)")
            p.warnings.append("Unlock heuristics fail on server-validated purchases")

    # Safety: never unlock unless boom/--unlock explicitly requested
    if not (boom or enable_unlock):
        flags["Purchase"] = False
        flags["Support_Unlock"] = False

    p.engine_flags = flags
    return p
