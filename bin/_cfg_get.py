#!/usr/bin/env python3
"""Read a single dotted key from a harness.config.toml file.

Usage: _cfg_get.py <config_path> <dotted.key>

Output format (one line):
  - string  → the string value
  - bool    → "true" or "false"
  - list    → space-separated string repr of each element
  - missing → empty line
"""

from __future__ import annotations

import pathlib
import sys

from _toml import loads


def main() -> int:
    if len(sys.argv) != 3:
        sys.stderr.write("usage: _cfg_get.py <config_path> <dotted.key>\n")
        return 2
    path, dotted = sys.argv[1], sys.argv[2]
    data = loads(pathlib.Path(path).read_text(encoding="utf-8"))
    node = data
    for part in dotted.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            print("")
            return 0
    if isinstance(node, bool):
        print("true" if node else "false")
    elif isinstance(node, list):
        print(" ".join(str(x) for x in node))
    else:
        print(node)
    return 0


if __name__ == "__main__":
    sys.exit(main())
