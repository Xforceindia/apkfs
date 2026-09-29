"""Extra clean-up applied automatically with ads remove (manifest-level)."""

from __future__ import annotations

from ..ANSI_COLORS import ANSI
from ..MODULES import IMPORT

C = ANSI()
M = IMPORT()


# Common ad / tracking components often declared in manifest
_KILL_NAME_SNIPS = (
    "adactivity",
    "adactivity",
    "adsactivity",
    "admob",
    "applovin",
    "unityads",
    "ironsource",
    "vungle",
    "chartboost",
    "inmobi",
    "appodeal",
    "startapp",
    "fyber",
    "tapjoy",
    "mopub",
    "facebook.ads",
    "audience.network",
    "com.google.android.gms.ads",
    "com.google.android.gms.measurement",
    "appsflyer",
    "com.adjust.sdk",
)


def Clean_Manifest_Ads(manifest_path: str) -> int:
    """
    Soft-disable obvious ad/tracker activities/services/receivers/meta-data in manifest.
    Does not delete whole app components blindly — only known ad SDK name snippets.
    Returns number of lines neutralized.
    """
    try:
        text = open(manifest_path, "r", encoding="utf-8", errors="ignore").read()
    except OSError:
        return 0

    original = text
    removed = 0

    # Remove meta-data that looks like ad app ids
    def _meta_sub(m):
        nonlocal removed
        block = m.group(0).lower()
        if any(s in block for s in (
            "application_id", "app_id", "admob", "applovin", "ads", "facebook_app",
            "com.google.android.gms.ads", "appsflyer", "adjust"
        )):
            removed += 1
            return ""
        return m.group(0)

    text = M.re.sub(
        r"\s*<meta-data\b[^>]*/>",
        _meta_sub,
        text,
        flags=M.re.I,
    )

    # Comment-out / strip components whose android:name smells like ads
    def _comp_sub(m):
        nonlocal removed
        block = m.group(0)
        low = block.lower()
        if any(s in low for s in _KILL_NAME_SNIPS):
            removed += 1
            return ""  # drop component
        return block

    for tag in ("activity", "activity-alias", "service", "receiver", "provider"):
        text = M.re.sub(
            rf"\s*<{tag}\b[^>]*?(?:/>|>[\s\S]*?</{tag}>)",
            _comp_sub,
            text,
            flags=M.re.I,
        )

    # Disable auto backup of ad ids noise — optional no-op

    if text != original:
        open(manifest_path, "w", encoding="utf-8", errors="ignore").write(text)
        print(
            f"\n{C.S} Clean Manifest {C.E} {C.OG}➸❥ {C.PN}{removed} {C.C}ad/tracker entries stripped {C.G} ✔\n"
        )
    return removed
