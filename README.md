<p align="center">
  <img src="https://img.shields.io/badge/MADE%20IN-INDIA-SCRIPT?colorA=%23ff8100&colorB=%23017e40&colorC=%23ff0000&style=for-the-badge" alt="Made in INDIA"/>
  <img src="https://img.shields.io/badge/NO%20ROOT-TERMUX-0B1F3A?style=for-the-badge&logo=android&logoColor=white" alt="No Root"/>
  <img src="https://img.shields.io/badge/v1.3.1-Professor%20X%20(FS)-7C3AED?style=for-the-badge" alt="Version"/>
  <img src="https://img.shields.io/badge/ORG-Xforceindia-111111?style=for-the-badge&logo=github" alt="Xforceindia"/>
</p>

<a name="readme-top"></a>

# apkfs

<p align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=800&size=34&pause=1000&color=A78BFA&center=true&vCenter=true&random=false&width=520&lines=apkfs;Professor+X+(FS);One+Click+·+Full+Auto" alt="apkfs"/>
</p>

<p align="center">
  <b>Fully Automatic APK Lab Suite</b><br/>
  <code>apkfs -i YourApp.apk</code> → detect · plan · patch · sign · <code>*_Patched.apk</code>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/SSL%20%2F%20VPN%20%2F%20NSC-AUTO-blue?style=for-the-badge" alt="SSL"/>
  <img src="https://img.shields.io/badge/ADS%20CLEAN-AUTO-green?style=for-the-badge" alt="Ads"/>
  <img src="https://img.shields.io/badge/Flutter%20%2F%20PairIP-DETECT-orange?style=for-the-badge" alt="Flutter"/>
  <img src="https://img.shields.io/badge/BOOM-SUPER%20PACK-red?style=for-the-badge" alt="Boom"/>
</p>

---

## Used Source

<p align="center">
  <a href="https://github.com/REAndroid/APKEditor"><img src="https://img.shields.io/badge/APKEditor-REAndroid-blue?style=for-the-badge&logo=github" alt="APKEditor"/></a>
  <a href="https://github.com/iBotPeaches/Apktool"><img src="https://img.shields.io/badge/Apktool-iBotPeaches-orange?style=for-the-badge&logo=github" alt="Apktool"/></a>
</p>
<p align="center">
  <a href="https://mvnrepository.com/artifact/com.android.tools.build/apksig"><img src="https://img.shields.io/badge/ApkSig-Android%20Tools-green?style=for-the-badge&logo=apachemaven" alt="ApkSig"/></a>
  <a href="https://github.com/google/smali"><img src="https://img.shields.io/badge/Dexlib2%20%2F%20Smali-Google-red?style=for-the-badge&logo=google" alt="Smali"/></a>
  <a href="https://github.com/radareorg/radare2"><img src="https://img.shields.io/badge/radare2-Flutter%20SSL-purple?style=for-the-badge&logo=github" alt="r2"/></a>
</p>

---

## Installation Method
-------

**💢 Requirement PKG 💢**

```bash
termux-setup-storage
pkg update -y
pkg upgrade -y
pkg install -y python openjdk-17 aapt2 unzip git
```

**👉🏻 Install apkfs — run any one method**

### 1st. Method — latest main (recommended)

```bash
pip install --force-reinstall https://github.com/Xforceindia/apkfs/archive/refs/heads/main.zip
```

`OR`

```bash
pip install --force-reinstall https://github.com/Xforceindia/apkfs/archive/refs/heads/main.tar.gz
```

`OR` (git)

```bash
pkg install python git
pip install -U "git+https://github.com/Xforceindia/apkfs.git"
```

### 2nd. Method — editable / local clone

```bash
git clone https://github.com/Xforceindia/apkfs.git
cd apkfs
pip install -U -e .
```

### 3rd. Method — one-shot Termux script

```bash
# from repo root
bash termux-install.sh

# or with private URL
export APKFS_REPO='https://<TOKEN>@github.com/Xforceindia/apkfs.git'
bash termux-install.sh
```

**Optional (Flutter SSL binary pack)**

```bash
pkg install -y radare2
pip install -U r2pipe
```

**Check**

```bash
apkfs doctor
# jars → ~/.apkfs/tools/   (no root)
```

### Linux / PC

```bash
pip install -U "git+https://github.com/Xforceindia/apkfs.git"
# Java 11+ required
apkfs doctor
```

> **Public repo · no token needed**  
> Live: **https://github.com/Xforceindia/apkfs**


---

## Uninstall apkfs
-----

```bash
pip uninstall apkfs
```

---

# Usage Example

## apkfs ( Input Mode )
-----

**Mode `-i` ➸ Full Auto Lab (Input Your APK Path)**

`Default AUTO pack ➸ SSL · VPN · NSC · ads clean · Support (LVL/sig) · Flutter/PairIP detect · sign`

```bash
apkfs -i YourApkPath.apk
apkfs -i YourApkPath.apks
apkfs YourApkPath.apk
```

**Output (ApkPatcher-style)**

```text
✔ DONE
✔ Final APK  ︻デ═一  /sdcard/Download/YourApkPath_Patched.apk
```

Patched file is written **next to your input**.

---

**Flag: `-a` ➸ Try with APKEditor (Default Apktool)**

```bash
apkfs -i YourApkPath.apk -a
```

**Flag: `-c` ➸ Embed Your Capture / Proxy CA**

`With Your Certificate ( .pem / .crt / .cert )`

`If the CA is already trusted under device CA store, you can skip -c — NSC still allows user CAs.`

```bash
apkfs -i YourApkPath.apk -c YourCertificatePath.cert
```

`Multiple certificates`

```bash
apkfs -i YourApkPath.apk -c \
  /sdcard/HttpCanary/certs/HttpCanary.pem \
  /sdcard/Download/Reqable/reqable-ca.crt \
  /sdcard/Download/ProxyPinCA.crt
```

**Flag: `-e` ➸ Emulator jar set (PC emulator)**

```bash
apkfs -i YourApkPath.apk -e
```

**Flag: `-u` ➸ Keep UnSigned APK**

```bash
apkfs -i YourApkPath.apk -u
```

---

## Smali / Detect ( Additional Flags )
-----

**Flag: `-f` / `-p` / `-p -x` ➸ Flutter & PairIP**

`Force Flutter SSL pack (auto-detects libflutter.so by default)`

```bash
apkfs -i YourApkPath.apk -f
```

`Force PairIP pack (VM / Multi-App friendly path)`

```bash
apkfs -i YourApkPath.apk -p
```

`PairIP CoreX hook (experimental, arm64)`

```bash
apkfs -i YourApkPath.apk -p -x
```

**Dedicated PairIP subcommand**

```bash
apkfs pairip -i YourApkPath.apk
apkfs pairip -i YourApkPath.apks --corex
```

**Flag: `-P` ➸ Purchase / Paid / Premium (client heuristics)**

```bash
apkfs -i YourApkPath.apk -P
```

> Not silent-default. Same family as `--unlock`. Online IAP / Play Integrity stay server-side.

**Flag: `-rmads` / `-rmss` / `-rmusb`**

Ads clean + screenshot/USB soften are **ON by default** in `-i`.  
Legacy flags are accepted; to **keep** ads / skip USB-SS:

```bash
apkfs -i YourApkPath.apk --no-ads
apkfs -i YourApkPath.apk --no-usb-ss
```

---

## BOOM Super Mode ( LuckPatcher-inspired )
-----

**Flag: `--boom` ➸ One-click super pack**

```bash
apkfs -i YourApkPath.apk --boom
```

| Layer | Action |
|-------|--------|
| Core | SSL / VPN / mock-location lab smali + NSC |
| Clean | Ads / tracker remove + manifest scrub |
| Support | LVL / signature / installer re-sign friendly |
| Unlock | Client purchase / premium heuristics |
| Safety | Auto backup of original + `working_score` in report |

**Flag: `--unlock` ➸ Client unlock only**

```bash
apkfs -i YourApkPath.apk --unlock
```

**Flag: `--no-support` ➸ Skip LVL/signature support pack**

```bash
apkfs -i YourApkPath.apk --no-support
```

```bash
apkfs -i app.apk              # safe lab default (no unlock)
apkfs -i app.apk --unlock     # client unlock only
apkfs -i app.apk --boom       # full super pack
```

> **Lab only.** Client-side patches do **not** guarantee online IAP, license servers, or Play Integrity.

---

## Speed & Quiet
-----

**Flag: `--fast` ➸ Faster decompile**

`apktool --only-main-classes` (may miss secondary dex)

```bash
apkfs -i YourApkPath.apk --fast
# or
export APKFS_FAST=1
apkfs -i YourApkPath.apk
```

**Flag: `--quiet` ➸ Less plan chatter**

```bash
apkfs -i YourApkPath.apk --quiet
```

**Defaults already tuned**

- apktool `--no-debug-info`
- smali worker pool capped (phone-friendly)
- Termux Java heap via `JAVA_TOOL_OPTIONS` when unset

---

## Merge Mode
-----

**Mode `-m` ➸ Anti-Split (Only Merge APK)**

`Supported: .apks / .apkm / .xapk`

```bash
apkfs -m YourApkPath.apks
```

---

## Plan / Doctor / Manual
-----

**Dry-run (detect + plan only)**

```bash
apkfs -i YourApkPath.apk --dry-run
```

Writes `YourApkPath_apkfs_report/plan.json`.

**Doctor**

```bash
apkfs doctor
apkfs setup
```

**Credits**

```bash
apkfs -C
```

**Manual / raw engine flags**

```bash
apkfs manual -- -i YourApkPath.apk -f -p
```

**Help**

```bash
apkfs -h
apkfs -V
```

---

## What `-i` Auto Does

| Detected | Auto action |
|----------|-------------|
| any APK | SSL / VPN / lab smali + `network_security_config` + sign |
| `.apks` / `.apkm` / `.xapk` | merge → then patch |
| `libflutter.so` | Flutter SSL binary patterns (radare2) |
| PairIP markers | soft integrity path (VM / MultiApp) |
| `-p -x` / `--corex` | experimental PairIP CoreX (arm64) |
| `-c certs` | embed your proxy CAs |
| ads / trackers | **AUTO REMOVE** (AdMob, AppLovin, Unity Ads, …) |
| USB / screenshot | soften `FLAG_SECURE` / USB-debug checks |
| billing / LVL | Support_Pack (re-sign friendly) |

**Never silent-default:** purchase / paid unlock → only `-P` / `--unlock` / `--boom`.

---

## Reports

Every auto run writes:

```text
YourApp_apkfs_report/
  plan.json
  report.json          # includes working_score on BOOM runs
```

Tools cache:

```text
~/.apkfs/tools/        # jars (writable, no root)
~/.apkfs/work/         # scratch
```

---

## Brand

```text
══════════════════════════════════════════════════════════════
  apkfs  v1.3.1  ·  Professor X (FS)
  Fully Automatic APK Lab Suite
══════════════════════════════════════════════════════════════

  🧠⚡  Professor X (FS)  ⚡🧠
```

---

## Modules

| Layer | Role |
|-------|------|
| `apkfs.cli` | ApkPatcher-style `-i` / flags / bare APK path |
| `apkfs.auto` | detect → plan → pipeline → score |
| `apkfs.engine` | smali / ads / support / flutter / pairip / sign |
| `apkfs.brand` | Professor X (FS) banner |

---

## NOTE

## 🇮🇳 Professor X (FS) · Xforceindia 🇮🇳

<p align="center">
  <a href="https://github.com/Xforceindia/apkfs"><img src="https://img.shields.io/badge/GITHUB-Xforceindia%2Fapkfs-181717?style=for-the-badge&logo=github" alt="GitHub"/></a>
</p>

**Authorized security testing, CTF, and your own apps only.**  
Client-side patches do **not** bypass server-side Play Integrity / license.  
You are responsible for local law and app ToS.

```text
apkfs -i app.apk
# → app_Patched.apk
```

<p align="right"><a href="#readme-top">⬆ back to top</a></p>
