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
        if "flutter_assets" in low or "/flutter/" in low or "res/xml/flutter_" in low:
            d.has_flutter = True
        if "kernel_blob.bin" in low or low.endswith("isolate_snapshot_data"):
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

    # Prefer specific API names — bare "com/android/vending" false-positives on any Play library
    d.has_installer_check = any(x in joined for x in (
        "getinstallerpackagename", "getinstallsourceinfo", "installsourceinfo",
        "getinstallingpackagename", "isinstalledfromplaystore",
        "isfromplaystore", "verifyinstaller", "getinstallsource",
    ))
    if d.has_installer_check:
        d.notes.append("Play Store installer/source checks")

    # Dex markers (PairIP Application class / Flutter JNI often only in classes*.dex)
    if not d.has_pairip or not d.has_flutter:
        try:
            with zipfile.ZipFile(path, "r") as zf:
                for n in zf.namelist():
                    low = n.lower()
                    if not low.endswith(".dex"):
                        continue
                    try:
                        data = zf.read(n)
                    except Exception:
                        continue
                    if not d.has_pairip and (
                        b"com/pairip" in data or b"com.pairip" in data or b"pairip" in data.lower()
                    ):
                        d.has_pairip = True
                        d.notes.append(f"pairip dex marker in {n}")
                    if not d.has_flutter and (
                        b"io.flutter" in data or b"FlutterJNI" in data or b"flutter_assets" in data
                    ):
                        d.has_flutter = True
                        d.notes.append(f"flutter dex marker in {n}")
                    if d.has_pairip and d.has_flutter:
                        break
        except Exception as e:
            d.notes.append(f"dex scan skipped: {e}")

    # Split bundles: nested base.apk scan
    if d.is_split and (not d.has_flutter or not d.has_pairip):
        try:
            import io
            with zipfile.ZipFile(path, "r") as zf:
                inner = [n for n in zf.namelist() if n.lower().endswith(".apk")]
                inner.sort(key=lambda n: (0 if Path(n).name.lower() == "base.apk" else 1, n))
                for name in inner[:8]:
                    try:
                        data = zf.read(name)
                    except Exception:
                        continue
                    try:
                        with zipfile.ZipFile(io.BytesIO(data)) as z2:
                            names2 = z2.namelist()
                            n2 = "\n".join(x.lower() for x in names2)
                            if not d.has_flutter and ("flutter_assets" in n2 or "libflutter.so" in n2):
                                d.has_flutter = True
                                d.notes.append(f"flutter in nested {name}")
                            if not d.has_pairip and "pairip" in n2:
                                d.has_pairip = True
                                d.notes.append(f"pairip paths in nested {name}")
                            for x in names2:
                                if x.startswith("lib/"):
                                    parts = x.split("/")
                                    if len(parts) >= 3 and parts[1] not in d.abis:
                                        d.abis.append(parts[1])
                                    if parts[-1] == "libflutter.so":
                                        d.has_flutter = True
                                    if parts[-1] == "libpairipcore.so":
                                        d.has_pairip = True
                            if not d.has_pairip or not d.has_flutter:
                                for x in names2:
                                    if not x.lower().endswith(".dex"):
                                        continue
                                    try:
                                        dx = z2.read(x)
                                    except Exception:
                                        continue
                                    if not d.has_pairip and (b"com/pairip" in dx or b"pairip" in dx.lower()):
                                        d.has_pairip = True
                                        d.notes.append(f"pairip dex in nested {name}:{x}")
                                    if not d.has_flutter and (b"io.flutter" in dx or b"FlutterJNI" in dx):
                                        d.has_flutter = True
                                    if d.has_pairip and d.has_flutter:
                                        break
                    except zipfile.BadZipFile:
                        pass
                    if d.has_flutter and d.has_pairip:
                        break
            d.abis = sorted(set(d.abis))
            d.has_arm64 = any("arm64" in a for a in d.abis)
        except Exception as e:
            d.notes.append(f"split nested scan skipped: {e}")

    if d.has_flutter and "flutter" not in " ".join(d.notes).lower():
        d.notes.append("flutter assets/engine markers")
    if d.has_pairip and "pairip" not in " ".join(d.notes).lower():
        d.notes.append("pairip protection markers")

    # Package name via aapt (prefer aapt dump badging)
    aapt = _which("aapt") or _which("aapt2")
    if aapt and path.suffix.lower() == ".apk":
        try:
            r = subprocess.run(
                [aapt, "dump", "badging", str(path)],
                capture_output=True, text=True, timeout=30, check=False,
            )
            out = r.stdout or ""
            m = re.search(r"package: name='([^']+)'", out)
            if not m:
                m = re.search(r'package: name="([^"]+)"', out)
            if m:
                d.package = m.group(1)
        except Exception:
            pass

    return d



def _which(cmd: str) -> str | None:
    from shutil import which
    import os
    w = which(cmd)
    if w:
        return w
    for base in (os.path.expanduser("~/.local/bin"), "/usr/local/bin",
                 "/data/data/com.termux/files/usr/bin"):
        cand = os.path.join(base, cmd)
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None
