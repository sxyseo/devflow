#!/bin/bash

# create-worktree.sh - Create a git worktree for isolated development
#
# Usage: ./create-worktree.sh <branch-name> [base-branch] [worktree-name]
#
# Examples:
#   ./create-worktree.sh feature/new-feature main feature-new-feature
#   ./create-worktree.sh story-123 main

set -e

BRANCH_NAME=$1
BASE_BRANCH=${2:-main}
WORKTREE_NAME=${3:-$BRANCH_NAME}
WORKTREES_DIR="${WORKTREES_DIR:-/tmp/devflow-worktrees}"

if [ -z "$BRANCH_NAME" ]; then
    echo "Usage: $0 <branch-name> [base-branch] [worktree-name]"
    exit 1
fi

WORKTREE_PATH="$WORKTREES_DIR/$WORKTREE_NAME"

echo "Creating git worktree..."
echo "  Branch: $BRANCH_NAME"
echo "  Base: $BASE_BRANCH"
echo "  Path: $WORKTREE_PATH"
echo ""

# Create worktrees directory if it doesn't exist
mkdir -p "$WORKTREES_DIR"

# Check if worktree already exists
if [ -d "$WORKTREE_PATH" ]; then
    echo "Error: Worktree path already exists: $WORKTREE_PATH"
    exit 1
fi

# Create the worktree
git worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH" "$BASE_BRANCH"

if [ $? -eq 0 ]; then
    echo "✓ Worktree created successfully!"
    echo ""
    echo "Worktree location: $WORKTREE_PATH"
    echo "Branch: $BRANCH_NAME"
    echo ""
    echo "To work in this worktree:"
    echo "  cd $WORKTREE_PATH"
    echo ""
    echo "To remove this worktree when done:"
    echo "  git worktree remove $WORKTREE_PATH"
else
    echo "✗ Failed to create worktree"
    exit 1
fi
