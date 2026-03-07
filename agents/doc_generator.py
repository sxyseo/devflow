#!/usr/bin/env python3
"""
DevFlow - 文档生成器
自动分析代码并生成和维护文档
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict

from devflow.docs.analyzer import DocumentationAnalyzer
from devflow.docs.generator import DocumentationGenerator
from devflow.docs.metrics import DocumentationMetrics


@dataclass
class DocGenerationRequest:
    """文档生成请求"""
    source_path: str
    output_path: str
    doc_types: List[str]  # ['api', 'readme', 'architecture']
    force_update: bool = False
    generate_metrics: bool = True


@dataclass
class DocGenerationResult:
    """文档生成结果"""
    success: bool
    files_generated: List[str]
    metrics: Optional[Dict] = None
    errors: List[str] = None
    generated_at: str = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.generated_at is None:
            self.generated_at = datetime.now().isoformat()


@dataclass
class DocumentationTask:
    """文档更新任务"""
    task_id: str
    type: str  # 'update-api', 'update-readme', 'sync-architecture'
    file_path: str
    priority: str  # 'P0', 'P1', 'P2', 'P3'
    reason: str
    suggested_action: str
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class DocumentationGeneratorAgent:
    """文档生成器智能代理"""

    def __init__(self, project_path: str = None):
        """
        初始化文档生成器代理

        Args:
            project_path: 项目根目录路径
        """
        if project_path is None:
            # 默认使用当前工作目录的父目录
            self.project_path = Path.cwd()
        else:
            self.project_path = Path(project_path)

        # 初始化服务组件
        self.analyzer = DocumentationAnalyzer()
        self.generator = DocumentationGenerator()
        self.metrics = DocumentationMetrics()

        # 设置文档目录
        self.docs_dir = self.project_path / 'docs'
        self.docs_dir.mkdir(parents=True, exist_ok=True)

        # 任务输出目录
        self.tasks_dir = self.project_path / '.devflow' / 'tasks'
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def analyze_codebase(self, path: str = None) -> Dict:
        """
        分析代码库

        Args:
            path: 要分析的路径，默认为整个项目

        Returns:
            分析结果字典
        """
        if path is None:
            path = str(self.project_path)

        print(f"📖 分析代码库: {path}")

        # 分析Python代码
        python_files = list(Path(path).rglob('*.py'))
        print(f"  🔍 找到 {len(python_files)} 个Python文件")

        analysis_results = {
            'python_files': [],
            'javascript_files': [],
            'total_functions': 0,
            'total_classes': 0,
            'documented_functions': 0,
            'documented_classes': 0
        }

        for py_file in python_files:
            try:
                result = self.analyzer.analyze_python_file(str(py_file))
                analysis_results['python_files'].append(result)
                analysis_results['total_functions'] += len(result.get('functions', []))
                analysis_results['total_classes'] += len(result.get('classes', []))

                # 统计已文档化的元素
                for func in result.get('functions', []):
                    if func.get('has_docstring'):
                        analysis_results['documented_functions'] += 1

                for cls in result.get('classes', []):
                    if cls.get('has_docstring'):
                        analysis_results['documented_classes'] += 1

            except Exception as e:
                print(f"  ⚠️  分析文件失败 {py_file}: {e}")

        print(f"  ✅ 分析完成: {analysis_results['total_functions']} 个函数, {analysis_results['total_classes']} 个类")

        return analysis_results

    def detect_documentation_gaps(self, analysis_results: Dict) -> List[DocumentationTask]:
        """
        检测文档缺口

        Args:
            analysis_results: 代码分析结果

        Returns:
            文档更新任务列表
        """
        print("🔍 检测文档缺口...")

        tasks = []
        task_counter = 0

        # 检查未文档化的函数
        total_functions = analysis_results.get('total_functions', 0)
        documented_functions = analysis_results.get('documented_functions', 0)
        undocumented_functions = total_functions - documented_functions

        if undocumented_functions > 0:
            task_counter += 1
            task = DocumentationTask(
                task_id=f'doc-task-{task_counter}',
                type='update-api',
                file_path='docs/api.md',
                priority='P1',
                reason=f'发现 {undocumented_functions} 个未文档化的函数',
                suggested_action='为未文档化的函数添加docstring或生成API文档'
            )
            tasks.append(task)

        # 检查未文档化的类
        total_classes = analysis_results.get('total_classes', 0)
        documented_classes = analysis_results.get('documented_classes', 0)
        undocumented_classes = total_classes - documented_classes

        if undocumented_classes > 0:
            task_counter += 1
            task = DocumentationTask(
                task_id=f'doc-task-{task_counter}',
                type='update-api',
                file_path='docs/api.md',
                priority='P1',
                reason=f'发现 {undocumented_classes} 个未文档化的类',
                suggested_action='为未文档化的类添加docstring或生成API文档'
            )
            tasks.append(task)

        print(f"  📋 生成了 {len(tasks)} 个文档更新任务")

        return tasks

    def save_documentation_tasks(self, tasks: List[DocumentationTask]):
        """
        保存文档更新任务到文件

        Args:
            tasks: 文档更新任务列表
        """
        print("💾 保存文档更新任务...")

        tasks_file = self.tasks_dir / 'documentation-tasks.json'

        # 转换为字典
        tasks_data = [asdict(task) for task in tasks]

        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump({
                'created_at': datetime.now().isoformat(),
                'total_tasks': len(tasks),
                'tasks': tasks_data
            }, f, indent=2, ensure_ascii=False)

        print(f"  ✅ 任务已保存: {tasks_file}")

    def generate_api_documentation(self, source_path: str, output_path: str = None) -> DocGenerationResult:
        """
        生成API文档

        Args:
            source_path: 源代码路径
            output_path: 输出文件路径

        Returns:
            文档生成结果
        """
        print(f"📝 生成API文档...")

        if output_path is None:
            output_path = str(self.docs_dir / 'api.md')

        try:
            # 分析代码
            analysis = self.analyze_codebase(source_path)

            # 生成文档
            self.generator.generate_api_docs(analysis, output_path)

            print(f"  ✅ API文档已生成: {output_path}")

            return DocGenerationResult(
                success=True,
                files_generated=[output_path],
                metrics={
                    'total_functions': analysis.get('total_functions', 0),
                    'total_classes': analysis.get('total_classes', 0)
                }
            )

        except Exception as e:
            print(f"  ❌ 生成API文档失败: {e}")
            return DocGenerationResult(
                success=False,
                files_generated=[],
                errors=[str(e)]
            )

    def propose_documentation_tasks(self, path: str = None) -> List[DocumentationTask]:
        """
        提出文档更新任务

        Args:
            path: 要分析的路径

        Returns:
            文档更新任务列表
        """
        print("🎯 生成文档更新任务...")

        # 分析代码库
        analysis_results = self.analyze_codebase(path)

        # 检测文档缺口
        tasks = self.detect_documentation_gaps(analysis_results)

        # 保存任务
        self.save_documentation_tasks(tasks)

        return tasks

    def run_generation_workflow(self, request: DocGenerationRequest) -> DocGenerationResult:
        """
        运行文档生成工作流

        Args:
            request: 文档生成请求

        Returns:
            文档生成结果
        """
        print("🚀 开始文档生成工作流...")
        print(f"  📂 源路径: {request.source_path}")
        print(f"  📄 输出路径: {request.output_path}")
        print(f"  📝 文档类型: {', '.join(request.doc_types)}")

        generated_files = []
        errors = []
        metrics = {}

        try:
            # 1. 分析代码
            analysis = self.analyze_codebase(request.source_path)

            # 2. 生成各种类型的文档
            for doc_type in request.doc_types:
                if doc_type == 'api':
                    result = self.generate_api_documentation(
                        request.source_path,
                        str(Path(request.output_path) / 'api.md')
                    )
                    if result.success:
                        generated_files.extend(result.files_generated)
                    else:
                        errors.extend(result.errors)

                elif doc_type == 'readme':
                    # TODO: 实现README生成
                    print("  ⚠️  README生成尚未实现")
                    pass

                elif doc_type == 'architecture':
                    # TODO: 实现架构图生成
                    print("  ⚠️  架构图生成尚未实现")
                    pass

            # 3. 生成指标
            if request.generate_metrics:
                print("📊 计算文档指标...")
                # TODO: 实现指标计算
                metrics['coverage'] = '计算中...'

            print(f"\n✅ 工作流完成! 生成了 {len(generated_files)} 个文件")

            return DocGenerationResult(
                success=len(errors) == 0,
                files_generated=generated_files,
                metrics=metrics if metrics else None,
                errors=errors if errors else None
            )

        except Exception as e:
            print(f"❌ 工作流失败: {e}")
            return DocGenerationResult(
                success=False,
                files_generated=generated_files,
                errors=[str(e)]
            )

    def incremental_update(self, path: str = None) -> DocGenerationResult:
        """
        增量更新文档（只更新有变化的文档）

        Args:
            path: 要检查的路径

        Returns:
            文档生成结果
        """
        print("🔄 检查文档更新...")

        if path is None:
            path = str(self.project_path)

        try:
            # 检测代码变化
            changes = self.analyzer.detect_changes(path)

            if not changes:
                print("  ✅ 没有检测到代码变化，无需更新文档")
                return DocGenerationResult(
                    success=True,
                    files_generated=[]
                )

            print(f"  📝 检测到 {len(changes)} 个文件变化")

            # 只更新变化文件的文档
            generated_files = []
            for change in changes:
                print(f"  更新文档: {change['file_path']}")

                # TODO: 实现增量更新逻辑
                # 这里应该只重新生成受影响部分的文档

            return DocGenerationResult(
                success=True,
                files_generated=generated_files
            )

        except Exception as e:
            print(f"  ❌ 增量更新失败: {e}")
            return DocGenerationResult(
                success=False,
                files_generated=[],
                errors=[str(e)]
            )


if __name__ == '__main__':
    import sys

    # 测试基本功能
    print("🧪 测试 DocumentationGeneratorAgent\n")

    # 创建代理
    agent = DocumentationGeneratorAgent()

    # 测试1: 分析代码库
    print("=" * 60)
    print("测试1: 分析代码库")
    print("=" * 60)
    analysis = agent.analyze_codebase('./devflow')
    print(f"\n结果: {analysis['total_functions']} 个函数, {analysis['total_classes']} 个类\n")

    # 测试2: 检测文档缺口
    print("=" * 60)
    print("测试2: 检测文档缺口")
    print("=" * 60)
    tasks = agent.detect_documentation_gaps(analysis)
    print(f"\n生成了 {len(tasks)} 个文档更新任务\n")

    # 测试3: 提出文档任务
    print("=" * 60)
    print("测试3: 提出文档任务")
    print("=" * 60)
    proposed_tasks = agent.propose_documentation_tasks('./devflow')
    print(f"\n提出了 {len(proposed_tasks)} 个任务\n")

    print("✅ 所有测试完成!")
