#!/usr/bin/env python3
"""
DevFlow - 自动监控引擎
监控Agent状态和系统健康度
"""

import os
import json
import psutil
import subprocess
from pathlib import Path
from datetime import datetime

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.status = {}
    
    def check_all(self):
        """检查所有指标"""
        print("📊 系统健康检查...")
        
        # 1. 系统资源
        self.check_system_resources()
        
        # 2. Git状态
        self.check_git_status()
        
        # 3. Agent进程
        self.check_agent_processes()
        
        # 4. 任务队列
        self.check_task_queue()
        
        # 5. 最近提交
        self.check_recent_commits()
        
        # 计算健康度
        health_score = self.calculate_health_score()
        
        # 保存状态
        self.save_status()
        
        # 打印报告
        self.print_report(health_score)
        
        return health_score
    
    def check_system_resources(self):
        """检查系统资源"""
        print("  💻 系统资源...")
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        self.status['system'] = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_gb': memory.available / (1024**3),
            'disk_percent': disk.percent,
            'disk_free_gb': disk.free / (1024**3)
        }
        
        # 判断状态
        if cpu_percent > 80 or memory.percent > 80:
            print(f"    ⚠️  CPU: {cpu_percent}%, 内存: {memory.percent}%")
        else:
            print(f"    ✅ CPU: {cpu_percent}%, 内存: {memory.percent}%")
    
    def check_git_status(self):
        """检查Git状态"""
        print("  📝 Git状态...")
        
        try:
            # 检查是否有未提交的变更
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            
            uncommitted = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            
            # 检查分支
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            branch = result.stdout.strip()
            
            # 检查远程状态
            result = subprocess.run(
                ['git', 'status', '-sb'],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            
            ahead = behind = 0
            if 'ahead' in result.stdout:
                ahead = int(result.stdout.split('ahead')[1].split()[0])
            if 'behind' in result.stdout:
                behind = int(result.stdout.split('behind')[1].split()[0])
            
            self.status['git'] = {
                'branch': branch,
                'uncommitted': uncommitted,
                'ahead': ahead,
                'behind': behind
            }
            
            print(f"    分支: {branch}, 未提交: {uncommitted}, ahead: {ahead}, behind: {behind}")
            
        except Exception as e:
            print(f"    ❌ 检查Git失败: {e}")
            self.status['git'] = {'error': str(e)}
    
    def check_agent_processes(self):
        """检查Agent进程"""
        print("  🤖 Agent进程...")
        
        agents = []
        
        # 检查特定进程
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                
                # 检查是否是Agent进程
                if any(keyword in cmdline.lower() for keyword in ['codex', 'claude', 'devflow', 'python']):
                    agents.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': cmdline[:100],
                        'cpu_percent': proc.info['cpu_percent'],
                        'memory_percent': proc.info['memory_percent']
                    })
            except:
                pass
        
        self.status['agents'] = {
            'count': len(agents),
            'processes': agents
        }
        
        print(f"    运行中的Agent: {len(agents)}")
    
    def check_task_queue(self):
        """检查任务队列"""
        print("  📋 任务队列...")
        
        tasks_dir = self.project_path / '.devflow' / 'tasks'
        
        if not tasks_dir.exists():
            print("    ℹ️  没有任务队列")
            self.status['tasks'] = {'total': 0}
            return
        
        # 读取最新的任务文件
        task_files = sorted(tasks_dir.glob('tasks-*.json'), reverse=True)
        
        if not task_files:
            print("    ℹ️  任务队列为空")
            self.status['tasks'] = {'total': 0}
            return
        
        try:
            with open(task_files[0], 'r') as f:
                tasks_data = json.load(f)
            
            self.status['tasks'] = {
                'total': tasks_data.get('total', 0),
                'by_priority': tasks_data.get('by_priority', {}),
                'by_type': tasks_data.get('by_type', {}),
                'file': str(task_files[0].name)
            }
            
            print(f"    待处理任务: {tasks_data.get('total', 0)}")
            
        except Exception as e:
            print(f"    ❌ 读取任务失败: {e}")
            self.status['tasks'] = {'error': str(e)}
    
    def check_recent_commits(self):
        """检查最近提交"""
        print("  📊 最近提交...")
        
        try:
            # 获取最近10次提交
            result = subprocess.run(
                ['git', 'log', '-10', '--oneline', '--format=%h %s %ci'],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        commits.append({
                            'hash': parts[0],
                            'message': parts[1],
                            'time': parts[2]
                        })
            
            self.status['commits'] = {
                'recent': commits,
                'count_24h': self._count_commits_24h(commits)
            }
            
            print(f"    最近24小时: {self.status['commits']['count_24h']} 次提交")
            
        except Exception as e:
            print(f"    ❌ 检查提交失败: {e}")
            self.status['commits'] = {'error': str(e)}
    
    def _count_commits_24h(self, commits):
        """统计24小时内提交次数"""
        # 简化处理，实际应该解析时间
        return len([c for c in commits if 'hours' in c.get('time', '')])
    
    def calculate_health_score(self):
        """计算健康度评分 (0-100)"""
        score = 100
        
        # CPU/内存过高扣分
        if self.status.get('system', {}).get('cpu_percent', 0) > 80:
            score -= 20
        if self.status.get('system', {}).get('memory_percent', 0) > 80:
            score -= 20
        
        # 有未提交的变更扣分
        uncommitted = self.status.get('git', {}).get('uncommitted', 0)
        if uncommitted > 10:
            score -= 10
        
        # 本地落后远程扣分
        behind = self.status.get('git', {}).get('behind', 0)
        if behind > 5:
            score -= 15
        
        # 没有Agent运行扣分
        if self.status.get('agents', {}).get('count', 0) == 0:
            score -= 10
        
        # 有待处理任务扣分（但扣得少，因为这是正常的）
        tasks = self.status.get('tasks', {}).get('total', 0)
        if tasks > 20:
            score -= 5
        
        return max(0, min(100, score))
    
    def save_status(self):
        """保存状态"""
        status_dir = self.project_path / '.devflow' / 'monitor'
        status_dir.mkdir(parents=True, exist_ok=True)
        
        status_file = status_dir / f'status-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json'
        
        with open(status_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'health_score': self.calculate_health_score(),
                'status': self.status
            }, f, indent=2)
    
    def print_report(self, health_score):
        """打印报告"""
        print("\n" + "="*50)
        print("📊 DevFlow 系统健康报告")
        print("="*50)
        print(f"健康度: {health_score}/100")
        
        if health_score >= 80:
            print("状态: ✅ 优秀")
        elif health_score >= 60:
            print("状态: ⚠️  良好")
        else:
            print("状态: ❌ 需要关注")
        
        print("\n详细信息:")
        print(f"  CPU: {self.status['system']['cpu_percent']}%")
        print(f"  内存: {self.status['system']['memory_percent']}%")
        print(f"  磁盘: {self.status['system']['disk_percent']}%")
        print(f"  Agent: {self.status['agents']['count']} 个运行中")
        print(f"  任务: {self.status['tasks']['total']} 个待处理")
        print(f"  Git: {self.status['git']['uncommitted']} 个未提交")
        print("="*50)

if __name__ == '__main__':
    monitor = SystemMonitor('/Users/abel/dev/devflow')
    monitor.check_all()
