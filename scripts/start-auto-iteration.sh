#!/bin/bash
# DevFlow 持续迭代启动脚本
# 使用tmux + Claude Code实现24/7自动开发

set -e

PROJECT_DIR="/Users/abel/dev/devflow"
SESSION_NAME="devflow-auto"

echo "🚀 DevFlow 持续迭代系统"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 检查tmux
if ! command -v tmux &> /dev/null; then
    echo "❌ tmux未安装"
    echo "安装: brew install tmux"
    exit 1
fi

# 检查是否已有会话
if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "⚠️  会话已存在: $SESSION_NAME"
    echo ""
    echo "附加到会话:"
    echo "  tmux attach -t $SESSION_NAME"
    echo ""
    echo "查看窗口:"
    echo "  tmux list-windows -t $SESSION_NAME"
    echo ""
    echo "停止会话:"
    echo "  tmux kill-session -t $SESSION_NAME"
    exit 0
fi

echo "创建tmux会话..."
tmux new-session -d -s $SESSION_NAME -c $PROJECT_DIR

# 窗口0: 主控制台
tmux rename-window -t $SESSION_NAME:0 'Main'
tmux send-keys -t $SESSION_NAME:0 "cd $PROJECT_DIR && clear" C-m
tmux send-keys -t $SESSION_NAME:0 "echo '🎯 DevFlow主控制台'" C-m
tmux send-keys -t $SESSION_NAME:0 "echo ''" C-m
tmux send-keys -t $SESSION_NAME:0 "echo '可用命令:'" C-m
tmux send-keys -t $SESSION_NAME:0 "echo '  df        - 主菜单'" C-m
tmux send-keys -t $SESSION_NAME:0 "echo '  dfr       - 单次运行'" C-m
tmux send-keys -t $SESSION_NAME:0 "echo '  dfs       - 查看状态'" C-m
tmux send-keys -t $SESSION_NAME:0 "echo '  dflog     - 查看日志'" C-m

# 窗口1: Claude Code - 自动开发
tmux new-window -t $SESSION_NAME:1 -n 'ClaudeCode'
tmux send-keys -t $SESSION_NAME:1 "cd $PROJECT_DIR && clear" C-m
tmux send-keys -t $SESSION_NAME:1 "echo '🤖 Claude Code - 自动开发引擎'" C-m
tmux send-keys -t $SESSION_NAME:1 "echo ''" C-m
tmux send-keys -t $SESSION_NAME:1 "echo '持续运行任务发现和执行...'" C-m
tmux send-keys -t $SESSION_NAME:1 "echo ''" C-m
# 运行Claude Code（如果可用）
if command -v claude-code &> /dev/null; then
    tmux send-keys -t $SESSION_NAME:1 "claude-code --project $PROJECT_DIR --auto-loop" C-m
else
    tmux send-keys -t $SESSION_NAME:1 "echo '⚠️  Claude Code未安装，使用Python Agent代替'" C-m
    tmux send-keys -t $SESSION_NAME:1 "python3 agents/agent_manager.py --loop --interval 60" C-m
fi

# 窗口2: 任务发现
tmux new-window -t $SESSION_NAME:2 -n 'Discovery'
tmux send-keys -t $SESSION_NAME:2 "cd $PROJECT_DIR && clear" C-m
tmux send-keys -t $SESSION_NAME:2 "echo '📋 任务发现引擎'" C-m
tmux send-keys -t $SESSION_NAME:2 "echo ''" C-m
tmux send-keys -t $SESSION_NAME:2 "watch -n 60 'python3 scripts/auto-discover.sh 2>&1 | tail -20'" C-m

# 窗口3: 自动提交
tmux new-window -t $SESSION_NAME:3 -n 'GitCommit'
tmux send-keys -t $SESSION_NAME:3 "cd $PROJECT_DIR && clear" C-m
tmux send-keys -t $SESSION_NAME:3 "echo '📝 自动提交引擎'" C-m
tmux send-keys -t $SESSION_NAME:3 "echo ''" C-m
tmux send-keys -t $SESSION_NAME:3 "watch -n 300 'python3 scripts/auto-commit.sh 2>&1 | tail -10'" C-m

# 窗口4: 系统监控
tmux new-window -t $SESSION_NAME:4 -n 'Monitor'
tmux send-keys -t $SESSION_NAME:4 "cd $PROJECT_DIR && clear" C-m
tmux send-keys -t $SESSION_NAME:4 "echo '📊 系统监控'" C-m
tmux send-keys -t $SESSION_NAME:4 "echo ''" C-m
tmux send-keys -t $SESSION_NAME:4 "watch -n 30 'python3 scripts/auto-monitor.sh 2>&1 | tail -30'" C-m

# 窗口5: 实时日志
tmux new-window -t $SESSION_NAME:5 -n 'Logs'
tmux send-keys -t $SESSION_NAME:5 "cd $PROJECT_DIR && clear" C-m
tmux send-keys -t $SESSION_NAME:5 "echo '📄 实时日志'" C-m
tmux send-keys -t $SESSION_NAME:5 "echo ''" C-m
tmux send-keys -t $SESSION_NAME:5 "tail -f .devflow/logs/iteration.log" C-m

# 窗口6: 自我进化
tmux new-window -t $SESSION_NAME:6 -n 'Evolution'
tmux send-keys -t $SESSION_NAME:6 "cd $PROJECT_DIR && clear" C-m
tmux send-keys -t $SESSION_NAME:6 "echo '🧬 自我进化引擎'" C-m
tmux send-keys -t $SESSION_NAME:6 "echo ''" C-m
tmux send-keys -t $SESSION_NAME:6 "watch -n 3600 'python3 agents/evolution_engine.py 2>&1 | tail -20'" C-m

echo ""
echo "✅ DevFlow持续迭代系统已启动！"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 系统窗口:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  0: Main         - 主控制台"
echo "  1: ClaudeCode   - AI自动开发"
echo "  2: Discovery    - 任务发现"
echo "  3: GitCommit    - 自动提交"
echo "  4: Monitor      - 系统监控"
echo "  5: Logs         - 实时日志"
echo "  6: Evolution    - 自我进化"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 附加到会话:"
echo "  tmux attach -t $SESSION_NAME"
echo ""
echo "🔄 切换窗口 (在tmux中):"
echo "  Ctrl+b <窗口号>    # 例如: Ctrl+b 1"
echo "  Ctrl+b n           # 下一个窗口"
echo "  Ctrl+b p           # 上一个窗口"
echo "  Ctrl+b d           # 分离会话（后台运行）"
echo ""
echo "⏹️  停止系统:"
echo "  tmux kill-session -t $SESSION_NAME"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 系统现在正在:"
echo "  ✅ 每60秒发现新任务"
echo "  ✅ 自动执行任务"
echo "  ✅ 每5分钟提交代码"
echo "  ✅ 每30秒监控系统"
echo "  ✅ 每小时自我进化"
echo "  ✅ 24/7持续运行"
echo ""
echo "GitHub: https://github.com/sxyseo/devflow"
echo ""
