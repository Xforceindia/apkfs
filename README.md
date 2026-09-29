# apkfs

**Professor X (FS)** — Smali patcher lab tool.

Same engine/behavior as [TechnoIndian/ApkPatcher](https://github.com/TechnoIndian/ApkPatcher) **v2.0**.  
Only the **name / brand** is apkfs · Professor X (FS). Patch logic, flags, and defaults are unchanged.

## Install (Termux)

```bash
termux-setup-storage
pkg update -y && pkg upgrade -y
pkg install -y python openjdk-17 aapt2 git
pkg install -y radare2   # Flutter SSL (-f)

pip install -U pip wheel setuptools
pip install --force-reinstall https://github.com/Xforceindia/apkfs/archive/refs/heads/main.zip
```

## Usage (same flags as ApkPatcher)

```bash
# Default = VPN & SSL bypass
apkfs -i YourApk.apk

# APKEditor
apkfs -i YourApk.apk -a

# Flutter SSL
apkfs -i YourApk.apk -f

# PairIP (unsigned / VM) · CoreX
apkfs -i YourApk.apk -p
apkfs -i YourApk.apk -p -x

# Ads / screenshot / USB
apkfs -i YourApk.apk -rmads
apkfs -i YourApk.apk -rmss
apkfs -i YourApk.apk -rmusb

# Merge splits only
apkfs -m Your.apks

# Other flags: -c cert.pem  -e  -u  -P  -r  -pkg  -A  -t  -pine -l ...
apkfs -O
```

Output: `<name>_Patched.apk` next to input.

## Credit

- Engine based on **ApkPatcher** by TechnoIndian / RK  
- APKEditor (REAndroid), Apktool, ApkSig, smali/dexlib2, TG/Flutter scripts as upstream

## License

MIT
