#!/bin/bash

# monitor-sessions.sh - Monitor all active agent sessions
#
# Usage: ./monitor-sessions.sh

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "           Active Agent Sessions - $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
  echo "Error: tmux is not installed"
  exit 1
fi

# List all sessions
if ! tmux list-sessions 2>/dev/null; then
  echo "No active sessions found"
  exit 0
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "                     Session Details"
echo "═══════════════════════════════════════════════════════════════"

# Get list of sessions
SESSIONS=$(tmux list-sessions -F "#{session_name}")

for session in $SESSIONS; do
  echo ""
  echo "─────────────────────────────────────────────────────────────"
  echo "Session: $session"
  echo "─────────────────────────────────────────────────────────────"

  # Get session info
  PANES=$(tmux list-panes -t "$session" -F "#{pane_active} #{pane_current_command} #{pane_pid}" | head -1)

  # Show last 20 lines of each pane
  tmux capture-pane -t "$session" -p -S -20 | head -20
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "                         Log Files"
echo "═══════════════════════════════════════════════════════════════"

# Show log files if they exist
LOG_DIR="$PWD/.openclaw/logs/sessions"
if [ -d "$LOG_DIR" ]; then
  for log_file in "$LOG_DIR"/*.log; do
    if [ -f "$log_file" ]; then
      echo ""
      echo "Log: $(basename "$log_file")"
      echo "Size: $(wc -l < "$log_file") lines"
      echo "Last modified: $(stat -f "%Sm" "$log_file" 2>/dev/null || stat -c "%y" "$log_file" 2>/dev/null)"
    fi
  done
else
  echo "No log directory found"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
