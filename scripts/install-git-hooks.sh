#!/usr/bin/env bash
# Point this clone at scripts/git-hooks/ for git hooks. Idempotent.
set -euo pipefail
repo_root="$(git rev-parse --show-toplevel)"
git -C "$repo_root" config core.hooksPath scripts/git-hooks
chmod +x "$repo_root"/scripts/git-hooks/* "$repo_root"/scripts/check-keel-pin.sh 2>/dev/null || true
echo "Git hooks installed: $(git -C "$repo_root" config core.hooksPath)"
