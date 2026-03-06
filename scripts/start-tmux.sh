#!/bin/bash

# DevFlow - AI自动开发系统启动脚本
# 使用tmux后台运行多个Agent

set -e

PROJECT_DIR="/Users/abel/dev/devflow"
SESSION_NAME="devflow"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 DevFlow - AI自动开发系统${NC}"
echo ""

# 检查tmux是否安装
if ! command -v tmux &> /dev/null; then
    echo -e "${RED}错误: tmux未安装${NC}"
    echo "请先安装tmux: brew install tmux"
    exit 1
fi

# 检查是否已有会话在运行
if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo -e "${YELLOW}⚠️  DevFlow会话已在运行${NC}"
    echo ""
    echo "附加到会话: tmux attach -t $SESSION_NAME"
    echo "停止会话: tmux kill-session -t $SESSION_NAME"
    exit 0
fi

echo "创建tmux会话..."
tmux new-session -d -s $SESSION_NAME -c $PROJECT_DIR

# 窗口0: 主控制台
tmux rename-window -t $SESSION_NAME:0 'Main'
tmux send-keys -t $SESSION_NAME:0 "cd $PROJECT_DIR && clear" C-m
tmux send-keys -t $SESSION_NAME:0 "echo '🤖 DevFlow主控制台'" C-m
tmux send-keys -t $SESSION_NAME:0 "echo '可用命令:'" C-m
tmux send-keys -t $SESSION_NAME:0 "echo '  - ./scripts/auto-discover.sh  # 自动发现任务'" C-m
tmux send-keys -t $SESSION_NAME:0 "echo '  - ./scripts/auto-commit.sh    # 自动提交'" C-m
tmux send-keys -t $SESSION_NAME:0 "echo '  - ./scripts/auto-monitor.sh   # 自动监控'" C-m

# 窗口1: TaskMaster - 任务发现
tmux new-window -t $SESSION_NAME:1 -n 'TaskMaster'
tmux send-keys -t $SESSION_NAME:1 "cd $PROJECT_DIR && clear" C-m
tmux send-keys -t $SESSION_NAME:1 "echo '📋 TaskMaster - 任务发现引擎'" C-m
tmux send-keys -t $SESSION_NAME:1 "watch -n 60 'python3 skills/taskmaster/discover.py'" C-m

# 窗口2: Codex - 代码生成
tmux new-window -t $SESSION_NAME:2 -n 'Codex'
tmux send-keys -t $SESSION_NAME:2 "cd $PROJECT_DIR && clear" C-m
tmux send-keys -t $SESSION_NAME:2 "echo '⚡ Codex - 代码生成引擎'" C-m
tmux send-keys -t $SESSION_NAME:2 "echo '等待任务...'" C-m
# tmux send-keys -t $SESSION_NAME:2 "codex --agent auto" C-m

# 窗口3: Claude Code - 代码审查
tmux new-window -t $SESSION_NAME:3 -n 'ClaudeCode'
tmux send-keys -t $SESSION_NAME:3 "cd $PROJECT_DIR && clear" C-m
tmux send-keys -t $SESSION_NAME:3 "echo '🔍 Claude Code - 代码审查引擎'" C-m
tmux send-keys -t $SESSION_NAME:3 "echo '等待代码审查...'" C-m
# tmux send-keys -t $SESSION_NAME:3 "claude-code --auto-review" C-m

# 窗口4: Monitor - 监控
tmux new-window -t $SESSION_NAME:4 -n 'Monitor'
tmux send-keys -t $SESSION_NAME:4 "cd $PROJECT_DIR && clear" C-m
tmux send-keys -t $SESSION_NAME:4 "echo '📊 Monitor - 系统监控'" C-m
tmux send-keys -t $SESSION_NAME:4 "watch -n 5 'python3 skills/monitor/status.py'" C-m

# 窗口5: Git - 自动提交
tmux new-window -t $SESSION_NAME:5 -n 'Git'
tmux send-keys -t $SESSION_NAME:5 "cd $PROJECT_DIR && clear" C-m
tmux send-keys -t $SESSION_NAME:5 "echo '📝 Git - 自动提交引擎'" C-m
tmux send-keys -t $SESSION_NAME:5 "watch -n 300 'python3 skills/git/auto-commit.py'" C-m

# 窗口6: Dashboard - Web界面
tmux new-window -t $SESSION_NAME:6 -n 'Dashboard'
tmux send-keys -t $SESSION_NAME:6 "cd $PROJECT_DIR/dashboard && clear" C-m
tmux send-keys -t $SESSION_NAME:6 "echo '🖥️  Dashboard - Web界面'" C-m
# tmux send-keys -t $SESSION_NAME:6 "npm run dev" C-m

echo ""
echo -e "${GREEN}✅ DevFlow已启动！${NC}"
echo ""
echo "tmux会话: $SESSION_NAME"
echo ""
echo "窗口列表:"
echo "  0: Main         - 主控制台"
echo "  1: TaskMaster   - 任务发现"
echo "  2: Codex        - 代码生成"
echo "  3: ClaudeCode   - 代码审查"
echo "  4: Monitor      - 系统监控"
echo "  5: Git          - 自动提交"
echo "  6: Dashboard    - Web界面"
echo ""
echo "附加到会话:"
echo "  tmux attach -t $SESSION_NAME"
echo ""
echo "切换窗口 (在tmux中):"
echo "  Ctrl+b <窗口号>  # 例如: Ctrl+b 1"
echo "  Ctrl+b n         # 下一个窗口"
echo "  Ctrl+b p         # 上一个窗口"
echo ""
echo "停止会话:"
echo "  tmux kill-session -t $SESSION_NAME"
echo ""
