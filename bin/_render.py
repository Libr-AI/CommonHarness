#!/usr/bin/env python3
# bin/_render.py — invoked by `harness init`.
#
# Reads env vars HARNESS_HOME, TARGET_ROOT, HARNESS_VERSION, PRESET, PRESET_FILE,
# TODAY, FORCE; renders every template under $HARNESS_HOME/templates/ to its
# corresponding location under $TARGET_ROOT, substituting {{var}} from the
# preset config and supporting {{#cond}}…{{/cond}} / {{^cond}}…{{/cond}} blocks.

from __future__ import annotations

import os
import pathlib
import re
import sys

from _toml import loads as _load_toml


# --- config ------------------------------------------------------------------

HARNESS_HOME    = pathlib.Path(os.environ["HARNESS_HOME"])
TARGET_ROOT     = pathlib.Path(os.environ["TARGET_ROOT"])
HARNESS_VERSION = os.environ["HARNESS_VERSION"]
PRESET          = os.environ.get("PRESET", "none")
PRESET_FILE     = os.environ.get("PRESET_FILE", "")
TODAY           = os.environ.get("TODAY", "")
FORCE           = os.environ.get("FORCE", "false") == "true"

TEMPLATES_DIR = HARNESS_HOME / "templates"


# Template → output mapping. (template_rel, output_rel, integration_flag, executable)
# integration_flag = None means always render. Otherwise render only if the
# corresponding [integrations].<flag> is true in the preset.
ROUTES: list[tuple[str, str, str | None, bool]] = [
    # core (always)
    ("AGENTS.md.tmpl",                                              "AGENTS.md",                                  None,           False),
    ("CONTRIBUTING.md.section.tmpl",                                "CONTRIBUTING.md",                            None,           False),
    ("harness.config.toml.tmpl",                                    "harness.config.toml",                        None,           False),
    (".harness/README.md.tmpl",                                     ".harness/README.md",                         None,           False),
    (".harness/workflow.md.tmpl",                                   ".harness/workflow.md",                       None,           False),
    (".harness/triage.md.tmpl",                                     ".harness/triage.md",                         None,           False),
    (".harness/CURRENT.md.tmpl",                                    ".harness/CURRENT.md",                        None,           False),
    (".harness/MEMORY.md.tmpl",                                     ".harness/MEMORY.md",                         None,           False),
    (".harness/templates/start-coordinator.md.tmpl",                ".harness/templates/start-coordinator.md",    None,           False),
    (".harness/templates/start-implementer.md.tmpl",                ".harness/templates/start-implementer.md",    None,           False),
    (".harness/templates/task-brief.md.tmpl",                       ".harness/templates/task-brief.md",           None,           False),

    # Claude Code
    ("claude/CLAUDE.md.section.tmpl",                               "CLAUDE.md",                                  "claude_code",  False),
    ("claude/commands_harness.md.tmpl",                             ".claude/commands/harness.md",                "claude_code",  False),
    ("claude/hooks_check-harness-state.sh.tmpl",                    ".claude/hooks/check-harness-state.sh",       "claude_code",  True),
    ("claude/settings.json.section.tmpl",                           ".claude/settings.json",                      "claude_code",  False),

    # Cursor
    ("cursor/rules_harness.mdc.tmpl",                               ".cursor/rules/harness.mdc",                  "cursor",       False),

    # Codex / MCP
    ("codex/skills_harness_SKILL.md.tmpl",                          "mcp/skills/harness/SKILL.md",                "codex_mcp",    False),

    # GitHub
    ("github/PULL_REQUEST_TEMPLATE.md.tmpl",                        ".github/PULL_REQUEST_TEMPLATE.md",           "github_pr",    False),
]

# Files that should never be overwritten on `harness init` once they exist:
# they hold per-project state, even if init is re-run with --force.
OWNED_PATHS = {
    ".harness/CURRENT.md",
    ".harness/MEMORY.md",
}


# --- preset / vars -----------------------------------------------------------

def load_preset() -> dict:
    if not PRESET_FILE:
        return {}
    return _load_toml(pathlib.Path(PRESET_FILE).read_text(encoding="utf-8"))


def md_inline_dirs(dirs: list[str]) -> str:
    """`a/`, `b/`, `c/`"""
    return ", ".join(f"`{d.rstrip('/')}/`" for d in dirs)


def md_inline_dirs_or(dirs: list[str]) -> str:
    """`a/`, `b/`, or `c/`"""
    if not dirs:
        return ""
    if len(dirs) == 1:
        return f"`{dirs[0].rstrip('/')}/`"
    head = ", ".join(f"`{d.rstrip('/')}/`" for d in dirs[:-1])
    return f"{head}, or `{dirs[-1].rstrip('/')}/`"


def toml_array(values: list[str]) -> str:
    """[\"a\", \"b\"]"""
    return "[" + ", ".join(f'"{v}"' for v in values) + "]"


def build_vars(preset: dict) -> dict[str, str]:
    verify = preset.get("verify", {})
    paths  = preset.get("paths", {})
    branch = preset.get("branch", {})
    integ  = preset.get("integrations", {})

    fmt        = verify.get("format", "")
    fmt_check  = verify.get("format_check", "")
    test_cmd   = verify.get("test", "")
    # Provide a sensible default for format_check if the preset only defined format.
    if fmt and not fmt_check:
        fmt_check = fmt + " --check" if " --check" not in fmt else fmt

    forbidden = paths.get("forbidden_without_brief", []) or []
    cross_cut = paths.get("cross_cutting", []) or []
    arch_doc  = paths.get("architecture_doc", "docs/ARCHITECTURE.md")

    feature_prefix = branch.get("feature_prefix", "feature/")
    main_branch    = branch.get("main_branch", "main")
    dev_branch     = branch.get("dev_branch", "")

    # Booleans rendered as TOML literals (config file) and truthy strings (templates).
    def bf(name, default=False):
        v = integ.get(name, default)
        return "true" if v else "false"

    return {
        "harness_version":             HARNESS_VERSION,
        "preset":                      PRESET,
        "today":                       TODAY,

        "verify_format":               fmt,
        "verify_format_check":         fmt_check,
        "verify_test":                 test_cmd,

        "paths_forbidden_inline":      md_inline_dirs(forbidden),
        "paths_forbidden_inline_or":   md_inline_dirs_or(forbidden),
        "paths_forbidden_toml_array":  toml_array(forbidden),

        "paths_cross_cutting_inline":  md_inline_dirs(cross_cut),
        "paths_cross_cutting_toml_array": toml_array(cross_cut),

        "paths_architecture_doc":      arch_doc,

        "branch_feature_prefix":       feature_prefix,
        "branch_main":                 main_branch,
        "branch_dev":                  dev_branch,
        # Conditional flag for {{#has_dev_branch}}…{{/has_dev_branch}}.
        "has_dev_branch":              "1" if dev_branch else "",

        "int_claude_code":             bf("claude_code"),
        "int_cursor":                  bf("cursor"),
        "int_codex_mcp":               bf("codex_mcp"),
        "int_github_pr":               bf("github_pr"),
    }


# --- rendering ---------------------------------------------------------------

SECTION_RE = re.compile(r"\{\{([#^])([a-zA-Z0-9_]+)\}\}(.*?)\{\{/\2\}\}", re.DOTALL)
VAR_RE     = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")


def render(template_text: str, variables: dict[str, str]) -> str:
    # Resolve sections (innermost first; iterate until stable).
    text = template_text
    while True:
        new_text, n = SECTION_RE.subn(
            lambda m: _section_repl(m, variables), text
        )
        if n == 0:
            break
        text = new_text

    return VAR_RE.sub(
        lambda m: variables.get(m.group(1), m.group(0)), text
    )


def _section_repl(match: re.Match, variables: dict[str, str]) -> str:
    marker, key, body = match.group(1), match.group(2), match.group(3)
    val = variables.get(key, "")
    truthy = bool(val) and val not in ("false", "False", "0")
    if marker == "#" and truthy:
        return body
    if marker == "^" and not truthy:
        return body
    return ""


# --- marker-aware merge ------------------------------------------------------
#
# Some templates (CONTRIBUTING.md, CLAUDE.md, PR template) are designed as
# *fragments*: the bit between `<!-- harness:begin -->` and `<!-- harness:end -->`
# is plugin-managed, everything outside is user territory. When the target
# already contains the same markers, we splice the new fenced block in and
# leave user territory untouched — even under `--force`.

MARKER_BEGIN = "<!-- harness:begin -->"
MARKER_END   = "<!-- harness:end -->"


def has_markers(text: str) -> bool:
    b = text.find(MARKER_BEGIN)
    e = text.find(MARKER_END)
    return b != -1 and e != -1 and e > b


def marker_merge(existing: str, rendered: str) -> str:
    """Splice the harness:begin/end block from `rendered` into `existing`.
    Caller must have verified both sides contain the markers in correct order."""
    r_start = rendered.index(MARKER_BEGIN)
    r_end = rendered.index(MARKER_END) + len(MARKER_END)
    new_block = rendered[r_start:r_end]
    e_start = existing.index(MARKER_BEGIN)
    e_end = existing.index(MARKER_END) + len(MARKER_END)
    return existing[:e_start] + new_block + existing[e_end:]


# --- main --------------------------------------------------------------------

def is_integration_enabled(preset: dict, flag: str) -> bool:
    return bool(preset.get("integrations", {}).get(flag, False))


def main() -> int:
    preset = load_preset()
    variables = build_vars(preset)

    written  = []   # files written from scratch
    merged   = []   # existing files where only the harness:* fence was replaced
    skipped  = []   # files left untouched, with reason

    for template_rel, output_rel, integration_flag, executable in ROUTES:
        if integration_flag is not None and not is_integration_enabled(preset, integration_flag):
            continue

        template_path = TEMPLATES_DIR / template_rel
        if not template_path.exists():
            sys.stderr.write(f"harness: missing template {template_path}\n")
            continue

        output_path = TARGET_ROOT / output_rel

        # Owned files: never overwrite once they exist.
        if output_rel in OWNED_PATHS and output_path.exists():
            skipped.append((output_rel, "owned (preserved)"))
            continue

        rendered = render(template_path.read_text(encoding="utf-8"), variables)
        template_has_fence = has_markers(rendered)

        if output_path.exists():
            existing = output_path.read_text(encoding="utf-8")

            # Fragment template + target with markers → marker-aware merge.
            # Safe regardless of FORCE: only the in-fence region is replaced.
            if template_has_fence and has_markers(existing):
                new_text = marker_merge(existing, rendered)
                if new_text == existing:
                    skipped.append((output_rel, "managed section already up to date"))
                    continue
                output_path.write_text(new_text, encoding="utf-8")
                merged.append(output_rel)
                continue

            # Fragment template + target without markers → don't auto-clobber
            # a pre-existing file the user wrote without expecting a fence.
            if template_has_fence and not has_markers(existing):
                skipped.append((
                    output_rel,
                    "exists without harness:begin/end markers — paste the fence manually or remove the file",
                ))
                continue

            # No fence in template: respect FORCE for everything except the
            # config (already gated in the bash side).
            if not FORCE and output_rel != "harness.config.toml":
                skipped.append((output_rel, "exists (use --force to overwrite)"))
                continue

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        if executable:
            mode = output_path.stat().st_mode
            output_path.chmod(mode | 0o111)
        written.append(output_rel)

    # Ensure state directories exist with .gitkeep.
    for sub in (".harness/active", ".harness/archive"):
        d = TARGET_ROOT / sub
        d.mkdir(parents=True, exist_ok=True)
        keep = d / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")

    # Report what was written / merged / skipped.
    if written:
        print(f"harness: wrote {len(written)} file{'s' if len(written) != 1 else ''}:")
        for p in written:
            print(f"  + {p}")
    if merged:
        print(f"harness: merged {len(merged)} file{'s' if len(merged) != 1 else ''} (replaced harness:begin/end fence, kept your edits outside):")
        for p in merged:
            print(f"  ~ {p}")
    if skipped:
        print(f"harness: skipped {len(skipped)} file{'s' if len(skipped) != 1 else ''}:")
        for p, why in skipped:
            print(f"  · {p}  ({why})")

    # Surface unfilled "TODO (project maintainers)" callouts in any file we
    # just touched. These mark sections the user MUST fill in.
    todos: list[tuple[str, int]] = []
    todo_pat = re.compile(r"TODO \(project maintainers\)")
    for rel in written + merged:
        path = TARGET_ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        count = len(todo_pat.findall(text))
        if count:
            todos.append((rel, count))
    if todos:
        print()
        print("harness: ⚠ project-maintainer TODO sections to fill in:")
        for rel, n in todos:
            print(f"  ! {rel}  ({n} block{'s' if n != 1 else ''})")
        print("    (search each file for 'TODO (project maintainers)'.)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
