from ..ANSI_COLORS import ANSI; C = ANSI()
from ..MODULES import IMPORT; M = IMPORT()

from apkfs.Utils.Files_Check import FileCheck

F = FileCheck(); F.Set_Path()


# ---------------- Pine Hook Patch ----------------
def Pine_Hook_Patch(decompile_dir, isAPKEditor, isModules, isDex):

    print(f"{C.X}{C.C} Pine HooK, {C.OG}🇮🇳 AbhiTheM0dder 🇮🇳 {C.PN}& {C.OG}残页 {C.P}(canyie)\n")

    Target_Path = M.os.path.join(decompile_dir,
        *(
            ['root', 'hook'] if isAPKEditor else ['unknown', 'hook']
        )
    )
    
    Dex_Path = M.os.path.join(decompile_dir,
        *(
            ['dex'] if isAPKEditor else []
        )
    )

    # ---------------- Hook dexloader ----------------
    Loader_Dex = M.os.path.join(Dex_Path, isDex)

    M.shutil.copy(F.loader, Loader_Dex)

    print(f'\n{C.S} Loader {C.E} {C.G}➸❥ {C.OG}{isDex} {C.G} ✔\n')


    # ---------------- Hook library ----------------
    if not M.os.path.exists(Target_Path):
        M.os.makedirs(Target_Path)

    print(f'\n{C.S} Target Path {C.E} {C.G}➸❥ hook\n')

    for Target_Files in [F.config, F.libpine32, F.libpine64]:

        M.shutil.copy(Target_Files, Target_Path)

        print(f'\n{C.S} HooK {C.E} {C.G}➸❥ {C.OG}{M.os.path.basename(Target_Files)} {C.G} ✔\n')


    # ---------------- isModules ----------------
    if isModules:

        Modules_Path = M.os.path.join(Target_Path, 'modules')

        if not M.os.path.exists(Modules_Path):
            M.os.makedirs(Modules_Path)

        print(f"\n{C.S} Modules Path {C.E} {C.G}➸❥ hook/modules\n")

        Module_List = isModules if isinstance(isModules, (list, tuple)) else [isModules]

        for Modules in Module_List:
            if M.os.path.exists(Modules):
                M.shutil.copy(Modules, Modules_Path)

                print(f'\n{C.S} Module {C.E} {C.G}➸❥ {C.OG}{M.os.path.basename(Modules)} {C.G} ✔\n')