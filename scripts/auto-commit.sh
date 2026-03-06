#!/usr/bin/env python3
"""
DevFlow - 自动提交引擎
自动提交代码到Git
"""

import os
import subprocess
import json
from pathlib import Path
from datetime import datetime

class AutoCommitter:
    """自动提交器"""
    
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.git_dir = self.project_path / '.git'
        
        if not self.git_dir.exists():
            raise Exception("不是Git仓库")
    
    def has_changes(self):
        """检查是否有变更"""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            return len(result.stdout.strip()) > 0
        except Exception as e:
            print(f"❌ 检查Git状态失败: {e}")
            return False
    
    def get_changes_summary(self):
        """获取变更摘要"""
        try:
            result = subprocess.run(
                ['git', 'status', '--short'],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except Exception as e:
            return ""
    
    def generate_commit_message(self):
        """生成提交消息"""
        summary = self.get_changes_summary()
        
        if not summary:
            return "chore: 自动提交"
        
        lines = summary.split('\n')
        
        # 统计变更类型
        added = len([l for l in lines if l.startswith('??') or l.startswith('A')])
        modified = len([l for l in lines if l.startswith(' M') or l.startswith('M')])
        deleted = len([l for l in lines if l.startswith(' D') or l.startswith('D')])
        
        # 生成消息
        parts = []
        if added > 0:
            parts.append(f"+{added} 文件")
        if modified > 0:
            parts.append(f"~{modified} 文件")
        if deleted > 0:
            parts.append(f"-{deleted} 文件")
        
        change_summary = ' '.join(parts)
        
        # 根据变更类型生成前缀
        if modified > added and modified > deleted:
            prefix = "feat"
        elif added > modified:
            prefix = "feat"
        elif deleted > 0:
            prefix = "refactor"
        else:
            prefix = "chore"
        
        return f"{prefix}: {change_summary} [auto-commit]"
    
    def commit(self):
        """执行提交"""
        if not self.has_changes():
            print("ℹ️  没有变更需要提交")
            return False
        
        print("📝 自动提交...")
        
        # 添加所有变更
        try:
            subprocess.run(
                ['git', 'add', '-A'],
                cwd=self.project_path,
                check=True
            )
            print("  ✅ 已添加所有变更")
        except Exception as e:
            print(f"  ❌ 添加变更失败: {e}")
            return False
        
        # 生成提交消息
        message = self.generate_commit_message()
        print(f"  💬 提交消息: {message}")
        
        # 提交
        try:
            subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=self.project_path,
                check=True
            )
            print("  ✅ 提交成功")
        except Exception as e:
            print(f"  ❌ 提交失败: {e}")
            return False
        
        # 推送
        try:
            subprocess.run(
                ['git', 'push'],
                cwd=self.project_path,
                check=True,
                timeout=30
            )
            print("  ✅ 推送成功")
        except subprocess.TimeoutExpired:
            print("  ⚠️  推送超时，跳过")
        except Exception as e:
            print(f"  ⚠️  推送失败: {e}")
        
        # 记录提交日志
        self.log_commit(message)
        
        return True
    
    def log_commit(self, message):
        """记录提交日志"""
        log_dir = self.project_path / '.devflow' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / 'commits.json'
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'changes': self.get_changes_summary()
        }
        
        # 读取现有日志
        logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            except:
                pass
        
        # 添加新日志
        logs.append(log_entry)
        
        # 保存日志（保留最近100条）
        logs = logs[-100:]
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)

if __name__ == '__main__':
    try:
        committer = AutoCommitter('/Users/abel/dev/devflow')
        committer.commit()
    except Exception as e:
        print(f"❌ 错误: {e}")
