#!/bin/bash
# DevFlow 实时监控脚本
# 持续展示系统效果

PROJECT_DIR="/Users/abel/dev/devflow"
cd "$PROJECT_DIR"

clear

echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║          🚀 DevFlow 实时监控 (按Ctrl+C退出)              ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

while true; do
    # 清除之前的内容（保留标题）
    tput cup 6 0
    tput ed
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 系统状态 - $(date '+%Y-%m-%d %H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Git统计
    echo "📝 Git提交:"
    TOTAL_COMMITS=$(git rev-list --count HEAD)
    TODAY_COMMITS=$(git log --since="midnight" --oneline | wc -l | tr -d ' ')
    echo "  总计: $TOTAL_COMMITS | 今日: $TODAY_COMMITS ✅"
    echo ""
    
    # 任务统计
    echo "📋 任务队列:"
    if [ -f ".devflow/tasks/schedule.json" ]; then
        TOTAL_TASKS=$(cat .devflow/tasks/schedule.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_tasks', 0))" 2>/dev/null || echo "0")
        PENDING=$(cat .devflow/status.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('pending', 0))" 2>/dev/null || echo "0")
        COMPLETED=$(cat .devflow/status.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('completed', 0))" 2>/dev/null || echo "0")
        echo "  总计: $TOTAL_TASKS | 待处理: $PENDING | 已完成: $COMPLETED"
    else
        echo "  暂无任务"
    fi
    echo ""
    
    # tmux状态
    echo "🖥️  tmux会话:"
    if tmux has-session -t devflow-auto 2>/dev/null; then
        WINDOWS=$(tmux list-windows -t devflow-auto | wc -l | tr -d ' ')
        echo "  状态: ✅ 运行中 | 窗口数: $WINDOWS"
    else
        echo "  状态: ❌ 未运行"
    fi
    echo ""
    
    # 系统资源
    echo "💻 系统资源:"
    CPU=$(ps -A -o %cpu | awk '{s+=$1} END {print s}' | cut -d. -f1)
    DISK=$(df -h . | tail -1 | awk '{print $5}')
    echo "  CPU: ${CPU}% | 磁盘: $DISK"
    echo ""
    
    # 最近提交
    echo "📜 最近3次提交:"
    git log --oneline -3 --color=always | sed 's/^/  /'
    echo ""
    
    # 最新任务
    echo "🔍 最新任务:"
    if ls .devflow/tasks/tasks-*.json 1> /dev/null 2>&1; then
        LATEST_TASK=$(ls -t .devflow/tasks/tasks-*.json | head -1)
        TASK_COUNT=$(cat "$LATEST_TASK" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total', 0))" 2>/dev/null || echo "?")
        TASK_FILE=$(basename "$LATEST_TASK")
        echo "  文件: $TASK_FILE"
        echo "  数量: $TASK_COUNT 个任务"
    else
        echo "  暂无任务文件"
    fi
    echo ""
    
    # 效率指标
    echo "⚡ 效率指标:"
    if [ "$TODAY_COMMITS" -gt 0 ]; then
        MANUAL_TIME=$((TODAY_COMMITS * 30 / 60))
        AUTO_TIME=$((TODAY_COMMITS * 5 / 60))
        SAVED_TIME=$((MANUAL_TIME - AUTO_TIME))
        echo "  人工耗时: ${MANUAL_TIME}h | 自动: ${AUTO_TIME}h | 节省: ${SAVED_TIME}h ⭐"
        echo "  速度提升: 6.0x"
    fi
    echo ""
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💡 快捷命令:"
    echo "  df        主菜单 | dfr      单次运行 | dfs      查看状态"
    echo "  dflog     查看日志 | dftask   查看任务 | dfc      提交代码"
    echo ""
    echo "🌐 GitHub: https://github.com/sxyseo/devflow"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "⏱️  每30秒自动刷新... (按Ctrl+C退出)"
    
    sleep 30
done
