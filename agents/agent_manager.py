#!/usr/bin/env python3
"""
DevFlow - Agent管理器
管理和调度多个AI Agent
"""

import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class AgentType(Enum):
    CODEX = "codex"
    CLAUDE_CODE = "claude-code"
    TASKMASTER = "taskmaster"
    BMAD = "bmad"

class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class AgentTask:
    id: str
    type: str
    description: str
    priority: str  # P0, P1, P2, P3
    agent_type: AgentType
    status: AgentStatus = AgentStatus.IDLE
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    result: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

class AgentManager:
    """Agent管理器"""
    
    def __init__(self, config_path: str = None):
        self.project_path = Path("/Users/abel/dev/devflow")
        self.config = self._load_config(config_path)
        self.agents: Dict[str, AgentTask] = {}
        self.running_agents: Dict[str, subprocess.Popen] = {}
        self.max_parallel = self.config.get('scheduling', {}).get('max_parallel', 4)
        
    def _load_config(self, config_path: str) -> dict:
        """加载配置"""
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        
        # 默认配置
        return {
            'agents': {
                'codex': {
                    'enabled': True,
                    'model': 'gpt-4',
                    'max_tasks': 3,
                    'timeout': 3600
                },
                'claude-code': {
                    'enabled': True,
                    'model': 'claude-3-opus',
                    'max_tasks': 3,
                    'timeout': 3600
                }
            },
            'scheduling': {
                'max_parallel': 4,
                'retry_policy': {
                    'max_retries': 3,
                    'backoff': 'exponential'
                }
            }
        }
    
    def add_task(self, task: AgentTask) -> str:
        """添加任务"""
        task.id = task.id or f"task-{len(self.agents)}-{int(time.time())}"
        self.agents[task.id] = task
        self._save_task(task)
        print(f"✅ 添加任务: {task.id} - {task.description}")
        return task.id
    
    def get_next_task(self) -> Optional[AgentTask]:
        """获取下一个任务（按优先级）"""
        # 按优先级排序
        priority_order = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}
        
        pending_tasks = [
            t for t in self.agents.values()
            if t.status == AgentStatus.IDLE
        ]
        
        if not pending_tasks:
            return None
        
        # 按优先级排序
        pending_tasks.sort(key=lambda t: priority_order.get(t.priority, 3))
        return pending_tasks[0]
    
    def execute_task(self, task_id: str) -> bool:
        """执行任务"""
        task = self.agents.get(task_id)
        if not task:
            print(f"❌ 任务不存在: {task_id}")
            return False
        
        # 检查是否超过最大并发
        if len(self.running_agents) >= self.max_parallel:
            print(f"⚠️  达到最大并发数 {self.max_parallel}，等待...")
            return False
        
        print(f"🚀 执行任务: {task_id} (Agent: {task.agent_type.value})")
        
        task.status = AgentStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        self._save_task(task)
        
        try:
            # 根据Agent类型执行
            if task.agent_type == AgentType.CODEX:
                result = self._execute_codex(task)
            elif task.agent_type == AgentType.CLAUDE_CODE:
                result = self._execute_claude_code(task)
            elif task.agent_type == AgentType.TASKMASTER:
                result = self._execute_taskmaster(task)
            elif task.agent_type == AgentType.BMAD:
                result = self._execute_bmad(task)
            else:
                raise ValueError(f"未知Agent类型: {task.agent_type}")
            
            task.status = AgentStatus.SUCCESS
            task.result = result
            task.completed_at = datetime.now().isoformat()
            print(f"✅ 任务完成: {task_id}")
            return True
            
        except Exception as e:
            task.status = AgentStatus.FAILED
            task.error = str(e)
            task.retry_count += 1
            print(f"❌ 任务失败: {task_id} - {e}")
            
            # 重试
            if task.retry_count < task.max_retries:
                print(f"🔄 重试任务 ({task.retry_count}/{task.max_retries})")
                time.sleep(5 * task.retry_count)  # 指数退避
                task.status = AgentStatus.IDLE
                return self.execute_task(task_id)
            
            return False
        
        finally:
            self._save_task(task)
    
    def _execute_codex(self, task: AgentTask) -> str:
        """执行Codex Agent"""
        print(f"  🤖 Codex处理: {task.description}")
        
        # 检查codex是否可用
        if not self._check_command_available('codex'):
            raise Exception("Codex未安装或不可用")
        
        # 构建命令
        cmd = [
            'codex',
            '--task', task.description,
            '--project', str(self.project_path),
            '--auto'
        ]
        
        # 执行
        result = subprocess.run(
            cmd,
            cwd=self.project_path,
            capture_output=True,
            text=True,
            timeout=self.config['agents']['codex']['timeout']
        )
        
        if result.returncode != 0:
            raise Exception(f"Codex执行失败: {result.stderr}")
        
        return result.stdout
    
    def _execute_claude_code(self, task: AgentTask) -> str:
        """执行Claude Code Agent"""
        print(f"  🤖 Claude Code处理: {task.description}")
        
        # 检查claude-code是否可用
        if not self._check_command_available('claude-code'):
            raise Exception("Claude Code未安装或不可用")
        
        # 构建命令
        cmd = [
            'claude-code',
            '--task', task.description,
            '--project', str(self.project_path)
        ]
        
        # 执行
        result = subprocess.run(
            cmd,
            cwd=self.project_path,
            capture_output=True,
            text=True,
            timeout=self.config['agents']['claude-code']['timeout']
        )
        
        if result.returncode != 0:
            raise Exception(f"Claude Code执行失败: {result.stderr}")
        
        return result.stdout
    
    def _execute_taskmaster(self, task: AgentTask) -> str:
        """执行TaskMaster Agent"""
        print(f"  🤖 TaskMaster处理: {task.description}")
        
        # 使用TaskMaster Skill
        from skills.taskmaster import TaskMaster
        
        tm = TaskMaster(prd_path=str(self.project_path / "PRD.md"))
        tasks = tm.generate_tasks()
        
        return f"生成了 {len(tasks)} 个任务"
    
    def _execute_bmad(self, task: AgentTask) -> str:
        """执行BMAD Agent"""
        print(f"  🤖 BMAD处理: {task.description}")
        
        # TODO: 实现BMAD执行
        time.sleep(2)  # 模拟执行
        return "BMAD执行完成"
    
    def _check_command_available(self, command: str) -> bool:
        """检查命令是否可用"""
        try:
            result = subprocess.run(
                ['which', command],
                capture_output=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _save_task(self, task: AgentTask):
        """保存任务状态"""
        task_dir = self.project_path / '.devflow' / 'tasks'
        task_dir.mkdir(parents=True, exist_ok=True)
        
        task_file = task_dir / f"{task.id}.json"
        
        with open(task_file, 'w') as f:
            json.dump(asdict(task), f, indent=2, default=str)
    
    def run_autonomous_loop(self, interval: int = 60):
        """运行自动循环"""
        print("🔄 启动自动循环...")
        print(f"   检查间隔: {interval}秒")
        print(f"   最大并发: {self.max_parallel}")
        
        iteration = 0
        while True:
            iteration += 1
            print(f"\n{'='*50}")
            print(f"循环 #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*50}")
            
            # 1. 发现新任务
            print("\n1️⃣ 发现任务...")
            new_tasks = self._discover_tasks()
            print(f"   发现 {len(new_tasks)} 个新任务")
            
            # 2. 执行任务
            print("\n2️⃣ 执行任务...")
            task = self.get_next_task()
            if task:
                success = self.execute_task(task.id)
                if success:
                    print(f"   ✅ 任务 {task.id} 执行成功")
                else:
                    print(f"   ❌ 任务 {task.id} 执行失败")
            else:
                print("   ℹ️  没有待执行的任务")
            
            # 3. 提交代码
            print("\n3️⃣ 自动提交...")
            self._auto_commit()
            
            # 4. 更新状态
            print("\n4️⃣ 更新状态...")
            self._update_status()
            
            # 5. 显示统计
            print("\n📊 统计:")
            self._print_stats()
            
            # 等待下次循环
            print(f"\n⏰ 等待 {interval} 秒...")
            time.sleep(interval)
    
    def _discover_tasks(self) -> List[AgentTask]:
        """发现新任务"""
        # 使用auto-discover脚本
        try:
            result = subprocess.run(
                ['python3', 'scripts/auto-discover.sh'],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            
            # 读取生成的任务
            task_dir = self.project_path / '.devflow' / 'tasks'
            latest_task_file = max(
                task_dir.glob('tasks-*.json'),
                key=lambda p: p.stat().st_mtime,
                default=None
            )
            
            if latest_task_file:
                with open(latest_task_file) as f:
                    data = json.load(f)
                    return [AgentTask(**t) for t in data.get('tasks', [])]
        except Exception as e:
            print(f"   ⚠️  发现任务失败: {e}")
        
        return []
    
    def _auto_commit(self):
        """自动提交"""
        try:
            result = subprocess.run(
                ['python3', 'scripts/auto-commit.sh'],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("   ✅ 自动提交成功")
            else:
                print(f"   ℹ️  {result.stdout.strip()}")
        except Exception as e:
            print(f"   ⚠️  自动提交失败: {e}")
    
    def _update_status(self):
        """更新状态"""
        status = {
            'total_tasks': len(self.agents),
            'pending': len([t for t in self.agents.values() if t.status == AgentStatus.IDLE]),
            'running': len([t for t in self.agents.values() if t.status == AgentStatus.RUNING]),
            'completed': len([t for t in self.agents.values() if t.status == AgentStatus.SUCCESS]),
            'failed': len([t for t in self.agents.values() if t.status == AgentStatus.FAILED])
            'updated_at': datetime.now().isoformat()
        }
        
        status_file = self.project_path / '.devflow' / 'status.json'
        status_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(status_file, 'w') as f:
            json.dump(status, f, indent=2)
    
    def _print_stats(self):
        """打印统计"""
        status = {
            'total': len(self.agents),
            'pending': len([t for t in self.agents.values() if t.status == AgentStatus.IDLE]),
            'running': len([t for t in self.agents.values() if t.status == AgentStatus.RUNING]),
            'completed': len([t for t in self.agents.values() if t.status == AgentStatus.SUCCESS]),
            'failed': len([t for t in self.agents.values() if t.status == AgentStatus.FAILED])
        }
        
        print(f"   总任务: {status['total']}")
        print(f"   待处理: {status['pending']}")
        print(f"   进行中: {status['running']}")
        print(f"   已完成: {status['completed']}")
        print(f"   已失败: {status['failed']}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='DevFlow Agent管理器')
    parser.add_argument('--loop', action='store_true', help='运行自动循环')
    parser.add_argument('--interval', type=int, default=60, help='循环间隔（秒）')
    parser.add_argument('--config', type=str, help='配置文件路径')
    
    args = parser.parse_args()
    
    manager = AgentManager(config_path=args.config)
    
    if args.loop:
        manager.run_autonomous_loop(interval=args.interval)
    else:
        # 单次执行
        task = manager.get_next_task()
        if task:
            manager.execute_task(task.id)
        else:
            print("没有待执行的任务")
