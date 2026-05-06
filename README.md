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

## Conventions used in this README

Every code block below has a label telling you **where to run it**:

- **`bash`** blocks → run in your **terminal** (zsh / bash). Copy the whole block; comments (`# ...`) are fine to keep.
- **`text`** blocks → **paste into your AI tool** (Claude Code / Cursor chat / Codex CLI prompt) as a chat message.
- File-edit instructions are spelled out in prose ("open `harness.config.toml` in your editor and …") — no code block.

If a block has no explicit "Paste into your AI tool" callout, treat it as a terminal command.

---

## Install

CommonHarness is distributed as **release tags**. Every install pins to a specific version and lands in its own directory; a `current` symlink picks which version is active. Multiple versions can co-exist for safe upgrades and rollback.

### One-liner (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/Libr-AI/CommonHarness/v0.1.0/install.sh | bash
```

That's the whole install. After it finishes, `~/.local/bin/harness` is symlinked through `~/.commonharness/current/`. Make sure `~/.local/bin` is on your `PATH`:

```bash
echo $PATH | tr ':' '\n' | grep -F "$HOME/.local/bin" \
  || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
# (or ~/.bashrc; then open a new terminal)

harness --version    # expect: harness 0.1.0
```

### Pin to a different version

Note: env vars must come **before `bash`**, not before `curl` — otherwise the variable only reaches `curl` and is dropped before `install.sh` runs.

```bash
curl -fsSL https://raw.githubusercontent.com/Libr-AI/CommonHarness/v0.2.0/install.sh \
  | HARNESS_VERSION=v0.2.0 bash
```

### Roll on `main` (always latest, unstable)

```bash
curl -fsSL https://raw.githubusercontent.com/Libr-AI/CommonHarness/main/install.sh \
  | HARNESS_VERSION=main bash
```

### Manual install (if you don't want curl-pipe-bash)

```bash
git clone --depth 1 --branch v0.1.0 \
  https://github.com/Libr-AI/CommonHarness.git \
  ~/.commonharness/v0.1.0
~/.commonharness/v0.1.0/install.sh
```

To use SSH instead, set `HARNESS_REPO_URL` (note: env var goes before `bash`, not before `curl`):

```bash
curl -fsSL https://raw.githubusercontent.com/Libr-AI/CommonHarness/v0.1.0/install.sh \
  | HARNESS_REPO_URL=git@github.com:Libr-AI/CommonHarness.git bash
```

**Requires**: bash, git, python ≥ 3.9.

### Layout produced

```
~/.commonharness/
├── v0.1.0/                ← pinned snapshot (shallow tag clone, can't switch branches)
├── v0.2.0/                ← later, after upgrade — old versions kept for rollback
└── current  →  v0.2.0     ← which version is active
~/.local/bin/harness  →  ~/.commonharness/current/bin/harness
```

`harness --version` reads from the active install's `VERSION` file. Each project records the version it was init'd against in its `harness.config.toml` (`harness_version = "..."`), so team consistency is auditable.

---

## Quick start

### 1. Initialize harness in your project

In your **terminal**, from the project's repo root:

```bash
cd /path/to/your/project
harness init --preset python-uv
```

That writes `AGENTS.md`, `CONTRIBUTING.md` (with TODO sections to fill in), `harness.config.toml`, the `.harness/` state directory, and the AI integrations. The CLI prints "Next steps" telling you what to fill in.

### 2. Open `CONTRIBUTING.md` in your editor and fill the 4 TODO sections

Search the file for `TODO (project maintainers)` — there are 4 callouts marking:
- **Path B** (manual setup commands for your project)
- **Project-specific code style**
- **Project-specific pitfalls**

Edit them, save, then commit:

```bash
git add .
git commit -m "Adopt harness governance protocol"
git push
```

### 3. Start your first iteration

In your **terminal**:

```bash
harness start
```

This prints a long block of text — the **coordinator session opening prompt**. The next step happens in your AI tool.

**Paste the printed text into your AI tool** (Claude Code / Cursor / Codex chat) as your first chat message:

```text
You are the **coordinator** for an iteration on this repository. Follow the harness governance protocol strictly.
…
(everything `harness start` printed)
```

The AI then walks you through the protocol: asks what you want to change, runs triage, writes a task brief at `.harness/active/<task-id>.md`, and tells you how to start the implementer session.

### 4. Continue, resume, end — daily commands

In your **terminal**:

```bash
harness implement <task-id>    # resume / enter the implementer session (also prints a prompt to paste into AI tool)
harness status                 # show CURRENT.md + the active brief
harness end                    # archive a finished task → CURRENT.md back to idle
harness remember "<text>"      # append a convention/pitfall/decision to MEMORY.md
harness curate-memory          # quarterly MEMORY.md cleanup (opens it in $EDITOR)
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
curl -fsSL https://raw.githubusercontent.com/Libr-AI/CommonHarness/v0.2.0/install.sh \
  | HARNESS_VERSION=v0.2.0 bash

harness --version    # confirms 0.2.0 is now active

# Roll back any time by flipping the symlink (v0.1.0 stays on disk):
ln -sfn ~/.commonharness/v0.1.0 ~/.commonharness/current
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
