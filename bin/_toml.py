"""Tiny TOML loader.

Tries `tomllib` (Python 3.11+) → `tomli` → a minimal inline parser that
covers the subset used by harness preset/config files: strings, booleans,
arrays of strings, sections, comments. Centralised here so both `_render.py`
(during `harness init`) and `_cfg_get.py` (during workflow commands) read
config the same way and work on Python 3.9+ without extra dependencies.
"""

from __future__ import annotations

import re


def loads(text: str) -> dict:
    try:
        import tomllib  # Python 3.11+
        return tomllib.loads(text)
    except ModuleNotFoundError:
        pass
    try:
        import tomli  # type: ignore
        return tomli.loads(text)
    except ModuleNotFoundError:
        pass
    return _parse_minimal(text)


_STR_RE     = re.compile(r'^"((?:[^"\\]|\\.)*)"$')
_BOOL_RE    = re.compile(r"^(true|false)$")
_SECTION_RE = re.compile(r"^\[([A-Za-z0-9_.-]+)\]$")
_PAIR_RE    = re.compile(r"^([A-Za-z0-9_-]+)\s*=\s*(.+)$")


def _strip_comment(s: str) -> str:
    out = []
    in_str = False
    i = 0
    while i < len(s):
        c = s[i]
        if c == '"' and (i == 0 or s[i - 1] != "\\"):
            in_str = not in_str
        if c == "#" and not in_str:
            break
        out.append(c)
        i += 1
    return "".join(out).rstrip()


def _parse_value(raw: str):
    raw = raw.strip()
    m = _STR_RE.match(raw)
    if m:
        return m.group(1).encode("utf-8").decode("unicode_escape")
    m = _BOOL_RE.match(raw)
    if m:
        return raw == "true"
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        items, buf, in_str = [], [], False
        for ch in inner:
            if ch == '"':
                in_str = not in_str
            if ch == "," and not in_str:
                items.append("".join(buf).strip())
                buf = []
            else:
                buf.append(ch)
        if buf:
            items.append("".join(buf).strip())
        return [_parse_value(x) for x in items]
    raise ValueError(f"unsupported TOML value: {raw!r}")


def _parse_minimal(text: str) -> dict:
    root: dict = {}
    cur: dict = root
    for raw_line in text.splitlines():
        line = _strip_comment(raw_line).strip()
        if not line:
            continue
        m = _SECTION_RE.match(line)
        if m:
            cur = root
            for part in m.group(1).split("."):
                cur = cur.setdefault(part, {})
            continue
        m = _PAIR_RE.match(line)
        if not m:
            raise ValueError(f"can't parse line: {raw_line!r}")
        cur[m.group(1)] = _parse_value(m.group(2))
    return root
