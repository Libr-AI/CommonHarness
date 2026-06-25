#!/usr/bin/env bash
# install.sh — install a pinned release of the harness CLI.
#
# One-liner (recommended):
#   curl -fsSL https://raw.githubusercontent.com/Libr-AI/CommonHarness/v0.6.0/install.sh | bash
#
# Pin to an older version (env var goes BEFORE bash, not before curl —
# otherwise it only reaches curl and is dropped before install.sh runs):
#   curl -fsSL https://raw.githubusercontent.com/Libr-AI/CommonHarness/v0.1.0/install.sh \
#     | HARNESS_VERSION=v0.1.0 bash
#
# Roll on main (latest unstable):
#   curl -fsSL https://raw.githubusercontent.com/Libr-AI/CommonHarness/main/install.sh \
#     | HARNESS_VERSION=main bash
#
# SSH instead of HTTPS:
#   curl -fsSL .../install.sh \
#     | HARNESS_REPO_URL=git@github.com:Libr-AI/CommonHarness.git bash
#
# Layout produced:
#   ~/.commonharness/v0.5.0/        ← pinned snapshot (one dir per version)
#   ~/.commonharness/v0.6.0/
#   ~/.commonharness/current  →  v0.6.0   ← which one is "active"
#   ~/.local/bin/harness  →  ~/.commonharness/current/bin/harness
#
# Upgrade = re-run with new HARNESS_VERSION; old versions stay on disk for
# rollback. Switching is a single symlink flip. No git checkout drift —
# each version dir is a shallow tag clone with no other refs to switch to.

set -euo pipefail

REPO_URL="${HARNESS_REPO_URL:-https://github.com/Libr-AI/CommonHarness.git}"
INSTALL_DIR="${HARNESS_INSTALL_DIR:-$HOME/.commonharness}"
VERSION="${HARNESS_VERSION:-v0.6.0}"
BIN_DIR="${HARNESS_BIN_DIR:-$HOME/.local/bin}"

err() { echo "install: $*" >&2; exit 1; }
log() { echo "install: $*"; }

command -v git     >/dev/null || err "git is required"
command -v python3 >/dev/null || err "python3 is required"

mkdir -p "$INSTALL_DIR" "$BIN_DIR"

DEST="$INSTALL_DIR/$VERSION"

if [[ -d "$DEST/.git" ]] || [[ -f "$DEST/VERSION" ]]; then
  log "$VERSION already installed at $DEST — skipping clone"
else
  log "fetching $VERSION from $REPO_URL → $DEST"
  rm -rf "$DEST"
  if [[ "$VERSION" == "main" ]]; then
    # Rolling install (development / latest unstable): full clone, can `git pull`.
    git clone --quiet "$REPO_URL" "$DEST"
  else
    # Tag-pinned install: init + shallow-fetch the tag + checkout. We avoid
    # `clone --depth 1 --branch <annotated-tag>`, which prints git's harmless but
    # alarming "is not a commit!" warning and a detached-HEAD advice block. The
    # result is the same single pinned commit (no branch to switch to —
    # intentional, prevents version drift).
    git init --quiet "$DEST"
    git -C "$DEST" fetch --quiet --depth 1 "$REPO_URL" tag "$VERSION" \
      || err "couldn't fetch $VERSION — check the tag exists and you have access"
    git -C "$DEST" -c advice.detachedHead=false checkout --quiet "$VERSION" \
      || err "couldn't check out $VERSION"
  fi
fi

chmod +x "$DEST/bin/harness" "$DEST/bin/_render.py" "$DEST/bin/_cfg_get.py" 2>/dev/null || true

# Flip the "current" pointer to this version.
CURRENT="$INSTALL_DIR/current"
ln -sfn "$DEST" "$CURRENT"

# System bin symlink → current → versioned dir.
LINK="$BIN_DIR/harness"
ln -sf "$CURRENT/bin/harness" "$LINK"

INSTALLED_VERSION="$(cat "$DEST/VERSION" 2>/dev/null | tr -d '[:space:]' || echo "$VERSION")"

cat <<EOF
install: done.

  active version: $INSTALLED_VERSION  (resolved from $VERSION)
  binary:         $LINK
  versioned dir:  $DEST
  current →:      $CURRENT → $DEST

If $BIN_DIR is not in your PATH, add this to your shell rc:

  export PATH="\$HOME/.local/bin:\$PATH"

Verify:

  harness --version

Use:

  cd /path/to/your/project
  harness init            # prompts for a preset; on the first 'harness start'
                          # the coordinator adapts [verify]/[paths] to your stack

Upgrade later (example — replace v0.6.0 with the next release):

  HARNESS_VERSION=v0.6.0 \$HOME/.commonharness/current/install.sh

  ↑ flips the 'current' symlink; older versions stay on disk for rollback.
EOF
