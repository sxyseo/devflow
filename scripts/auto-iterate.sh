#!/bin/bash
# DevFlow自动迭代脚本
# 每隔60秒自动检测任务并执行

set -e

PROJECT_DIR="/Users/abel/dev/devflow"
LOG_FILE="$PROJECT_DIR/.devflow/logs/iteration.log"

# 创建日志目录
mkdir -p "$(dirname "$LOG_FILE")"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "🚀 DevFlow自动迭代启动"
log "项目目录: $PROJECT_DIR"
log "日志文件: $LOG_FILE"
log ""

# 循环计数
ITERATION=0

while true; do
    ITERATION=$((ITERATION + 1))
    
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "循环 #$ITERATION"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # 1. 发现任务
    log "1️⃣ 发现任务..."
    cd "$PROJECT_DIR"
    python3 scripts/auto-discover.sh 2>&1 | while read line; do log "  $line"; done
    
    # 2. 执行任务
    log ""
    log "2️⃣ 执行任务..."
    python3 agents/agent_manager.py 2>&1 | while read line; do log "  $line"; done
    
    # 3. 自动提交
    log ""
    log "3️⃣ 自动提交..."
    python3 scripts/auto-commit.sh 2>&1 | while read line; do log "  $line"; done
    
    # 4. 系统监控
    log ""
    log "4️⃣ 系统监控..."
    python3 scripts/auto-monitor.sh 2>&1 | while read line; do log "  $line"; done
    
    # 5. 显示状态
    log ""
    log "📊 当前状态:"
    if [ -f "$PROJECT_DIR/.devflow/status.json" ]; then
        cat "$PROJECT_DIR/.devflow/status.json" | python3 -m json.tool | while read line; do log "  $line"; done
    fi
    
    # 等待60秒
    log ""
    log "⏰ 等待60秒后继续..."
    log ""
    sleep 60
done
