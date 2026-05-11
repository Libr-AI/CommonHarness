# CommonHarness

A drop-in **governance protocol** for AI-assisted iteration. `harness init` lays a `harness` CLI plus the `.harness/` state machine into any repo so AI sessions (Claude Code, Codex, Cursor) follow a coordinator → implementer two-session split with checkpointed commits.

Language-agnostic. Three AI-platform integrations + GitHub. Designed so target repos can pull upstream updates without losing their own state.

---

## What it does

- **Two-session protocol** — coordinator session writes a task brief at `.harness/active/<id>.md`; implementer session executes one phase at a time, stops at every commit point and session boundary.
- **Three triage paths** — coordinator routes each request to **scaffold** (greenfield bootstrap), **light** (small change), or **full** (non-trivial change). Greenfield is auto-detected at `harness init` (no language manifest + no source dirs + no architecture doc) or forced via `--greenfield`.
- **TODO gate** — if `CONTRIBUTING.md` still has unfilled `🛠 TODO (project maintainers)` blocks, the coordinator first runs a `fill-contributing` prep task that scans manifest/CI/formatter configs, proposes candidate answers, and writes only after you confirm. No surprise auto-fills.
- **Spec gate** — for tasks that span cross-cutting dirs, introduce new external dependencies, change external interfaces, or affect the data model, the coordinator decides whether to produce a standalone design spec at `docs/specs/<task-id>.md` (in addition to the task brief). Phase 0 of the brief writes the spec; subsequent phases use it as the design authority.
- **State on disk** — `.harness/CURRENT.md` is the single source of truth; sessions can crash and resume with no information loss. `.harness/SCAFFOLD-PENDING` is the marker that drives the scaffold gate.
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

#### Step 1 — Download and install

In your terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/Libr-AI/CommonHarness/v0.2.0/install.sh | bash
```

When this finishes, the `harness` CLI is at `~/.local/bin/harness` (symlinked through `~/.commonharness/current/`).

#### Step 2 — Make sure `~/.local/bin` is on your `PATH`

Check whether it's already there:

```bash
echo $PATH | tr ':' '\n' | grep -F "$HOME/.local/bin"
```

- **If it prints a path** (e.g. `/Users/you/.local/bin`) → already set, skip to Step 3.
- **If it prints nothing** → add it to your shell rc and reload it:

  ```bash
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
  source ~/.zshrc
  ```

  > macOS default shell since Catalina is **zsh** (`~/.zshrc`). If you're on bash, use `~/.bashrc` instead. If `source` doesn't seem to take effect, open a fresh terminal window.

#### Step 3 — Verify

```bash
harness --version
```

Expected: `harness 0.2.0`. If you see `command not found: harness`, redo Step 2 (most likely the PATH change didn't propagate to your current shell — open a new terminal window).

### Pin to a different version

Note: env vars must come **before `bash`**, not before `curl` — otherwise the variable only reaches `curl` and is dropped before `install.sh` runs.

```bash
# Example: pin to an older release for rollback.
curl -fsSL https://raw.githubusercontent.com/Libr-AI/CommonHarness/v0.1.0/install.sh \
  | HARNESS_VERSION=v0.1.0 bash
```

### Roll on `main` (always latest, unstable)

```bash
curl -fsSL https://raw.githubusercontent.com/Libr-AI/CommonHarness/main/install.sh \
  | HARNESS_VERSION=main bash
```

### Manual install (if you don't want curl-pipe-bash)

```bash
git clone --depth 1 --branch v0.2.0 \
  https://github.com/Libr-AI/CommonHarness.git \
  ~/.commonharness/v0.2.0
~/.commonharness/v0.2.0/install.sh
```

To use SSH instead, set `HARNESS_REPO_URL` (note: env var goes before `bash`, not before `curl`):

```bash
curl -fsSL https://raw.githubusercontent.com/Libr-AI/CommonHarness/v0.2.0/install.sh \
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

That writes `AGENTS.md`, `CONTRIBUTING.md` (with TODO sections), `harness.config.toml`, the `.harness/` state directory, and the AI integrations. The CLI prints "Next steps" telling you what to do next.

**Greenfield projects.** If you're initializing into an empty repo (no language manifest, no source dirs, no architecture doc), `harness init` auto-detects this and offers to bootstrap with the **scaffold path**. You can also force the decision:

```bash
harness init --preset python-uv --greenfield        # force greenfield bootstrap
harness init --preset python-uv --no-greenfield     # force brownfield (skip detection)
harness init --preset python-uv --non-interactive   # auto-confirm detection
```

When greenfield is on, a marker file `.harness/SCAFFOLD-PENDING` is written; your first `harness start` will route to a 4-phase scaffold task (architecture decisions → directory skeleton → first runnable module → CONTRIBUTING fill + CI). The marker clears automatically when the scaffold task archives.

### 2. (Brownfield only) Don't touch `CONTRIBUTING.md` yet

The first `harness start` will offer to fill `CONTRIBUTING.md`'s `🛠 TODO (project maintainers)` blocks for you (scans your manifest/CI/formatter configs, proposes candidates, writes only after you confirm). You can still hand-edit if you prefer — but the coordinator's TODO gate will detect unfilled blocks and offer the prep task either way.

For greenfield projects: same — but the TODO fill happens as Phase 4 of the scaffold task, not a separate prep task.

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

The full protocol (triage paths, commit-point markers, anti-garbage rules) is rendered into your repo as `AGENTS.md` and `.harness/workflow.md`. Read those.

---

## Triage paths and gates

The coordinator routes each request through three sequential gates ([`.harness/triage.md`](templates/.harness/triage.md.tmpl) in target repos):

| Gate          | When                                                               | What happens                                                                                                              |
|---------------|--------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| **Step 0 — Scaffold gate** | `.harness/SCAFFOLD-PENDING` marker exists           | Force **scaffold path** (4 pre-named phases). Skip the three-question rubric. Marker is removed when the scaffold task archives. |
| **Steps 1–3 — Light/Full rubric** | Marker absent                                | Three checks (schema / cross-cutting / tests). All NO → **light** (single phase). Any YES → **full** (multi-phase, fresh session per phase). |
| **Step 4 — Spec gate** | After path decision                                     | Decide if the task needs a standalone design spec at `docs/specs/<task-id>.md`. Triggers: cross 2+ cross-cutting dirs, new external dep, external-interface change, data-model change, or explicit ask. Adds a Phase 0 to the brief. |

There's also a **TODO gate** in the coordinator opening (before the rubric): if `CONTRIBUTING.md` still has unfilled `🛠 TODO (project maintainers)` blocks and you're not in scaffold mode, the coordinator runs a `fill-contributing` prep task first — scans your manifest/CI/formatter configs, proposes candidates, writes only after you confirm.

---

## Presets

| Preset      | Format / test commands              | Default `forbidden_without_brief` | Default `spec_dir` |
|-------------|-------------------------------------|-----------------------------------|--------------------|
| `python-uv` | `uv run ruff format .` / `uv run pytest` | `["src", "tests"]`           | `docs/specs/`      |

Adding a new preset is one TOML file under [presets/](presets/) — copy [presets/python-uv.toml](presets/python-uv.toml) and edit. After running `init`, `harness.config.toml` is yours to tune; the preset only seeds the defaults.

Key config keys you'll want to know about:

- `paths.architecture_doc` — where the project's directory-layout doc lives (defaults to `docs/ARCHITECTURE.md`); coordinator/implementer always read this.
- `paths.spec_dir` — where standalone design specs land when the spec gate fires (defaults to `docs/specs/`).
- `paths.cross_cutting` — directories whose 2+-span triggers full path and spec gate.

---

## File ownership in target repos

CommonHarness sorts files in the target repo into three layers, and each behaves differently on re-runs / upgrades:

| Layer              | Files                                                                                       | Behavior on `harness init --force` / future `harness upgrade` |
|--------------------|---------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| **Managed**        | `AGENTS.md`, `.harness/{workflow,triage,README,templates/*}`, `.claude/*`, `.cursor/rules/harness.mdc`, `mcp/skills/harness/SKILL.md` | Overwritten cleanly from upstream templates                   |
| **Fenced fragment**| `CONTRIBUTING.md`, `CLAUDE.md`, `.github/PULL_REQUEST_TEMPLATE.md`                          | **Marker-aware merge**: only the `<!-- harness:begin --> … <!-- harness:end -->` block is replaced; everything outside (your business content) is preserved |
| **Owned**          | `.harness/CURRENT.md`, `.harness/MEMORY.md`, `.harness/active/*`, `.harness/archive/*`, `.harness/SCAFFOLD-PENDING`, `docs/specs/*` | Never touched. The scaffold marker is created by `--greenfield` init and removed by `harness end` of a `path: scaffold` brief. Spec files are created by the implementer in Phase 0. |

This is what makes the protocol upgradable without clobbering project-specific work.

---

## Upgrade story

### Step 1 — bump the CLI to a new version (per developer)

```bash
# Install a new version alongside the old one + flip 'current'.
# (Replace v0.3.0 with whichever release you're upgrading to.)
curl -fsSL https://raw.githubusercontent.com/Libr-AI/CommonHarness/v0.3.0/install.sh \
  | HARNESS_VERSION=v0.3.0 bash

harness --version    # confirms the new version is now active

# Roll back any time by flipping the symlink (older versions stay on disk):
ln -sfn ~/.commonharness/v0.2.0 ~/.commonharness/current
```

Old versions stay on disk; switching is a single symlink. Because each version dir is a shallow tag clone, you can't accidentally `git checkout` a different ref and produce inconsistent behavior across the team.

### Step 2 — apply the new version to a project

Find the preset your project was originally initialized with — it's recorded at the bottom of `harness.config.toml`:

```bash
grep '^preset' harness.config.toml
# e.g.  preset = "python-uv"  → use python-uv below
```

Then back up the config (it's the one file that gets overwritten in full — see the caveat below) and re-run init with `--force` and `--no-greenfield`:

```bash
cd /path/to/target/project
cp harness.config.toml harness.config.toml.bak           # safety backup
harness init --preset <same-preset> --force --no-greenfield
diff harness.config.toml.bak harness.config.toml         # spot any tuning to merge back
# (manually re-apply any [verify] / [paths] / [branch] tuning you'd customized)
rm harness.config.toml.bak                                # once you're satisfied
```

**Why `--no-greenfield`?** Without that flag, init's greenfield detection re-runs on every `--force` re-init. The heuristic CAN false-positive on existing projects whose source dir isn't named `src/` / `tests/` etc. — and an accidental `Y` at the prompt would write a stray scaffold marker into your already-mature project. `--no-greenfield` skips the prompt and the detection entirely; for any project being **upgraded** (not freshly bootstrapped), that's always the right answer.

**What `--force` touches:**

- **Managed files** (`AGENTS.md`, `.harness/{workflow,triage,README,templates/*}`, `.claude/*`, `.cursor/rules/*`, `mcp/skills/*`) → re-rendered from upstream templates (your edits to these files are overwritten — they're not meant to be edited locally).
- **Fenced fragments** (`CONTRIBUTING.md`, `CLAUDE.md`, `.github/PULL_REQUEST_TEMPLATE.md`) → marker-aware merged. Only the `<!-- harness:begin --> … <!-- harness:end -->` block is replaced; your business content outside the fence is preserved.
- **Owned files** (`.harness/CURRENT.md`, `.harness/MEMORY.md`, `.harness/active/*`, `.harness/archive/*`, `.harness/SCAFFOLD-PENDING`, `docs/specs/*`) → never touched. In-progress tasks, accumulated memory, and existing specs all survive.
- **`harness.config.toml`** → ⚠ **rewritten in full from the preset defaults**, including resetting `[verify]` / `[paths]` / `[branch]` to preset values. This is why Step 2 starts with `cp ... .bak` — diff your backup against the new file and re-apply any tuning. (A future `harness upgrade` command, planned, will do field-level merge to avoid this manual step.)

The renderer prints `+ wrote` / `~ merged` / `· skipped` for each file so the diff is auditable.

Whoever runs Step 2 then commits + pushes, and the rest of the team gets the new protocol on `git pull` of their project — they don't all need to run `init --force` themselves.

### Planned for future versions

- `harness upgrade [--to <ver>] [--dry-run]` — combines Steps 1 and 2; shows diff before writing.
- `harness doctor` — reports drift, broken hooks, version mismatch (`harness --version` ≠ project's `harness_version`), and unfilled `🛠 TODO (project maintainers)` markers (note: the v0.2.0 TODO gate already detects these at `harness start` time, but doctor surfaces them outside any coordinator session).

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
