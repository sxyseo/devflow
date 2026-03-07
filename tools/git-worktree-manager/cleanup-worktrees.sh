#!/bin/bash

# cleanup-worktrees.sh - Cleanup old git worktrees
#
# Usage: ./cleanup-worktrees.sh [--dry-run] [--max-age-days=N]
#
# Examples:
#   ./cleanup-worktrees.sh --dry-run --max-age-days=7
#   ./cleanup-worktrees.sh --max-age-days=30

set -e

DRY_RUN=false
MAX_AGE_DAYS=7
WORKTREES_DIR="${WORKTREES_DIR:-/tmp/devflow-worktrees}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --max-age-days=*)
            MAX_AGE_DAYS="${1#*=}"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "Cleaning up git worktrees..."
echo "  Max age: $MAX_AGE_DAYS days"
echo "  Worktrees dir: $WORKTREES_DIR"
echo "  Dry run: $DRY_RUN"
echo ""

# List all worktrees
WORKTREES=$(git worktree list | grep -v "bare$" | awk '{print $1}')

CURRENT_TIME=$(date +%s)
MAX_AGE_SECONDS=$((MAX_AGE_DAYS * 24 * 60 * 60))
CLEANED_COUNT=0

for WORKTREE in $WORKTREES; do
    # Skip main repo
    if [ "$WORKTREE" = "$(git rev-parse --show-toplevel)" ]; then
        continue
    fi

    # Skip if not in worktrees directory
    if [[ "$WORKTREE" != "$WORKTREES_DIR"/* ]]; then
        continue
    fi

    # Check if directory exists
    if [ ! -d "$WORKTREE" ]; then
        echo "  Pruning: $WORKTREE (directory missing)"
        if [ "$DRY_RUN" = false ]; then
            git worktree prune
        fi
        ((CLEANED_COUNT++))
        continue
    fi

    # Check age
    LAST_MODIFIED=$(stat -f %m "$WORKTREE" 2>/dev/null || stat -c %Y "$WORKTREE" 2>/dev/null)
    AGE=$((CURRENT_TIME - LAST_MODIFIED))

    if [ $AGE -gt $MAX_AGE_SECONDS ]; then
        AGE_DAYS=$((AGE / 86400))
        echo "  Removing: $WORKTREE (age: ${AGE_DAYS} days)"

        if [ "$DRY_RUN" = false ]; then
            git worktree remove "$WORKTREE"
        fi

        ((CLEANED_COUNT++))
    fi
done

echo ""
echo "Cleaned up $CLEANED_COUNT worktree(s)"

if [ "$DRY_RUN" = true ]; then
    echo "(Dry run - no actual cleanup performed)"
fi
