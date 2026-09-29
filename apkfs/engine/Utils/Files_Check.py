from ..ANSI_COLORS import ANSI; C = ANSI()
from ..MODULES import IMPORT; M = IMPORT()

try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("apkfs")
except Exception:
    try:
        from apkfs import __version__ as __version__
    except Exception:
        __version__ = "1.4.3"


def _is_termux() -> bool:
    """True on Termux / Android userspace (no root required)."""
    prefix = M.os.environ.get("PREFIX", "")
    if "com.termux" in prefix:
        return True
    if M.os.path.isdir("/data/data/com.termux/files/usr"):
        return True
    if M.os.environ.get("TERMUX_VERSION"):
        return True
    if M.shutil.which("termux-setup-storage") or M.shutil.which("termux-wake-lock"):
        return True
    return False


def _tools_home() -> str:
    """
    Writable tools dir for jars.
    - Termux / normal user:  $HOME/.apkfs/tools
    - Never write into pip site-packages bin/ (not writable / messy)
    """
    home = M.os.path.expanduser("~")
    # Prefer explicit env override
    override = M.os.environ.get("APKFS_HOME")
    base = override if override else M.os.path.join(home, ".apkfs")
    tools = M.os.path.join(base, "tools")
    M.os.makedirs(tools, exist_ok=True)
    return tools


def _script_pkg_dir() -> str:
    return M.os.path.dirname(M.os.path.abspath(__file__))


# ---------------- Set Path ----------------
# Jars live in ~/.apkfs/tools  (Termux-friendly, no root)
run_dir = _tools_home()
script_dir = _script_pkg_dir()

files_dir = M.os.path.join(script_dir, "Files")
pine_dir = M.os.path.join(script_dir, "Pine")
M.os.makedirs(files_dir, exist_ok=True)
M.os.makedirs(pine_dir, exist_ok=True)
M.os.makedirs(run_dir, exist_ok=True)


# Public tool mirrors (jars/so only — not product branding).
# Hosted on existing public release CDN so Termux installs work offline-of-our-org.
_T = "https://github.com/TechnoIndian/Tools/releases/download/Tools"
_PINE = "https://github.com/TechnoIndian/PineHookPlus/releases/download/v1.0"


class FileCheck:
    # ---------------- Set Jar & Files Paths ----------------
    def Set_Path(self):

        # ---------------- Jar Tools (HOME/.apkfs/tools) ----------------
        self.APKTool_Path, self.APKEditor_Path, self.ApkSig = (
            M.os.path.join(run_dir, jar)
            for jar in ("APKTool.jar", "APKEditor.jar", "ApkSig.jar")
        )

        # ---------------- HooK Files (bundled next to package) ----------------
        self.AES_Smali, self.Algorithm_Dex, self.Hook_Smali, self.Pairip_CoreX = (
            M.os.path.join(files_dir, files)
            for files in ("AES.smali", "Algorithm.dex", "Hook.smali", "lib_Pairip_CoreX.so")
        )

        # ---------------- Pine HooK ----------------
        self.config, self.libpine32, self.libpine64, self.loader = (
            M.os.path.join(pine_dir, pine)
            for pine in ("config.json", "libpine32", "libpine64", "loader.dex")
        )

    def isEmulator(self):
        self.APKTool_Path_E = M.os.path.join(run_dir, "APKTool_OR.jar")

    # ---------------- SHA-256 CheckSum ----------------
    def Calculate_CheckSum(self, file_path):
        sha256_hash = M.hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except FileNotFoundError:
            return None

    # ---------------- Download Files ----------------
    def Download_Files(self, Jar_Files):

        import requests

        for File_URL, File_Path, Expected_CheckSum in Jar_Files:
            File_Name = M.os.path.basename(File_Path)

            # Skip download if bundled asset already present & good
            if M.os.path.exists(File_Path) and M.os.path.getsize(File_Path) > 64:
                if Expected_CheckSum:
                    if self.Calculate_CheckSum(File_Path) == Expected_CheckSum:
                        continue
                    # bundled smali may differ slightly — keep if non-jar and size ok
                    if not File_Name.endswith((".jar", ".so", ".dex")) and M.os.path.getsize(File_Path) > 100:
                        continue
                    print(
                        f"{C.ERROR} {C.C}{File_Name} {C.R}is Corrupt (Checksum Mismatch).  ✘\n"
                        f"\n{C.INFO} Re-Downloading, Need Internet Connection.\n"
                    )
                    try:
                        M.os.remove(File_Path)
                    except OSError:
                        pass
                else:
                    continue

            try:
                print(f'\n{C.S} Downloading {C.E} {C.G}{File_Name}')
                print(f'{C.G}       |')
                print(f'{C.G}       └─ {C.CC}{File_URL[:70]}…' if len(File_URL) > 70 else f'{C.G}       └─ {C.CC}{File_URL}')

                with requests.get(File_URL, stream=True, timeout=120) as response:
                    if response.status_code == 200:
                        total_size = int(response.headers.get('content-length', 0))
                        M.os.makedirs(M.os.path.dirname(File_Path) or ".", exist_ok=True)
                        with open(File_Path, 'wb') as f:
                            for data in response.iter_content(1024 * 64):
                                if not data:
                                    continue
                                f.write(data)
                                if total_size:
                                    print(
                                        f"\r       {C.CC}╰┈ PS {C.OG}➸❥ {C.G}{f.tell()/(1024*1024):.2f}/{total_size/(1024*1024):.2f} MB ({f.tell()/total_size*100:.1f}%)",
                                        end='', flush=True
                                    )
                        print('  ✔\n')
                    else:
                        exit(
                            f'\n\n{C.ERROR} Failed to download {C.Y}{File_Name} {C.R}Status Code: {response.status_code}  ✘\n'
                            f'\n{C.INFO} Restart Script / check internet…\n'
                        )

            except requests.exceptions.RequestException:
                exit(
                    f'\n\n{C.ERROR} Got an error while Fetching {C.Y}{File_Path}\n'
                    f'\n{C.ERROR} No internet Connection\n'
                    f'\n{C.INFO} Internet Connection is Required to Download {C.Y}{File_Name}\n'
                )

            if Expected_CheckSum and M.os.path.exists(File_Path):
                got = self.Calculate_CheckSum(File_Path)
                if got != Expected_CheckSum:
                    # warn but don't always hard-fail on optional pine assets
                    if File_Name.endswith(".jar"):
                        exit(
                            f"\n{C.ERROR} Checksum mismatch for {File_Name}\n"
                            f"  expected {Expected_CheckSum}\n  got      {got}\n"
                        )

    # ---------------- Files Download Link ----------------
    def F_D(self):
        # Termux uses APKTool_Termux.jar (Termux-optimized build)
        is_win = M.os.name == "nt"
        apktool_url = f"{_T}/APKTool.jar" if is_win else f"{_T}/APKTool_Termux.jar"
        apktool_sum = (
            "dbf930b076c6b9be08d57c449cacefc3bdd6b71ebd59b3066fc0e1f5b14f9423"
            if is_win
            else "0ac5be78edd13772b3d8e261548e5b7f7d2579310c078476e12b8c91341ea5dc"
        )

        self.Download_Files(
            [
                (f"{_T}/APKEditor.jar", self.APKEditor_Path,
                 "a9cd40df818845456be6d696de6110c89edf4b0a0580cb83438ed6b25a366e67"),
                (apktool_url, self.APKTool_Path, apktool_sum),
                (f"{_T}/ApkSig.jar", self.ApkSig,
                 "f91862c60910f2d85b950c1bee8e0f48494e29202f70b87a957e05314caa616d"),
                # AES.smali: use bundled rebranded asset (skip upstream download)
                (f"{_T}/Algorithm.dex", self.Algorithm_Dex,
                 "f5c7f7764b45cb375aa3da0d78b6a0d141ec2d6b17bba81666c50e1ae8ab1fc3"),
                # Hook.smali: bundled
                (f"{_T}/lib_Pairip_CoreX.so", self.Pairip_CoreX,
                 "22a7954092001e7c87f0cacb7e2efb1772adbf598ecf73190e88d76edf6a7d2a"),
                (f"{_PINE}/config.json", self.config,
                 "da5eef2fa153068e19fca6fabfd144fbb9d7075a61e333814369bd36c51289c1"),
                (f"{_PINE}/libpine32", self.libpine32,
                 "94854417f9bbb4e2dc49a5edede51dfc1eafca2c7cbb163f59585da7d97fc5db"),
                (f"{_PINE}/libpine64", self.libpine64,
                 "d3e415243b80b866d2c75408cc9a26ba4fcab0775f798442f9a622097d845e0c"),
                (f"{_PINE}/loader.dex", self.loader,
                 "c23fcc7aac75d3ea760523876dc837b6506726194c2fe4376d5172c8271b7c46"),
            ]
        )

        if not M.os.environ.get("APKFS_QUIET"):
            M.os.system("cls" if M.os.name == "nt" else "clear")

    # ---------------- Files Download isEmulator ----------------
    def F_D_A(self):
        self.Download_Files(
            [
                (
                    f"{_T}/APKTool.jar",
                    self.APKTool_Path_E,
                    "dbf930b076c6b9be08d57c449cacefc3bdd6b71ebd59b3066fc0e1f5b14f9423",
                )
            ]
        )
