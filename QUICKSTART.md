# DevFlow 快速开始指南

## 🚀 5分钟快速启动

### 1. 初始化项目

```bash
cd /Users/abel/dev/devflow

# 初始化Git仓库
git init
git add .
git commit -m "feat: 初始化DevFlow项目"

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp config/.env.example config/.env

# 编辑配置
vim config/.env
```

必需的环境变量：
```bash
# OpenAI API（用于Codex）
OPENAI_API_KEY=sk-...

# Anthropic API（用于Claude Code）
ANTHROPIC_API_KEY=sk-ant-...

# 飞书通知（可选）
FEISHU_WEBHOOK=https://...

# GitHub Token（自动推送）
GITHUB_TOKEN=ghp_...
```

### 3. 启动系统

```bash
# 方式1: 使用tmux（推荐）
chmod +x scripts/start-tmux.sh
./scripts/start-tmux.sh

# 方式2: 单独启动
python3 scripts/auto-discover.sh  # 任务发现
python3 scripts/auto-commit.sh    # 自动提交
python3 scripts/auto-monitor.sh   # 系统监控
```

### 4. 访问Dashboard

```bash
cd dashboard
npm install
npm run dev
```

打开浏览器: http://localhost:5173

## 📋 使用场景

### 场景1: 新项目开发

```bash
# 1. 创建PRD文档
cat > PRD.md << 'EOF'
# 贪吃蛇大作战

## 功能需求
- 用户登录
- 多人在线对战
- 实时排行榜
EOF

# 2. 启动自动开发
python3 -c "
from skills.taskmaster import TaskMaster
tm = TaskMaster('PRD.md')
tasks = tm.generate_tasks()
print(f'生成了 {len(tasks)} 个任务')
"

# 3. 查看任务
cat .devflow/tasks/tasks-*.json | jq '.total'
```

### 场景2: 持续维护

```bash
# 启动持续监控（每5分钟检查一次）
watch -n 300 'python3 scripts/auto-discover.sh'

# 或者在tmux中运行
tmux new -d -s monitor 'python3 scripts/auto-monitor.sh'
```

### 场景3: 并行开发

```bash
# 启动4个并行Agent
python3 -c "
from skills.symphony import SymphonyExecutor
symphony = SymphonyExecutor(max_workers=4)
symphony.start()
"
```

## 🎯 核心命令

| 命令 | 说明 |
|------|------|
| `./scripts/start-tmux.sh` | 启动tmux会话 |
| `python3 scripts/auto-discover.sh` | 发现任务 |
| `python3 scripts/auto-commit.sh` | 自动提交 |
| `python3 scripts/auto-monitor.sh` | 系统监控 |
| `tmux attach -t devflow` | 附加到会话 |
| `tmux kill-session -t devflow` | 停止会话 |

## 📊 监控指标

访问 http://localhost:5173 查看：

- ✅ 系统健康度
- 📊 任务完成率
- ⏱️ 平均执行时间
- 🤖 Agent状态
- 📈 提交统计

## 🔧 故障排查

### 问题1: tmux启动失败

```bash
# 检查tmux是否安装
which tmux

# 安装tmux
brew install tmux
```

### 问题2: 任务发现为空

```bash
# 检查项目结构
ls -la

# 确保有代码文件
find . -name "*.py" -o -name "*.js" | head

# 手动运行发现
python3 scripts/auto-discover.sh
```

### 问题3: 自动提交失败

```bash
# 检查Git配置
git config user.name
git config user.email

# 检查远程仓库
git remote -v

# 测试推送
git push
```

## 📚 下一步

- [阅读完整文档](./README.md)
- [了解架构设计](./docs/ARCHITECTURE.md)
- [配置高级功能](./docs/CONFIGURATION.md)
- [加入社区](https://discord.gg/clawd)

---

**遇到问题？** 
- 查看 [故障排查指南](./docs/TROUBLESHOOTING.md)
- 提交 [Issue](https://github.com/your-repo/devflow/issues)
- 加入 [Discord社区](https://discord.gg/clawd)
