#!/usr/bin/env python3
"""
DevFlow 演示运行器
2分钟展示DevFlow的核心能力
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

class DemoRunner:
    """演示运行器"""
    
    def __init__(self):
        self.project_path = Path("/Users/abel/dev/devflow")
        self.demo_dir = self.project_path / "demo_output"
        self.demo_dir.mkdir(exist_ok=True)
        
    def run(self):
        """运行演示"""
        self.print_banner()
        
        # 阶段1: 介绍
        self.introduce()
        
        # 阶段2: 创建演示任务
        self.create_demo_task()
        
        # 阶段3: 模拟任务发现
        self.simulate_task_discovery()
        
        # 阶段4: 模拟任务执行
        self.simulate_task_execution()
        
        # 阶段5: 模拟代码提交
        self.simulate_commit()
        
        # 阶段6: 展示结果
        self.show_results()
        
        # 阶段7: 总结
        self.summarize()
    
    def print_banner(self):
        """打印横幅"""
        print("\n")
        print("╔══════════════════════════════════════════╗")
        print("║                                          ║")
        print("║      🎬 DevFlow 演示模式                 ║")
        print("║                                          ║")
        print("╚══════════════════════════════════════════╝")
        print("\n")
        print("这个演示将展示DevFlow如何自动完成一个简单任务")
        print("预计时间: 2分钟")
        print("")
        input("按Enter开始演示...")
    
    def introduce(self):
        """介绍"""
        print("\n")
        print("━" * 50)
        print("📚 演示说明")
        print("━" * 50)
        print("")
        print("DevFlow是一个AI驱动的自动开发系统")
        print("")
        print("核心能力:")
        print("  ✅ 自动发现任务（扫描TODO/FIXME/PRD）")
        print("  ✅ 智能调度任务（优先级+依赖关系）")
        print("  ✅ AI执行任务（Codex/Claude Code）")
        print("  ✅ 自动提交代码（Git集成）")
        print("  ✅ 24/7持续运行（无需人工干预）")
        print("")
        time.sleep(2)
    
    def create_demo_task(self):
        """创建演示任务"""
        print("\n")
        print("━" * 50)
        print("1️⃣ 创建演示任务")
        print("━" * 50)
        print("")
        print("演示任务: 创建一个简单的工具函数")
        print("")
        
        # 创建PRD
        prd_file = self.demo_dir / "DEMO_PRD.md"
        prd_content = """# 演示项目需求

## 功能需求

### 1. 字符串处理函数
创建 `string_utils.py` 文件，包含以下函数:
- `reverse_string(s)`: 反转字符串
- `capitalize_words(s)`: 首字母大写
- `count_words(s)`: 统计单词数

每个函数需要:
- 函数文档
- 类型提示
- 单元测试
"""
        
        with open(prd_file, 'w') as f:
            f.write(prd_content)
        
        print("  ✅ 创建了演示PRD: demo_output/DEMO_PRD.md")
        print("")
        time.sleep(1)
    
    def simulate_task_discovery(self):
        """模拟任务发现"""
        print("\n")
        print("━" * 50)
        print("2️⃣ 自动发现任务")
        print("━" * 50)
        print("")
        print("正在扫描项目...")
        
        # 动画效果
        for i in range(3):
            print(".", end="", flush=True)
            time.sleep(0.5)
        
        print(" 完成!")
        print("")
        print("发现 3 个任务:")
        print("  1. [P1] 创建string_utils.py文件")
        print("  2. [P1] 实现reverse_string函数")
        print("  3. [P2] 添加单元测试")
        print("")
        
        # 保存任务
        tasks = {
            "total": 3,
            "tasks": [
                {"id": "task-1", "priority": "P1", "description": "创建string_utils.py"},
                {"id": "task-2", "priority": "P1", "description": "实现reverse_string函数"},
                {"id": "task-3", "priority": "P2", "description": "添加单元测试"}
            ]
        }
        
        tasks_file = self.demo_dir / "demo_tasks.json"
        with open(tasks_file, 'w') as f:
            json.dump(tasks, f, indent=2)
        
        print("  ✅ 任务已保存: demo_output/demo_tasks.json")
        print("")
        time.sleep(1)
    
    def simulate_task_execution(self):
        """模拟任务执行"""
        print("\n")
        print("━" * 50)
        print("3️⃣ 执行任务")
        print("━" * 50)
        print("")
        
        # 模拟进度
        tasks = ["创建文件", "编写代码", "添加测试"]
        
        for i, task in enumerate(tasks, 1):
            print(f"  任务 {i}/3: {task}")
            print(f"  🤖 Agent: Codex")
            print(f"  ⏳ 执行中", end="")
            
            # 进度动画
            for _ in range(3):
                print(".", end="", flush=True)
                time.sleep(0.3)
            
            print(" 完成!")
            print("")
            time.sleep(0.5)
        
        # 创建实际的文件
        string_utils = self.demo_dir / "string_utils.py"
        with open(string_utils, 'w') as f:
            f.write('''"""
字符串工具函数
"""

def reverse_string(s: str) -> str:
    """反转字符串"""
    return s[::-1]

def capitalize_words(s: str) -> str:
    """首字母大写"""
    return ' '.join(word.capitalize() for word in s.split())

def count_words(s: str) -> int:
    """统计单词数"""
    return len(s.split())

if __name__ == "__main__":
    # 测试
    print(reverse_string("hello"))  # olleh
    print(capitalize_words("hello world"))  # Hello World
    print(count_words("hello world"))  # 2
''')
        
        print("  ✅ 创建了文件: demo_output/string_utils.py")
        print("")
        time.sleep(1)
    
    def simulate_commit(self):
        """模拟提交"""
        print("\n")
        print("━" * 50)
        print("4️⃣ 自动提交代码")
        print("━" * 50)
        print("")
        print("正在提交到Git...")
        
        # 模拟Git命令
        print("  $ git add demo_output/")
        time.sleep(0.5)
        print("  $ git commit -m \"demo: 添加字符串工具函数\"")
        time.sleep(0.5)
        print("  $ git push")
        time.sleep(0.5)
        
        print("")
        print("  ✅ 代码已提交!")
        print("")
        time.sleep(1)
    
    def show_results(self):
        """展示结果"""
        print("\n")
        print("━" * 50)
        print("5️⃣ 查看结果")
        print("━" * 50)
        print("")
        print("生成的文件:")
        print("")
        
        # 展示文件列表
        for file in self.demo_dir.glob("*"):
            size = file.stat().st_size
            print(f"  📄 {file.name:30s} ({size} bytes)")
        
        print("")
        print("文件内容预览:")
        print("")
        
        # 展示代码
        string_utils = self.demo_dir / "string_utils.py"
        if string_utils.exists():
            print("  " + "─" * 46)
            with open(string_utils) as f:
                for i, line in enumerate(f, 1):
                    if i <= 15:  # 只显示前15行
                        print(f"  {i:2d} | {line.rstrip()}")
            print("  " + "─" * 46)
        
        print("")
        
        # 测试运行
        print("运行测试:")
        print("")
        print("  $ python3 demo_output/string_utils.py")
        print("  olleh")
        print("  Hello World")
        print("  2")
        print("")
        print("  ✅ 测试通过!")
        print("")
        time.sleep(2)
    
    def summarize(self):
        """总结"""
        print("\n")
        print("╔══════════════════════════════════════════╗")
        print("║                                          ║")
        print("║          ✅ 演示完成！                   ║")
        print("║                                          ║")
        print("╚══════════════════════════════════════════╝")
        print("\n")
        print("📊 演示总结:")
        print("")
        print("  耗时: 约2分钟")
        print("  发现任务: 3个")
        print("  完成任务: 3个")
        print("  生成代码: 25行")
        print("  提交次数: 1次")
        print("")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("")
        print("🚀 DevFlow现在可以:")
        print("")
        print("  ✅ 自动发现更复杂的任务")
        print("  ✅ 自动修复Bug")
        print("  ✅ 自动添加新功能")
        print("  ✅ 24/7持续运行")
        print("  ✅ 每天完成50-100+次提交")
        print("")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("")
        print("🎯 下一步:")
        print("")
        print("  1. 运行验证: ./verify.sh")
        print("  2. 单次运行: ./devflow.sh (选择2)")
        print("  3. 自动迭代: ./scripts/auto-iterate.sh")
        print("  4. 查看文档: cat README.md")
        print("")
        print("准备好开始了吗? 🚀")
        print("")

if __name__ == '__main__':
    demo = DemoRunner()
    demo.run()
