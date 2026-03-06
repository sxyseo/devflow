#!/bin/bash

# run-bmad-workflow.sh - Run the complete BMad workflow for a project
#
# Usage: ./run-bmad-workflow.sh <project-name> "<project-idea>"
#
# Example:
#   ./run-bmad-workflow.sh my-task-app "A task management app for AI developers"

set -e

PROJECT_NAME=$1
PROJECT_IDEA=$2

# Validate inputs
if [ -z "$PROJECT_NAME" ] || [ -z "$PROJECT_IDEA" ]; then
  echo "Usage: $0 <project-name> '<project-idea>'"
  echo ""
  echo "Example:"
  echo "  $0 my-task-app 'A task management app for AI developers'"
  exit 1
fi

echo "═══════════════════════════════════════════════════════════════"
echo "           BMad Workflow for: $PROJECT_NAME"
echo "═══════════════════════════════════════════════════════════════"
echo "Project Idea: $PROJECT_IDEA"
echo "Started at: $(date)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Create project directory structure
PROJECT_DIR=".openclaw/workspace/$PROJECT_NAME"
mkdir -p "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/.taskmaster/docs"
mkdir -p "$PROJECT_DIR/.taskmaster/stories"
mkdir -p "$PROJECT_DIR/.taskmaster/tasks"

echo "✓ Project directory created: $PROJECT_DIR"
echo ""

# Phase 1: Planning
echo "═══════════════════════════════════════════════════════════════"
echo "                    PHASE 1: PLANNING"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Step 1: Product Owner
echo "Step 1: Product Owner Agent - Generating Product Brief"
./tools/tmux-manager/spawn-session.sh \
  "${PROJECT_NAME}-product-owner" \
  "planning" \
  "Run product-owner skill. Generate product brief for: $PROJECT_IDEA. Save to $PROJECT_DIR/.taskmaster/docs/product-brief.md"

sleep 5

# Step 2: Business Analyst
echo ""
echo "Step 2: Business Analyst Agent - Generating PRD"
./tools/tmux-manager/spawn-session.sh \
  "${PROJECT_NAME}-business-analyst" \
  "planning" \
  "Run business-analyst skill. Read brief from $PROJECT_DIR/.taskmaster/docs/product-brief.md and generate PRD. Save to $PROJECT_DIR/.taskmaster/docs/prd.md"

sleep 5

# Step 3: Architect
echo ""
echo "Step 3: Architect Agent - Generating Architecture"
./tools/tmux-manager/spawn-session.sh \
  "${PROJECT_NAME}-architect" \
  "planning" \
  "Run architect skill. Read PRD from $PROJECT_DIR/.taskmaster/docs/prd.md and generate architecture document. Save to $PROJECT_DIR/.taskmaster/docs/architecture.md"

sleep 5

# Step 4: UX Designer
echo ""
echo "Step 4: UX Designer Agent - Generating UX Specifications"
./tools/tmux-manager/spawn-session.sh \
  "${PROJECT_NAME}-ux-designer" \
  "planning" \
  "Run ux-designer skill. Read PRD from $PROJECT_DIR/.taskmaster/docs/prd.md and architecture from $PROJECT_DIR/.taskmaster/docs/architecture.md, then generate UX specifications. Save to $PROJECT_DIR/.taskmaster/docs/ux-spec.md"

sleep 5

# Step 5: Scrum Master
echo ""
echo "Step 5: Scrum Master Agent - Breaking Down Stories"
./tools/tmux-manager/spawn-session.sh \
  "${PROJECT_NAME}-scrum-master" \
  "planning" \
  "Run scrum-master skill. Read PRD from $PROJECT_DIR/.taskmaster/docs/prd.md and break down into epics and stories. Save to $PROJECT_DIR/.taskmaster/stories/"

sleep 5

# Step 6: Readiness Check
echo ""
echo "Step 6: Readiness Check Agent - GO/NO-GO Decision"
./tools/tmux-manager/spawn-session.sh \
  "${PROJECT_NAME}-readiness-check" \
  "planning" \
  "Run readiness-check skill. Review all planning artifacts in $PROJECT_DIR/.taskmaster/docs/ and stories in $PROJECT_DIR/.taskmaster/stories/. Provide GO/NO-GO decision and any issues found. Save to $PROJECT_DIR/.taskmaster/docs/readiness-check.md"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "                  PLANNING PHASE COMPLETE"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Planning agents are running in the background."
echo ""
echo "Monitor sessions with:"
echo "  ./tools/tmux-manager/monitor-sessions.sh"
echo ""
echo "Attach to a session:"
echo "  tmux attach -t ${PROJECT_NAME}-product-owner"
echo "  tmux attach -t ${PROJECT_NAME}-business-analyst"
echo "  tmux attach -t ${PROJECT_NAME}-architect"
echo "  etc."
echo ""
echo "When all planning agents complete:"
echo "  1. Review the artifacts in $PROJECT_DIR/.taskmaster/docs/"
echo "  2. Review the stories in $PROJECT_DIR/.taskmaster/stories/"
echo "  3. Run execution phase for each story"
echo ""
echo "Execution command (per story):"
echo "  ./scripts/run-story-execution.sh $PROJECT_NAME <story-id>"
echo ""
echo "═══════════════════════════════════════════════════════════════"
