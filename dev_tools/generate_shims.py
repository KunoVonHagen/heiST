#!/usr/bin/env python3
"""Generate small executable shims in ./bin to run package modules with `python -m`.

Usage:
  python dev_tools/generate_shims.py

This searches the repository for Python files containing "if __name__ == '__main__'" and
creates `bin/<name>` which execs `python -m <dotted.module> "$@"` so scripts that
rely on package-relative imports keep working without `python -m` or installing the
package.
"""

from __future__ import annotations
import os
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN_DIR = ROOT / 'bin'

MAIN_RE = re.compile(r"if\s+__name__\s*==\s*['\"]__main__['\"]")


def find_module_name_for_path(path: Path, root: Path) -> str | None:
    # Build a dotted module name for a .py file inside the project rooted at `root`.
    # Stop walking up when we reach the repository root so the top-level repo folder
    # name isn't inserted into the module path. This avoids invalid module names
    # like 'heiST.ai_training.sanitizer'.
    path = path.resolve()
    if path.suffix != '.py':
        return None
    module_name = path.stem
    cur = path.parent
    pkg_parts: list[str] = []

    # Walk upward while the directory is a Python package (has __init__.py) and
    # we haven't reached the explicit repository root.
    while cur != root and (cur / '__init__.py').exists():
        pkg_parts.append(cur.name)
        parent = cur.parent
        if parent == cur:
            break
        cur = parent

    # If the immediate parent is the root and it still has __init__.py, do not
    # include the root directory name in the package path; stop there.
    if (cur == root) and (cur / '__init__.py').exists():
        # pkg_parts currently contains package segments from leaf up to, but not including, root
        pass

    if not pkg_parts:
        # No package structure above the module (or we stopped at repo root): return module name
        return module_name

    pkg_parts.reverse()
    return '.'.join(pkg_parts + [module_name])


def find_candidate_scripts(root: Path):
    for p in root.rglob('*.py'):
        # skip hidden, venvs, egg-info, dist, .git
        if any(part in ('venv', '.venv', 'env', '.git', '__pycache__') or part.endswith('.egg-info') for part in p.parts):
            continue
        if p.name == '__init__.py':
            continue
        try:
            text = p.read_text()
        except Exception:
            continue
        if MAIN_RE.search(text):
            yield p


def write_shim(target_module: str, shim_path: Path):
    shim_text = f"""#!/usr/bin/env bash
# Auto-generated shim - runs the module as a package so package-relative imports work
exec /usr/bin/env python3 -m {target_module} "$@"
"""
    shim_path.write_text(shim_text)
    # chmod later in batch


def main():
    scripts = list(find_candidate_scripts(ROOT))
    if not scripts:
        print('No candidate scripts with __main__ found.')
        return
    BIN_DIR.mkdir(exist_ok=True)
    created = []
    for p in scripts:
        mod = find_module_name_for_path(p, ROOT)
        if not mod:
            continue
        shim_name = p.stem
        shim_path = BIN_DIR / shim_name
        write_shim(mod, shim_path)
        created.append((p, mod, shim_path))

    for src, mod, shim in created:
        print(f"Created shim: {shim} -> python -m {mod}  (from {src})")

    if created:
        # make shims executable
        import stat
        for _src, _mod, shim in created:
            shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"Wrote {len(created)} shims into {BIN_DIR}")


if __name__ == '__main__':
    main()
