from ..ANSI_COLORS import ANSI; C = ANSI()
from ..MODULES import IMPORT; M = IMPORT()

from .Files_Check import FileCheck;

F = FileCheck(); F.Set_Path(); F.isEmulator()

def _run_tool(cmd, check=True):
    """Run java/apktool with Termux-friendly env."""
    import os
    env = os.environ.copy()
    # Prefer user APKFS_JAVA_OPTS; else modest heap on small devices
    if "JAVA_TOOL_OPTIONS" not in env and "APKFS_JAVA_OPTS" in env:
        env["JAVA_TOOL_OPTIONS"] = env["APKFS_JAVA_OPTS"]
    elif "JAVA_TOOL_OPTIONS" not in env and (
        "com.termux" in env.get("PREFIX", "") or env.get("TERMUX_VERSION")
    ):
        env["JAVA_TOOL_OPTIONS"] = env.get("APKFS_JAVA_OPTS", "-Xmx512m")
    return M.subprocess.run(cmd, check=check, env=env)


C_Line = f"{C.CC}{'_' * 61}"

SUGGEST = (
    f"{C_Line}\n\n"
    f"\n{C.SUGGEST} Try With APKEditor, Flag {C.OG}-a"
    f"\n     |\n     └──── {C.CC}~ Ex. {C.G}$ {C.OG}apkfs {C.Y}{' '.join(M.sys.argv[1:])} {C.OG}-a\n"
)


# ---------------- Decompile APK ----------------
def Decompile_Apk(apk_path, decompile_dir, isEmulator, isAPKEditor, isAES, isAlgorithm, isPine_Hook, Package_Name):

    APKTool_Path = F.APKTool_Path_E if isEmulator else F.APKTool_Path

    AA = f"{'APKEditor' if isAPKEditor else 'APKTool'}"

    print(
        f"\n{C_Line}\n\n"
        f"\n{C.X}{C.C} Decompile APK with {AA}..."
    )

    if isAPKEditor:
        cmd = ["java", "-jar", F.APKEditor_Path, "d", "-i", apk_path, "-o", decompile_dir, "-f", "-no-dex-debug", "-dex-lib", "jf"]

        if isPine_Hook:
            cmd += ["-dex"]

        print(
            f"{C.G}  |\n  └──── {C.CC}Decompiling ~{C.G}$ java -jar {M.os.path.basename(F.APKEditor_Path)} d -i {apk_path} -o {M.os.path.basename(decompile_dir)} -f -no-dex-debug -dex-lib jf\n"
            f"\n{C_Line}{C.G}\n"
        )

    else:
        # Faster than stock ApkPatcher defaults, still full multi-dex (all patches work):
        #  --no-debug-info → less smali I/O
        #  APKFS_FAST=1    → also --only-main-classes (risk: misses code in secondary dex)
        cmd = [
            "java", "-jar", APKTool_Path, "d", apk_path,
            "-o", decompile_dir, "-p", decompile_dir, "-f",
            "--no-debug-info",
        ]
        if M.os.environ.get("APKFS_FAST", "").strip() in ("1", "true", "yes"):
            cmd.append("--only-main-classes")
            print(f"{C.Y}  · APKFS_FAST: only-main-classes (faster, may miss secondary dex){C.CC}")

        if isPine_Hook:
            cmd = ["java", "-jar", APKTool_Path, "d", apk_path, "-o", decompile_dir, "-p", decompile_dir, "-f", "-s"]

        print(
            f"{C.G}  |\n  └──── {C.CC}Decompiling ~{C.G}$ java -jar {M.os.path.basename(APKTool_Path)} d {apk_path} -o {M.os.path.basename(decompile_dir)} -f\n"
            f"\n{C_Line}{C.G}\n"
        )

    try:
        _run_tool(cmd, check=True)

        print(
            f"\n{C.X}{C.C} Decompile Successful {C.G} ✔\n"
            f"\n{C_Line}\n\n"
        )

    except M.subprocess.CalledProcessError:
        M.shutil.rmtree(decompile_dir)

        print(f"\n{C.ERROR} Decompile {Package_Name}.apk Failed with {AA}  ✘\n")

        if not isAPKEditor:
            print(SUGGEST)

        exit(1)


# ---------------- Recompile APK ----------------
def Recompile_Apk(decompile_dir, apk_path, build_dir, isEmulator, isAPKEditor, Package_Name):

    APKTool_Path = F.APKTool_Path_E if isEmulator else F.APKTool_Path

    AA = f"{'APKEditor' if isAPKEditor else 'APKTool'}"

    print(
        f"{C_Line}\n\n"
        f"\n{C.X}{C.C} Recompile APK with {AA}..."
    )

    if isAPKEditor:
        cmd = ["java", "-jar", F.APKEditor_Path, "b", "-i", decompile_dir, "-o", build_dir, "-f", "-dex-lib", "jf"]

        print(
            f"{C.G}  |\n  └──── {C.CC}Recompiling ~{C.G}$ java -jar {M.os.path.basename(F.APKEditor_Path)} b -i {M.os.path.basename(decompile_dir)} -o {M.os.path.basename(build_dir)} -f -dex-lib jf\n"
            f"\n{C_Line}{C.G}\n"
        )

    else:
        original_directory = M.os.path.join(decompile_dir, "original")

        for item in M.os.listdir(original_directory):
            if item != "META-INF":

                item_path = M.os.path.join(original_directory, item)

                if M.os.path.isdir(item_path):
                    M.shutil.rmtree(item_path)
                else:
                    M.os.remove(item_path)

        cmd = ["java", "-jar", APKTool_Path, "b", decompile_dir, "-o", build_dir, "-p", decompile_dir, "-f", "--copy-original"]

        print(
            f"{C.G}  |\n  └──── {C.CC}Recompiling ~{C.G}$ java -jar {M.os.path.basename(APKTool_Path)} b {M.os.path.basename(decompile_dir)} -o {M.os.path.basename(build_dir)} -f --copy-original\n"
            f"\n{C_Line}{C.G}\n"
        )

    try:
        _run_tool(cmd, check=True)

        print(
            f"\n{C.X}{C.C} Recompile Successful {C.G} ✔\n"
            f"\n{C_Line}\n"
        )

    except M.subprocess.CalledProcessError:
        #M.shutil.rmtree(decompile_dir)

        print(f"\n{C.ERROR} Recompile {Package_Name}.apk Failed with {AA}...  ✘\n")

        if not isAPKEditor:
            print(SUGGEST)

        exit(1)

    if M.os.path.exists(build_dir):
        print(
            f"\n{C.S} APK Created {C.E} {C.OG}➸❥ {C.Y}{build_dir} {C.G} ✔\n"
            f"\n{C_Line}\n"
        )

    M.shutil.rmtree(decompile_dir)


# ---------------- FixSigBlock ----------------
def FixSigBlock(decompile_dir, apk_path, build_dir, rebuild_dir):

    M.os.rename(build_dir, rebuild_dir)

    sig_dir = decompile_dir.replace('_decompiled', '_SigBlock')

    for operation in ["d", "b"]:
        cmd = ["java", "-jar", F.APKEditor_Path, operation, "-t", "sig", "-i", (apk_path if operation == "d" else rebuild_dir), "-f", "-sig", sig_dir]

        if operation == "b":
            cmd.extend(["-o", build_dir])

        M.subprocess.run(cmd, check=True, text=True, capture_output=True)

    M.shutil.rmtree(sig_dir)

    M.os.remove(rebuild_dir)


# ---------------- Sign APK ----------------
def Sign_APK(build_dir):

    cmd = ["java", "-jar", F.ApkSig, build_dir]

    print(f"\n{C.X}{C.C} Signing APK...")

    print(
        f"{C.G}  |\n  └──── {C.CC}Signing ~{C.G}$ java -jar {M.os.path.basename(F.ApkSig)} {build_dir}\n"
        f"\n{C_Line}{C.G}\n"
    )

    try:
        _run_tool(cmd, check=True)

        print(f"\n{C.X}{C.C} Sign Successful {C.G} ✔\n")

        print(f'{C_Line}\n\n')

    except M.subprocess.CalledProcessError:
        exit(f"\n{C.ERROR} Sign Failed !  ✘\n")