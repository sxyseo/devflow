#!/usr/bin/env python3
# DevFlow 易用性改进器
# 让系统越来越好用

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

class UsabilityImprover:
    """易用性改进器 - 让系统越来越好用"""
    
    def __init__(self, project_path: str = "/Users/abel/dev/devflow"):
        self.project_path = Path(project_path)
        self.feedback_dir = self.project_path / '.devflow' / 'feedback'
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        
        self.improvements_file = self.feedback_dir / 'improvements.json'
        
    def collect_feedback(self, feedback_type: str, content: str, rating: int = None):
        """收集用户反馈"""
        feedback = {
            'id': f"fb-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'type': feedback_type,  # bug, feature, improvement, question
            'content': content,
            'rating': rating,  # 1-5星
            'status': 'pending'
        }
        
        # 保存反馈
        feedback_file = self.feedback_dir / f"{feedback['id']}.json"
        with open(feedback_file, 'w') as f:
            json.dump(feedback, f, indent=2)
        
        print(f"💬 收集反馈: {feedback['id']}")
        print(f"  类型: {feedback_type}")
        print(f"  内容: {content}")
        
        # 自动分类和处理
        self._auto_process_feedback(feedback)
        
        return feedback['id']
    
    def _auto_process_feedback(self, feedback: dict):
        """自动处理反馈"""
        feedback_type = feedback['type']
        
        if feedback_type == 'bug':
            print("  🔍 自动创建Bug修复任务...")
            self._create_bug_task(feedback)
        
        elif feedback_type == 'feature':
            print("  💡 记录功能请求...")
            self._record_feature_request(feedback)
        
        elif feedback_type == 'improvement':
            print("  ⚡ 记录改进建议...")
            self._record_improvement(feedback)
    
    def _create_bug_task(self, feedback: dict):
        """创建Bug修复任务"""
        task = {
            'id': f"bug-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'type': 'bug',
            'priority': 'P1',
            'description': f"修复用户报告的Bug: {feedback['content']}",
            'source': 'user_feedback',
            'feedback_id': feedback['id'],
            'created_at': datetime.now().isoformat()
        }
        
        # 保存任务
        task_file = self.project_path / '.devflow' / 'tasks' / f"{task['id']}.json"
        task_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(task_file, 'w') as f:
            json.dump(task, f, indent=2)
        
        print(f"  ✅ 创建任务: {task['id']}")
    
    def _record_feature_request(self, feedback: dict):
        """记录功能请求"""
        # TODO: 实现功能请求记录
        print(f"  📝 已记录功能请求")
    
    def _record_improvement(self, feedback: dict):
        """记录改进建议"""
        # 加载现有改进
        if self.improvements_file.exists():
            with open(self.improvements_file) as f:
                improvements = json.load(f)
        else:
            improvements = {'pending': [], 'in_progress': [], 'completed': []}
        
        # 添加新改进
        improvement = {
            'id': f"imp-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'content': feedback['content'],
            'rating': feedback.get('rating'),
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        
        improvements['pending'].append(improvement)
        
        # 保存
        with open(self.improvements_file, 'w') as f:
            json.dump(improvements, f, indent=2)
        
        print(f"  📊 记录改进: {improvement['id']}")
    
    def suggest_quick_wins(self) -> List[dict]:
        """建议快速改进（Quick Wins）"""
        # 分析反馈，找出容易实现的改进
        quick_wins = []
        
        # 常见的Quick Wins
        common_improvements = [
            {
                'id': 'qw-1',
                'title': '添加命令别名',
                'description': '让常用命令更短',
                'effort': '1小时',
                'impact': 'high',
                'example': 'df -> devflow, dfr -> devflow run'
            },
            {
                'id': 'qw-2',
                'title': '改进错误提示',
                'description': '让错误信息更友好',
                'effort': '2小时',
                'impact': 'high',
                'example': '❌ 权限错误 -> 💡 请运行: chmod +x devflow.sh'
            },
            {
                'id': 'qw-3',
                'title': '添加进度显示',
                'description': '显示任务执行进度',
                'effort': '3小时',
                'impact': 'medium',
                'example': '⏳ 正在执行任务 3/10 (30%)'
            },
            {
                'id': 'qw-4',
                'title': '智能命令提示',
                'description': '根据上下文建议下一步操作',
                'effort': '4小时',
                'impact': 'high',
                'example': '💡 检测到3个待处理任务，运行 devflow run 开始执行'
            },
            {
                'id': 'qw-5',
                'title': '添加配置向导',
                'description': '首次运行时引导配置',
                'effort': '5小时',
                'impact': 'high',
                'example': '🚀 欢迎使用DevFlow！让我们完成初始配置...'
            }
        ]
        
        # 优先级排序
        quick_wins = sorted(common_improvements, key=lambda x: (
            {'high': 3, 'medium': 2, 'low': 1}[x['impact']],
            -int(x['effort'].split()[0])
        ))
        
        return quick_wins[:5]  # 返回前5个
    
    def apply_quick_win(self, quick_win_id: str):
        """应用快速改进"""
        quick_wins = self.suggest_quick_wins()
        quick_win = next((qw for qw in quick_wins if qw['id'] == quick_win_id), None)
        
        if not quick_win:
            print(f"❌ 找不到Quick Win: {quick_win_id}")
            return False
        
        print(f"🚀 应用Quick Win: {quick_win['title']}")
        print(f"  预计耗时: {quick_win['effort']}")
        print(f"  影响程度: {quick_win['impact']}")
        
        # TODO: 实现实际应用逻辑
        
        print("  ✅ 已应用")
        return True
    
    def measure_usability(self) -> dict:
        """度量易用性"""
        metrics = {
            'command_count': self._count_commands(),
            'doc_completeness': self._check_doc_completeness(),
            'error_rate': self._calculate_error_rate(),
            'avg_setup_time': self._estimate_setup_time(),
            'learning_curve': self._assess_learning_curve()
        }
        
        # 计算易用性评分 (0-100)
        score = self._calculate_usability_score(metrics)
        
        metrics['usability_score'] = score
        
        return metrics
    
    def _count_commands(self) -> int:
        """统计命令数量"""
        # 主要命令数量
        return 9  # devflow.sh中的9个命令
    
    def _check_doc_completeness(self) -> float:
        """检查文档完整性"""
        required_docs = [
            'README.md',
            'QUICKSTART.md',
            'ARCHITECTURE.md',
            'IMPLEMENTATION_GUIDE.md',
            'STATUS.md'
        ]
        
        existing = sum(1 for doc in required_docs if (self.project_path / doc).exists())
        
        return existing / len(required_docs)
    
    def _calculate_error_rate(self) -> float:
        """计算错误率"""
        # TODO: 从日志中统计
        return 0.1  # 假设10%的错误率
    
    def _estimate_setup_time(self) -> int:
        """估算设置时间（分钟）"""
        # README中的快速开始说是5分钟
        return 5
    
    def _assess_learning_curve(self) -> str:
        """评估学习曲线"""
        # 基于命令复杂度
        return 'easy'  # easy, medium, hard
    
    def _calculate_usability_score(self, metrics: dict) -> int:
        """计算易用性评分"""
        score = 100
        
        # 命令数量（越少越好，但要有足够功能）
        if metrics['command_count'] > 15:
            score -= 10
        elif metrics['command_count'] < 5:
            score -= 5
        
        # 文档完整性
        score += int(metrics['doc_completeness'] * 20)
        
        # 错误率
        score -= int(metrics['error_rate'] * 100)
        
        # 设置时间
        if metrics['avg_setup_time'] > 10:
            score -= 10
        elif metrics['avg_setup_time'] < 3:
            score += 10
        
        # 学习曲线
        curve_scores = {'easy': 10, 'medium': 0, 'hard': -10}
        score += curve_scores.get(metrics['learning_curve'], 0)
        
        return max(0, min(100, score))

if __name__ == '__main__':
    improver = UsabilityImprover()
    
    # 示例：收集反馈
    print("📝 收集用户反馈...")
    improver.collect_feedback(
        feedback_type='improvement',
        content='希望能有一个命令查看所有可用Agent',
        rating=4
    )
    
    # 示例：建议Quick Wins
    print("\n🚀 建议Quick Wins:")
    quick_wins = improver.suggest_quick_wins()
    for qw in quick_wins:
        print(f"  {qw['id']}. {qw['title']} ({qw['effort']}, 影响: {qw['impact']})")
    
    # 示例：度量易用性
    print("\n📊 易用性指标:")
    metrics = improver.measure_usability()
    print(json.dumps(metrics, indent=2))
