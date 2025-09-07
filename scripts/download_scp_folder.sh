#!/usr/bin/env bash
# download_scp_folder.sh
# Usage: ./download_scp_folder.sh [output_dir]
set -euo pipefail

REPO_URL="https://github.com/scp-data/scp-api.git"
BRANCH="main"
SUBDIR="docs/data/scp"
OUTDIR="${1:-.}"

# Work in a temp dir
CWD="$(pwd)"
TMP="$(mktemp -d)"
# Guard trap to only delete if TMP is actually a temp directory
trap 'if [[ "$TMP" =~ ^(/tmp/|/var/folders/) ]] && [[ -d "$TMP" ]]; then rm -rf "$TMP"; fi' EXIT

# Clone shallow & sparse
if git --version >/dev/null 2>&1; then
  git -c advice.detachedHead=false clone --filter=blob:none --no-checkout --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP/repo"
  cd "$TMP/repo"

  if git sparse-checkout -h >/dev/null 2>&1; then
    # Modern Git (>=2.25)
    git sparse-checkout init --cone
    git sparse-checkout set "$SUBDIR"
    git checkout
  else
    # Fallback for older Git
    git config core.sparseCheckout true
    echo "$SUBDIR/*" > .git/info/sparse-checkout
    git checkout -f
  fi
else
  echo "Error: git is required on PATH." >&2
  exit 1
fi

# Commit id & timestamp
commit_id="$(git rev-parse --short=12 HEAD)"
# Use epoch seconds to avoid cross-platform date quirks
commit_ts="$(git show -s --format=%ct HEAD)"

target_dir="scp-${commit_ts}-${commit_id}"
mkdir -p "${CWD}/${OUTDIR}"
mv "$SUBDIR" "${CWD}/${OUTDIR}/${target_dir}"

echo "Saved: ${OUTDIR%/}/${target_dir}"
