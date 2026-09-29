"""
Support Pack — LuckPatcher-inspired *client-side* lab patterns (no root).

What this does (APK rebuild path, like LP "create modified APK"):
  - Google Play LVL / LicenseChecker soft gates
  - common signature / installer integrity gates (so re-signed APK can run)
  - Play Store install-source spoof (getInstallerPackageName + API 30 InstallSourceInfo)
  - "Get it on Play Store" / sideload gate heuristics (client-side)
  - BillingClient / premium boolean heuristics (best-effort, often fails if server-checked)

What this does NOT do:
  - real Google Play billing / server receipts
  - Play Integrity / SafetyNet server verdicts
  - guaranteed IAP on online games
  - system-level installer identity (that needs adb -i com.android.vending at install time)

For authorized testing of apps you own or have permission to test.
"""

from __future__ import annotations

from ._smali_fix import write_smali
from ..ANSI_COLORS import ANSI
from ..MODULES import IMPORT

C = ANSI()
M = IMPORT()
C_Line = f"{C.CC}{'_' * 61}"


def _scan(path, regs, count, lock):
    try:
        text = open(path, "r", encoding="utf-8", errors="ignore").read()
    except OSError:
        return None
    hit = False
    for r in regs:
        if r.search(text):
            hit = True
            break
    if not hit:
        return None
    def _bump():
        try:
            if hasattr(count, "value"):
                count.value += 1
                n = count.value
            else:
                count[0] += 1
                n = count[0]
        except Exception:
            n = 0
        print(f"\r{C.S} Support targets {C.E} {C.OG}➸❥ {C.PN}{n}", end="", flush=True)
    if lock:
        try:
            with lock:
                _bump()
        except Exception:
            _bump()
    else:
        _bump()
    return path



def Support_Smali_Pack(smali_folders, *, unlock: bool = True) -> dict:
    """
    Apply support patterns across smali trees.
    Returns stats dict for report.
    """
    patterns = [
        # ---- LVL / License (classic LP targets) ----
        (
            r"(invoke-\w+ \{[^}]*\}, Lcom/google/android/vending/licensing/Policy;->allowAccess\(\)Z[^>]*?\s+)move-result ([pv]\d+)",
            r"\1const/4 \2, 0x1",
            "LVL Policy.allowAccess → true",
            "lvl",
        ),
        (
            r"(\.method [^(]*allowAccess\(\)Z\s+\.locals \d+)[\s\S]*?(\n.end method)",
            r"\1\n    const/4 v0, 0x1\n    return v0\2",
            "LVL allowAccess method body",
            "lvl",
        ),
        (
            r"(\.method [^(]*verify\([^)]*\)V\s+\.locals \d+)(?:(?!\.end method)[\s\S])*?(Lcom/google/android/vending/licensing/|LicenseValidator)(?:(?!\.end method)[\s\S])*?(\n.end method)",
            r"\1\n    return-void\2",
            "LVL LicenseValidator.verify soften",
            "lvl",
        ),
        (
            r"(\.method [^(]*(?:checkAccess|checkLicense|processServerResponse)\([^)]*\)V\s+\.locals \d+)[\s\S]*?(\s+return-void\n.end method)",
            r"\1\2",
            "LVL checkAccess/checkLicense empty",
            "lvl",
        ),
        # response codes: LICENSED = 0x0 in old LVL
        (
            r"(const/16 [pv]\d+, 0x)(?:100|101|102|103)(\s+.*License)",
            r"\g<1>0\2",
            "LVL error codes nudge",
            "lvl",
        ),
        # ---- Signature / tamper (needed after re-sign, LP-like) ----
        (
            r"(invoke-\w+ \{[^}]*\}, Landroid/content/pm/PackageManager;->checkSignatures\(.*?\)I[^>]*?)move-result ([pv]\d+)",
            r"\1const/4 \2, 0x0",
            "PackageManager.checkSignatures → SIGNATURE_MATCH(0)",
            "signature",
        ),
        (
            r"(invoke-\w+ \{[^}]*\}, Landroid/content/pm/Signature;->(?:hashCode|toCharsString|toByteArray)\(\)[^>]*?move-result)",
            r"# apkfs-support keep invoke for stack; softened below\n    \1",
            "Signature read marker",
            "signature",
        ),
        (
            r"(\.method [^(]*(?:verifyIntegrity|checkSignature|validateSignature|isSignatureValid|verifySigningCertificate)\([^)]*\)Z\s+\.locals \d+)[\s\S]*?(\n.end method)",
            r"\1\n    const/4 v0, 0x1\n    return v0\2",
            "custom signature valid → true",
            "signature",
        ),
        (
            r"(\.method [^(]*(?:verifyIntegrity|checkSignature|validateSignature)\([^)]*\)V\s+\.locals \d+)[\s\S]*?(\s+return-void\n.end method)",
            r"\1\2",
            "custom signature void checks emptied",
            "signature",
        ),
        # ---- Installer / Play Store source (sideload & "Get from Play Store" gates) ----
        # Classic API (pre-30) — also in core Smali_Patch; reinforce here
        (
            r"(invoke-(?:virtual|interface) \{[^}]*\}, Landroid/content/pm/PackageManager;->getInstallerPackageName\(Ljava/lang/String;\)Ljava/lang/String;[^>]*?)move-result-object ([pv]\d+)",
            r'\1const-string \2, "com.android.vending"',
            "getInstallerPackageName → com.android.vending",
            "installer",
        ),
        # Android 11+ PackageManager.getInstallSourceInfo(pkg)
        (
            r"(invoke-(?:virtual|interface) \{[^}]*\}, Landroid/content/pm/PackageManager;->getInstallSourceInfo\(Ljava/lang/String;\)Landroid/content/pm/InstallSourceInfo;[^>]*?)move-result-object ([pv]\d+)",
            r"\1# apkfs: keep InstallSourceInfo object; field reads patched below\n    move-result-object \2",
            "getInstallSourceInfo marker",
            "installer",
        ),
        # InstallSourceInfo.getInstallingPackageName() / getInitiatingPackageName() / getOriginatingPackageName()
        (
            r"(invoke-(?:virtual|interface) \{[^}]*\}, Landroid/content/pm/InstallSourceInfo;->(?:getInstallingPackageName|getInitiatingPackageName|getOriginatingPackageName)\(\)Ljava/lang/String;[^>]*?)move-result-object ([pv]\d+)",
            r'\1const-string \2, "com.android.vending"',
            "InstallSourceInfo.*PackageName → Play Store",
            "installer",
        ),
        # Some OEMs / wrappers expose installing package via helper returning String
        (
            r"(invoke-\w+ \{[^}]*\}, L[^;]+;->(?:getInstallerPackageName|getInstallingPackageName|getInstallSource|getInstallerName|readInstallerPackageName)\([^)]*\)Ljava/lang/String;[^>]*?)move-result-object ([pv]\d+)",
            r'\1const-string \2, "com.android.vending"',
            "helper getInstaller* → Play Store",
            "installer",
        ),
        # Boolean gates: isFromPlayStore / verifyInstaller / etc. → TRUE
        (
            r"(\.method [^(]*(?:isInstalledFromPlayStore|isInstalledFromGooglePlay|isFromPlayStore|isFromGooglePlay|isPlayStoreInstall|isPlayStoreInstalled|installedFromPlayStore|installedFromGooglePlay|verifyInstaller|verifyInstallerId|checkInstaller|checkInstallSource|isValidInstaller|isValidInstallSource|isStoreVersion|isStoreInstall|isDownloadFromPlayStore|isGooglePlayInstall|fromPlayStore|fromGooglePlay|hasValidInstaller|hasPlayStoreInstaller)\([^)]*\)Z\s+\.locals \d+)[\s\S]*?(\n.end method)",
            r"\1\n    const/4 v0, 0x1\n    return v0\2",
            "Play Store / installer boolean → true",
            "installer",
        ),
        # isSideloaded / unknown-source → FALSE
        (
            r"(\.method [^(]*(?:isSideload|isSideLoad|isSideloaded|isSideLoaded|isNonStore|isNotFromPlayStore|isIllegalInstall|isUnofficialInstall|isUnknownSource|isThirdPartyInstall)\([^)]*\)Z\s+\.locals \d+)[\s\S]*?(\n.end method)",
            r"\1\n    const/4 v0, 0x0\n    return v0\2",
            "sideload / unknown-source boolean → false",
            "installer",
        ),
        # Boolean object wrappers → TRUE
        (
            r"(\.method [^(]*(?:isInstalledFromPlayStore|isFromPlayStore|isPlayStoreInstall|verifyInstaller|isStoreVersion|isValidInstaller)\([^)]*\)Ljava/lang/Boolean;\s+\.locals \d+)[\s\S]*?(\n.end method)",
            r"\1\n    const/4 v0, 0x1\n    invoke-static {v0}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;\n    move-result-object v0\n    return-object v0\2",
            "Play Store Boolean → TRUE",
            "installer",
        ),
        # equals("com.android.vending") / feedback — force true after compare
        (
            r'(const-string [pv]\d+, "com\.android\.vending"[\s\S]{0,160}?invoke-virtual \{[^}]*\}, Ljava/lang/String;->equals\(Ljava/lang/Object;\)Z[^>]*?)move-result ([pv]\d+)',
            r"\1const/4 \2, 0x1",
            "equals(com.android.vending) → true",
            "installer",
        ),
        (
            r'(const-string [pv]\d+, "com\.google\.android\.feedback"[\s\S]{0,160}?invoke-virtual \{[^}]*\}, Ljava/lang/String;->equals\(Ljava/lang/Object;\)Z[^>]*?)move-result ([pv]\d+)',
            r"\1const/4 \2, 0x1",
            "equals(com.google.android.feedback) → true",
            "installer",
        ),
        # ---- Update nags / force update ----
        (
            r'"(com\.google\.android\.play\.core\.appupdate|com\.google\.android\.play\.core\.install)"',
            r'""',
            "Play AppUpdate service string blank",
            "update",
        ),
        (
            r"(\.method [^(]*(?:isUpdateAvailable|isImmediateUpdateAllowed|startUpdateFlow)\([^)]*\)Z\s+\.locals \d+)[\s\S]*?(\n.end method)",
            r"\1\n    const/4 v0, 0x0\n    return v0\2",
            "in-app update available → false",
            "update",
        ),
        # ---- Get-from-Play-Store nags / force-store dialogs ----
        (
            r"(\.method [^(]*(?:shouldShowPlayStore|isPlayStoreRequired|requirePlayStore|mustInstallFromPlay|openPlayStore|gotoPlayStore|launchPlayStore|showPlayStoreDialog|checkPlayStore|verifyPlayStore|redirectToPlayStore|navigateToPlayStore|forcePlayStore|blockIfNotPlayStore)\([^)]*\)Z\s+\.locals \d+)[\s\S]*?(\n.end method)",
            r"\1\n    const/4 v0, 0x0\n    return v0\2",
            "play_store_required/show → false",
            "installer",
        ),
        (
            r"(\.method [^(]*(?:shouldShowPlayStore|openPlayStore|gotoPlayStore|launchPlayStore|showPlayStoreDialog|redirectToPlayStore|navigateToPlayStore)\([^)]*\)V\s+\.locals \d+)[\s\S]*?(\n.end method)",
            r"\1\n    return-void\2",
            "play_store_action void empty",
            "installer",
        ),
        # market:// / play.google.com startActivity nops (client nag)
        (
            r'(const-string [pv]\d+, "(?:market://details|https?://play\.google\.com/store)[^"]*"[\s\S]{0,400}?invoke-(?:virtual|interface) \{[^}]*\}, Landroid/content/Context;->startActivity\(Landroid/content/Intent;\)V)',
            r"nop",
            "startActivity(Play Store) nop",
            "installer",
        ),
        # PairIP / license client without requiring libpairipcore.so
        (
            r"(invoke-\w+ \{[^}]*\}, L[^;]*[Pp]air[Ii]p[^;]*;->(?:verifyIntegrity|checkIntegrity|authenticate|checkLicense|doCheck)\([^)]*\)V)",
            r"nop",
            "pairip invoke integrity/license nop",
            "lvl",
        ),
        (
            r"(\.method [^(]*(?:verifyIntegrity|checkIntegrity)\([^)]*\)V\s+\.locals \d+)[\s\S]*?(\n.end method)",
            r"\1\n    return-void\2",
            "verifyIntegrity method empty",
            "signature",
        ),
    ]

    if unlock:
        patterns.extend(
            [
                # ---- Premium / pro gates (heuristic names — LP style client only) ----
                (
                    r"(\.method [^(]*(?:isPremium|isPro|isVip|isVipUser|getIsPremium|getPremium|isSubscribed|hasSubscription|isUnlocked|isProUser|isProVersion|isFullVersion|isLite|wasPurchased|hasPurchased|isPurchased|getPurchaseState|isBillingSetupFinished|isCredit|hasCredit|getCredits|isPaid|isPaidUser|isMember|hasPremium|premiumEnabled|canUsePremium|isRemoveAds|adsRemoved|isAdFree|isAdfree|getIsPro|checkPremium|checkPro)\([^)]*\)Z\s+\.locals \d+)[\s\S]*?(\n.end method)",
                    r"\1\n    const/4 v0, 0x1\n    return v0\2",
                    "premium boolean → true",
                    "unlock",
                ),
                (
                    r"(\.method [^(]*(?:isPremium|isPro|isVip|isSubscribed|hasSubscription|isUnlocked|isPurchased|isCredit|isPaid|isAdFree|isRemoveAds)\([^)]*\)Ljava/lang/Boolean;\s+\.locals \d+)[\s\S]*?(\n.end method)",
                    r"\1\n    const/4 v0, 0x1\n    invoke-static {v0}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;\n    move-result-object v0\n    return-object v0\2",
                    "premium Boolean → TRUE",
                    "unlock",
                ),
                (
                    r"(invoke-\w+ \{[^}]*\}, Lcom/android/billingclient/api/Purchase;->getPurchaseState\(\)I[^>]*?)move-result ([pv]\d+)",
                    r"\1const/4 \2, 0x1",
                    "BillingClient PurchaseState → PURCHASED(1)",
                    "unlock",
                ),
                (
                    r"(invoke-\w+ \{[^}]*\}, Lcom/android/billingclient/api/BillingClient;->isReady\(\)Z[^>]*?)move-result ([pv]\d+)",
                    r"\1const/4 \2, 0x1",
                    "BillingClient.isReady → true",
                    "unlock",
                ),
                (
                    r"(\.method [^(]*onBillingSetupFinished\(Lcom/android/billingclient/api/BillingResult;\)V\s+\.locals \d+)[\s\S]*?(\n.end method)",
                    r"\1\n    return-void\2",
                    "onBillingSetupFinished soften",
                    "unlock",
                ),
                (
                    r'const-string [pv]\d+, "(?:PURCHASED|owned|premium|pro_unlocked)"',
                    None,  # marker only — handled via other patterns
                    "purchase string marker",
                    "unlock",
                ),
                # generic getPrice → 0 already in Smali_Patch Purchase
            ]
        )

    # drop patterns with None replacement (markers)
    patterns = [p for p in patterns if p[1] is not None]

    target_regex = [M.re.compile(p[0]) for p in patterns]
    smali_paths = []
    for folder in smali_folders:
        for root, _, files in M.os.walk(folder):
            for f in files:
                if f.endswith(".smali"):
                    smali_paths.append(M.os.path.join(root, f))

    match = []
    try:
        with M.Manager() as mt:
            count = mt.Value("i", 0)
            lock = mt.Lock()
            with M.Pool(max(1, min(4, (M.cpu_count() or 2)))) as pool:
                match = [
                    x
                    for x in pool.starmap(
                        _scan,
                        [(sp, target_regex, count, lock) for sp in smali_paths],
                    )
                    if x
                ]
    except Exception:
        count = [0]
        for sp in smali_paths:
            r = _scan(sp, target_regex, count, None)
            if r:
                match.append(r)

    print(f" {C.G} ✔", flush=True)
    print(f"\n{C_Line}\n")

    stats = {"files": 0, "hits": 0, "by_tag": {}}
    if not match:
        print(f"{C.S} Support Pack {C.E} {C.Y}no classic LVL/billing patterns found (obfuscated or server-side){C.CC}\n")
        return stats

    applied_files = set()
    for pattern, repl, desc, tag in patterns:
        hits = 0
        for fp in match:
            try:
                content = open(fp, "r", encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            new_c, n = M.re.subn(pattern, repl, content)
            if n:
                write_smali(fp, new_c)
                hits += n
                applied_files.add(fp)
                stats["by_tag"][tag] = stats["by_tag"].get(tag, 0) + n
        if hits:
            stats["hits"] += hits
            print(f"\n{C.S} Support {C.E} {C.G}{desc}")
            print(f"{C.G}  └──── {C.PN}{hits}{C.C} hit(s) {C.G}✔")

    stats["files"] = len(applied_files)
    print(
        f"\n{C.S} Support Pack Total {C.E} {C.OG}➸❥ {C.PN}{stats['hits']}{C.C} patches "
        f"in {C.PN}{stats['files']}{C.C} files {C.G}✔\n"
    )
    print(f"{C_Line}\n")
    return stats


def support_score(det_flags: dict, stats: dict | None) -> dict:
    """
    LuckPatcher-like traffic-light for report (not a guarantee).
    green / yellow / red
    """
    stats = stats or {}
    hits = stats.get("hits", 0)
    tags = stats.get("by_tag", {})
    reasons = []
    score = "yellow"

    if det_flags.get("pairip"):
        reasons.append("PairIP present — support patches may be incomplete")
        # do not force yellow below; hits below can still promote to green
    if det_flags.get("flutter") and not det_flags.get("ssl_ok", True):
        reasons.append("Flutter SSL depends on engine patterns")

    inst = tags.get("installer", 0)
    if hits >= 8 or tags.get("lvl", 0) + tags.get("unlock", 0) >= 4 or inst >= 2:
        score = "green"
        reasons.append(f"strong client-side pattern hits ({hits})")
    elif hits >= 1:
        score = "yellow"
        reasons.append(f"partial client-side hits ({hits})")
    else:
        score = "red"
        reasons.append("no LVL/billing/installer smali hits — likely obfuscated or server-side")

    if inst:
        reasons.append(f"Play Store installer/source spoof hits ({inst})")

    if det_flags.get("has_ads"):
        reasons.append("ads SDKs detected — auto-clean applied separately")

    return {
        "score": score,
        "hits": hits,
        "tags": tags,
        "reasons": reasons,
        "note": "Client-side only. Online IAP/Play Integrity still enforced by servers.",
    }
