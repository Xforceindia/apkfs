from __future__ import annotations

import re
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


SPLIT_EXT = {".apks", ".apkm", ".xapk"}


@dataclass
class Detection:
    path: Path
    is_split: bool = False
    package: str = ""
    abis: list[str] = field(default_factory=list)
    has_arm64: bool = False
    has_flutter: bool = False
    has_pairip: bool = False
    has_okhttp: bool = False
    has_firebase: bool = False
    has_unity: bool = False
    has_ads: bool = False
    has_trackers: bool = False
    has_billing: bool = False
    has_lvl: bool = False
    has_installer_check: bool = False
    ad_sdks: list[str] = field(default_factory=list)
    native_libs: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        flags = []
        if self.is_split:
            flags.append("split-bundle")
        if self.has_flutter:
            flags.append("flutter")
        if self.has_pairip:
            flags.append("pairip")
        if self.has_okhttp:
            flags.append("okhttp")
        if self.has_unity:
            flags.append("unity")
        if self.has_ads:
            flags.append("ads")
        if self.has_billing:
            flags.append("billing")
        if self.has_lvl:
            flags.append("lvl")
        if self.has_installer_check:
            flags.append("play-installer")
        if self.has_trackers:
            flags.append("trackers")
        if self.has_arm64:
            flags.append("arm64")
        return [
            f"file       : {self.path.name}",
            f"package    : {self.package or '(pending scan)'}",
            f"abis       : {', '.join(self.abis) or 'unknown'}",
            f"signals    : {', '.join(flags) or 'generic'}",
        ]


def detect(path: Path) -> Detection:
    path = path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"APK not found: {path}")

    d = Detection(path=path, is_split=path.suffix.lower() in SPLIT_EXT)

    # Quick zip scan (works for .apk; for split, scan still lists entries)
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
    except zipfile.BadZipFile as e:
        if d.is_split:
            # some xapk are zip; if fail, still allow merge later
            d.notes.append(f"zip preview skipped: {e}")
            return d
        raise RuntimeError(f"Not a valid zip/apk: {path}") from e

    abis = set()
    for n in names:
        low = n.lower()
        if low.startswith("lib/"):
            parts = n.split("/")
            if len(parts) >= 3:
                abis.add(parts[1])
            base = parts[-1]
            d.native_libs.append(base)
            if base == "libflutter.so":
                d.has_flutter = True
            if base == "libpairipcore.so":
                d.has_pairip = True
            if "unity" in base.lower() or base.startswith("libil2cpp"):
                d.has_unity = True
            if "firebase" in base.lower():
                d.has_firebase = True
        if "okhttp" in low:
            d.has_okhttp = True
        if "pairip" in low:
            d.has_pairip = True
        if low.endswith("libflutter.so"):
            d.has_flutter = True


    d.abis = sorted(abis)
    d.has_arm64 = any("arm64" in a for a in d.abis)

    # --- ads / trackers from zip paths ---
    joined = "\n".join(n.lower().replace("\\", "/") for n in names)
    found_ads = []
    for sdk, keys in {
        "admob": ("admob", "gms/ads/", "/ads/ad"),
        "applovin": ("applovin",),
        "unityads": ("unityads", "unity3d/ads"),
        "ironsource": ("ironsource", "supersonic"),
        "vungle": ("vungle",),
        "facebook_ads": ("facebook/ads", "audience_network"),
        "appodeal": ("appodeal",),
        "chartboost": ("chartboost",),
        "inmobi": ("inmobi",),
        "mintegral": ("mintegral", "mbridge"),
        "pangle": ("pangle", "openadsdk"),
        "startapp": ("startapp",),
        "mopub": ("mopub",),
        "fyber": ("fyber",),
        "tapjoy": ("tapjoy",),
        "smaato": ("smaato",),
    }.items():
        if any(k in joined for k in keys):
            found_ads.append(sdk)
    d.ad_sdks = found_ads
    d.has_ads = bool(found_ads) or ("ca-app-pub-" in joined) or ("/ads/" in joined and "admob" in joined)

    found_tr = []
    for name, keys in {
        "appsflyer": ("appsflyer",),
        "adjust": ("com/adjust", "/adjust/"),
        "firebase_analytics": ("firebase/analytics",),
        "crashlytics": ("crashlytics",),
        "flurry": ("flurry",),
        "onesignal": ("onesignal",),
        "mixpanel": ("mixpanel",),
    }.items():
        if any(k in joined for k in keys):
            found_tr.append(name)
    d.has_trackers = bool(found_tr)
    if found_tr:
        d.notes.append("trackers: " + ", ".join(found_tr))
    if found_ads:
        d.notes.append("ad-sdks: " + ", ".join(found_ads))

    d.has_billing = any(x in joined for x in (
        "billingclient", "billing/client", "inappbilling", "aidl/billing",
        "com/android/vending/billing", "purchase.purchase",
    ))
    d.has_lvl = any(x in joined for x in (
        "vending/licensing", "licensechecker", "licensevalidator",
        "com/google/android/vending/licensing",
    ))
    if d.has_billing:
        d.notes.append("play-billing markers")
    if d.has_lvl:
        d.notes.append("LVL/licensing markers")

    d.has_installer_check = any(x in joined for x in (
        "getinstallerpackagename", "getinstallsourceinfo", "installsourceinfo",
        "getinstallingpackagename", "com/android/vending", "isinstalledfromplaystore",
        "isfromplaystore", "verifyinstaller", "installsource",
    ))
    if d.has_installer_check:
        d.notes.append("Play Store installer/source checks")



    # Optional aapt2 package name (fast)
    aapt = _which("aapt2") or _which("aapt")
    if aapt and path.suffix.lower() == ".apk":
        try:
            r = subprocess.run(
                [aapt, "dump", "badging", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            m = re.search(r"package: name='([^']+)'", r.stdout or "")
            if m:
                d.package = m.group(1)
        except Exception:
            pass

    return d


def _which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)
