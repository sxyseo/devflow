#!/bin/bash
# DevFlow 完整启动脚本
# 一键启动持续迭代系统

PROJECT_DIR="/Users/abel/dev/devflow"

echo "🚀 DevFlow 完整启动流程"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "$PROJECT_DIR"

# 1. 检查并安装别名
if [ ! -f "$HOME/.devflow_aliases" ]; then
    echo "1️⃣ 安装命令别名..."
    ./scripts/install-aliases.sh
    source ~/.zshrc 2>/dev/null || source ~/.bashrc 2>/dev/null
    echo ""
else
    echo "✅ 别名已安装"
    echo ""
fi

# 2. 运行快速验证
echo "2️⃣ 运行系统验证..."
./verify.sh
echo ""

# 3. 显示效果验证
echo "3️⃣ 当前效果验证..."
python3 agents/effect_validator.py
echo ""

# 4. 启动tmux持续迭代
echo "4️⃣ 启动持续迭代系统..."
echo ""
read -p "是否启动tmux持续迭代? [Y/n]: " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    ./scripts/start-auto-iteration.sh
    
    echo ""
    echo "✅ 系统已启动！"
    echo ""
    echo "🎯 立即附加:"
    echo "  tmux attach -t devflow-auto"
    echo ""
    echo "📊 查看效果:"
    echo "  python3 agents/effect_validator.py"
    echo ""
    echo "📄 查看日志:"
    echo "  tail -f .devflow/logs/iteration.log"
    echo ""
    echo "🌐 GitHub:"
    echo "  https://github.com/sxyseo/devflow"
fi
