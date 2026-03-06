#!/usr/bin/env python3
"""
DevFlow - 智能任务调度器
基于优先级、依赖关系和资源情况智能调度任务
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Set
from dataclasses import dataclass

@dataclass
class TaskDependency:
    """任务依赖关系"""
    task_id: str
    depends_on: List[str]
    priority: str

class TaskScheduler:
    """智能任务调度器"""
    
    def __init__(self, project_path: str = "/Users/abel/dev/devflow"):
        self.project_path = Path(project_path)
        self.task_dir = self.project_path / '.devflow' / 'tasks'
        self.task_dir.mkdir(parents=True, exist_ok=True)
        
    def schedule_tasks(self) -> List[dict]:
        """智能调度任务"""
        print("🎯 智能任务调度...")
        
        # 1. 加载所有任务
        all_tasks = self._load_all_tasks()
        print(f"  📋 加载了 {len(all_tasks)} 个任务")
        
        # 2. 分析依赖关系
        dependencies = self._analyze_dependencies(all_tasks)
        print(f"  🔗 分析了 {len(dependencies)} 个依赖关系")
        
        # 3. 拓扑排序
        sorted_tasks = self._topological_sort(all_tasks, dependencies)
        print(f"  ✅ 拓扑排序完成")
        
        # 4. 优先级调整
        prioritized_tasks = self._adjust_priority(sorted_tasks)
        print(f"  ⭐ 优先级调整完成")
        
        # 5. 资源分配
        scheduled_tasks = self._allocate_resources(prioritized_tasks)
        print(f"  🎯 资源分配完成")
        
        # 6. 保存调度结果
        self._save_schedule(scheduled_tasks)
        
        return scheduled_tasks
    
    def _load_all_tasks(self) -> List[dict]:
        """加载所有任务"""
        tasks = []
        
        # 从任务文件加载
        for task_file in self.task_dir.glob('tasks-*.json'):
            with open(task_file) as f:
                data = json.load(f)
                tasks.extend(data.get('tasks', []))
        
        # 从各个任务文件加载
        for task_file in self.task_dir.glob('task-*.json'):
            with open(task_file) as f:
                task = json.load(f)
                tasks.append(task)
        
        return tasks
    
    def _analyze_dependencies(self, tasks: List[dict]) -> Dict[str, List[str]]:
        """分析任务依赖关系"""
        dependencies = {}
        
        # 简单的依赖分析（实际应该用AI分析）
        for task in tasks:
            task_id = task.get('id')
            description = task.get('description', '').lower()
            
            deps = []
            
            # 检测常见的依赖关系
            if '实现用户登录' in description:
                deps.extend([t['id'] for t in tasks if '用户模型' in t.get('description', '').lower()])
            
            if '用户注册' in description:
                deps.extend([t['id'] for t in tasks if '邮箱验证' in t.get('description', '').lower()])
            
            dependencies[task_id] = deps
        
        return dependencies
    
    def _topological_sort(self, tasks: List[dict], dependencies: Dict[str, List[str]]) -> List[dict]:
        """拓扑排序"""
        # 构建图
        graph = {task['id']: set(dependencies.get(task['id'], [])) for task in tasks}
        
        # Kahn算法
        in_degree = {node: 0 for node in graph}
        for node in graph:
            for dep in graph[node]:
                in_degree[dep] = in_degree.get(dep, 0)
        
        queue = [node for node, degree in in_degree.items() if degree == 0]
        sorted_ids = []
        
        while queue:
            node = queue.pop(0)
            sorted_ids.append(node)
            
            for neighbor in graph:
                if node in graph[neighbor]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
        
        # 按排序顺序返回任务
        task_map = {task['id']: task for task in tasks}
        return [task_map[task_id] for task_id in sorted_ids if task_id in task_map]
    
    def _adjust_priority(self, tasks: List[dict]) -> List[dict]:
        """调整优先级"""
        priority_weights = {
            'P0': 4,  # 最高
            'P1': 3,
            'P2': 2,
            'P3': 1   # 最低
        }
        
        # 根据优先级和创建时间调整
        def priority_score(task):
            priority = task.get('priority', 'P3')
            created_at = task.get('created_at', datetime.now().isoformat())
            
            # 优先级分数
            score = priority_weights.get(priority, 1) * 1000
            
            # 时间因子（越早创建越优先）
            try:
                created_time = datetime.fromisoformat(created_at)
                age_hours = (datetime.now() - created_time).total_seconds() / 3600
                score += min(age_hours, 100)  # 最多加100分
            except Exception:
                pass
            
            return -score  # 负号因为要升序排序
        
        return sorted(tasks, key=priority_score)
    
    def _allocate_resources(self, tasks: List[dict]) -> List[dict]:
        """资源分配"""
        max_parallel = 4
        agent_types = ['codex', 'claude-code', 'taskmaster']
        
        scheduled = []
        
        for i, task in enumerate(tasks[:max_parallel * 2]):  # 最多调度2倍的并发数
            # 分配Agent类型
            task_type = task.get('type', 'feature')
            
            if task_type in ['test-failure', 'lint-error', 'fixme']:
                agent = 'codex'  # Codex擅长修复
            elif task_type in ['prd-task', 'feature']:
                agent = 'claude-code'  # Claude Code擅长新功能
            else:
                agent = agent_types[i % len(agent_types)]
            
            task['assigned_agent'] = agent
            task['scheduled_at'] = datetime.now().isoformat()
            scheduled.append(task)
        
        return scheduled
    
    def _save_schedule(self, tasks: List[dict]):
        """保存调度结果"""
        schedule_file = self.task_dir / 'schedule.json'
        
        with open(schedule_file, 'w') as f:
            json.dump({
                'scheduled_at': datetime.now().isoformat(),
                'total_tasks': len(tasks),
                'tasks': tasks
            }, f, indent=2)
        
        print(f"  💾 调度结果已保存: {schedule_file}")
    
    def get_next_batch(self, batch_size: int = 4) -> List[dict]:
        """获取下一批任务"""
        schedule_file = self.task_dir / 'schedule.json'
        
        if not schedule_file.exists():
            # 如果没有调度文件，先调度
            self.schedule_tasks()
        
        with open(schedule_file) as f:
            data = json.load(f)
        
        # 获取前N个未执行的任务
        tasks = data.get('tasks', [])[:batch_size]
        
        print(f"\n📋 下一批任务 ({len(tasks)} 个):")
        for i, task in enumerate(tasks, 1):
            print(f"  {i}. [{task.get('priority')}] {task.get('description')}")
            print(f"     Agent: {task.get('assigned_agent')}")
            print(f"     ID: {task.get('id')}")
        
        return tasks

if __name__ == '__main__':
    scheduler = TaskScheduler()
    
    # 调度任务
    scheduled = scheduler.schedule_tasks()
    
    # 显示下一批
    next_batch = scheduler.get_next_batch()
