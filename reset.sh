#!/usr/bin/env bash
#
# reset.sh — restore this repo + local CommonTrace skill state to a clean
# pre-take baseline so demo takes are repeatable.
#
# Safe to run repeatedly (idempotent). It touches ONLY:
#
#   1. This repo's working tree, app/ and tests/ only:
#        - git checkout -- app tests   (revert the on-camera fix + Task 2 edits)
#        - git clean  -fd app tests    (remove any test files the agent added)
#      Nothing outside app/ and tests/ is touched — SCRIPT.md, PLAN.md, seed/,
#      and any recorded clips are left alone.
#
#   2. The local skill session state under ${COMMONTRACE_HOME:-~/.commontrace}:
#        - sessions/   (per-session working files: candidates, contributed flag)
#        - pending/    (pending contribution candidates)
#      These are ephemeral working state; the skill recreates them next session.
#
#   3. This demo project's rows in ${COMMONTRACE_HOME:-~/.commontrace}/local.db
#      (matched by this repo's absolute path). Deleting the project row cascades
#      to its sessions / trace_cache / trigger_feedback / error_signatures rows,
#      which re-arms the auto-contribute trigger and clears the resolved-fix
#      signature so recall injection re-fires cleanly.
#
#   It does NOT delete local.db, does NOT touch other projects' rows, and does
#   NOT touch ~/.commontrace/config.json or your API key.
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CT_HOME="${COMMONTRACE_HOME:-$HOME/.commontrace}"

echo "reset.sh — restoring demo baseline"
echo "  repo:          $REPO_DIR"
echo "  commontrace:   $CT_HOME"

# 1. Restore the buggy app + tests -------------------------------------------
cd "$REPO_DIR"
if git rev-parse --git-dir >/dev/null 2>&1; then
  git checkout -- app tests 2>/dev/null || true
  git clean -fd app tests   >/dev/null 2>&1 || true
  # Drop compiled caches so a stale .pyc can't mask the restore.
  find app tests -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
  echo "  [ok] app/ and tests/ restored to committed (buggy) state"
else
  echo "  [skip] not a git repo — cannot restore app/tests"
fi

# 2. Clear ephemeral per-session skill state ---------------------------------
if [ -d "$CT_HOME" ]; then
  rm -rf "$CT_HOME/sessions" 2>/dev/null || true
  rm -f  "$CT_HOME"/pending/*.jsonl 2>/dev/null || true
  echo "  [ok] cleared sessions/ and pending/ under $CT_HOME"
else
  echo "  [skip] $CT_HOME does not exist yet (nothing to clear)"
fi

# 3. Remove this project's rows from local.db (scoped, cascading) -------------
DB="$CT_HOME/local.db"
if [ -f "$DB" ]; then
  REPO_DIR="$REPO_DIR" DB="$DB" python3 - <<'PY'
import os, sqlite3, sys
db = os.environ["DB"]
repo = os.environ["REPO_DIR"]
try:
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys = ON")  # cascade project -> child rows
    cur = conn.execute("SELECT id FROM projects WHERE path = ?", (repo,))
    ids = [r[0] for r in cur.fetchall()]
    if ids:
        conn.executemany("DELETE FROM projects WHERE id = ?", [(i,) for i in ids])
        conn.commit()
        print(f"  [ok] removed {len(ids)} demo project row(s) from local.db (cascaded)")
    else:
        print("  [ok] no demo project rows in local.db (already clean)")
    conn.close()
except sqlite3.Error as e:
    print(f"  [warn] could not clean local.db ({e}); continuing")
PY
else
  echo "  [skip] $DB does not exist yet (nothing to clean)"
fi

echo "reset.sh — done. Ready for the next take."
