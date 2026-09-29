# apkfs

```
  apkfs  ·  Professor X (FS)
  Fully Automatic APK Lab Suite
```

**One command. Full auto.**

```bash
apkfs -i YourApp.apk
apkfs -i YourApp.apks
```

No flag soup. `apkfs` detects Flutter / PairIP / split APKs, builds a plan, patches, rebuilds, signs, and writes a report.

---

## Install — Termux phone (**no root**)

Works like original ApkPatcher on Termux: userland only, no Magisk/root.

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

Also auto (lab friction): screenshot `FLAG_SECURE`, USB-debug detection, ads call-sites (disable with `--no-ads` / `--no-usb-ss`).

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

(Replaces older “Jai Shree Ram” banner from upstream lineage.)

---

## Modules inside

| Layer | Role |
|-------|------|
| `apkfs.cli` | user CLI (`-i` full auto) |
| `apkfs.auto` | detect → plan → drive engine |
| `apkfs.engine` | battle-tested smali / flutter / pairip / sign core (upgraded fork of ApkPatcher lineage) |
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
