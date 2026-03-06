#!/bin/bash

# create-worktree.sh - Create a new git worktree for isolated testing
#
# Usage: ./create-worktree.sh <worktree-name> [base-branch]

set -e

WORKTREE_NAME=$1
BASE_BRANCH=${2:-main}

# Validate inputs
if [ -z "$WORKTREE_NAME" ]; then
  echo "Usage: $0 <worktree-name> [base-branch]"
  echo ""
  echo "Example:"
  echo "  $0 story-123              # Create from main branch"
  echo "  $0 feature-auth develop  # Create from develop branch"
  exit 1
fi

# Set up worktree directory
WORKTREE_BASE="/tmp/devflow-worktrees"
WORKTREE_PATH="$WORKTREE_BASE/$WORKTREE_NAME"

# Check if worktree already exists
if [ -d "$WORKTREE_PATH" ]; then
  echo "Error: Worktree already exists at $WORKTREE_PATH"
  echo "Remove with: git worktree remove $WORKTREE_PATH"
  exit 1
fi

# Create worktree base directory
mkdir -p "$WORKTREE_BASE"

# Create worktree
echo "Creating worktree..."
git worktree add -b "$WORKTREE_NAME" "$WORKTREE_PATH" "$BASE_BRANCH"

if [ $? -ne 0 ]; then
  echo "Error: Failed to create worktree"
  exit 1
fi

# Set up node_modules in worktree (optional)
if [ -f "package.json" ]; then
  echo "Setting up dependencies in worktree..."
  (cd "$WORKTREE_PATH" && npm install > /dev/null 2>&1 &)
  echo "Dependencies installing in background..."
fi

# Success message
echo "✓ Worktree created successfully"
echo ""
echo "Worktree details:"
echo "  Path:    $WORKTREE_PATH"
echo "  Branch:  $WORKTREE_NAME"
echo "  Base:    $BASE_BRANCH"
echo ""
echo "Commands:"
echo "  Enter:    cd $WORKTREE_PATH"
echo "  Remove:   git worktree remove $WORKTREE_PATH"
echo "  List:     git worktree list"
echo "  Prune:    git worktree prune"
echo ""
echo "Note: Worktrees older than 7 days will be automatically cleaned up"
