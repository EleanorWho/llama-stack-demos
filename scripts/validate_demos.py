#!/usr/bin/env python3
"""Validate demo files meet structural requirements.

Uses only the ast module — no third-party dependencies, no OGX server needed.
Runs both in pre-commit (on changed files) and in CI (on all demo files).

Usage:
    # Validate specific files (pre-commit passes changed files)
    python scripts/validate_demos.py demos/01_foundations/01_client_setup.py

    # Validate all demo files
    python scripts/validate_demos.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "demos"

DEMO_FILE_PATTERN = re.compile(r"^\d{2}_[a-z][a-z0-9_]*\.py$")

REQUIRED_DOCSTRING_FIELDS = ["Demo:", "Description:", "Learning Objectives:"]

SKIP_FILES = {"_template.py"}


def find_demo_files() -> list[Path]:
    """Find all demo Python files matching NN_name.py in phase directories."""
    files = []
    for phase_dir in sorted(DEMO_DIR.iterdir()):
        if not phase_dir.is_dir():
            continue
        if not re.match(r"\d{2}_", phase_dir.name):
            continue
        for py_file in sorted(phase_dir.glob("*.py")):
            if py_file.name.startswith("__"):
                continue
            if py_file.name in SKIP_FILES:
                continue
            files.append(py_file)
    return files


def validate_file(path: Path) -> tuple[list[str], list[str]]:
    """Validate a single demo file. Returns (errors, warnings)."""
    errors = []
    warnings = []
    relative = path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path

    try:
        source = path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"{relative}: cannot read file: {e}"], []

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        return [f"{relative}: syntax error: {e}"], []

    # 1. File naming
    if not DEMO_FILE_PATTERN.match(path.name):
        errors.append(
            f"{relative}: file name '{path.name}' does not match pattern NN_snake_case_name.py"
        )

    # 2. Module docstring with required fields
    docstring = ast.get_docstring(tree)
    if docstring is None:
        errors.append(f"{relative}: missing module docstring")
    else:
        for field in REQUIRED_DOCSTRING_FIELDS:
            if field not in docstring:
                errors.append(f"{relative}: docstring missing required field '{field}'")

    # 3. if __name__ == "__main__" block with fire.Fire(...)
    has_main_guard = False
    fire_target = None
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.If):
            continue
        if _is_name_main_check(node.test):
            has_main_guard = True
            for stmt in ast.walk(node):
                target = _get_fire_target(stmt)
                if target is not None:
                    fire_target = target
                    break
            break

    if not has_main_guard:
        errors.append(f"{relative}: missing 'if __name__ == \"__main__\"' guard")
    elif fire_target is None:
        errors.append(f"{relative}: 'if __name__' block does not call fire.Fire(...)")

    # 4. main() function with host and port parameters
    #    Only required when fire.Fire is called with main (not a dict dispatch).
    if fire_target == "main":
        main_func = None
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "main":
                main_func = node
                break

        if main_func is None:
            errors.append(f"{relative}: missing top-level main() function")
        else:
            param_names = [arg.arg for arg in main_func.args.args]
            if "host" not in param_names:
                errors.append(f"{relative}: main() missing 'host' parameter")
            if "port" not in param_names:
                errors.append(f"{relative}: main() missing 'port' parameter")

    # 5. Warn on sys.path manipulation (non-blocking)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Attribute)
            and node.func.attr in ("insert", "append")
            and _is_sys_path(node.func.value)
        ):
                warnings.append(
                    f"{relative}:{node.lineno}: uses sys.path manipulation — "
                    "use package imports instead (from demos.shared.utils import ...)"
                )

    return errors, warnings


def _is_name_main_check(node: ast.expr) -> bool:
    """Check if an AST node is `__name__ == '__main__'`."""
    if not isinstance(node, ast.Compare):
        return False
    if len(node.ops) != 1 or not isinstance(node.ops[0], ast.Eq):
        return False
    left = node.left
    comparators = node.comparators
    if len(comparators) != 1:
        return False
    right = comparators[0]

    def is_name(n: ast.expr) -> bool:
        return isinstance(n, ast.Name) and n.id == "__name__"

    def is_main_str(n: ast.expr) -> bool:
        return isinstance(n, ast.Constant) and n.value == "__main__"

    return (is_name(left) and is_main_str(right)) or (is_main_str(left) and is_name(right))


def _get_fire_target(node: ast.AST) -> str | None:
    """Return the target of fire.Fire(...), or None if not a fire.Fire call.

    Returns "main" for fire.Fire(main), "dict" for fire.Fire({...}), or
    "other" for any other fire.Fire(...) call.
    """
    if not isinstance(node, ast.Expr):
        return None
    call = node.value
    if not isinstance(call, ast.Call):
        return None
    func = call.func
    if not (isinstance(func, ast.Attribute) and func.attr == "Fire"):
        return None
    if not (isinstance(func.value, ast.Name) and func.value.id == "fire"):
        return None
    if call.args and isinstance(call.args[0], ast.Name) and call.args[0].id == "main":
        return "main"
    if call.args and isinstance(call.args[0], ast.Dict):
        return "dict"
    return "other"


def _is_sys_path(node: ast.expr) -> bool:
    """Check if an AST node is `sys.path`."""
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
        and node.attr == "path"
    )


def main() -> int:
    if len(sys.argv) > 1:
        files = [Path(f) for f in sys.argv[1:]]
    else:
        files = find_demo_files()

    if not files:
        print("No demo files to validate.")
        return 0

    all_errors = []
    all_warnings = []
    for f in files:
        file_errors, file_warnings = validate_file(f)
        all_errors.extend(file_errors)
        all_warnings.extend(file_warnings)

    if all_warnings:
        print(f"Warnings ({len(all_warnings)}):\n")
        for warning in all_warnings:
            print(f"  {warning}")
        print()

    if all_errors:
        print(f"Found {len(all_errors)} validation error(s):\n")
        for error in all_errors:
            print(f"  {error}")
        return 1

    print(f"Validated {len(files)} demo file(s) — all passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
