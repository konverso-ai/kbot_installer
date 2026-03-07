#!/usr/bin/env python3
"""
Git merge driver CLI for pyproject.toml.
Usage: run_merge.py <base> <current> <incoming>
Reads the 3 files, calls merge(), writes result to current.
Per git merge driver protocol: exit 0 = merge succeeded (file auto-staged);
non-zero = merge had conflicts (file left unmerged, user must resolve).
"""
import sys
from pathlib import Path

from pyproject_merge import merge

# Git conflict markers: if present in output, TOML is invalid and merge must not be auto-staged
CONFLICT_START = "<<<<<<<"


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
    # When merge() produced conflicts it appends <<<<<<</=======/>>>>>>> markers.
    # Return non-zero so git does not auto-stage the file (invalid TOML).
    if CONFLICT_START in result:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
