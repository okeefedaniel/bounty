#!/usr/bin/env bash
# Verify the keel pin in requirements.txt is reachable from a branch on the
# keel remote (i.e. NOT a pull-request-only commit). pip's `git clone` does
# not fetch refs/pull/*, so a PR-only SHA builds locally (cached) but breaks
# Railway. See bounty 09a26b1 → b33e81f for the incident.
#
# Usage: scripts/check-keel-pin.sh [path/to/requirements.txt]
# Exit 0 if reachable, 1 otherwise. Set SKIP_KEEL_PIN_CHECK=1 to bypass.

set -euo pipefail

REQ_FILE="${1:-requirements.txt}"

if [[ "${SKIP_KEEL_PIN_CHECK:-0}" = "1" ]]; then
  echo "check-keel-pin: skipped (SKIP_KEEL_PIN_CHECK=1)" >&2
  exit 0
fi

if [[ ! -f "$REQ_FILE" ]]; then
  echo "check-keel-pin: $REQ_FILE not found" >&2
  exit 0
fi

# Match: keel @ git+https://github.com/<owner>/keel.git@<ref>
line="$(grep -E '^keel @ git\+https://github\.com/[^/]+/keel\.git@' "$REQ_FILE" || true)"
if [[ -z "$line" ]]; then
  echo "check-keel-pin: no keel git pin in $REQ_FILE — nothing to verify" >&2
  exit 0
fi

remote_url="$(printf '%s\n' "$line" | sed -E 's|^keel @ (git\+)?(https://github\.com/[^/]+/keel\.git)@.*$|\2|')"
ref="$(printf '%s\n' "$line" | sed -E 's|^.*@([^[:space:]#]+).*$|\1|')"

if [[ -z "$remote_url" || -z "$ref" ]]; then
  echo "check-keel-pin: could not parse keel pin: $line" >&2
  exit 1
fi

echo "check-keel-pin: verifying $ref is reachable from a branch on $remote_url" >&2

# Fetch all branch heads + tags from the keel remote.
ls_remote="$(git ls-remote --heads --tags "$remote_url" 2>/dev/null || true)"
if [[ -z "$ls_remote" ]]; then
  echo "check-keel-pin: WARNING — git ls-remote returned no output (offline?). Skipping." >&2
  exit 0
fi

# If the ref looks like a full 40-char SHA, match exact-equality OR ancestry
# (a branch tip whose history contains the SHA). Tag/branch names match by
# the ref name on the right side of ls-remote output.
is_full_sha=0
if [[ "$ref" =~ ^[0-9a-f]{40}$ ]]; then is_full_sha=1; fi
is_short_sha=0
if [[ "$ref" =~ ^[0-9a-f]{7,39}$ ]]; then is_short_sha=1; fi

# Fast path: exact ref name (tag or branch) match.
if [[ "$is_full_sha" -eq 0 && "$is_short_sha" -eq 0 ]]; then
  if printf '%s\n' "$ls_remote" | awk '{print $2}' | grep -E "^refs/(heads|tags)/${ref}$" -q; then
    echo "check-keel-pin: OK — $ref matches a branch or tag on $remote_url" >&2
    exit 0
  fi
  echo "check-keel-pin: FAIL — $ref is not a branch or tag on $remote_url" >&2
  exit 1
fi

# SHA path: check exact match against any branch/tag head.
if [[ "$is_full_sha" -eq 1 ]]; then
  if printf '%s\n' "$ls_remote" | awk '{print $1}' | grep -Fxq "$ref"; then
    echo "check-keel-pin: OK — $ref is at the tip of a branch or tag on $remote_url" >&2
    exit 0
  fi
fi

# SHA may be an ancestor of a branch tip. Clone shallow-ish to verify.
# Reuse a cached bare clone if present to keep this fast on repeat runs.
cache_dir="${TMPDIR:-/tmp}/keel-pin-check"
mkdir -p "$cache_dir"
bare_dir="$cache_dir/keel.git"
if [[ ! -d "$bare_dir" ]]; then
  git clone --quiet --bare --filter=blob:none "$remote_url" "$bare_dir" >/dev/null 2>&1 || {
    echo "check-keel-pin: could not clone $remote_url to verify ancestry" >&2
    exit 1
  }
else
  git --git-dir="$bare_dir" fetch --quiet --prune origin '+refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*' >/dev/null 2>&1 || true
fi

# Resolve the (possibly short) SHA inside the bare repo. If it resolves AND
# is an ancestor of any branch tip, we're good. If it doesn't resolve at all,
# it's almost certainly a PR-only commit.
if ! full_sha="$(git --git-dir="$bare_dir" rev-parse --verify --quiet "${ref}^{commit}" 2>/dev/null)"; then
  echo "check-keel-pin: FAIL — $ref does not resolve to any commit reachable from a branch or tag on $remote_url" >&2
  echo "check-keel-pin:        (likely a refs/pull/* SHA — pip cannot fetch those)" >&2
  exit 1
fi

while read -r tip _; do
  if git --git-dir="$bare_dir" merge-base --is-ancestor "$full_sha" "$tip" 2>/dev/null; then
    echo "check-keel-pin: OK — $ref ($full_sha) is reachable from a branch/tag on $remote_url" >&2
    exit 0
  fi
done < <(git --git-dir="$bare_dir" for-each-ref --format='%(objectname) %(refname)' refs/heads refs/tags)

echo "check-keel-pin: FAIL — $ref ($full_sha) is not reachable from any branch or tag on $remote_url" >&2
echo "check-keel-pin:        (likely a refs/pull/* SHA — pip cannot fetch those)" >&2
exit 1
