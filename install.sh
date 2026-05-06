#!/usr/bin/env bash
# install.sh — bootstrap the harness CLI on a developer machine.
#
# Usage (one-liner from upstream):
#   curl -fsSL https://raw.githubusercontent.com/<owner>/CommonHarness/main/install.sh | bash
#
# Effects:
#   - Clones the repo to ~/.agent-harness/<version>/
#   - Symlinks ~/.local/bin/harness -> .../bin/harness
#   - Prints next-step instructions

set -euo pipefail

REPO_URL="${HARNESS_REPO_URL:-https://github.com/librai/CommonHarness}"
INSTALL_DIR="${HARNESS_INSTALL_DIR:-$HOME/.agent-harness}"
VERSION="${HARNESS_VERSION:-main}"
BIN_DIR="${HARNESS_BIN_DIR:-$HOME/.local/bin}"

err() { echo "install: $*" >&2; exit 1; }

command -v git    >/dev/null || err "git is required"
command -v python3 >/dev/null || err "python3 is required"

mkdir -p "$INSTALL_DIR" "$BIN_DIR"
DEST="$INSTALL_DIR/$VERSION"

if [[ -d "$DEST/.git" ]]; then
  echo "install: updating existing checkout at $DEST"
  git -C "$DEST" fetch --tags --quiet
  git -C "$DEST" checkout --quiet "$VERSION"
  git -C "$DEST" pull --quiet --ff-only || true
else
  echo "install: cloning $REPO_URL @ $VERSION → $DEST"
  rm -rf "$DEST"
  git clone --quiet --depth 1 --branch "$VERSION" "$REPO_URL" "$DEST" \
    || git clone --quiet "$REPO_URL" "$DEST"
fi

chmod +x "$DEST/bin/harness" "$DEST/bin/_render.py"

LINK="$BIN_DIR/harness"
ln -sf "$DEST/bin/harness" "$LINK"

cat <<EOF
install: done.

  binary:   $LINK
  upstream: $DEST

If $BIN_DIR is not in your PATH, add this line to your shell rc file:

  export PATH="\$HOME/.local/bin:\$PATH"

Next: cd into your project, then run:

  harness init --preset python-uv
EOF
