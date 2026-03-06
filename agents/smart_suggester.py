#!/usr/bin/env python3
"""
DevFlow 智能建议器
根据系统状态智能建议下一步操作
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class SmartSuggester:
    """智能建议系统"""
    
    def __init__(self, project_path: str = "/Users/abel/dev/devflow"):
        self.project_path = Path(project_path)
        self.status_file = self.project_path / '.devflow' / 'status.json'
        self.tasks_dir = self.project_path / '.devflow' / 'tasks'
        
    def analyze_system_state(self) -> dict:
        """分析系统状态"""
        state = {
            'has_pending_tasks': False,
            'pending_task_count': 0,
            'has_failed_tasks': False,
            'failed_task_count': 0,
            'last_run_time': None,
            'git_status': 'clean',
            'system_health': 'unknown'
        }
        
        # 检查待处理任务
        if self.status_file.exists():
            with open(self.status_file) as f:
                status = json.load(f)
                state['pending_task_count'] = status.get('pending', 0)
                state['has_pending_tasks'] = state['pending_task_count'] > 0
                state['failed_task_count'] = status.get('failed', 0)
                state['has_failed_tasks'] = state['failed_task_count'] > 0
        
        # 检查Git状态
        import subprocess
        try:
            result = subprocess.run(
                ['git', 'status', '--short'],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            changes = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            state['git_status'] = 'dirty' if changes > 0 else 'clean'
            state['uncommitted_changes'] = changes
        except Exception:
            pass
        
        return state
    
    def generate_suggestions(self) -> List[dict]:
        """生成智能建议"""
        state = self.analyze_system_state()
        suggestions = []
        
        # 优先级1: 有待处理任务
        if state['has_pending_tasks']:
            suggestions.append({
                'priority': 1,
                'command': 'devflow run',
                'description': f"执行 {state['pending_task_count']} 个待处理任务",
                'icon': '🚀',
                'estimated_time': f"{state['pending_task_count'] * 5} 分钟"
            })
        
        # 优先级2: 有失败任务
        if state['has_failed_tasks']:
            suggestions.append({
                'priority': 2,
                'command': 'devflow fix',
                'description': f"修复 {state['failed_task_count']} 个失败任务",
                'icon': '🔧',
                'estimated_time': '10 分钟'
            })
        
        # 优先级3: 有未提交变更
        if state.get('uncommitted_changes', 0) > 0:
            suggestions.append({
                'priority': 3,
                'command': 'devflow commit',
                'description': f"提交 {state['uncommitted_changes']} 个文件变更",
                'icon': '📝',
                'estimated_time': '1 分钟'
            })
        
        # 优先级4: 系统长时间未运行
        if state.get('last_run_time'):
            last_run = datetime.fromisoformat(state['last_run_time'])
            hours_since = (datetime.now() - last_run).total_seconds() / 3600
            
            if hours_since > 1:
                suggestions.append({
                    'priority': 4,
                    'command': 'devflow iterate',
                    'description': f"启动自动迭代（已 {int(hours_since)} 小时未运行）",
                    'icon': '🔄',
                    'estimated_time': '持续运行'
                })
        
        # 优先级5: 查看状态
        suggestions.append({
            'priority': 5,
            'command': 'devflow status',
            'description': '查看系统详细状态',
            'icon': '📊',
            'estimated_time': '10 秒'
        })
        
        # 优先级6: 查看文档
        suggestions.append({
            'priority': 6,
            'command': 'devflow help',
            'description': '查看帮助文档',
            'icon': '📖',
            'estimated_time': '1 分钟'
        })
        
        # 按优先级排序
        return sorted(suggestions, key=lambda x: x['priority'])
    
    def render_suggestions(self) -> str:
        """渲染建议列表"""
        suggestions = self.generate_suggestions()
        state = self.analyze_system_state()
        
        lines = []
        
        # 系统状态概览
        lines.append("📊 系统状态:")
        lines.append(f"  {'✅' if state['pending_task_count'] > 0 else 'ℹ️ '} {state['pending_task_count']} 个待处理任务")
        lines.append(f"  {'⚠️ ' if state['has_failed_tasks'] else '✅ '} {state['failed_task_count']} 个失败任务")
        lines.append(f"  {'📝' if state.get('uncommitted_changes', 0) > 0 else '✅ '} {state.get('uncommitted_changes', 0)} 个未提交变更")
        lines.append("")
        
        # 建议列表
        lines.append("💡 建议操作:")
        for sugg in suggestions:
            lines.append(f"  {sugg['icon']} {sugg['command']:20s} # {sugg['description']}")
        
        lines.append("")
        lines.append("选择操作 [0-9]: ")
        
        return '\n'.join(lines)
    
    def get_next_action(self) -> Optional[dict]:
        """获取最优先的下一步操作"""
        suggestions = self.generate_suggestions()
        return suggestions[0] if suggestions else None
    
    def explain_command(self, command: str) -> str:
        """解释命令的作用"""
        explanations = {
            'devflow run': """
🚀 devflow run - 执行任务

这个命令会:
1. 扫描项目发现待处理任务
2. 智能调度任务优先级
3. 调用AI Agent执行任务
4. 自动提交完成的代码

适合场景:
- 有新需求要实现
- 有Bug要修复
- 有TODO要完成
""",
            'devflow status': """
📊 devflow status - 查看状态

这个命令会显示:
- 系统健康度评分
- Agent运行状态
- 任务队列情况
- Git仓库状态
- 最近提交历史

适合场景:
- 想了解系统运行情况
- 检查是否有错误
- 查看进度
""",
            'devflow iterate': """
🔄 devflow iterate - 自动迭代

这个命令会:
1. 每60秒自动循环
2. 持续发现和执行任务
3. 自动提交代码
4. 24/7不间断运行

适合场景:
- 希望系统自动工作
- 长期项目维护
- 持续集成
"""
        }
        
        return explanations.get(command, f"命令: {command}")

if __name__ == '__main__':
    print("🧪 测试智能建议器\n")
    
    suggester = SmartSuggester()
    
    # 显示建议
    print(suggester.render_suggestions())
    
    # 获取最优先的操作
    next_action = suggester.get_next_action()
    if next_action:
        print(f"\n🎯 最优先的操作:")
        print(f"  {next_action['icon']} {next_action['command']}")
        print(f"  {next_action['description']}")
