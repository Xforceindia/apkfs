from ..ANSI_COLORS import ANSI; C = ANSI()
from ..MODULES import IMPORT; M = IMPORT()

from .Files_Check import FileCheck;

F = FileCheck(); F.Set_Path(); F.isEmulator()

def _resolve_aapt2():
    """
    Prefer a real host aapt2 (x86_64/arm Linux or Termux) over apktool's
    embedded binary — the embedded one is often the wrong arch in lab VMs.
    Override: export APKFS_AAPT2=/path/to/aapt2
    """
    import os
    from shutil import which
    cand = os.environ.get("APKFS_AAPT2") or which("aapt2")
    if cand and M.os.path.isfile(cand) and M.os.access(cand, M.os.X_OK):
        return cand
    # common Termux / user locations
    for p in (
        M.os.path.expanduser("~/.local/bin/aapt2"),
        "/data/data/com.termux/files/usr/bin/aapt2",
        "/usr/bin/aapt2",
        "/usr/local/bin/aapt2",
    ):
        if M.os.path.isfile(p) and M.os.access(p, M.os.X_OK):
            return p
    return None


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
    # Help dynamic aapt2 find libc++ when installed beside ~/.local/lib
    local_lib = M.os.path.expanduser("~/.local/lib")
    if M.os.path.isdir(local_lib):
        prev = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = local_lib + ((":" + prev) if prev else "")
    return M.subprocess.run(cmd, check=check, env=env)


from ..Patch._smali_fix import scan_fix_smali_tree

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
        if M.os.path.isdir(decompile_dir):
            M.shutil.rmtree(decompile_dir, ignore_errors=True)

        print(f"\n{C.ERROR} Decompile {Package_Name}.apk Failed with {AA}  ✘\n")

        if not isAPKEditor:
            print(SUGGEST)
            print(f"{C.INFO} apkfs will auto-retry with APKEditor (-a) when run via auto -i\n")
            exit(42)  # same fallback as recompile — APKEditor decompile path

        exit(1)


# ---------------- Recompile APK ----------------
def Recompile_Apk(decompile_dir, apk_path, build_dir, isEmulator, isAPKEditor, Package_Name):

    APKTool_Path = F.APKTool_Path_E if isEmulator else F.APKTool_Path

    AA = f"{'APKEditor' if isAPKEditor else 'APKTool'}"

    try:
        nfix = scan_fix_smali_tree(decompile_dir)
        if nfix:
            print(f"{C.INFO} smali const/4→const/16 fixed in {nfix} file(s)")
    except Exception as _e:
        print(f"{C.INFO} smali fix skipped: {_e}")

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

        if M.os.path.isdir(original_directory):
            for item in M.os.listdir(original_directory):
                if item != "META-INF":
                    item_path = M.os.path.join(original_directory, item)
                    if M.os.path.isdir(item_path):
                        M.shutil.rmtree(item_path)
                    else:
                        M.os.remove(item_path)

        cmd = ["java", "-jar", APKTool_Path, "b", decompile_dir, "-o", build_dir, "-p", decompile_dir, "-f", "--copy-original"]
        aapt2 = _resolve_aapt2()
        if aapt2:
            cmd.extend(["--aapt", aapt2])
            print(f"{C.Y}  · aapt2 : {aapt2}{C.CC}")
            print(f"{C.Y}  · note  : apktool+aapt2 may run quietly for a while on big APKs — wait{C.CC}")

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
            print(f"{C.INFO} apkfs will auto-retry with APKEditor (-a) when run via auto -i\n")
            exit(42)

        exit(1)

    if M.os.path.exists(build_dir):
        print(
            f"\n{C.S} APK Created {C.E} {C.OG}➸❥ {C.Y}{build_dir} {C.G} ✔\n"
            f"\n{C_Line}\n"
        )

    M.shutil.rmtree(decompile_dir)


# ---------------- FixSigBlock ----------------
def FixSigBlock(decompile_dir, apk_path, build_dir, rebuild_dir):
    """Preserve original APK signing block into rebuilt APK (unsigned/CRC path)."""

    if not M.os.path.isfile(build_dir):
        raise FileNotFoundError(f"FixSigBlock: missing build apk {build_dir}")

    M.os.rename(build_dir, rebuild_dir)

    # Work dir next to rebuild — decompile_dir may already be deleted after recompile
    base = M.os.path.basename(str(decompile_dir).rstrip("/").rstrip("\\"))
    parent = M.os.path.dirname(rebuild_dir) or "."
    sig_dir = M.os.path.join(parent, base + "_SigBlock")

    try:
        for operation in ["d", "b"]:
            cmd = [
                "java", "-jar", F.APKEditor_Path, operation, "-t", "sig",
                "-i", (apk_path if operation == "d" else rebuild_dir),
                "-f", "-sig", sig_dir,
            ]
            if operation == "b":
                cmd.extend(["-o", build_dir])
            M.subprocess.run(cmd, check=True, text=True, capture_output=True)
    finally:
        if M.os.path.isdir(sig_dir):
            M.shutil.rmtree(sig_dir, ignore_errors=True)
        if M.os.path.isfile(rebuild_dir) and M.os.path.isfile(build_dir):
            try:
                M.os.remove(rebuild_dir)
            except OSError:
                pass
        elif M.os.path.isfile(rebuild_dir) and not M.os.path.isfile(build_dir):
            try:
                M.os.rename(rebuild_dir, build_dir)
            except OSError:
                pass


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
        print(f"\n{C.ERROR} Sign Failed !  ✘\n"); exit(1)