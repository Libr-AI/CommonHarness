#!/usr/bin/env python3
"""Detect a project's real [verify] / [paths] values from its manifest.

Usage: _detect_stack.py <target_root>

Prints `dotted.key=value` lines (one per confidently-detected setting). Values
for path arrays are emitted as TOML array literals (`["a", "b"]`). Keys that
can't be confidently detected are omitted, so the caller keeps the preset's
value. Used by `harness init` to correct a preset that doesn't match the stack.
"""

from __future__ import annotations

import json
import pathlib
import sys

# Candidate source / test directories, checked for existence at the repo root.
SRC_DIRS  = ["src", "app", "lib", "components", "pages", "server"]
TEST_DIRS = ["tests", "test", "__tests__", "spec"]


def _toml_array(items: list[str]) -> str:
    return "[" + ", ".join(f'"{i}"' for i in items) + "]"


def detect_paths(root: pathlib.Path) -> dict[str, str]:
    src  = [d for d in SRC_DIRS if (root / d).is_dir()]
    test = [d for d in TEST_DIRS if (root / d).is_dir()]
    out: dict[str, str] = {}
    if src or test:
        out["paths.forbidden_without_brief"] = _toml_array(src + test)
    if src:
        out["paths.cross_cutting"] = _toml_array(src)
    return out


def detect_node(root: pathlib.Path) -> dict[str, str]:
    try:
        pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    scripts = pkg.get("scripts", {}) or {}
    dev = {**(pkg.get("devDependencies", {}) or {}), **(pkg.get("dependencies", {}) or {})}

    if (root / "pnpm-lock.yaml").exists():
        pm = "pnpm"
    elif (root / "yarn.lock").exists():
        pm = "yarn"
    elif (root / "bun.lockb").exists():
        pm = "bun"
    else:
        pm = "npm"

    out: dict[str, str] = {}
    if "test" in scripts:
        out["verify.test"] = f"{pm} run test"
    if "format" in scripts:
        out["verify.format"] = f"{pm} run format"
    # A non-mutating format check for CI. Prefer an explicit script, else
    # prettier --check if prettier is present.
    if "format:check" in scripts:
        out["verify.format_check"] = f"{pm} run format:check"
    elif "prettier" in dev:
        out["verify.format_check"] = f"{pm} exec prettier --check ."
    return out


def detect_python(root: pathlib.Path) -> dict[str, str]:
    if not (root / "pyproject.toml").exists():
        return {}
    text = (root / "pyproject.toml").read_text(encoding="utf-8", errors="ignore")
    out: dict[str, str] = {}
    # uv-managed projects are the common modern case; ruff for format.
    if "ruff" in text:
        out["verify.format"] = "uv run ruff format ."
        out["verify.format_check"] = "uv run ruff format --check ."
    out["verify.test"] = "uv run pytest"
    return out


def main() -> int:
    if len(sys.argv) != 2:
        sys.stderr.write("usage: _detect_stack.py <target_root>\n")
        return 2
    root = pathlib.Path(sys.argv[1])

    detected: dict[str, str] = {}
    if (root / "package.json").exists():
        detected.update(detect_node(root))
    elif (root / "pyproject.toml").exists():
        detected.update(detect_python(root))
    detected.update(detect_paths(root))

    for key, value in detected.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
