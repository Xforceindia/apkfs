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

## Install

```bash
# Termux
pkg install python openjdk-17 aapt2 -y
pip install -U git+https://github.com/xforcemob-commits/apkfs.git

# Linux / Windows (Java 11+ required)
pip install -U git+https://github.com/xforcemob-commits/apkfs.git
```

Editable (dev):

```bash
git clone https://github.com/xforcemob-commits/apkfs.git
cd apkfs && pip install -e .
```

---

## Usage

### Full auto (recommended)

```bash
apkfs -i app.apk
apkfs -i app.apks
apkfs -i app.apk -c burp.pem reqable.crt
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
