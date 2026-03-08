#!/bin/bash

# DevFlow Auto-Dev - Main Autonomous Loop Script
# Orchestrates the autonomous development cycle: poll tasks, spawn workers, collect results

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OPENCLAW_DIR="$HOME/.openclaw"
STATE_DIR="$OPENCLAW_DIR/state"
WORKERS_DIR="$STATE_DIR/workers"
OUTPUT_DIR="$STATE_DIR/output"
CONTEXT_DIR="$OPENCLAW_DIR/context/tasks"
LOG_DIR="$OPENCLAW_DIR/logs"
POLL_INTERVAL=${POLL_INTERVAL:-30}
MAX_CONCURRENT_WORKERS=${MAX_CONCURRENT_WORKERS:-3}
OPENCLAW_PORT=${OPENCLAW_PORT:-4444}

# State files
CURRENT_TASK_FILE="$STATE_DIR/current-task.json"
WORKER_POOL_FILE="$STATE_DIR/worker-pool.json"
HALT_FILE="$STATE_DIR/halt.flag"
SHUTDOWN_FILE="$STATE_DIR/shutdown.flag"

# ============================================
# UTILITY FUNCTIONS
# ============================================

log() {
    local level=$1
    shift
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] $*"
    echo "${timestamp} [${level}] $*" >> "$LOG_DIR/autonomous.log"
}

log_info() {
    log "INFO" "${GREEN}$*${NC}"
}

log_warn() {
    log "WARN" "${YELLOW}$*${NC}"
}

log_error() {
    log "ERROR" "${RED}$*${NC}"
}

log_debug() {
    if [ "$DEBUG" = "true" ]; then
        log "DEBUG" "${BLUE}$*${NC}"
    fi
}

cleanup() {
    log_info "Shutting down autonomous loop..."
    rm -f "$HALT_FILE"
    touch "$SHUTDOWN_FILE"
    exit 0
}

trap cleanup SIGINT SIGTERM

# ============================================
# INITIALIZATION
# ============================================

init_directories() {
    mkdir -p "$STATE_DIR"
    mkdir -p "$WORKERS_DIR"
    mkdir -p "$OUTPUT_DIR"
    mkdir -p "$CONTEXT_DIR"
    mkdir -p "$LOG_DIR"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check OpenClaw gateway
    if ! curl -s "http://localhost:$OPENCLAW_PORT/health" > /dev/null 2>&1; then
        log_error "OpenClaw gateway not responding on port $OPENCLAW_PORT"
        log_info "Start with: openclaw start --port $OPENCLAW_PORT"
        return 1
    fi
    log_info "OpenClaw gateway healthy"

    # Check for API keys
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        log_warn "ANTHROPIC_API_KEY not set - Claude Code worker may fail"
    fi

    if [ -z "$OPENAI_API_KEY" ]; then
        log_warn "OPENAI_API_KEY not set - Codex worker may fail"
    fi

    # Check skills are installed
    if [ ! -d "$OPENCLAW_DIR/workspace/skills" ]; then
        log_error "Skills not installed. Run: ./scripts/install-skills.sh"
        return 1
    fi

    return 0
}

# ============================================
# TASK MANAGEMENT
# ============================================

get_next_task() {
    # Poll for next available task
    # This could be from TaskMaster, a file-based queue, or OpenClaw

    local task_file="$1"

    # Check for pending tasks in context directory
    local pending_task=$(find "$CONTEXT_DIR" -name "*.json" -type f 2>/dev/null | head -1)

    if [ -n "$pending_task" ]; then
        cp "$pending_task" "$task_file"
        log_info "Found pending task: $(basename "$pending_task")"
        return 0
    fi

    # Check TaskMaster for tasks (if available)
    if command -v task-master &> /dev/null; then
        local tm_task=$(task-master list --status pending --format json 2>/dev/null | head -1)
        if [ -n "$tm_task" ]; then
            echo "$tm_task" > "$task_file"
            log_info "Found TaskMaster task"
            return 0
        fi
    fi

    log_debug "No pending tasks found"
    return 1
}

select_worker_for_task() {
    local task_file=$1
    local task_type=$(jq -r '.task_type // "general"' "$task_file" 2>/dev/null)

    case "$task_type" in
        "implement-feature"|"refactor"|"fix-bug"|"write-tests")
            echo "claude-code"
            ;;
        "research"|"documentation"|"explain")
            echo "codex"
            ;;
        *)
            echo "claude-code"  # Default worker
            ;;
    esac
}

spawn_worker() {
    local worker_type=$1
    local task_file=$2
    local output_file=$3
    local worker_id=$(date +%s)

    log_info "Spawning $worker_type worker (id: $worker_id)"

    # Create worker state file
    local worker_state="$WORKERS_DIR/${worker_type}-${worker_id}.json"
    cat > "$worker_state" << EOF
{
    "worker_id": "$worker_id",
    "worker_type": "$worker_type",
    "status": "running",
    "task_file": "$task_file",
    "output_file": "$output_file",
    "started_at": "$(date -Iseconds)",
    "pid": null
}
EOF

    # Spawn worker based on type
    case "$worker_type" in
        "claude-code")
            spawn_claude_code_worker "$task_file" "$output_file" "$worker_state" &
            ;;
        "codex")
            spawn_codex_worker "$task_file" "$output_file" "$worker_state" &
            ;;
        *)
            log_error "Unknown worker type: $worker_type"
            return 1
            ;;
    esac

    local worker_pid=$!
    log_debug "Worker spawned with PID: $worker_pid"

    # Update state with PID
    jq --arg pid "$worker_pid" '.pid = $pid' "$worker_state" > "${worker_state}.tmp" && mv "${worker_state}.tmp" "$worker_state"

    echo "$worker_pid"
}

spawn_claude_code_worker() {
    local task_file=$1
    local output_file=$2
    local worker_state=$3

    local prompt=$(jq -r '.prompt // .description // "Execute task"' "$task_file")
    local timeout=$(jq -r '.timeout // 300000' "$task_file")

    log_debug "Claude Code prompt: $prompt"

    # Execute Claude Code
    if command -v claude &> /dev/null; then
        timeout $((timeout / 1000)) claude --print "$prompt" > "$output_file" 2>&1
        local exit_code=$?
    else
        log_error "Claude CLI not found"
        echo '{"status": "failed", "error": "Claude CLI not found"}' > "$output_file"
        local exit_code=1
    fi

    # Update worker state
    local status="completed"
    if [ $exit_code -ne 0 ]; then
        status="failed"
    fi

    jq --arg status "$status" --arg exit_code "$exit_code" \
        '.status = $status | .exit_code = ($exit_code | tonumber) | .completed_at = "'"$(date -Iseconds)"'"' \
        "$worker_state" > "${worker_state}.tmp" && mv "${worker_state}.tmp" "$worker_state"

    return $exit_code
}

spawn_codex_worker() {
    local task_file=$1
    local output_file=$2
    local worker_state=$3

    local prompt=$(jq -r '.prompt // .description // "Execute task"' "$task_file")
    local timeout=$(jq -r '.timeout // 300000' "$task_file")

    log_debug "Codex prompt: $prompt"

    # Execute Codex
    if command -v codex &> /dev/null; then
        timeout $((timeout / 1000)) codex "$prompt" --full-auto > "$output_file" 2>&1
        local exit_code=$?
    else
        log_error "Codex CLI not found"
        echo '{"status": "failed", "error": "Codex CLI not found"}' > "$output_file"
        local exit_code=1
    fi

    # Update worker state
    local status="completed"
    if [ $exit_code -ne 0 ]; then
        status="failed"
    fi

    jq --arg status "$status" --arg exit_code "$exit_code" \
        '.status = $status | .exit_code = ($exit_code | tonumber) | .completed_at = "'"$(date -Iseconds)"'"' \
        "$worker_state" > "${worker_state}.tmp" && mv "${worker_state}.tmp" "$worker_state"

    return $exit_code
}

collect_results() {
    local output_file=$1

    if [ -f "$output_file" ]; then
        log_info "Collecting results from: $(basename "$output_file")"

        # Parse and log results
        local status=$(jq -r '.status // "unknown"' "$output_file")
        local summary=$(jq -r '.summary // "No summary"' "$output_file")

        log_info "Task status: $status"
        log_debug "Summary: $summary"

        # Archive completed output
        local archive_dir="$OUTPUT_DIR/archive"
        mkdir -p "$archive_dir"
        mv "$output_file" "$archive_dir/$(date +%Y%m%d_%H%M%S)_$(basename "$output_file")"
    fi
}

# ============================================
# HEALTH MONITORING
# ============================================

check_worker_health() {
    # Check for stale worker processes
    local stale_workers=0

    for worker_state in "$WORKERS_DIR"/*.json; do
        [ -f "$worker_state" ] || continue

        local status=$(jq -r '.status' "$worker_state")
        local pid=$(jq -r '.pid // empty' "$worker_state")

        if [ "$status" = "running" ] && [ -n "$pid" ]; then
            if ! kill -0 "$pid" 2>/dev/null; then
                log_warn "Stale worker detected: $(basename "$worker_state")"
                jq '.status = "crashed" | .crashed_at = "'"$(date -Iseconds)"'"' \
                    "$worker_state" > "${worker_state}.tmp" && mv "${worker_state}.tmp" "$worker_state"
                stale_workers=$((stale_workers + 1))
            fi
        fi
    done

    return $stale_workers
}

check_system_health() {
    # Periodic health check
    local issues=0

    # Check OpenClaw gateway
    if ! curl -s "http://localhost:$OPENCLAW_PORT/health" > /dev/null 2>&1; then
        log_error "OpenClaw gateway unhealthy"
        issues=$((issues + 1))
    fi

    # Check disk space
    local disk_usage=$(df -h "$STATE_DIR" | tail -1 | awk '{print $5}' | tr -d '%')
    if [ "$disk_usage" -gt 90 ]; then
        log_warn "Disk usage high: ${disk_usage}%"
        issues=$((issues + 1))
    fi

    # Check for HALT flag
    if [ -f "$HALT_FILE" ]; then
        log_warn "HALT flag detected - pausing operations"
        return 1
    fi

    return $issues
}

# ============================================
# MAIN LOOP
# ============================================

main_loop() {
    log_info "Starting autonomous loop..."
    log_info "Poll interval: ${POLL_INTERVAL}s"
    log_info "Max concurrent workers: $MAX_CONCURRENT_WORKERS"

    local iteration=0
    local active_workers=0

    while true; do
        # Check for shutdown
        if [ -f "$SHUTDOWN_FILE" ]; then
            log_info "Shutdown requested - exiting"
            break
        fi

        iteration=$((iteration + 1))
        log_debug "=== Iteration $iteration ==="

        # Health check every 10 iterations
        if [ $((iteration % 10)) -eq 0 ]; then
            check_system_health || {
                log_warn "System health issues detected - waiting..."
                sleep $((POLL_INTERVAL * 2))
                continue
            }
            check_worker_health
        fi

        # Count active workers
        active_workers=$(find "$WORKERS_DIR" -name "*.json" -exec jq -r 'select(.status == "running") | .worker_id' {} \; 2>/dev/null | wc -l | tr -d ' ')
        log_debug "Active workers: $active_workers"

        # Spawn new workers if capacity available
        if [ "$active_workers" -lt "$MAX_CONCURRENT_WORKERS" ]; then
            if get_next_task "$CURRENT_TASK_FILE"; then
                local worker_type=$(select_worker_for_task "$CURRENT_TASK_FILE")
                local task_id=$(jq -r '.task_id // "unknown"' "$CURRENT_TASK_FILE")
                local output_file="$OUTPUT_DIR/${worker_type}-${task_id}-$(date +%s).json"

                spawn_worker "$worker_type" "$CURRENT_TASK_FILE" "$output_file"

                # Clean up current task file
                rm -f "$CURRENT_TASK_FILE"
            fi
        else
            log_debug "Max workers reached ($active_workers/$MAX_CONCURRENT_WORKERS)"
        fi

        # Collect completed results
        for output_file in "$OUTPUT_DIR"/*.json; do
            [ -f "$output_file" ] || continue
            collect_results "$output_file"
        done

        # Wait for next iteration
        log_debug "Waiting ${POLL_INTERVAL}s..."
        sleep "$POLL_INTERVAL"
    done

    log_info "Autonomous loop ended"
}

# ============================================
# ENTRY POINT
# ============================================

echo "========================================"
echo "DevFlow Auto-Dev - Autonomous Loop"
echo "========================================"
echo ""

# Initialize
init_directories

# Check prerequisites
if ! check_prerequisites; then
    log_error "Prerequisites not met - exiting"
    exit 1
fi

echo ""
echo "Configuration:"
echo "  Project Dir:     $PROJECT_DIR"
echo "  State Dir:       $STATE_DIR"
echo "  Poll Interval:   ${POLL_INTERVAL}s"
echo "  Max Workers:     $MAX_CONCURRENT_WORKERS"
echo "  OpenClaw Port:   $OPENCLAW_PORT"
echo ""

# Start main loop
main_loop
