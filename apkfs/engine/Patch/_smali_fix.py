"""Smali write helpers — keep bytecode valid after regex patches."""
from __future__ import annotations

import os
import re

_CONST4_BAD = re.compile(r"\bconst/4\s+([pv](\d+)),\s*(0x[0-9a-fA-F]+|-?\d+)\b")


def fix_const4_registers(text: str) -> str:
    def _repl(m: re.Match) -> str:
        reg, num, val = m.group(1), int(m.group(2)), m.group(3)
        if num > 15:
            return f"const/16 {reg}, {val}"
        return m.group(0)

    return _CONST4_BAD.sub(_repl, text)


def write_smali(path: str, content: str) -> None:
    open(path, "w", encoding="utf-8", errors="ignore").write(fix_const4_registers(content))


def scan_fix_smali_tree(root: str) -> int:
    fixed = 0
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if not fn.endswith(".smali"):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    old = f.read()
            except OSError:
                continue
            new = fix_const4_registers(old)
            if new != old:
                with open(fp, "w", encoding="utf-8", errors="ignore") as f:
                    f.write(new)
                fixed += 1
    return fixed
