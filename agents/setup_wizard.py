#!/usr/bin/env python3
"""
DevFlow 配置向导
首次运行时的交互式配置
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Optional

class SetupWizard:
    """配置向导"""
    
    def __init__(self, project_path: str = "/Users/abel/dev/devflow"):
        self.project_path = Path(project_path)
        self.env_file = self.project_path / '.env'
        self.config_file = self.project_path / 'config' / 'user_config.json'
        
    def run(self):
        """运行配置向导"""
        self.print_welcome()
        
        # 检查是否已配置
        if self.env_file.exists() and self.config_file.exists():
            print("\nℹ️  检测到已有配置")
            choice = input("是否重新配置? [y/N]: ").strip().lower()
            if choice != 'y':
                print("✅ 使用现有配置")
                return
        
        # 步骤1: 检查依赖
        if not self.check_dependencies():
            return
        
        # 步骤2: 配置API密钥
        self.configure_api_keys()
        
        # 步骤3: 选择默认Agent
        self.configure_default_agent()
        
        # 步骤4: 配置自动提交
        self.configure_auto_commit()
        
        # 步骤5: 完成设置
        self.complete_setup()
    
    def print_welcome(self):
        """打印欢迎信息"""
        print("\n")
        print("╔══════════════════════════════════════════╗")
        print("║                                          ║")
        print("║        🚀 DevFlow 配置向导               ║")
        print("║                                          ║")
        print("╚══════════════════════════════════════════╝")
        print("\n")
        print("这个向导将帮助你完成初始配置（大约2分钟）\n")
    
    def check_dependencies(self) -> bool:
        """检查依赖"""
        print("\n1️⃣ 检查依赖...")
        print("")
        
        all_ok = True
        
        # Python
        if self.check_command('python3 --version'):
            print("  ✅ Python 3")
        else:
            print("  ❌ Python 3 未安装")
            all_ok = False
        
        # Git
        if self.check_command('git --version'):
            print("  ✅ Git")
        else:
            print("  ❌ Git 未安装")
            all_ok = False
        
        # tmux
        if self.check_command('tmux -V'):
            print("  ✅ tmux")
        else:
            print("  ⚠️  tmux 未安装（可选）")
        
        if not all_ok:
            print("\n❌ 请先安装缺失的依赖")
            return False
        
        print("\n  ✅ 依赖检查通过")
        return True
    
    def check_command(self, command: str) -> bool:
        """检查命令是否可用"""
        try:
            subprocess.run(
                command.split(),
                capture_output=True,
                check=True
            )
            return True
        except Exception:
            return False
    
    def configure_api_keys(self):
        """配置API密钥"""
        print("\n2️⃣ 配置API密钥...")
        print("")
        print("  DevFlow需要API密钥来调用AI服务")
        print("")
        
        env_vars = {}
        
        # OpenAI API Key
        openai_key = input("  OpenAI API Key (可选): ").strip()
        if openai_key:
            env_vars['OPENAI_API_KEY'] = openai_key
            print("    ✅ 已保存")
        
        # Anthropic API Key
        anthropic_key = input("  Anthropic API Key (可选): ").strip()
        if anthropic_key:
            env_vars['ANTHROPIC_API_KEY'] = anthropic_key
            print("    ✅ 已保存")
        
        # 保存到.env文件
        if env_vars:
            with open(self.env_file, 'w') as f:
                for key, value in env_vars.items():
                    f.write(f"{key}={value}\n")
            
            print(f"\n  ✅ 已保存到 {self.env_file}")
            print("  ⚠️  请勿将.env文件提交到Git")
        else:
            print("\n  ℹ️  跳过API密钥配置（可以稍后手动配置）")
    
    def configure_default_agent(self):
        """配置默认Agent"""
        print("\n3️⃣ 选择默认Agent...")
        print("")
        print("  [1] Codex (推荐用于Bug修复)")
        print("  [2] Claude Code (推荐用于新功能)")
        print("  [3] 混合使用（根据任务类型自动选择）")
        print("")
        
        choice = input("  选择 [1-3, 默认3]: ").strip() or '3'
        
        agent_map = {
            '1': 'codex',
            '2': 'claude-code',
            '3': 'hybrid'
        }
        
        selected_agent = agent_map.get(choice, 'hybrid')
        
        config = self.load_config()
        config['default_agent'] = selected_agent
        
        self.save_config(config)
        
        print(f"\n  ✅ 已选择: {selected_agent}")
    
    def configure_auto_commit(self):
        """配置自动提交"""
        print("\n4️⃣ 设置自动提交...")
        print("")
        
        commit_interval = input("  自动提交间隔（分钟）[5]: ").strip() or '5'
        
        push_choice = input("  自动推送到GitHub? [Y/n]: ").strip().lower()
        auto_push = push_choice != 'n'
        
        config = self.load_config()
        config['auto_commit'] = {
            'enabled': True,
            'interval_minutes': int(commit_interval),
            'auto_push': auto_push
        }
        
        self.save_config(config)
        
        print(f"\n  ✅ 每{commit_interval}分钟自动提交")
        if auto_push:
            print("  ✅ 自动推送到GitHub")
    
    def load_config(self) -> dict:
        """加载配置"""
        if self.config_file.exists():
            with open(self.config_file) as f:
                return json.load(f)
        return {}
    
    def save_config(self, config: dict):
        """保存配置"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def complete_setup(self):
        """完成设置"""
        print("\n")
        print("╔══════════════════════════════════════════╗")
        print("║                                          ║")
        print("║          ✅ 配置完成！                   ║")
        print("║                                          ║")
        print("╚══════════════════════════════════════════╝")
        print("\n")
        print("现在你可以运行:")
        print("")
        print("  devflow run      # 开始自动开发")
        print("  devflow demo     # 查看演示")
        print("  devflow help     # 查看帮助")
        print("")
        
        # 添加到Git忽略
        gitignore = self.project_path / '.gitignore'
        if gitignore.exists():
            with open(gitignore, 'a') as f:
                f.write('\n# DevFlow\n')
                f.write('.env\n')
                f.write('.devflow/\n')
        
        print("💡 提示: .env已添加到.gitignore\n")

if __name__ == '__main__':
    wizard = SetupWizard()
    wizard.run()
