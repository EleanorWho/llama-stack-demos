#!/usr/bin/env python3
"""Run all demos against an OGX server and report results.

Auto-scans demo files, reads # demo-requires: tags to determine which demos
to skip, and runs the rest with a timeout.

Usage:
    python tests/run_demos.py localhost 8321
    python tests/run_demos.py localhost 8321 --timeout 180
    python tests/run_demos.py localhost 8321 --capabilities vision_model,mcp_server
    python tests/run_demos.py localhost 8321 --phase 04_agents
    python tests/run_demos.py localhost 8321 --demo demos/03_rag/01_simple_rag.py
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from validate_demos import find_demo_files, parse_demo_requires

ERROR_PATTERNS = re.compile(
    r"Traceback|ModuleNotFoundError|No available models|No available chat-capable models"
    r"|No available embedding models|ImportError|SyntaxError"
)

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[0;33m"
NC = "\033[0m"


def check_requirements(requires: list[str], capabilities: set[str]) -> str | None:
    """Check if all requirements are met. Returns the first unmet requirement, or None."""
    for req in requires:
        if req[0].isupper():
            if not os.environ.get(req):
                return f"{req} not set"
        else:
            if req not in capabilities:
                return f"requires {req}"
    return None


def file_to_module(path: Path) -> str:
    """Convert a file path to a Python module path."""
    relative = path.relative_to(REPO_ROOT)
    return str(relative.with_suffix("")).replace(os.sep, ".")


def run_demo(module: str, host: str, port: int, timeout: int, preview_lines: int) -> str:
    """Run a single demo. Returns status: 'pass', 'fail', or 'timeout'."""
    label = module.removeprefix("demos.")
    print(f"  {label:<55} ", end="", flush=True)

    try:
        result = subprocess.run(
            [sys.executable, "-m", module, host, str(port)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        print(f"{YELLOW}TIMEOUT{NC}")
        return "timeout"

    output = result.stdout + result.stderr

    if result.returncode != 0:
        print(f"{RED}FAIL{NC} (exit {result.returncode})")
        status = "fail"
    elif ERROR_PATTERNS.search(output):
        print(f"{RED}FAIL{NC} (error in output)")
        status = "fail"
    else:
        print(f"{GREEN}PASS{NC}")
        status = "pass"

    if output.strip():
        for line in output.strip().splitlines()[-preview_lines:]:
            print(f"    | {line}")
        print()

    return status


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OGX demos and report results.")
    parser.add_argument("host", help="OGX server host")
    parser.add_argument("port", type=int, help="OGX server port")
    parser.add_argument("--timeout", type=int, default=120, help="Per-demo timeout in seconds (default: 120)")
    parser.add_argument("--capabilities", default="", help="Comma-separated capability tags to enable (e.g., vision_model,mcp_server)")
    parser.add_argument("--phase", help="Run only demos in this phase (e.g., 04_agents)")
    parser.add_argument("--demo", help="Run a single demo file (e.g., demos/03_rag/01_simple_rag.py)")
    parser.add_argument("--preview-lines", type=int, default=3, help="Number of output lines to show per demo (default: 3)")
    args = parser.parse_args()

    capabilities = {c.strip() for c in args.capabilities.split(",") if c.strip()}

    if args.demo:
        demo_path = Path(args.demo)
        if not demo_path.exists():
            print(f"Error: {args.demo} not found.")
            return 1
        files = [demo_path]
    else:
        files = find_demo_files()
        if args.phase:
            files = [f for f in files if f.parent.name == args.phase or f.parent.name.endswith(f"_{args.phase}")]

    if not files:
        print("No demo files found.")
        return 1

    counts = {"pass": 0, "fail": 0, "skip": 0, "timeout": 0}
    failures = []

    print(f"=== OGX Demos Test Suite ===")
    print(f"Server: {args.host}:{args.port}  Timeout: {args.timeout}s")
    if capabilities:
        print(f"Capabilities: {', '.join(sorted(capabilities))}")
    print()

    current_phase = None
    for f in files:
        phase = f.parent.name
        if phase != current_phase:
            current_phase = phase
            print(f"--- {phase} ---")

        requires = parse_demo_requires(f)
        unmet = check_requirements(requires, capabilities)
        if unmet:
            label = file_to_module(f).removeprefix("demos.")
            print(f"  {label:<55} {YELLOW}SKIP{NC}  ({unmet})")
            counts["skip"] += 1
            continue

        module = file_to_module(f)
        status = run_demo(module, args.host, args.port, args.timeout, args.preview_lines)
        counts[status] += 1
        if status == "fail":
            failures.append(module)

    total = sum(counts.values())
    print()
    print("=== Summary ===")
    print(
        f"  Total: {total}  "
        f"{GREEN}Pass: {counts['pass']}{NC}  "
        f"{RED}Fail: {counts['fail']}{NC}  "
        f"{YELLOW}Skip: {counts['skip']}  Timeout: {counts['timeout']}{NC}"
    )

    if failures:
        print()
        print("Failed demos:")
        for f in failures:
            print(f"  {f}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
