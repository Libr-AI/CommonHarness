#!/usr/bin/env python3
"""Set a single dotted key (section.key) to a string value in a config file.

Usage: _cfg_set.py <config_path> <section.key> <value>

Line-based and comment-preserving: only the target line is replaced (or
inserted). Used by `harness mode` / `harness lang` / `harness arch` so the user
never hand-edits those keys. Values are written as quoted TOML strings.
"""

from __future__ import annotations

import pathlib
import sys


def _is_section_header(line: str) -> bool:
    s = line.strip()
    return s.startswith("[") and s.endswith("]")


def set_key(text: str, section: str, key: str, value: str) -> str:
    lines = text.splitlines()
    new_line = f'{key} = "{value}"'
    header = f"[{section}]"
    trailing_nl = "\n" if text.endswith("\n") or text == "" else ""

    # Locate the section header.
    sec_start = None
    for i, line in enumerate(lines):
        if line.strip() == header:
            sec_start = i
            break

    if sec_start is None:
        block = f"[{section}]\n{new_line}"
        if not lines:
            return block + "\n"
        body = "\n".join(lines).rstrip("\n")
        return f"{body}\n\n{block}\n"

    # Find the end of the section (next header or EOF).
    sec_end = len(lines)
    for j in range(sec_start + 1, len(lines)):
        if _is_section_header(lines[j]):
            sec_end = j
            break

    # Find the key within the section.
    for j in range(sec_start + 1, sec_end):
        stripped = lines[j].strip()
        if "=" in stripped and stripped.split("=", 1)[0].strip() == key:
            lines[j] = new_line
            return "\n".join(lines) + trailing_nl

    # Key not present: insert at the end of the section (after the last
    # non-blank line so we don't push a trailing blank further down).
    insert_at = sec_end
    while insert_at - 1 > sec_start and lines[insert_at - 1].strip() == "":
        insert_at -= 1
    lines.insert(insert_at, new_line)
    return "\n".join(lines) + trailing_nl


def main() -> int:
    if len(sys.argv) != 4:
        sys.stderr.write("usage: _cfg_set.py <config_path> <section.key> <value>\n")
        return 2
    path, dotted, value = sys.argv[1], sys.argv[2], sys.argv[3]
    if "." not in dotted:
        sys.stderr.write("_cfg_set.py: key must be of the form section.key\n")
        return 2
    section, key = dotted.split(".", 1)
    p = pathlib.Path(path)
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    p.write_text(set_key(text, section, key, value), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
