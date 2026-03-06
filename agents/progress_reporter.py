#!/usr/bin/env python3
"""
DevFlow 进度显示器
实时显示任务执行进度
"""

import sys
import time
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class ProgressTask:
    """进度任务"""
    name: str
    total: int = 0
    completed: int = 0
    status: str = 'pending'  # pending, running, completed, failed
    
    @property
    def percent(self) -> float:
        if self.total == 0:
            return 0
        return (self.completed / self.total) * 100

class ProgressReporter:
    """进度报告器"""
    
    def __init__(self):
        self.tasks: Dict[str, ProgressTask] = {}
        self.start_time = datetime.now()
        
    def add_task(self, name: str, total: int = 0):
        """添加任务"""
        self.tasks[name] = ProgressTask(name=name, total=total)
    
    def update_task(self, name: str, completed: int, status: str = None):
        """更新任务进度"""
        if name in self.tasks:
            self.tasks[name].completed = completed
            if status:
                self.tasks[name].status = status
    
    def render_progress_bar(self, percent: float, width: int = 30) -> str:
        """渲染进度条"""
        filled = int(width * (percent / 100))
        empty = width - filled
        
        bar = '█' * filled + '░' * empty
        return f"[{bar}] {percent:5.1f}%"
    
    def estimate_remaining_time(self) -> str:
        """估算剩余时间"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        # 计算总体进度
        total_tasks = len(self.tasks)
        if total_tasks == 0:
            return "计算中..."
        
        completed_tasks = sum(1 for t in self.tasks.values() if t.status == 'completed')
        if completed_tasks == 0:
            return "计算中..."
        
        # 估算
        avg_time_per_task = elapsed / completed_tasks
        remaining_tasks = total_tasks - completed_tasks
        remaining_seconds = avg_time_per_task * remaining_tasks
        
        if remaining_seconds < 60:
            return f"{int(remaining_seconds)}秒"
        elif remaining_seconds < 3600:
            return f"{int(remaining_seconds / 60)}分钟"
        else:
            return f"{int(remaining_seconds / 3600)}小时"
    
    def render(self) -> str:
        """渲染完整进度报告"""
        lines = []
        
        # 标题
        lines.append("⏳ 任务执行中...")
        lines.append("━" * 50)
        
        # 各阶段进度
        stage_order = [
            ('发现任务', 'discover'),
            ('调度任务', 'schedule'),
            ('执行任务', 'execute'),
            ('提交代码', 'commit')
        ]
        
        status_emoji = {
            'pending': '⏳',
            'running': '🔄',
            'completed': '✅',
            'failed': '❌'
        }
        
        for display_name, task_key in stage_order:
            if task_key in self.tasks:
                task = self.tasks[task_key]
                emoji = status_emoji.get(task.status, '⏳')
                bar = self.render_progress_bar(task.percent)
                
                if task.total > 0:
                    lines.append(f"{emoji} {display_name:12s} {bar} ({task.completed}/{task.total})")
                else:
                    lines.append(f"{emoji} {display_name:12s} {bar}")
        
        # 底部信息
        lines.append("━" * 50)
        lines.append(f"⏰ 预计剩余时间: {self.estimate_remaining_time()}")
        
        return '\n'.join(lines)
    
    def print(self):
        """打印进度（覆盖之前的内容）"""
        # 清除之前的输出
        sys.stdout.write('\033[F' * 10)  # 上移10行
        sys.stdout.write('\033[J')  # 清除到末尾
        
        # 打印新的进度
        print(self.render())
    
    def start_animation(self):
        """开始动画（演示用）"""
        # 初始化任务
        self.add_task('discover', total=10)
        self.add_task('schedule', total=5)
        self.add_task('execute', total=10)
        self.add_task('commit', total=3)
        
        print(self.render())
        
        # 模拟进度
        for i in range(11):
            time.sleep(0.3)
            self.update_task('discover', i, 'running' if i < 10 else 'completed')
            self.print()
        
        for i in range(6):
            time.sleep(0.2)
            self.update_task('schedule', i, 'running' if i < 5 else 'completed')
            self.print()
        
        for i in range(11):
            time.sleep(0.5)
            self.update_task('execute', i, 'running' if i < 10 else 'completed')
            self.print()
        
        for i in range(4):
            time.sleep(0.3)
            self.update_task('commit', i, 'running' if i < 3 else 'completed')
            self.print()
        
        print("\n✅ 所有任务完成！")

class SimpleProgress:
    """简单进度条（单行）"""
    
    @staticmethod
    def show(description: str, current: int, total: int):
        """显示单行进度"""
        percent = (current / total * 100) if total > 0 else 0
        bar_width = 40
        filled = int(bar_width * (percent / 100))
        bar = '█' * filled + '░' * (bar_width - filled)
        
        sys.stdout.write(f'\r{description}: {bar} {percent:.1f}% ({current}/{total})')
        sys.stdout.flush()
        
        if current == total:
            print()  # 完成后换行

if __name__ == '__main__':
    print("🧪 测试进度显示器\n")
    
    # 测试完整进度报告
    reporter = ProgressReporter()
    reporter.start_animation()
    
    print("\n" + "━" * 60)
    print("测试简单进度条\n")
    
    # 测试简单进度条
    for i in range(101):
        SimpleProgress.show("下载文件", i, 100)
        time.sleep(0.02)
