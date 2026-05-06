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

## Install (version-pinned)

CommonHarness is distributed as **release tags**. Every install pins to a specific version and lands in its own directory; a `current` symlink picks which version is active. Multiple versions can co-exist for safe upgrades and rollback.

### One-liner (public repo / when you have HTTPS access)

```bash
curl -fsSL https://raw.githubusercontent.com/librai/CommonHarness/v0.1.0/install.sh | bash
# Pin to a specific version explicitly:
HARNESS_VERSION=v0.1.0 curl -fsSL https://raw.githubusercontent.com/librai/CommonHarness/v0.1.0/install.sh | bash
```

### Private-repo (team install — recommended for `librai/CommonHarness` today)

The `raw.githubusercontent.com` endpoint won't work for private repos, so do a one-time SSH-authenticated clone, then run the bundled `install.sh`:

```bash
# First time on this machine:
git clone --depth 1 --branch v0.1.0 \
  git@github.com:librai/CommonHarness.git \
  ~/.agent-harness/v0.1.0
~/.agent-harness/v0.1.0/install.sh

# Or all-in-one if you already have ~/.agent-harness/v0.1.0:
HARNESS_VERSION=v0.1.0 ~/.agent-harness/v0.1.0/install.sh
```

After install: `~/.local/bin/harness` is symlinked through `~/.agent-harness/current/`. Make sure `~/.local/bin` is on your `PATH`. Verify:

```bash
harness --version    # prints e.g. "harness 0.1.0"
```

**Requires**: bash, git, python ≥ 3.9.

### Layout produced

```
~/.agent-harness/
├── v0.1.0/                ← pinned snapshot (shallow tag clone, can't switch branches)
├── v0.2.0/                ← later, after upgrade — old versions kept for rollback
└── current  →  v0.2.0     ← which version is active
~/.local/bin/harness  →  ~/.agent-harness/current/bin/harness
```

`harness --version` reads from the active install's `VERSION` file. Each project records the version it was init'd against in its `harness.config.toml` (`harness_version = "..."`), so team consistency is auditable.

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

### Step 1 — bump the CLI to a new version (per developer)

```bash
# Install a new version alongside the old one + flip 'current':
git clone --depth 1 --branch v0.2.0 \
  git@github.com:librai/CommonHarness.git \
  ~/.agent-harness/v0.2.0
HARNESS_VERSION=v0.2.0 ~/.agent-harness/v0.2.0/install.sh

harness --version    # confirms 0.2.0 is now active

# Roll back any time by flipping the symlink:
ln -sfn ~/.agent-harness/v0.1.0 ~/.agent-harness/current
```

Old versions stay on disk; switching is a single symlink. Because each version dir is a shallow tag clone, you can't accidentally `git checkout` a different ref and produce inconsistent behavior across the team.

### Step 2 — apply the new version to a project

```bash
cd /path/to/target/project
harness init --preset <same-preset> --force
```

`--force` re-renders managed files. Fenced fragments (`CONTRIBUTING.md`, `CLAUDE.md`, PR template) get marker-aware merged — your business content outside the fence is preserved. Owned files (`CURRENT.md`, `MEMORY.md`, `active/`, `archive/`) are never touched. The renderer reports each file as `+ wrote`, `~ merged`, or `· skipped` so diffs are auditable.

Whoever runs Step 2 then commits + pushes, and the rest of the team gets the new protocol on `git pull` of their project — they don't all need to run `init --force` themselves.

### Coming in v0.2

- `harness upgrade [--to <ver>] [--dry-run]` — combines Steps 1 and 2; shows diff before writing.
- `harness doctor` — reports drift, broken hooks, version mismatch (`harness --version` ≠ project's `harness_version`), and unfilled `TODO (project maintainers)` markers.

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
