#!/bin/bash

# DevFlow Auto-Dev - System Health Check Script
# Monitors and reports the health status of all system components

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
LOG_DIR="$OPENCLAW_DIR/logs"
OPENCLAW_PORT=${OPENCLAW_PORT:-4444}

# Status tracking
TOTAL_CHECKS=0
PASSED_CHECKS=0
WARNINGS=0
ERRORS=0

# ============================================
# UTILITY FUNCTIONS
# ============================================

print_header() {
    echo ""
    echo "========================================"
    echo "$1"
    echo "========================================"
}

print_check() {
    local name=$1
    local status=$2
    local message=${3:-""}

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    case "$status" in
        "pass"|"ok"|"healthy")
            echo -e "${GREEN}[OK]${NC} $name"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            ;;
        "warn"|"warning")
            echo -e "${YELLOW}[WARN]${NC} $name${message:+: $message}"
            WARNINGS=$((WARNINGS + 1))
            ;;
        "fail"|"error"|"unhealthy")
            echo -e "${RED}[FAIL]${NC} $name${message:+: $message}"
            ERRORS=$((ERRORS + 1))
            ;;
        "skip")
            echo -e "${BLUE}[SKIP]${NC} $name${message:+: $message}"
            ;;
    esac
}

# ============================================
# SYSTEM CHECKS
# ============================================

check_disk_space() {
    print_header "Disk Space"

    # Check root partition
    local disk_usage=$(df -h / | tail -1 | awk '{print $5}' | tr -d '%')
    local disk_avail=$(df -h / | tail -1 | awk '{print $4}')

    if [ "$disk_usage" -gt 90 ]; then
        print_check "Root partition disk usage" "fail" "${disk_usage}% used, ${disk_avail} available"
    elif [ "$disk_usage" -gt 80 ]; then
        print_check "Root partition disk usage" "warn" "${disk_usage}% used, ${disk_avail} available"
    else
        print_check "Root partition disk usage" "pass" "${disk_usage}% used, ${disk_avail} available"
    fi

    # Check home partition (if different)
    local home_usage=$(df -h "$HOME" 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%')
    local home_avail=$(df -h "$HOME" 2>/dev/null | tail -1 | awk '{print $4}')

    if [ -n "$home_usage" ]; then
        if [ "$home_usage" -gt 90 ]; then
            print_check "Home partition disk usage" "fail" "${home_usage}% used, ${home_avail} available"
        elif [ "$home_usage" -gt 80 ]; then
            print_check "Home partition disk usage" "warn" "${home_usage}% used, ${home_avail} available"
        else
            print_check "Home partition disk usage" "pass" "${home_usage}% used, ${home_avail} available"
        fi
    fi
}

check_memory() {
    print_header "Memory Status"

    if command -v free &> /dev/null; then
        local mem_info=$(free -m | grep "Mem:")
        local mem_total=$(echo "$mem_info" | awk '{print $2}')
        local mem_used=$(echo "$mem_info" | awk '{print $3}')
        local mem_avail=$(echo "$mem_info" | awk '{print $7}')
        local mem_percent=$((mem_used * 100 / mem_total))

        if [ "$mem_percent" -gt 90 ]; then
            print_check "Memory usage" "fail" "${mem_percent}% used (${mem_used}MB/${mem_total}MB)"
        elif [ "$mem_percent" -gt 80 ]; then
            print_check "Memory usage" "warn" "${mem_percent}% used (${mem_used}MB/${mem_total}MB)"
        else
            print_check "Memory usage" "pass" "${mem_percent}% used (${mem_used}MB/${mem_total}MB, ${mem_avail}MB available)"
        fi
    else
        # macOS
        local vm_stat=$(vm_stat 2>/dev/null)
        if [ -n "$vm_stat" ]; then
            local mem_total=$(sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1024/1024)}')
            local page_size=4096
            local free_pages=$(echo "$vm_stat" | grep "Pages free" | awk '{print $3}' | tr -d '.')
            local free_mem=$((free_pages * page_size / 1024 / 1024))
            print_check "Memory (macOS)" "pass" "${free_mem}MB free of ${mem_total}MB"
        else
            print_check "Memory check" "skip" "Unable to determine memory status"
        fi
    fi
}

check_cpu_load() {
    print_header "CPU Load"

    if [ -f /proc/loadavg ]; then
        local load_avg=$(cat /proc/loadavg | awk '{print $1, $2, $3}')
        local cpu_count=$(nproc 2>/dev/null || echo 1)
        local load_1=$(echo "$load_avg" | awk '{print $1}' | cut -d. -f1)

        if [ "$load_1" -gt "$cpu_count" ]; then
            print_check "CPU load average" "warn" "Load $load_avg exceeds CPU count ($cpu_count)"
        else
            print_check "CPU load average" "pass" "$load_avg (CPUs: $cpu_count)"
        fi
    else
        # macOS
        local cpu_load=$(sysctl -n vm.loadavg 2>/dev/null)
        if [ -n "$cpu_load" ]; then
            print_check "CPU load average" "pass" "$cpu_load"
        else
            print_check "CPU load check" "skip" "Unable to determine CPU load"
        fi
    fi
}

# ============================================
# SERVICE CHECKS
# ============================================

check_openclaw_gateway() {
    print_header "OpenClaw Gateway"

    if curl -s --max-time 5 "http://localhost:$OPENCLAW_PORT/health" > /dev/null 2>&1; then
        print_check "OpenClaw gateway health" "pass" "Responding on port $OPENCLAW_PORT"

        # Try to get more details
        local version=$(curl -s --max-time 5 "http://localhost:$OPENCLAW_PORT/version" 2>/dev/null)
        if [ -n "$version" ]; then
            print_check "OpenClaw version" "pass" "$version"
        fi
    else
        print_check "OpenClaw gateway health" "fail" "Not responding on port $OPENCLAW_PORT"
        print_check "OpenClaw version" "skip" "Gateway not available"
    fi
}

check_api_keys() {
    print_header "API Configuration"

    if [ -n "$ANTHROPIC_API_KEY" ]; then
        # Mask the key for security
        local masked_key="${ANTHROPIC_API_KEY:0:8}...${ANTHROPIC_API_KEY: -4}"
        print_check "ANTHROPIC_API_KEY" "pass" "Set ($masked_key)"
    else
        print_check "ANTHROPIC_API_KEY" "warn" "Not set - Claude Code worker may fail"
    fi

    if [ -n "$OPENAI_API_KEY" ]; then
        local masked_key="${OPENAI_API_KEY:0:8}...${OPENAI_API_KEY: -4}"
        print_check "OPENAI_API_KEY" "pass" "Set ($masked_key)"
    else
        print_check "OPENAI_API_KEY" "warn" "Not set - Codex worker may fail"
    fi
}

# ============================================
# PROJECT CHECKS
# ============================================

check_project_structure() {
    print_header "Project Structure"

    # Check essential directories
    if [ -d "$PROJECT_DIR/scripts" ]; then
        print_check "scripts/ directory" "pass"
    else
        print_check "scripts/ directory" "fail" "Not found"
    fi

    if [ -d "$PROJECT_DIR/skills" ]; then
        print_check "skills/ directory" "pass"
    else
        print_check "skills/ directory" "warn" "Not found"
    fi

    if [ -d "$PROJECT_DIR/.auto-claude" ]; then
        print_check ".auto-claude/ directory" "pass"
    else
        print_check ".auto-claude/ directory" "warn" "Not found"
    fi
}

check_skills_installation() {
    print_header "Skills Installation"

    local skills_dir="$OPENCLAW_DIR/workspace/skills"

    if [ -d "$skills_dir" ]; then
        local skill_count=$(find "$skills_dir" -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
        skill_count=$((skill_count - 1))  # Subtract 1 for the directory itself

        if [ "$skill_count" -gt 0 ]; then
            print_check "Skills directory" "pass" "$skill_count skill(s) installed"

            # Check for specific skills
            for skill in taskmaster bmad spec-driven; do
                if [ -d "$skills_dir/$skill" ]; then
                    if [ -f "$skills_dir/$skill/SKILL.md" ]; then
                        print_check "Skill: $skill" "pass" "SKILL.md present"
                    else
                        print_check "Skill: $skill" "warn" "Placeholder only"
                    fi
                else
                    print_check "Skill: $skill" "warn" "Not installed"
                fi
            done
        else
            print_check "Skills directory" "warn" "No skills installed"
        fi
    else
        print_check "Skills directory" "fail" "Not found at $skills_dir"
    fi
}

# ============================================
# WORKER STATE CHECKS
# ============================================

check_worker_state() {
    print_header "Worker State"

    if [ -d "$WORKERS_DIR" ]; then
        local total_workers=$(find "$WORKERS_DIR" -name "*.json" -type f 2>/dev/null | wc -l | tr -d ' ')

        if [ "$total_workers" -gt 0 ]; then
            print_check "Worker state directory" "pass" "$total_workers worker state file(s)"

            # Count by status
            local running=0
            local completed=0
            local failed=0
            local crashed=0

            for worker_file in "$WORKERS_DIR"/*.json; do
                [ -f "$worker_file" ] || continue

                if command -v jq &> /dev/null; then
                    local status=$(jq -r '.status // "unknown"' "$worker_file" 2>/dev/null)
                    case "$status" in
                        "running") running=$((running + 1)) ;;
                        "completed") completed=$((completed + 1)) ;;
                        "failed") failed=$((failed + 1)) ;;
                        "crashed") crashed=$((crashed + 1)) ;;
                    esac
                fi
            done

            if [ "$running" -gt 0 ]; then
                print_check "Running workers" "pass" "$running active"
            fi
            if [ "$completed" -gt 0 ]; then
                print_check "Completed workers" "pass" "$completed total"
            fi
            if [ "$failed" -gt 0 ]; then
                print_check "Failed workers" "warn" "$failed total"
            fi
            if [ "$crashed" -gt 0 ]; then
                print_check "Crashed workers" "fail" "$crashed total"
            fi
        else
            print_check "Worker state directory" "pass" "No active workers"
        fi
    else
        print_check "Worker state directory" "pass" "Not initialized (no workers run yet)"
    fi

    # Check for halt/shutdown flags
    if [ -f "$STATE_DIR/halt.flag" ]; then
        print_check "System halt flag" "warn" "Operations paused"
    fi

    if [ -f "$STATE_DIR/shutdown.flag" ]; then
        print_check "System shutdown flag" "warn" "Shutdown requested"
    fi
}

# ============================================
# LOG CHECKS
# ============================================

check_logs() {
    print_header "Log Status"

    if [ -d "$LOG_DIR" ]; then
        local log_count=$(find "$LOG_DIR" -name "*.log" -type f 2>/dev/null | wc -l | tr -d ' ')
        print_check "Log directory" "pass" "$log_count log file(s)"

        # Check for recent errors in autonomous.log
        local autonomous_log="$LOG_DIR/autonomous.log"
        if [ -f "$autonomous_log" ]; then
            local error_count=$(grep -c "\[ERROR\]" "$autonomous_log" 2>/dev/null || echo 0)
            local warn_count=$(grep -c "\[WARN\]" "$autonomous_log" 2>/dev/null || echo 0)

            if [ "$error_count" -gt 0 ]; then
                print_check "Autonomous log errors" "warn" "$error_count error(s) found"
            else
                print_check "Autonomous log errors" "pass" "No errors"
            fi

            if [ "$warn_count" -gt 10 ]; then
                print_check "Autonomous log warnings" "warn" "$warn_count warning(s) found"
            else
                print_check "Autonomous log warnings" "pass" "$warn_count warning(s)"
            fi

            # Check log file size
            local log_size=$(du -h "$autonomous_log" 2>/dev/null | cut -f1)
            print_check "Autonomous log size" "pass" "$log_size"
        else
            print_check "Autonomous log" "pass" "No log file yet"
        fi
    else
        print_check "Log directory" "pass" "Not created yet"
    fi
}

# ============================================
# CLI TOOLS CHECK
# ============================================

check_cli_tools() {
    print_header "CLI Tools"

    if command -v claude &> /dev/null; then
        local claude_version=$(claude --version 2>/dev/null | head -1 || echo "installed")
        print_check "Claude CLI" "pass" "$claude_version"
    else
        print_check "Claude CLI" "warn" "Not installed"
    fi

    if command -v codex &> /dev/null; then
        local codex_version=$(codex --version 2>/dev/null | head -1 || echo "installed")
        print_check "Codex CLI" "pass" "$codex_version"
    else
        print_check "Codex CLI" "warn" "Not installed"
    fi

    if command -v jq &> /dev/null; then
        local jq_version=$(jq --version 2>/dev/null)
        print_check "jq" "pass" "$jq_version"
    else
        print_check "jq" "warn" "Not installed - JSON parsing limited"
    fi

    if command -v curl &> /dev/null; then
        print_check "curl" "pass"
    else
        print_check "curl" "fail" "Not installed"
    fi
}

# ============================================
# SUMMARY
# ============================================

print_summary() {
    print_header "Health Check Summary"

    echo ""
    echo "Total Checks: $TOTAL_CHECKS"
    echo -e "Passed:       ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "Warnings:     ${YELLOW}$WARNINGS${NC}"
    echo -e "Errors:       ${RED}$ERRORS${NC}"
    echo ""

    if [ "$ERRORS" -gt 0 ]; then
        echo -e "${RED}Status: UNHEALTHY${NC}"
        echo ""
        echo "Recommended actions:"
        echo "  - Fix the errors above before proceeding"
        echo "  - Check OpenClaw gateway is running"
        echo "  - Verify API keys are configured"
        return 1
    elif [ "$WARNINGS" -gt 0 ]; then
        echo -e "${YELLOW}Status: HEALTHY (with warnings)${NC}"
        echo ""
        echo "Note: System is operational but some checks raised warnings."
        return 0
    else
        echo -e "${GREEN}Status: HEALTHY${NC}"
        echo ""
        echo "All systems operational."
        return 0
    fi
}

# ============================================
# MAIN ENTRY POINT
# ============================================

main() {
    local output_format=${1:-"text"}
    local check_type=${2:-"all"}

    echo "========================================"
    echo "DevFlow Auto-Dev - Health Check"
    echo "========================================"
    echo ""
    echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Project:   $PROJECT_DIR"
    echo ""

    case "$check_type" in
        "system")
            check_disk_space
            check_memory
            check_cpu_load
            ;;
        "services")
            check_openclaw_gateway
            check_api_keys
            ;;
        "project")
            check_project_structure
            check_skills_installation
            ;;
        "workers")
            check_worker_state
            check_logs
            ;;
        "all"|*)
            check_disk_space
            check_memory
            check_cpu_load
            check_openclaw_gateway
            check_api_keys
            check_project_structure
            check_skills_installation
            check_worker_state
            check_logs
            check_cli_tools
            ;;
    esac

    print_summary
}

# Run main
main "$@"
