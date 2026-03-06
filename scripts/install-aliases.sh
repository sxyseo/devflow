#!/bin/bash
# DevFlow 命令别名安装脚本

ALIASES_FILE="$HOME/.devflow_aliases"
SHELL_RC=""

# 检测shell类型
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
else
    echo "⚠️  未检测到支持的shell (bash/zsh)"
    exit 1
fi

echo "🚀 DevFlow 命令别名安装"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 定义别名
cat > "$ALIASES_FILE" << 'EOF'
# DevFlow 命令别名
# 安装时间: $(date)

# 基础命令
alias df='/Users/abel/dev/devflow/devflow.sh'
alias devflow='/Users/abel/dev/devflow/devflow.sh'

# 快捷命令
alias dfr='cd /Users/abel/dev/devflow && ./devflow.sh <<< "2"'  # 单次运行
alias dfs='cd /Users/abel/dev/devflow && python3 scripts/auto-monitor.sh'  # 查看状态
alias dfi='cd /Users/abel/dev/devflow && ./scripts/auto-iterate.sh'  # 自动迭代
alias dft='cd /Users/abel/dev/devflow && pytest tests/ -v 2>/dev/null || npm test 2>/dev/null'  # 运行测试
alias dfc='cd /Users/abel/dev/devflow && python3 scripts/auto-commit.sh'  # 提交代码
alias dfp='cd /Users/abel/dev/devflow && ./scripts/fix-permissions.sh'  # 修复权限

# Git快捷命令
alias dfg='cd /Users/abel/dev/devflow && git status'
alias dfl='cd /Users/abel/dev/devflow && git log --oneline -10'
alias dfpush='cd /Users/abel/dev/devflow && git push'

# 日志和监控
alias dflog='tail -f /Users/abel/dev/devflow/.devflow/logs/iteration.log'
alias dftask='cat /Users/abel/dev/devflow/.devflow/tasks/schedule.json | python3 -m json.tool'

# 配置和帮助
alias dfsetup='cd /Users/abel/dev/devflow && python3 agents/setup_wizard.py'
alias dfhelp='cat /Users/abel/dev/devflow/README.md | less'
alias dfdoc='open https://github.com/sxyseo/devflow'

# 验证和测试
alias dfverify='cd /Users/abel/dev/devflow && ./verify.sh'
alias dftest='cd /Users/abel/dev/devflow && python3 -m pytest tests/ -v'

echo "✅ DevFlow别名已加载"
EOF

echo "✅ 别名文件已创建: $ALIASES_FILE"
echo ""

# 添加到shell配置
if ! grep -q "devflow_aliases" "$SHELL_RC"; then
    echo "" >> "$SHELL_RC"
    echo "# DevFlow aliases" >> "$SHELL_RC"
    echo "[ -f ~/.devflow_aliases ] && source ~/.devflow_aliases" >> "$SHELL_RC"
    echo "✅ 已添加到 $SHELL_RC"
else
    echo "ℹ️  $SHELL_RC 已包含DevFlow别名"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 可用别名:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "基础命令:"
echo "  df          devflow (主命令)"
echo "  dfr         devflow run (单次运行)"
echo "  dfs         devflow status (查看状态)"
echo "  dfi         devflow iterate (自动迭代)"
echo ""
echo "快捷操作:"
echo "  dft         运行测试"
echo "  dfc         提交代码"
echo "  dfp         修复权限"
echo "  dfg         Git状态"
echo "  dfl         Git日志"
echo "  dflog       查看日志"
echo "  dftask      查看任务"
echo ""
echo "帮助和配置:"
echo "  dfsetup     配置向导"
echo "  dfhelp      查看帮助"
echo "  dfdoc       打开文档"
echo "  dfverify    验证系统"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔄 重新加载shell配置:"
echo "  source $SHELL_RC"
echo ""
echo "或者重启终端"
echo ""
echo "✅ 安装完成！"
