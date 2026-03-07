#!/usr/bin/env python3
"""
Git merge driver CLI for pyproject.toml.
Usage: run_merge.py <base> <current> <incoming>
Reads the 3 files, calls merge(), writes result to current.
"""
import sys
from pathlib import Path

from pyproject_merge import merge


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: run_merge.py <base> <current> <incoming>", file=sys.stderr)
        return 2
    base_path = Path(sys.argv[1])
    current_path = Path(sys.argv[2])
    incoming_path = Path(sys.argv[3])
    if not base_path.exists() or not current_path.exists() or not incoming_path.exists():
        print("All three file paths must exist.", file=sys.stderr)
        return 1
    base = base_path.read_text(encoding="utf-8")
    current = current_path.read_text(encoding="utf-8")
    incoming = incoming_path.read_text(encoding="utf-8")
    result = merge(base, current, incoming)
    current_path.write_text(result, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
