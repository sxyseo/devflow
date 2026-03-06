#!/bin/bash

# cleanup-worktrees.sh - Remove old worktrees
#
# Usage: ./cleanup-worktrees.sh [--dry-run]

set -e

DRY_RUN=false

# Check for --dry-run flag
if [ "$1" == "--dry-run" ]; then
  DRY_RUN=true
  echo "DRY RUN MODE - No changes will be made"
  echo ""
fi

WORKTREE_BASE="/tmp/devflow-worktrees"

echo "═══════════════════════════════════════════════════════════════"
echo "           Git Worktree Cleanup - $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Prune git worktrees
echo "Pruning git worktrees..."
git worktree prune

echo ""

# Find worktrees older than 7 days
if [ -d "$WORKTREE_BASE" ]; then
  echo "Checking for worktrees older than 7 days in $WORKTREE_BASE..."
  echo ""

  # Count old worktrees
  OLD_WORKTREES=$(find "$WORKTREE_BASE" -maxdepth 1 -type d -mtime +7 2>/dev/null | wc -l)

  if [ "$OLD_WORKTREES" -eq 0 ]; then
    echo "No old worktrees found"
    exit 0
  fi

  echo "Found $OLD_WORKTREES old worktree(s):"
  echo ""

  # List old worktrees
  find "$WORKTREE_BASE" -maxdepth 1 -type d -mtime +7 -print0 | while IFS= read -r -d '' worktree; do
    if [ "$(basename "$worktree")" != "$(basename "$WORKTREE_BASE")" ]; then
      WORKTREE_NAME=$(basename "$worktree")
      WORKTREE_AGE=$(find "$worktree" -maxdepth 0 -mtime +7 -printf "%Td days")
      WORKTREE_SIZE=$(du -sh "$worktree" 2>/dev/null | cut -f1)

      echo "  - $WORKTREE_NAME"
      echo "    Age: $WORKTREE_AGE"
      echo "    Size: $WORKTREE_SIZE"
      echo ""
    fi
  done

  if [ "$DRY_RUN" = false ]; then
    echo "Removing old worktrees..."
    find "$WORKTREE_BASE" -maxdepth 1 -type d -mtime +7 -print0 | while IFS= read -r -d '' worktree; do
      if [ "$(basename "$worktree")" != "$(basename "$WORKTREE_BASE")" ]; then
        WORKTREE_NAME=$(basename "$worktree")
        echo "  Removing: $WORKTREE_NAME"

        # Remove from git first
        git worktree remove "$worktree" 2>/dev/null || true

        # Then remove directory if it still exists
        rm -rf "$worktree" 2>/dev/null || true
      fi
    done

    echo ""
    echo "✓ Cleanup complete"
  else
    echo "DRY RUN - No worktrees were removed"
    echo "Run without --dry-run to actually remove them"
  fi
else
  echo "No worktree directory found at $WORKTREE_BASE"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
