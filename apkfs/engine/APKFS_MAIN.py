from apkfs.engine.CLI import parse_arguments
from .ANSI_COLORS import ANSI; C = ANSI()
from .MODULES import IMPORT; M = IMPORT()

from apkfs.engine.Utils.CRC import CRC_Fix
from apkfs.engine.Utils.Credits import Credits
from apkfs.engine.Utils.Scan import Scan_Apk
from apkfs.engine.Utils.Anti_Splits import Anti_Split
from apkfs.engine.Utils.Files_Check import FileCheck, __version__
from apkfs.engine.Utils.Decompile_Compile import Decompile_Apk, Recompile_Apk, FixSigBlock, Sign_APK

from apkfs.engine.Patch.CERT_NSC import Write_NSC
from apkfs.engine.Patch.Smali_Patch import Smali_Patch
from apkfs.engine.Patch.TG_Patch import TG_Smali_Patch
from apkfs.engine.Patch.Ads_Patch import Ads_Smali_Patch
from apkfs.engine.Patch.Pine_Hook import Pine_Hook_Patch
from apkfs.engine.Patch.Spoof_Patch import Patch_Random_Info
from apkfs.engine.Patch.Flutter_SSL_Patch import Patch_Flutter_SSL
from apkfs.engine.Patch.AES import Copy_AES_Smali, Patch_Algorithm
from apkfs.engine.Patch.Pairip_CoreX import Check_CoreX, Hook_Core
from apkfs.engine.Patch.Manifest_Patch import Fix_Manifest, Patch_Manifest, Permission_Manifest


def Clear():
    if M.os.environ.get("APKFS_QUIET"):
        return
    M.os.system('cls' if M.os.name == 'nt' else 'clear')

if not M.os.environ.get("APKFS_QUIET"):
    Clear()


# ---------------- Install Require Module ---------------
required_modules = ['requests', 'r2pipe', 'asn1crypto', 'multiprocess']
for module in required_modules:
    try:
        __import__(module)
    except ImportError:
        print(f"{C.S} Installing {C.E} {C.OG}➸❥ {C.G}{module}...\n")
        try:
            M.subprocess.check_call([M.sys.executable, "-m", "pip", "install", module])
            Clear()
        except (M.subprocess.CalledProcessError, Exception):
            exit(
                f"\n{C.ERROR} No Internet Connection.  ✘\n"
                f"\n{C.INFO} Internet Connection is Required to Install {C.G} pip install {module}\n"
            )


# ---------------- Check Dependencies ---------------
def check_dependencies():
    try:
        M.subprocess.run(['java', '-version'], stdout=M.subprocess.PIPE, stderr=M.subprocess.PIPE, check=True, text=True)
    except (M.subprocess.CalledProcessError, FileNotFoundError):
        if M.os.name == 'posix' and M.shutil.which('pkg'):
            install_package('openjdk-17')
        else:
            exit(
                f'\n\n{C.ERROR} Java is not installed on Your System.  ✘\n'
                f'\n{C.INFO} Install Java & Run Script Again in New CMD.  ✘\n'
                f'\n{C.INFO} Verify Java Installation {C.G} java --version\n'
            )

    # Termux only — desktop Linux users install aapt/aapt2 themselves
    if M.os.name == 'posix' and M.shutil.which('pkg'):
        install_package('aapt2')


# ---------------- Install Package ---------------
def install_package(pkg):
    """Termux pkg install helper — no-root; no-op outside Termux."""
    if not M.shutil.which('pkg'):
        return
    try:
        result = M.subprocess.run(['pkg', 'list-installed'], stdout=M.subprocess.PIPE, stderr=M.subprocess.PIPE, text=True)
        if pkg not in (result.stdout or ''):
            print(f"{C.S} Installing {C.E} {C.OG}➸❥ {C.G}{pkg}...\n")
            M.subprocess.check_call(['pkg', 'install', '-y', pkg])
            Clear()
    except (M.subprocess.CalledProcessError, Exception) as e:
        print(
            f"\n{C.ERROR} Could not auto-install {pkg}: {e}\n"
            f"{C.INFO} Run manually: {C.G}pkg install {pkg}\n"
        )

F = None  # initialized in _bootstrap()

def _bootstrap():
    """Lazy init jars/deps once per process (import-safe)."""
    global F
    check_dependencies()
    F = FileCheck(); F.Set_Path(); F.F_D()
    if M.os.environ.get("APKFS_QUIET"):
        return
    Date = M.datetime.now().strftime('%d/%m/%y')
    print(f"{C.OG}{f'v{__version__}':>22}")
    # compact brand line instead of old compressed logo
    print(f"{C.P}apkfs engine{C.CC} · {C.OG}Professor X (FS){C.CC} · {C.B}{Date}{C.CC}")
    print("————————|——————————————————|—————————————————|——————————————|————")


# ---------------- Target All Classes Folder ---------------
def Find_Smali_Folders(decompile_dir, isAPKEditor, isPine_Hook):

    dex_path = M.os.path.join(decompile_dir, "dex") if isAPKEditor else decompile_dir

    smali_path = M.os.path.join(decompile_dir, "smali") if isAPKEditor else decompile_dir

    if isPine_Hook:

        classes_files = [file for file in M.os.listdir(dex_path) if file.startswith("classes") and file.endswith(".dex")]

        return f"classes{len(classes_files) + 1}.dex"

    else:

        prefix = "classes" if isAPKEditor else "smali_classes"

        folders = sorted([folder for folder in M.os.listdir(smali_path) if folder == "smali" or folder.startswith(prefix)], key=lambda x: int(x.split(prefix)[-1]) if x.split(prefix)[-1].isdigit() else 0)

        return [M.os.path.join(smali_path, folder) for folder in folders]


# ---------------- Execute Main Function ---------------
def apkfs_main():
    _bootstrap()
    args = parse_arguments()
    isCoreX = args.Hook_CoreX
    isFlutter = args.Flutter; isPairip = args.Pairip
    Skip_Patch = args.Skip_Patch if args.Skip_Patch else []
    isAPKEditor = args.APKEditor; isEmulator = args.For_Emulator

    if isEmulator:
        F.isEmulator()
        F.F_D_A()

    if args.Credits:
        Credits()

    apk_path = args.input or args.Merge

    if not M.os.path.isfile(apk_path):
        exit(
            f"\n{C.ERROR} APK file '{apk_path}' not found.  ✘\n\n"
            f"\n{C.FYI}{C.G} Make Sure There Is 'No Extra Space' In The Folder/Apk Name In The Input Text. If Yes, Then Remove Extra Space & Correct It By Renaming It.\n"
        )
    
    if args.CA_Certificate:
        isCert = [Cert for Cert in args.CA_Certificate if not M.os.path.isfile(Cert)]

        if isCert:
            exit(f"\n{C.ERROR} Not exist: {', '.join(isCert)}\n")

    apk_path = Anti_Split(apk_path, args.Merge, isCoreX)

    # ---------------- Set All Paths Directory ----------------
    decompile_dir = M.os.path.join(M.os.path.expanduser("~"), f"{M.os.path.splitext(M.os.path.basename(apk_path))[0]}_decompiled")

    build_dir = M.os.path.abspath(M.os.path.join(M.os.path.dirname(apk_path), f"{M.os.path.splitext(M.os.path.basename(apk_path))[0]}_Patched.apk"))

    rebuild_dir = build_dir.replace('_Patched.apk', '_Patch.apk')

    manifest_path = M.os.path.join(decompile_dir, 'AndroidManifest.xml')

    if M.os.name == 'posix':
        M.subprocess.run(['termux-wake-lock'], check=False) if M.shutil.which('termux-wake-lock') else None
        print(f"\n{C.X}{C.C} Acquiring Wake Lock...\r")

    start_time = M.time.time()

    # ---------------- Scan & Decompile APK ---------------
    Package_Name, isFlutter_lib, isPairip_lib = Scan_Apk(apk_path, isFlutter, isPairip)

    Decompile_Apk(apk_path, decompile_dir, isEmulator, isAPKEditor, args.AES_Logs, args.Algorithm, args.Pine_Hook, Package_Name)

    smali_folders = Find_Smali_Folders(decompile_dir, isAPKEditor, args.Pine_Hook)

    # ---------------- Pine Hook ----------------
    if args.Pine_Hook:
        Pine_Hook_Patch(decompile_dir, isAPKEditor, args.Load_Modules, smali_folders)
    else:
        # ---------------- AES Logs Inject ----------------
        if args.AES_Logs or args.Algorithm:
            Copy_AES_Smali(decompile_dir, smali_folders, manifest_path, args.AES_S, args.Algorithm, isAPKEditor)

            Permission_Manifest(decompile_dir, manifest_path, isAPKEditor)

        # ---------------- Remove Ads ----------------
        if args.Remove_Ads:
            Ads_Smali_Patch(smali_folders)

        # ---------------- Fake / Spoof Device Info ----------------
        if args.Random_Info:
            Patch_Random_Info(smali_folders, args.Android_ID)

        # ---------------- TG Patch ----------------
        if args.TG_Patch:
            TG_Smali_Patch(decompile_dir, smali_folders, isAPKEditor)


    # ---------------- Other Patch ----------------
    if args.AES_Logs or args.Algorithm or args.Remove_Ads or args.Random_Info or args.Pine_Hook or args.TG_Patch:
        Fix_Manifest(manifest_path, args.Spoof_PKG, args.Pine_Hook, Package_Name)
    else:
        if isFlutter and isFlutter_lib:
            Patch_Flutter_SSL(decompile_dir, isAPKEditor)

        # ---------------- Smali Patching / Hook CoreX ----------------
        if isCoreX and isPairip and isPairip_lib and Check_CoreX(decompile_dir, isAPKEditor):
            M.shutil.rmtree(decompile_dir)
            exit(1)

        Smali_Patch(decompile_dir, smali_folders, isAPKEditor, args.CA_Certificate, args.Android_ID, isPairip, isPairip_lib, args.Spoof_PKG, args.Purchase, args.Remove_SS, Skip_Patch, args.Remove_USB, isCoreX)

        if isCoreX and isPairip and isPairip_lib:
            Hook_Core(args.input, decompile_dir, isAPKEditor, Package_Name)

        # ---------------- Patch Manifest & Write Network Config ----------------
        Fix_Manifest(manifest_path, args.Spoof_PKG, args.Pine_Hook, Package_Name)

        Patch_Manifest(decompile_dir, manifest_path)

        Write_NSC(decompile_dir, isAPKEditor, args.CA_Certificate)

    # ---------------- Recompile APK ----------------
    Recompile_Apk(decompile_dir, apk_path, build_dir, isEmulator, isAPKEditor, Package_Name)

    # ---------------- Fix CRC / Sign APK ----------------
    if not isCoreX and isPairip and isPairip_lib or args.unsigned_apk:

        if not isAPKEditor:
            FixSigBlock(decompile_dir, apk_path, build_dir, rebuild_dir);

        CRC_Fix(apk_path, build_dir, ["AndroidManifest.xml", ".dex"])

    else:
        Sign_APK(build_dir)

    if M.os.path.exists(build_dir):
        print(f'{C.S} Final APK {C.E} {C.G}︻デ═一 {C.Y}{build_dir} {C.G} ✔')

    print(f"\n{C.CC}{'_' * 61}\n")

    if not isCoreX and isPairip and isPairip_lib:
        print(f'\n{C.FYI}{C.C} This is Pairip Apk So U Install {C.G}( Keep Apk Without Sign ) {C.C}in VM / Multi_App\n')

    print(f'\n{C.S} Time Spent {C.E} {C.G}︻デ═一 {C.PN}{M.time.time() - start_time:.2f} {C.CC}Seconds {C.G} ✔\n')

    print(f'\n🚩 {C.CC}࿗ {C.OG}Professor X (FS) {C.CC}࿗ 🚩\n     🧠⚡ FS LAB ⚡🧠\n')

    if M.os.name == 'posix':
        M.subprocess.run(['termux-wake-unlock'], check=False) if M.shutil.which('termux-wake-unlock') else None
        exit(f"\n{C.X}{C.C} Releasing Wake Lock...\n")
    exit(0)