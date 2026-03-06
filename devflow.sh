#!/bin/bash
# DevFlow主控制脚本 - 一键启动所有功能

set -e

PROJECT_DIR="/Users/abel/dev/devflow"
cd "$PROJECT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

show_banner() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════╗"
    echo "║                                          ║"
    echo "║        🚀 DevFlow - AI自治开发系统        ║"
    echo "║                                          ║"
    echo "╚══════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_menu() {
    echo ""
    echo -e "${BLUE}可用命令:${NC}"
    echo ""
    echo "  ${GREEN}1.${NC} 启动完整系统（tmux后台运行）"
    echo "  ${GREEN}2.${NC} 单次运行（任务发现+执行+提交）"
    echo "  ${GREEN}3.${NC} 启动自动迭代循环"
    echo "  ${GREEN}4.${NC} 查看系统状态"
    echo "  ${GREEN}5.${NC} 查看任务列表"
    echo "  ${GREEN}6.${NC} 手动提交代码"
    echo "  ${GREEN}7.${NC} 运行测试"
    echo "  ${GREEN}8.${NC} 查看日志"
    echo "  ${GREEN}9.${NC} 停止所有进程"
    echo "  ${GREEN}0.${NC} 退出"
    echo ""
}

start_full_system() {
    echo -e "${GREEN}🚀 启动完整系统...${NC}"
    
    # 检查tmux
    if ! command -v tmux &> /dev/null; then
        echo -e "${RED}错误: tmux未安装${NC}"
        echo "安装: brew install tmux"
        exit 1
    fi
    
    # 启动tmux会话
    ./scripts/start-tmux.sh
    
    echo ""
    echo -e "${GREEN}✅ 系统已启动！${NC}"
    echo ""
    echo "附加到会话:"
    echo "  tmux attach -t devflow"
    echo ""
    echo "查看日志:"
    echo "  tail -f .devflow/logs/iteration.log"
}

run_once() {
    echo -e "${GREEN}🔄 单次运行...${NC}"
    
    echo ""
    echo "1️⃣ 发现任务..."
    python3 scripts/auto-discover.sh
    
    echo ""
    echo "2️⃣ 调度任务..."
    python3 agents/task_scheduler.py
    
    echo ""
    echo "3️⃣ 执行任务..."
    python3 agents/agent_manager.py
    
    echo ""
    echo "4️⃣ 提交代码..."
    python3 scripts/auto-commit.sh
    
    echo ""
    echo -e "${GREEN}✅ 单次运行完成！${NC}"
}

start_auto_iteration() {
    echo -e "${GREEN}🔄 启动自动迭代循环...${NC}"
    echo ""
    echo "按 Ctrl+C 停止"
    echo ""
    
    chmod +x scripts/auto-iterate.sh
    ./scripts/auto-iterate.sh
}

show_status() {
    echo -e "${GREEN}📊 系统状态...${NC}"
    
    python3 scripts/auto-monitor.sh
}

show_tasks() {
    echo -e "${GREEN}📋 任务列表...${NC}"
    
    if [ -f ".devflow/tasks/schedule.json" ]; then
        cat .devflow/tasks/schedule.json | python3 -m json.tool
    else
        echo "没有调度文件，运行任务发现..."
        python3 scripts/auto-discover.sh
    fi
}

manual_commit() {
    echo -e "${GREEN}📝 手动提交...${NC}"
    
    git status
    echo ""
    read -p "输入commit message: " message
    git add -A
    git commit -m "$message"
    git push
}

run_tests() {
    echo -e "${GREEN}🧪 运行测试...${NC}"
    
    if [ -f "pytest.ini" ] || [ -d "tests" ]; then
        pytest tests/ -v
    elif [ -f "package.json" ]; then
        npm test
    else
        echo "没有找到测试文件"
    fi
}

view_logs() {
    echo -e "${GREEN}📄 查看日志...${NC}"
    
    if [ -f ".devflow/logs/iteration.log" ]; then
        tail -f .devflow/logs/iteration.log
    else
        echo "日志文件不存在"
    fi
}

stop_all() {
    echo -e "${YELLOW}⏹️  停止所有进程...${NC}"
    
    # 停止tmux会话
    tmux kill-session -t devflow 2>/dev/null || true
    
    # 停止所有Python进程
    pkill -f "python3.*devflow" 2>/dev/null || true
    
    echo -e "${GREEN}✅ 所有进程已停止${NC}"
}

# 主循环
show_banner

while true; do
    show_menu
    read -p "选择操作 [0-9]: " choice
    
    case $choice in
        1)
            start_full_system
            ;;
        2)
            run_once
            ;;
        3)
            start_auto_iteration
            ;;
        4)
            show_status
            ;;
        5)
            show_tasks
            ;;
        6)
            manual_commit
            ;;
        7)
            run_tests
            ;;
        8)
            view_logs
            ;;
        9)
            stop_all
            ;;
        0)
            echo -e "${GREEN}再见！${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}无效选择${NC}"
            ;;
    esac
done
