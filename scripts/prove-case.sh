#!/usr/bin/env bash
# Prove a case: the regression test must fail on the seed commit and pass on the fix commit.
# Usage: scripts/prove-case.sh N
set -uo pipefail

n="${1:?usage: prove-case.sh N}"
root="$(git rev-parse --show-toplevel)"
cd "$root"

seed="$(git log --format=%h --grep="^chore(case-$n): seed" -n1)"
fix="$(git log --format=%h --grep="^fix(case-$n):" -n1)"
row="$(awk -F'\t' -v n="$n" '$1 == n' cases/regression-tests.tsv)"
[ -n "$seed" ] && [ -n "$fix" ] && [ -n "$row" ] || { echo "case $n: missing seed, fix or tsv row" >&2; exit 2; }
runner="$(echo "$row" | cut -f2)"
selector="$(echo "$row" | cut -f3)"

run() {  # run <dir>
  if [ "$runner" = api ]; then
    (cd "$1/api" && eval "\"$root/api/.venv/bin/python\" -m pytest -q -p no:cacheprovider $selector" 2>&1)
  else
    (cd "$1/web" && eval "npx vitest run $selector" 2>&1)
  fi
}

work="$(mktemp -d)"
trap 'git worktree remove --force "$work/seed" >/dev/null 2>&1; rm -rf "$work"' EXIT
git worktree add --detach -q "$work/seed" "$seed"
ln -s "$root/web/node_modules" "$work/seed/web/node_modules"

# The regression test lands with the fix, so lay the fix commit's test files over the seed tree.
files="$(git diff --name-only "$seed" "$fix" | grep -E '^(api/tests/|web/src/.*test|web/e2e/)')"
[ -n "$files" ] && git -C "$work/seed" checkout "$fix" -- $files

echo "=== case $n: seed $seed (regression test on the buggy code) ==="
seed_out="$(run "$work/seed")"; seed_status=$?
echo "$seed_out" | tail -n 25
echo
echo "=== case $n: fix $fix (same test on the fixed code) ==="
fix_out="$(run "$root")"; fix_status=$?
echo "$fix_out" | tail -n 8
echo
if [ "$seed_status" -ne 0 ] && [ "$fix_status" -eq 0 ]; then
  echo "RESULT case $n: fails on seed $seed, passes on fix $fix"
else
  echo "RESULT case $n: UNEXPECTED (seed exit $seed_status, fix exit $fix_status)"; exit 1
fi
