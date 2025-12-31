#!/usr/bin/env bash
#
# setup_repo.sh
#
# One-time (or occasional) repo setup script.
# - Configures Git to use ./git-hooks as hooksPath
# - Makes all scripts in key folders executable (.sh and .py)
#
# Usage:
#   ./setup_repo.sh
#

set -euo pipefail

# Check git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: This script must be run inside a Git repository."
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/git-hooks"

echo "Repository root: $REPO_ROOT"
echo

# 1) Configure hooksPath
if [ -d "$HOOKS_DIR" ]; then
  echo "Found git-hooks directory at: $HOOKS_DIR"
  echo "Setting git config core.hooksPath to 'git-hooks' (repo-relative)..."
  git config core.hooksPath git-hooks
else
  echo "Warning: git-hooks directory does not exist."
  echo "Create a 'git-hooks' folder in the repo root and add your hooks there."
fi

echo
echo "Current hooksPath is:"
git config core.hooksPath || echo "(hooksPath not set)"

# 2) Make scripts executable
echo
echo "Making scripts executable (.sh and .py) in selected directories..."

SCRIPT_DIRS=(
  "$HOOKS_DIR"
  "$REPO_ROOT/scripts"
)

for dir in "${SCRIPT_DIRS[@]}"; do
  if [ -d "$dir" ]; then
    echo "Scanning directory: $dir"
    find "$dir" -type f \( -name "*.sh" -o -name "*.py" \) -print -exec chmod +x {} \;
  else
    echo "Skipping missing directory: $dir"
  fi
done

echo
echo "Setup complete."
echo "HooksPath is configured and scripts have been made executable."
