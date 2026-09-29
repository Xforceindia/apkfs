#!/data/data/com.termux/files/usr/bin/bash
# apkfs — Termux install (NO ROOT)
# Professor X (FS)
set -e

echo "════════════════════════════════════════"
echo "  apkfs · Professor X (FS)"
echo "  Termux setup — no root required"
echo "════════════════════════════════════════"

pkg update -y
pkg upgrade -y
pkg install -y python openjdk-17 aapt2 unzip git which

# storage access for /sdcard (user confirms once)
if command -v termux-setup-storage >/dev/null 2>&1; then
  if [ ! -d "$HOME/storage/shared" ]; then
    echo "[*] termux-setup-storage (allow permission popup)"
    termux-setup-storage || true
  fi
fi

pip install -U pip wheel setuptools

# Install from private repo if token provided, else local path / public
if [ -n "$APKFS_REPO" ]; then
  pip install -U "git+${APKFS_REPO}"
elif [ -f ./pyproject.toml ] && grep -q 'name = "apkfs"' ./pyproject.toml 2>/dev/null; then
  pip install -U -e .
else
  echo "[*] Set APKFS_REPO to your git URL, e.g.:"
  echo "    export APKFS_REPO='https://<TOKEN>@github.com/Xforceindia/apkfs.git'"
  echo "    bash termux-install.sh"
  # try default private clone style without embedding token here
  pip install -U "git+https://github.com/Xforceindia/apkfs.git" || true
fi

# optional flutter SSL
pkg install -y radare2 || true
pip install -U r2pipe asn1crypto multiprocess requests || true

mkdir -p "$HOME/.apkfs/tools" "$HOME/.apkfs/work"

echo
echo "[✔] install done"
echo "    apkfs doctor"
echo "    apkfs -i /sdcard/Download/YourApp.apk"
echo
echo "  🧠⚡  Professor X (FS)  ⚡🧠"
echo
