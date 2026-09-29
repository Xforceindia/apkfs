# apkfs

```
  apkfs  ·  Professor X (FS)
  Fully Automatic APK Lab Suite
```

**One command. Full auto.** (same as old `ApkPatcher -i`)

```bash
apkfs -i firoj.apk
apkfs -i firoj.apks
apkfs firoj.apk
apkfs -i /sdcard/Download/app.apk --fast
```

**Output (like ApkPatcher):** `firoj_Patched.apk` next to your input file.


No flag soup. `apkfs` detects Flutter / PairIP / split APKs, builds a plan, patches, rebuilds, signs, and writes a report.

---

## Install — Termux phone (**no root**)

Runs on Termux userland only — no Magisk/root required.

```bash
# 1) packages
pkg update -y
pkg install -y python openjdk-17 aapt2 unzip git

# 2) allow /sdcard access (popup once)
termux-setup-storage

# 3) install apkfs (private repo needs token once)
#    export APKFS_REPO='https://<GITHUB_TOKEN>@github.com/xforcemob-commits/apkfs.git'
#    pip install -U "git+${APKFS_REPO}"
pip install -U git+https://github.com/xforcemob-commits/apkfs.git

# 4) optional Flutter SSL support
pkg install -y radare2
pip install -U r2pipe

# 5) check
apkfs setup          # or: apkfs doctor
```

One-shot script (from repo):

```bash
bash termux-install.sh
```

Jars auto-download into **`~/.apkfs/tools/`** (writable, no root).

### Linux / Windows

```bash
pip install -U git+https://github.com/xforcemob-commits/apkfs.git
# need Java 11+
```

---

## Usage

### BOOM super mode (LuckPatcher-style modified APK)

One click pack inspired by LP *create modified APK* (no root):

```bash
apkfs -i /sdcard/Download/app.apk --boom
```

Includes: SSL/VPN/NSC · auto ads clean · LVL/signature support · client unlock heuristics · auto backup of original · working-score in report.

```bash
apkfs -i app.apk                 # safe lab default (no unlock)
apkfs -i app.apk --unlock        # client unlock only
apkfs -i app.apk --boom          # full super pack
```

> Client-side only. Online IAP / Play Integrity are server-checked and will not magically pass.

### Full auto (recommended)

```bash
# phone paths (Termux)
apkfs -i /sdcard/Download/app.apk
apkfs -i /sdcard/Download/app.apks
apkfs -i /sdcard/Download/app.apk -c /sdcard/HttpCanary/certs/HttpCanary.pem

# relative / cwd also OK
apkfs -i app.apk
apkfs -i app.apks
```

What auto does:

| Detected | Auto action |
|----------|-------------|
| any APK | SSL / VPN / mock-location lab smali + `network_security_config` + sign |
| `.apks/.apkm/.xapk` | merge → then patch |
| `libflutter.so` | Flutter SSL binary patterns (radare2) |
| PairIP | soft integrity path (VM/MultiApp friendly) |
| `--corex` + arm64 split | experimental PairIP CoreX |
| `-c certs` | embed your proxy CAs |

Also auto while patching:

- **ads / trackers AUTO REMOVE** (AdMob, AppLovin, Unity Ads, … + manifest clean)
- screenshot `FLAG_SECURE`, USB-debug detection soften
- disable with `--no-ads` / `--no-usb-ss` if you want to keep them


**Never auto:** purchase / paid unlock heuristics (policy).

### Dry-run (plan only)

```bash
apkfs -i app.apk --dry-run
```

Writes `*_apkfs_report/plan.json`.

### Merge only

```bash
apkfs -m app.apks
```

### PairIP helper

```bash
apkfs pairip -i app.apk
apkfs pairip -i app.apks --corex
```

### Doctor

```bash
apkfs doctor
```

### Manual / legacy power flags

```bash
apkfs manual -- -i app.apk -f -p -rmss
```

---

## Brand

End-of-run signature:

```
🧠⚡  Professor X (FS)  ⚡🧠
```

(Branded end-to-end as Professor X (FS).)

---

## Modules inside

| Layer | Role |
|-------|------|
| `apkfs.cli` | user CLI (`-i` full auto) |
| `apkfs.auto` | detect → plan → drive engine |
| `apkfs.engine` | battle-tested smali / flutter / pairip / sign core (smali/flutter/pairip patch engine) |
| `apkfs.brand` | Professor X (FS) banner |

Related research lineage (credits): Apktool, APKEditor, ApkSig, apk-mitm ideas, AbhiTheModder Flutter/TG notes, RKPairip / Pairip string-recovery ecosystem, mitmproxy android-unpinner concepts.

---

## Reports

Every auto run writes:

```text
YourApp_apkfs_report/
  plan.json
  report.json
```

---

## Safety / legal

For **authorized security testing**, CTF, and your own apps only.  
Client-side patches do **not** bypass server-side Play Integrity / license.  
You are responsible for local law and app ToS.

---

## Professor X (FS)

```
apkfs -i app.apk
```

That’s the whole product.
