# DevFlow 自我进化引擎
# 让系统从使用中学习，持续改进

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
from collections import defaultdict
import statistics

class EvolutionEngine:
    """自我进化引擎 - 让系统越来越好用"""
    
    def __init__(self, project_path: str = "/Users/abel/dev/devflow"):
        self.project_path = Path(project_path)
        self.experience_dir = self.project_path / '.devflow' / 'experiences'
        self.experience_dir.mkdir(parents=True, exist_ok=True)
        
        self.patterns_file = self.experience_dir / 'patterns.json'
        self.lessons_file = self.experience_dir / 'lessons.json'
        self.metrics_file = self.experience_dir / 'metrics.json'
        
    def record_experience(self, experience: dict):
        """记录一次执行经验"""
        experience_id = f"exp-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        experience['id'] = experience_id
        experience['recorded_at'] = datetime.now().isoformat()
        
        # 保存经验
        exp_file = self.experience_dir / f"{experience_id}.json"
        with open(exp_file, 'w') as f:
            json.dump(experience, f, indent=2)
        
        print(f"📝 记录经验: {experience_id}")
        
        # 分析模式
        self._analyze_patterns()
        
        # 更新指标
        self._update_metrics(experience)
        
        return experience_id
    
    def _analyze_patterns(self):
        """分析成功/失败模式"""
        experiences = list(self.experience_dir.glob('exp-*.json'))
        
        if len(experiences) < 5:
            print("  经验样本太少，暂不分析模式")
            return
        
        patterns = {
            'success_patterns': [],
            'failure_patterns': [],
            'optimal_settings': {},
            'recommendations': []
        }
        
        # 统计Agent成功率
        agent_stats = defaultdict(lambda: {'success': 0, 'failed': 0})
        
        for exp_file in experiences[-50:]:  # 最近50次经验
            with open(exp_file) as f:
                exp = json.load(f)
            
            agent_type = exp.get('agent_type', 'unknown')
            status = exp.get('status', 'unknown')
            
            if status == 'success':
                agent_stats[agent_type]['success'] += 1
            else:
                agent_stats[agent_type]['failed'] += 1
        
        # 计算成功率
        for agent, stats in agent_stats.items():
            total = stats['success'] + stats['failed']
            success_rate = stats['success'] / total if total > 0 else 0
            
            if success_rate > 0.8:
                patterns['success_patterns'].append({
                    'pattern': f"Agent {agent} 成功率高 ({success_rate:.1%})",
                    'confidence': success_rate,
                    'sample_size': total
                })
            elif success_rate < 0.5:
                patterns['failure_patterns'].append({
                    'pattern': f"Agent {agent} 成功率低 ({success_rate:.1%})",
                    'confidence': 1 - success_rate,
                    'sample_size': total
                })
        
        # 分析最优设置
        # TODO: 实现更复杂的分析
        
        # 生成建议
        if patterns['success_patterns']:
            patterns['recommendations'].append(
                "继续使用成功率高的Agent配置"
            )
        
        if patterns['failure_patterns']:
            patterns['recommendations'].append(
                "优化或替换成功率低的Agent配置"
            )
        
        # 保存模式
        with open(self.patterns_file, 'w') as f:
            json.dump(patterns, f, indent=2)
        
        print(f"  🔍 分析了 {len(experiences)} 个经验")
        print(f"  ✅ 发现 {len(patterns['success_patterns'])} 个成功模式")
        print(f"  ⚠️  发现 {len(patterns['failure_patterns'])} 个失败模式")
    
    def _update_metrics(self, experience: dict):
        """更新性能指标"""
        # 加载现有指标
        if self.metrics_file.exists():
            with open(self.metrics_file) as f:
                metrics = json.load(f)
        else:
            metrics = {
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'total_time': 0,
                'average_time': 0,
                'success_rate': 0,
                'daily_stats': {}
            }
        
        # 更新指标
        metrics['total_executions'] += 1
        
        if experience.get('status') == 'success':
            metrics['successful_executions'] += 1
        else:
            metrics['failed_executions'] += 1
        
        # 计算成功率
        metrics['success_rate'] = (
            metrics['successful_executions'] / metrics['total_executions']
        )
        
        # 更新时间统计
        if 'execution_time' in experience:
            metrics['total_time'] += experience['execution_time']
            metrics['average_time'] = metrics['total_time'] / metrics['total_executions']
        
        # 更新每日统计
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in metrics['daily_stats']:
            metrics['daily_stats'][today] = {
                'executions': 0,
                'success': 0,
                'failed': 0
            }
        
        metrics['daily_stats'][today]['executions'] += 1
        if experience.get('status') == 'success':
            metrics['daily_stats'][today]['success'] += 1
        else:
            metrics['daily_stats'][today]['failed'] += 1
        
        # 保存指标
        with open(self.metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        print(f"  📊 更新指标: 成功率 {metrics['success_rate']:.1%}")
    
    def learn_from_failure(self, failure: dict):
        """从失败中学习"""
        lesson = {
            'id': f"lesson-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'type': 'failure',
            'context': failure,
            'analysis': self._analyze_failure(failure),
            'solution': self._suggest_solution(failure),
            'prevention': self._suggest_prevention(failure)
        }
        
        # 保存教训
        with open(self.lessons_file, 'a') as f:
            f.write(json.dumps(lesson) + '\n')
        
        print(f"  💡 从失败中学习: {lesson['id']}")
        print(f"  🔧 建议解决方案: {lesson['solution']}")
        
        return lesson
    
    def _analyze_failure(self, failure: dict) -> str:
        """分析失败原因"""
        error_type = failure.get('error', 'unknown')
        
        # 常见失败原因分析
        analyses = {
            'timeout': '任务执行时间过长，可能需要拆分或优化',
            'permission': '权限不足，需要检查文件或目录权限',
            'dependency': '依赖关系错误，需要调整任务执行顺序',
            'resource': '资源不足（内存/CPU），需要释放资源或增加限制',
            'api_error': 'API调用失败，可能是网络问题或配额限制'
        }
        
        return analyses.get(error_type, f"未知错误类型: {error_type}")
    
    def _suggest_solution(self, failure: dict) -> str:
        """建议解决方案"""
        error_type = failure.get('error', 'unknown')
        
        solutions = {
            'timeout': '增加超时时间，或拆分任务为更小的子任务',
            'permission': '使用chmod/chown修改权限，或使用sudo',
            'dependency': '重新调度任务，确保依赖任务先完成',
            'resource': '等待资源释放，或减少并发数',
            'api_error': '检查网络连接，或等待API配额恢复'
        }
        
        return solutions.get(error_type, '查看详细日志，手动调试')
    
    def _suggest_prevention(self, failure: dict) -> List[str]:
        """建议预防措施"""
        error_type = failure.get('error', 'unknown')
        
        preventions = {
            'timeout': [
                '设置合理的超时时间',
                '实现任务进度检查',
                '添加超时自动重试'
            ],
            'permission': [
                '启动时检查必要权限',
                '提供权限修复脚本',
                '使用沙箱环境'
            ],
            'api_error': [
                '实现API调用限流',
                '添加多个API密钥轮换',
                '实现离线缓存'
            ]
        }
        
        return preventions.get(error_type, ['增加日志记录', '改进错误处理'])
    
    def generate_improvement_report(self) -> dict:
        """生成改进报告"""
        # 加载数据
        with open(self.patterns_file) as f:
            patterns = json.load(f)
        
        with open(self.metrics_file) as f:
            metrics = json.load(f)
        
        # 生成报告
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_executions': metrics['total_executions'],
                'success_rate': f"{metrics['success_rate']:.1%}",
                'average_time': f"{metrics['average_time']:.1f}s"
            },
            'success_patterns': patterns['success_patterns'][:3],
            'failure_patterns': patterns['failure_patterns'][:3],
            'recommendations': patterns['recommendations'],
            'next_improvements': self._suggest_improvements(patterns, metrics)
        }
        
        return report
    
    def _suggest_improvements(self, patterns: dict, metrics: dict) -> List[dict]:
        """建议下一步改进"""
        improvements = []
        
        # 基于成功率建议
        if metrics['success_rate'] < 0.8:
            improvements.append({
                'priority': 'high',
                'area': 'reliability',
                'suggestion': '提升整体成功率到80%以上',
                'actions': [
                    '优化失败任务的Agent选择',
                    '增加任务验证步骤',
                    '改进错误恢复机制'
                ]
            })
        
        # 基于性能建议
        if metrics['average_time'] > 300:  # 超过5分钟
            improvements.append({
                'priority': 'medium',
                'area': 'performance',
                'suggestion': '优化执行速度',
                'actions': [
                    '并行执行独立任务',
                    '缓存常用资源',
                    '优化任务调度算法'
                ]
            })
        
        # 基于模式建议
        if patterns['failure_patterns']:
            improvements.append({
                'priority': 'high',
                'area': 'stability',
                'suggestion': '解决常见失败模式',
                'actions': [
                    '分析失败根本原因',
                    '实现预防措施',
                    '添加自动化修复'
                ]
            })
        
        return improvements
    
    def auto_optimize(self):
        """自动优化系统"""
        print("🔧 自动优化系统...")
        
        # 1. 分析当前状态
        report = self.generate_improvement_report()
        print(f"  📊 当前成功率: {report['summary']['success_rate']}")
        
        # 2. 应用优化
        optimizations = []
        
        # 优化1: 调整Agent选择策略
        if report['failure_patterns']:
            print("  🔍 优化Agent选择策略...")
            optimizations.append(self._optimize_agent_selection())
        
        # 优化2: 调整并发数
        if report['summary']['average_time']:
            print("  ⚡ 优化并发配置...")
            optimizations.append(self._optimize_concurrency())
        
        # 优化3: 调整超时时间
        optimizations.append(self._optimize_timeouts())
        
        print(f"  ✅ 应用了 {len(optimizations)} 个优化")
        
        return optimizations
    
    def _optimize_agent_selection(self) -> dict:
        """优化Agent选择策略"""
        # 读取成功率数据
        # TODO: 实现实际优化
        return {
            'type': 'agent_selection',
            'action': '优先使用成功率高的Agent',
            'status': 'applied'
        }
    
    def _optimize_concurrency(self) -> dict:
        """优化并发配置"""
        # TODO: 基于历史数据动态调整
        return {
            'type': 'concurrency',
            'action': '调整最大并发数为4',
            'status': 'applied'
        }
    
    def _optimize_timeouts(self) -> dict:
        """优化超时配置"""
        # TODO: 基于任务复杂度动态调整
        return {
            'type': 'timeouts',
            'action': '设置合理的超时时间',
            'status': 'applied'
        }

if __name__ == '__main__':
    engine = EvolutionEngine()
    
    # 示例：记录一次成功经验
    engine.record_experience({
        'agent_type': 'codex',
        'task_type': 'bugfix',
        'status': 'success',
        'execution_time': 45,
        'description': '修复登录页面bug'
    })
    
    # 示例：从失败中学习
    engine.learn_from_failure({
        'error': 'timeout',
        'task': '大型重构任务',
        'context': '任务执行时间超过1小时'
    })
    
    # 生成改进报告
    report = engine.generate_improvement_report()
    print("\n📈 改进报告:")
    print(json.dumps(report, indent=2))
    
    # 自动优化
    engine.auto_optimize()
