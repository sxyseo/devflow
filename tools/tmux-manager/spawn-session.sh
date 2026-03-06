#!/bin/bash

# spawn-session.sh - Spawn a new tmux session for an agent
#
# Usage: ./spawn-session.sh <session-name> <agent-type> <task-description>
#
# Agent types:
#   - planning: For planning phase agents (PO, BA, Architect, etc.)
#   - development: For development phase agents (Dev Story, etc.)
#   - quality: For quality phase agents (Code Review, QA, etc.)

set -e

SESSION_NAME=$1
AGENT_TYPE=$2
TASK_DESCRIPTION=$3

# Validate inputs
if [ -z "$SESSION_NAME" ] || [ -z "$AGENT_TYPE" ] || [ -z "$TASK_DESCRIPTION" ]; then
  echo "Usage: $0 <session-name> <agent-type> <task-description>"
  echo ""
  echo "Agent types: planning, development, quality"
  exit 1
fi

# Check if session already exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "Error: Session '$SESSION_NAME' already exists"
  echo "Attach with: tmux attach -t $SESSION_NAME"
  echo "Or kill with: tmux kill-session -t $SESSION_NAME"
  exit 1
fi

# Create logs directory
LOG_DIR="$PWD/.openclaw/logs/sessions"
mkdir -p "$LOG_DIR"

# Create new session
tmux new-session -d -s "$SESSION_NAME"

# Set up session with agent-specific configuration
case $AGENT_TYPE in
  "planning")
    tmux send-keys -t "$SESSION_NAME" "export AGENT_MODE=planning" C-m
    tmux send-keys -t "$SESSION_NAME" "export AGENT_SESSION_ID=$(uuidgen)" C-m
    ;;
  "development")
    tmux send-keys -t "$SESSION_NAME" "export AGENT_MODE=development" C-m
    tmux send-keys -t "$SESSION_NAME" "export AGENT_SESSION_ID=$(uuidgen)" C-m
    ;;
  "quality")
    tmux send-keys -t "$SESSION_NAME" "export AGENT_MODE=quality" C-m
    tmux send-keys -t "$SESSION_NAME" "export AGENT_SESSION_ID=$(uuidgen)" C-m
    ;;
  *)
    echo "Warning: Unknown agent type '$AGENT_TYPE', using default configuration"
    tmux send-keys -t "$SESSION_NAME" "export AGENT_MODE=default" C-m
    ;;
esac

# Set up logging
tmux send-keys -t "$SESSION_NAME" "export AGENT_LOG_FILE='$LOG_DIR/${SESSION_NAME}.log'" C-m

# Start the agent task
tmux send-keys -t "$SESSION_NAME" "echo '========================================'" C-m
tmux send-keys -t "$SESSION_NAME" "echo 'Agent Session: $SESSION_NAME'" C-m
tmux send-keys -t "$SESSION_NAME" "echo 'Agent Type: $AGENT_TYPE'" C-m
tmux send-keys -t "$SESSION_NAME" "echo 'Task: $TASK_DESCRIPTION'" C-m
tmux send-keys -t "$SESSION_NAME" "echo 'Started at: $(date)'" C-m
tmux send-keys -t "$SESSION_NAME" "echo '========================================'" C-m
tmux send-keys -t "$SESSION_NAME" "echo ''" C-m

# Execute the task
tmux send-keys -t "$SESSION_NAME" "claude '$TASK_DESCRIPTION'" C-m

# Success message
echo "✓ Session '$SESSION_NAME' created for $AGENT_TYPE agent"
echo ""
echo "Session details:"
echo "  Name: $SESSION_NAME"
echo "  Type: $AGENT_TYPE"
echo "  Task: $TASK_DESCRIPTION"
echo "  Log: $LOG_DIR/${SESSION_NAME}.log"
echo ""
echo "Commands:"
echo "  Attach:    tmux attach -t $SESSION_NAME"
echo "  Detach:    Ctrl+B, D"
echo "  Monitor:   ./tools/tmux-manager/monitor-sessions.sh"
echo "  Kill:      tmux kill-session -t $SESSION_NAME"
