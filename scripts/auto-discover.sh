#!/usr/bin/env python3
"""
DevFlow - 自动任务发现引擎
自动扫描项目，发现待办任务
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime

class TaskDiscoverer:
    """自动任务发现器"""
    
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.tasks = []
        
    def discover_all(self):
        """发现所有类型的任务"""
        print("🔍 扫描项目...")
        
        # 1. 发现TODO注释
        self.discover_todos()
        
        # 2. 发现FIXME注释
        self.discover_fixmes()
        
        # 3. 发现测试失败
        self.discover_test_failures()
        
        # 4. 发现Lint错误
        self.discover_lint_errors()
        
        # 5. 发现安全漏洞
        self.discover_security_issues()
        
        # 6. 发现性能问题
        self.discover_performance_issues()
        
        # 7. 读取PRD需求
        self.discover_prd_tasks()
        
        # 保存任务
        self.save_tasks()
        
        print(f"✅ 发现 {len(self.tasks)} 个任务")
        return self.tasks
    
    def discover_todos(self):
        """扫描TODO注释"""
        print("  📝 扫描TODO注释...")
        count = 0
        
        for file_path in self.project_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.java']:
                try:
                    content = file_path.read_text()
                    # 匹配 TODO: xxx 或 # TODO: xxx
                    matches = re.findall(r'(?:\/\/|#|\/\*|\*)\s*TODO:\s*(.+)', content)
                    
                    for i, match in enumerate(matches):
                        task = {
                            'id': f'todo-{count}',
                            'type': 'todo',
                            'priority': 'P2',
                            'description': match.strip(),
                            'file': str(file_path.relative_to(self.project_path)),
                            'occurrence': i + 1,
                            'created_at': datetime.now().isoformat()
                        }
                        self.tasks.append(task)
                        count += 1
                        
                except Exception as e:
                    pass
        
        print(f"    发现 {count} 个TODO")
    
    def discover_fixmes(self):
        """扫描FIXME注释"""
        print("  🔧 扫描FIXME注释...")
        count = 0
        
        for file_path in self.project_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.jsx', '.tsx']:
                try:
                    content = file_path.read_text()
                    matches = re.findall(r'(?:\/\/|#|\/\*|\*)\s*FIXME:\s*(.+)', content)
                    
                    for i, match in enumerate(matches):
                        task = {
                            'id': f'fixme-{count}',
                            'type': 'fixme',
                            'priority': 'P1',  # FIXME优先级高于TODO
                            'description': match.strip(),
                            'file': str(file_path.relative_to(self.project_path)),
                            'occurrence': i + 1,
                            'created_at': datetime.now().isoformat()
                        }
                        self.tasks.append(task)
                        count += 1
                        
                except Exception as e:
                    pass
        
        print(f"    发现 {count} 个FIXME")
    
    def discover_test_failures(self):
        """发现测试失败"""
        print("  🧪 检查测试...")
        count = 0
        
        # 尝试运行测试
        test_commands = [
            'npm test 2>&1',
            'pytest 2>&1',
            'python -m pytest 2>&1'
        ]
        
        for cmd in test_commands:
            try:
                result = os.popen(cmd).read()
                if 'FAILED' in result or 'Error' in result:
                    # 提取失败的测试
                    matches = re.findall(r'FAILED\s+(.+)', result)
                    for match in matches:
                        task = {
                            'id': f'test-{count}',
                            'type': 'test-failure',
                            'priority': 'P0',  # 测试失败最高优先级
                            'description': f'修复失败的测试: {match.strip()}',
                            'file': match.strip(),
                            'created_at': datetime.now().isoformat()
                        }
                        self.tasks.append(task)
                        count += 1
                break  # 成功运行一个命令就退出
            except Exception as e:
                pass
        
        print(f"    发现 {count} 个测试失败")
    
    def discover_lint_errors(self):
        """发现Lint错误"""
        print("  🎨 检查Lint...")
        count = 0
        
        lint_commands = [
            'npm run lint 2>&1',
            'eslint . 2>&1',
            'ruff check . 2>&1'
        ]
        
        for cmd in lint_commands:
            try:
                result = os.popen(cmd).read()
                if 'error' in result.lower():
                    # 提取错误
                    lines = result.split('\n')
                    for line in lines:
                        if 'error' in line.lower():
                            task = {
                                'id': f'lint-{count}',
                                'type': 'lint-error',
                                'priority': 'P1',
                                'description': f'修复Lint错误: {line.strip()}',
                                'created_at': datetime.now().isoformat()
                            }
                            self.tasks.append(task)
                            count += 1
                break
            except Exception as e:
                pass
        
        print(f"    发现 {count} 个Lint错误")
    
    def discover_security_issues(self):
        """发现安全问题"""
        print("  🔒 检查安全...")
        count = 0
        
        # 检查依赖漏洞
        try:
            result = os.popen('npm audit --json 2>&1').read()
            audit = json.loads(result)
            
            if 'vulnerabilities' in audit:
                for vuln in audit['vulnerabilities'].values():
                    task = {
                        'id': f'security-{count}',
                        'type': 'security',
                        'priority': 'P0',
                        'description': f'安全漏洞: {vuln.get("name", "unknown")} - {vuln.get("severity", "unknown")}',
                        'severity': vuln.get('severity', 'unknown'),
                        'created_at': datetime.now().isoformat()
                    }
                    self.tasks.append(task)
                    count += 1
        except Exception as e:
            pass
        
        print(f"    发现 {count} 个安全问题")
    
    def discover_performance_issues(self):
        """发现性能问题"""
        print("  ⚡ 检查性能...")
        # TODO: 实现性能分析
        print("    发现 0 个性能问题")
    
    def discover_prd_tasks(self):
        """从PRD文档发现任务"""
        print("  📄 扫描PRD...")
        count = 0
        
        prd_files = ['PRD.md', 'prd.md', 'requirements.md', 'REQUIREMENTS.md']
        
        for prd_name in prd_files:
            prd_path = self.project_path / prd_name
            if prd_path.exists():
                try:
                    content = prd_path.read_text()
                    # 简单的任务提取（实际应该用AI分析）
                    lines = content.split('\n')
                    for line in lines:
                        if line.startswith('- [ ]') or line.startswith('* [ ]'):
                            task_desc = line.replace('- [ ]', '').replace('* [ ]', '').strip()
                            task = {
                                'id': f'prd-{count}',
                                'type': 'prd-task',
                                'priority': 'P1',
                                'description': task_desc,
                                'source': prd_name,
                                'created_at': datetime.now().isoformat()
                            }
                            self.tasks.append(task)
                            count += 1
                except Exception as e:
                    pass
        
        print(f"    发现 {count} 个PRD任务")
    
    def save_tasks(self):
        """保存任务到文件"""
        output_dir = self.project_path / '.devflow' / 'tasks'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f'tasks-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json'
        
        with open(output_file, 'w') as f:
            json.dump({
                'total': len(self.tasks),
                'by_priority': self._count_by_priority(),
                'by_type': self._count_by_type(),
                'tasks': self.tasks,
                'created_at': datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"  💾 任务已保存到: {output_file}")
    
    def _count_by_priority(self):
        """按优先级统计"""
        counts = {}
        for task in self.tasks:
            priority = task.get('priority', 'unknown')
            counts[priority] = counts.get(priority, 0) + 1
        return counts
    
    def _count_by_type(self):
        """按类型统计"""
        counts = {}
        for task in self.tasks:
            task_type = task.get('type', 'unknown')
            counts[task_type] = counts.get(task_type, 0) + 1
        return counts

if __name__ == '__main__':
    discoverer = TaskDiscoverer('/Users/abel/dev/devflow')
    tasks = discoverer.discover_all()
    
    print("\n📊 任务统计:")
    print(f"  总计: {len(tasks)} 个任务")
    print(f"  P0 (最高): {len([t for t in tasks if t.get('priority') == 'P0'])}")
    print(f"  P1 (高): {len([t for t in tasks if t.get('priority') == 'P1'])}")
    print(f"  P2 (中): {len([t for t in tasks if t.get('priority') == 'P2'])}")
