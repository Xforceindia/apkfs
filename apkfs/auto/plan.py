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
    enable_ads: bool = True,
    enable_usb_ss: bool = True,
    experimental: bool = False,
) -> Plan:
    """
    Decide everything automatically.

    Default lab preset (safe + useful):
      merge (if split) → SSL/VPN smali → NSC/cert → flutter if needed
      → pairip soft path if needed → sign
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
        "AES_Logs": False,
        "Algorithm": False,
        "Random_Info": False,
        "Spoof_PKG": False,
        "Purchase": False,  # never auto
        "TG_Patch": False,
        "Pine_Hook": False,
        "APKEditor": False,
        "For_Emulator": False,
        "unsigned_apk": False,
        "Android_ID": None,
        "Skip_Patch": [],
        "AES_S": False,
        "Load_Modules": None,
        "Spoof_PKG": False,
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

    # PairIP auto
    if det.has_pairip:
        flags["Pairip"] = True
        p.reasons.append("detected libpairipcore.so / pairip")
        if force_corex or (experimental and det.has_arm64 and det.is_split):
            flags["Hook_CoreX"] = True
            p.strategies.append("PairIP CoreX experimental hook (arm64 + split)")
            p.warnings.append("CoreX is unstable — app may crash; server integrity still applies")
            p.confidence = min(p.confidence, 0.45)
        else:
            # Soft path: pairip smali + keep unsigned/CRC style like upstream -p
            flags["unsigned_apk"] = True
            p.strategies.append("PairIP smali integrity soften + sig/CRC preserve (VM/MultiApp friendly)")
            p.warnings.append(
                "PairIP soft mode: prefer install in VM/MultiApp; use --corex for experimental direct path"
            )
            p.confidence = min(p.confidence, 0.6)

    if det.is_split:
        p.strategies.insert(0, "anti-split merge (.apks/.apkm/.xapk → apk)")
        if flags.get("Hook_CoreX"):
            p.reasons.append("CoreX requires split input for base.apk dump")

    if det.has_okhttp:
        p.reasons.append("okhttp markers present — certificate pinner patterns prioritized")

    # Never auto-enable purchase / piracy heuristics
    flags["Purchase"] = False

    p.engine_flags = flags
    return p
