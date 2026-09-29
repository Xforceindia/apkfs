from ..ANSI_COLORS import ANSI; C = ANSI()
from ..MODULES import IMPORT; M = IMPORT()

from .Files_Check import FileCheck

F = FileCheck(); F.Set_Path();

EX = f"{C.P}\n   |\n   ╰{C.CC}┈{C.OG}➢ {C.G}apkfs {' '.join(M.sys.argv[1:])} {C.OG}"


# ---------------- Scan APK ----------------
def Scan_Apk(apk_path, isFlutter, isPairip):

    print(f"\n{C.CC}{'_' * 61}\n")

    Package_Name = ''

    # ---------------- Extract Package Name with AAPT ----------------
    if M.os.name == 'posix':
        try:
            _aapt = M.shutil.which('aapt') or M.shutil.which('aapt2')
            if not _aapt:
                for _c in (M.os.path.expanduser('~/.local/bin/aapt'),
                           M.os.path.expanduser('~/.local/bin/aapt2')):
                    if M.os.path.isfile(_c):
                        _aapt = _c
                        break
            if _aapt and M.os.path.basename(_aapt) == 'aapt':
                out = M.subprocess.run(
                    [_aapt, 'dump', 'badging', apk_path],
                    capture_output=True, text=True
                ).stdout or ''
                import re as _re
                _m = _re.search(r"package: name='([^']+)'", out)
                Package_Name = _m.group(1) if _m else ''
            elif _aapt:
                Package_Name = M.subprocess.run(
                    [_aapt, 'dump', 'packagename', apk_path],
                    capture_output=True, text=True
                ).stdout.strip()
            else:
                Package_Name = ''

            if Package_Name:
                print(f"\n{C.S} Package Name {C.E} {C.OG}➸❥ {C.P}'{C.G}{Package_Name}{C.P}' {C.G} ✔")

        except Exception:
            Package_Name = ''

    # ---------------- Extract Package Name with APKEditor ----------------
    if not Package_Name:
        try:
            out = M.subprocess.run(
                ["java", "-jar", F.APKEditor_Path, "info", "-package", "-i", apk_path],
                capture_output=True, text=True
            ).stdout or ""
            import re as _re
            _m = _re.search(r'package\s*=\s*"([^"]+)"', out) or _re.search(r'"([^"]+\.[^"]+)"', out)
            Package_Name = _m.group(1) if _m else (out.split('"')[1] if '"' in out else "")
        except Exception:
            Package_Name = ""
        if Package_Name:
            print(f"\n{C.S} Package Name {C.E} {C.OG}➸❥ {C.P}'{C.G}{Package_Name}{C.P}' {C.G} ✔")
        else:
            print(f"\n{C.WARN} Package Name unresolved — continuing with empty id\n")
            Package_Name = "unknown"

    
    # ---------------- Check Flutter / Pairip Protection ----------------
    isPairip_lib = isFlutter_lib = False

    with M.zipfile.ZipFile(apk_path, 'r') as zip_ref:
        for item in zip_ref.infolist():
            if item.filename.startswith('lib/'):
                if item.filename.endswith('libpairipcore.so'):
                    isPairip_lib = True
                if item.filename.endswith('libflutter.so'):
                    isFlutter_lib = True

    
    # ---------------- Check Flutter Protection ----------------
    if isFlutter_lib:
        has_r2 = bool(M.shutil.which("radare2") or M.shutil.which("r2"))
        if not has_r2:
            if M.shutil.which("pkg"):
                try:
                    print(f"\n{C.S} Installing {C.E} {C.OG}➸❥ {C.G}radare2...\n")
                    M.subprocess.check_call(["pkg", "install", "-y", "radare2"])
                    has_r2 = bool(M.shutil.which("radare2") or M.shutil.which("r2"))
                except Exception as e:
                    print(f"\n{C.WARN} radare2 install failed: {e}\n")
            if not has_r2:
                print(
                    f"\n{C.WARN} Flutter libflutter.so present but radare2 missing — "
                    f"skip Flutter SSL binary patch (smali SSL / NSC / Support still apply).\n"
                    f"{C.INFO} Install: Termux {C.G}pkg install radare2{C.CC} · Linux: place r2 in PATH\n"
                )
                isFlutter_lib = False
        if isFlutter_lib:
            FP = f"\n\n{C.S} Flutter Protection {C.E} {C.OG}➸❥ {C.P}'{C.G}libflutter.so{C.P}' {C.G} ✔"
            if not isFlutter:
                print(f"{FP}\n{C.WARN} Flutter APK — add {C.G}-f{C.CC} (auto -i enables when detected).\n")
            else:
                print(FP)

    # ---------------- Check Pairip Protection ----------------
    if isPairip_lib:
        PP = f"\n\n{C.S} Pairip Protection {C.E} {C.OG}➸❥ {C.P}'{C.G}libpairipcore.so{C.P}' {C.G} ✔"
        if not isPairip:
            print(f"{PP}\n{C.WARN} PairIP — add {C.G}-p{C.CC} or {C.G}-p -x{C.CC} (auto -i enables -p).\n")
        else:
            print(PP)

    return Package_Name, isFlutter_lib, isPairip_lib