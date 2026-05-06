# CommonHarness

A drop-in **governance protocol** for AI-assisted iteration. `harness init` lays a `harness` CLI plus the `.harness/` state machine into any repo so AI sessions (Claude Code, Codex, Cursor) follow a coordinator → implementer two-session split with checkpointed commits.

Language-agnostic. Three AI-platform integrations + GitHub. Designed so target repos can pull upstream updates without losing their own state.

---

## What it does

- **Two-session protocol** — coordinator session writes a task brief at `.harness/active/<id>.md`; implementer session executes one phase at a time, stops at every commit point and session boundary.
- **State on disk** — `.harness/CURRENT.md` is the single source of truth; sessions can crash and resume with no information loss.
- **Cross-task memory** — `.harness/MEMORY.md` accumulates conventions, pitfalls, and decisions over time, surfaced to every new session.
- **Three AI-platform hooks** — Claude Code (slash command + `SessionStart` / `PreToolUse` hooks), Cursor (`alwaysApply` rule), Codex (MCP skill).
- **GitHub PR template** with a required protocol-status field.

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/librai/CommonHarness/main/install.sh | bash
```

This clones to `~/.agent-harness/main/` and symlinks `~/.local/bin/harness`. Make sure `~/.local/bin` is on your `PATH`.

Manual alternative:

```bash
git clone https://github.com/librai/CommonHarness ~/.agent-harness/main
ln -s ~/.agent-harness/main/bin/harness ~/.local/bin/harness
```

**Requires**: bash, git, python ≥ 3.9.

---

## Quick start

In any project repo:

```bash
harness init --preset python-uv
```

That writes `AGENTS.md`, `CONTRIBUTING.md` (with TODO sections to fill in), `harness.config.toml`, the `.harness/` state directory, and the AI integrations. The CLI prints "Next steps" telling you what to fill in and how to start your first iteration.

Begin a task:

```bash
harness start                  # prints the coordinator session prompt → paste into your AI tool
harness implement <task-id>    # resume / enter the implementer session
harness status                 # CURRENT.md + active brief
harness end                    # archive a finished task → idle
harness remember "<text>"      # append to MEMORY.md
harness curate-memory          # quarterly MEMORY.md cleanup
```

The full protocol (light vs full path triage, commit-point markers, anti-garbage rules) is rendered into your repo as `AGENTS.md` and `.harness/workflow.md`. Read those.

---

## Presets

| Preset      | Format / test commands              | Default `forbidden_without_brief` |
|-------------|-------------------------------------|-----------------------------------|
| `python-uv` | `uv run ruff format .` / `uv run pytest` | `["src", "tests"]`               |

Adding a new preset is one TOML file under [presets/](presets/) — copy [presets/python-uv.toml](presets/python-uv.toml) and edit. After running `init`, `harness.config.toml` is yours to tune; the preset only seeds the defaults.

---

## File ownership in target repos

CommonHarness sorts files in the target repo into three layers, and each behaves differently on re-runs / upgrades:

| Layer              | Files                                                                                       | Behavior on `harness init --force` / future `harness upgrade` |
|--------------------|---------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| **Managed**        | `AGENTS.md`, `.harness/{workflow,triage,README,templates/*}`, `.claude/*`, `.cursor/rules/harness.mdc`, `mcp/skills/harness/SKILL.md` | Overwritten cleanly from upstream templates                   |
| **Fenced fragment**| `CONTRIBUTING.md`, `CLAUDE.md`, `.github/PULL_REQUEST_TEMPLATE.md`                          | **Marker-aware merge**: only the `<!-- harness:begin --> … <!-- harness:end -->` block is replaced; everything outside (your business content) is preserved |
| **Owned**          | `.harness/CURRENT.md`, `.harness/MEMORY.md`, `.harness/active/*`, `.harness/archive/*`      | Never touched                                                 |

This is what makes the protocol upgradable without clobbering project-specific work.

---

## Upgrade story

Today (v0.1):

```bash
cd /path/to/target/project
git -C ~/.agent-harness/main pull        # bump the upstream
harness init --preset <same-preset> --force   # marker-aware merge runs automatically for fenced files
```

Coming in v0.2:

- `harness upgrade [--to <ver>] [--dry-run]` — pulls a pinned upstream version, shows diff before writing.
- `harness doctor` — reports drift, broken hooks, and unfilled `TODO (project maintainers)` markers.

---

## Repository layout

```
bin/
  harness            # bash CLI (init, start, implement, status, end, remember, curate-memory)
  _render.py         # template engine + marker-aware merge
  _toml.py           # zero-dep TOML loader (Python 3.9+ fallback)
  _cfg_get.py        # CLI: read one key from harness.config.toml
templates/           # .tmpl files; directory layout mirrors the target repo
presets/             # one .toml per preset
install.sh           # curl-pipe-bash bootstrap
.claude-plugin/      # Claude Code plugin manifest
tests/               # (placeholder for bats-core suite)
```

---

## License

[MIT](LICENSE).
