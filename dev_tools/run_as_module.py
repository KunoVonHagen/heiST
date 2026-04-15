#!/usr/bin/env python3
"""
Small helper to execute a Python script file as a module using import/run semantics.
Usage:
  python dev_tools/run_as_module.py path/to/module.py [args...]
  python dev_tools/run_as_module.py -m package.module [args...]

This computes the dotted module name for a file inside the project by
walking up until it finds a directory that is not a Python package (no __init__.py)
or the repository root. It then runs the module using runpy.run_module so
relative imports (package-style) work the same as running with `python -m`.

This is intended as a temporary compatibility shim while migrating scripts to
being executed as modules (python -m ...) or via console_scripts entry points.
"""

from __future__ import annotations
import sys
import os
import runpy
from typing import Optional


def find_module_name_for_path(path: str, stop_at: Optional[str] = None) -> Optional[str]:
    """Return a dotted module name for a .py file path inside a package tree.

    Example: /.../repo/ai_training/sanitizer.py -> 'ai_training.sanitizer'

    The algorithm walks up directories adding package parts while an
    __init__.py file exists in the directory. It stops when it reaches the
    filesystem root or the optional stop_at path.
    """
    path = os.path.abspath(path)
    if not path.endswith('.py'):
        return None

    pkg_parts = []
    cur = os.path.dirname(path)
    # include the module name (filename without .py)
    module_name = os.path.splitext(os.path.basename(path))[0]

    while True:
        if os.path.exists(os.path.join(cur, '__init__.py')):
            pkg_parts.append(os.path.basename(cur))
            parent = os.path.dirname(cur)
            if stop_at and os.path.abspath(cur) == os.path.abspath(stop_at):
                break
            if parent == cur:
                break
            cur = parent
            continue
        else:
            # If current dir has no __init__.py, treat the package root as the last appended
            # reverse parts since we appended from leaf to root
            break

    if not pkg_parts:
        # No package structure found; return module name, but note that running
        # as module may not preserve package-relative imports.
        return module_name

    pkg_parts = list(reversed(pkg_parts))
    dotted = '.'.join(pkg_parts + [module_name])
    return dotted


def run_module_by_path(path: str, argv: list[str]) -> int:
    """Run the module corresponding to path with argv as sys.argv.

    Returns the exit code (0 on success or any SystemExit code provided).
    """
    module_name = find_module_name_for_path(path)
    if module_name is None:
        print(f"Error: can't determine module name for {path}")
        return 2

    # set sys.argv for the module and run
    old_argv = sys.argv[:]
    sys.argv = [path] + argv
    try:
        runpy.run_module(module_name, run_name='__main__', alter_sys=True)
        return 0
    except SystemExit as se:
        return int(se.code) if se.code is not None else 0
    except Exception:
        raise
    finally:
        sys.argv = old_argv


def usage_and_exit() -> None:
    print(__doc__)
    sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        usage_and_exit()

    if argv[0] == '-m':
        if len(argv) < 2:
            usage_and_exit()
        module = argv[1]
        args = argv[2:]
        old_argv = sys.argv[:]
        sys.argv = [module] + args
        try:
            runpy.run_module(module, run_name='__main__', alter_sys=True)
            return 0
        except SystemExit as se:
            return int(se.code) if se.code is not None else 0
        finally:
            sys.argv = old_argv

    path = argv[0]
    args = argv[1:]
    return run_module_by_path(path, args)


if __name__ == '__main__':
    try:
        rc = main()
    except Exception as e:
        print(f"Fatal error while running module: {e}")
        raise
    sys.exit(rc)

