#!/usr/bin/env bash
# install.sh — install a pinned release of the harness CLI.
#
# Public-repo one-liner:
#   curl -fsSL https://raw.githubusercontent.com/librai/CommonHarness/main/install.sh | bash
#   HARNESS_VERSION=v0.2.0 curl -fsSL .../install.sh | bash
#
# Private-repo (after first clone):
#   ~/.agent-harness/<version>/install.sh
#   HARNESS_VERSION=v0.2.0 ~/.agent-harness/<version>/install.sh
#
# Layout produced:
#   ~/.agent-harness/v0.1.0/        ← pinned snapshot (one dir per version)
#   ~/.agent-harness/v0.2.0/
#   ~/.agent-harness/current  →  v0.2.0   ← which one is "active"
#   ~/.local/bin/harness  →  ~/.agent-harness/current/bin/harness
#
# Upgrade = re-run with new HARNESS_VERSION; old versions stay on disk for
# rollback. Switching is a single symlink flip. No git checkout drift —
# each version dir is a shallow tag clone with no other refs to switch to.

set -euo pipefail

REPO_URL="${HARNESS_REPO_URL:-git@github.com:librai/CommonHarness.git}"
INSTALL_DIR="${HARNESS_INSTALL_DIR:-$HOME/.agent-harness}"
VERSION="${HARNESS_VERSION:-v0.1.0}"
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
    # Tag-pinned install: shallow clone of a single ref. Can't easily switch
    # branches afterward — that's intentional, prevents version drift.
    git clone --quiet --depth 1 --branch "$VERSION" "$REPO_URL" "$DEST" \
      || err "couldn't fetch $VERSION — check the tag exists and you have access"
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
  harness init --preset python-uv

Upgrade later (example):

  HARNESS_VERSION=v0.2.0 $DEST/install.sh

  ↑ flips the 'current' symlink; v0.1.0 stays on disk for rollback.
EOF
