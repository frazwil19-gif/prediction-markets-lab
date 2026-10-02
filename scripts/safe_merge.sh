#!/usr/bin/env bash
# Fail-closed merge: a branch reaches master ONLY if the full test suite passes in a CLEAN virtualenv
# (requirements.txt + editable install) on the exact merge result. Any failure -> nothing is pushed.
# Usage: scripts/safe_merge.sh <branch> "<merge message>"
set -euo pipefail
BRANCH="$1"; MSG="$2"
REPO="$(git rev-parse --show-toplevel)"; cd "$REPO"
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "ABORT: working tree not clean"; exit 1; }
git fetch -q origin
PRE="$(git rev-parse origin/master)"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"; git worktree remove --force "$WORK/wt" 2>/dev/null || true' EXIT
git worktree add -q --detach "$WORK/wt" "$PRE"
cd "$WORK/wt"
git -c user.name=Claude -c user.email=noreply@anthropic.com merge -q --no-ff "origin/$BRANCH" -m "$MSG"
python3 -m venv "$WORK/venv"
"$WORK/venv/bin/pip" install -q -r requirements.txt
"$WORK/venv/bin/pip" install -q -e .
if ! "$WORK/venv/bin/python" -m pytest -q -p no:cacheprovider > "$WORK/pytest.log" 2>&1; then
  tail -30 "$WORK/pytest.log"; echo "ABORT: tests failed on the merge result -- nothing pushed"; exit 1
fi
tail -1 "$WORK/pytest.log"
MERGED="$(git rev-parse HEAD)"
git push -q origin "HEAD:master"     # rejected (non-fast-forward) if master moved meanwhile -> re-run
echo "pre-merge master $PRE -> merged $MERGED"
