#!/bin/bash
# 一键修复权限问题

echo "🔧 修复权限问题..."
echo ""

# 修复主脚本
if [ -f "devflow.sh" ]; then
    chmod +x devflow.sh
    echo "  ✅ devflow.sh"
fi

# 修复所有shell脚本
for script in scripts/*.sh; do
    if [ -f "$script" ]; then
        chmod +x "$script"
        echo "  ✅ $script"
    fi
done

# 修复Python脚本
for script in scripts/*.py; do
    if [ -f "$script" ]; then
        chmod +x "$script"
        echo "  ✅ $script"
    fi
done

# 修复Agent脚本
for agent in agents/*.py; do
    if [ -f "$agent" ]; then
        chmod +x "$agent"
        echo "  ✅ $agent"
    fi
done

echo ""
echo "✅ 权限已修复！"
echo ""
echo "现在你可以运行:"
echo "  ./devflow.sh"
