#!/usr/bin/env python3
"""
DevFlow - 文档生成器
自动分析代码并生成和维护文档
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import time

from devflow.docs.analyzer import DocumentationAnalyzer
from devflow.docs.generator import DocumentationGenerator
from devflow.docs.metrics import DocumentationMetrics


class DocWorkflowStatus(Enum):
    """Status of the documentation generation workflow."""
    IDLE = "idle"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


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
    status: DocWorkflowStatus
    duration: float
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

        # 回调函数列表
        self._callbacks: List[Callable[[DocGenerationResult], None]] = []

    def add_callback(self, callback: Callable[[DocGenerationResult], None]):
        """
        添加回调函数，在文档生成完成后调用

        Args:
            callback: 回调函数，接收 DocGenerationResult 参数
        """
        self._callbacks.append(callback)

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
        运行文档生成工作流 (analyze → generate → validate)

        Args:
            request: 文档生成请求

        Returns:
            文档生成结果
        """
        start_time = time.time()

        print("🚀 开始文档生成工作流...")
        print(f"  📂 源路径: {request.source_path}")
        print(f"  📄 输出路径: {request.output_path}")
        print(f"  📝 文档类型: {', '.join(request.doc_types)}")

        generated_files = []
        errors = []
        metrics = {}
        analysis_results = {}

        try:
            # Phase 1: Analyze
            print(f"\n📖 Phase 1: Analyzing codebase...")
            analysis_results = self._analyze_phase(request)

            if not analysis_results:
                return DocGenerationResult(
                    success=False,
                    files_generated=[],
                    status=DocWorkflowStatus.FAILED,
                    duration=time.time() - start_time,
                    errors=["Analysis phase failed"]
                )

            # Phase 2: Generate
            print(f"\n📝 Phase 2: Generating documentation...")
            generation_results = self._generate_phase(request, analysis_results)

            if generation_results['success']:
                generated_files.extend(generation_results['files'])
            else:
                errors.extend(generation_results.get('errors', []))

            # Phase 3: Validate
            print(f"\n✅ Phase 3: Validating documentation...")
            validation_results = self._validate_phase(request, generated_files)

            # Calculate metrics
            if request.generate_metrics:
                print(f"\n📊 Calculating metrics...")
                metrics = self._calculate_metrics(analysis_results, generated_files)

            # Determine overall status
            success = len(errors) == 0 and validation_results['valid']
            status = DocWorkflowStatus.COMPLETED if success else DocWorkflowStatus.FAILED

            print(f"\n{'✅' if success else '⚠️'}  Workflow completed!")
            print(f"  Generated: {len(generated_files)} files")
            print(f"  Validation: {'Passed' if validation_results['valid'] else 'Failed'}")
            if validation_results.get('warnings'):
                print(f"  Warnings: {len(validation_results['warnings'])}")

            # Create result
            result = DocGenerationResult(
                success=success,
                files_generated=generated_files,
                status=status,
                duration=time.time() - start_time,
                metrics=metrics if metrics else None,
                errors=errors if errors else None
            )

            # Notify callbacks
            for callback in self._callbacks:
                callback(result)

            return result

        except Exception as e:
            print(f"❌ Workflow failed: {e}")
            result = DocGenerationResult(
                success=False,
                files_generated=generated_files,
                status=DocWorkflowStatus.FAILED,
                duration=time.time() - start_time,
                errors=[str(e)]
            )

            # Notify callbacks even on failure
            for callback in self._callbacks:
                callback(result)

            return result

    def _analyze_phase(self, request: DocGenerationRequest) -> Dict:
        """
        分析阶段：分析代码库

        Args:
            request: 文档生成请求

        Returns:
            分析结果字典
        """
        try:
            analysis = self.analyze_codebase(request.source_path)
            print(f"  ✓ Analyzed {analysis.get('total_functions', 0)} functions, "
                  f"{analysis.get('total_classes', 0)} classes")
            return analysis
        except Exception as e:
            print(f"  ✗ Analysis failed: {e}")
            return {}

    def _generate_phase(self, request: DocGenerationRequest,
                       analysis_results: Dict) -> Dict:
        """
        生成阶段：生成各种类型的文档

        Args:
            request: 文档生成请求
            analysis_results: 分析结果

        Returns:
            生成结果字典 {'success': bool, 'files': List[str], 'errors': List[str]}
        """
        generated_files = []
        errors = []

        try:
            for doc_type in request.doc_types:
                if doc_type == 'api':
                    result = self.generate_api_documentation(
                        request.source_path,
                        str(Path(request.output_path) / 'api.md')
                    )
                    if result.success:
                        generated_files.extend(result.files_generated)
                        print(f"  ✓ Generated API documentation")
                    else:
                        errors.extend(result.errors)
                        print(f"  ✗ Failed to generate API documentation")

                elif doc_type == 'readme':
                    # TODO: 实现README生成
                    print(f"  ⚠ README generation not yet implemented")

                elif doc_type == 'architecture':
                    # TODO: 实现架构图生成
                    print(f"  ⚠ Architecture documentation not yet implemented")

        except Exception as e:
            errors.append(str(e))
            print(f"  ✗ Generation phase failed: {e}")

        return {
            'success': len(errors) == 0,
            'files': generated_files,
            'errors': errors
        }

    def _validate_phase(self, request: DocGenerationRequest,
                       generated_files: List[str]) -> Dict:
        """
        验证阶段：验证生成的文档

        Args:
            request: 文档生成请求
            generated_files: 生成的文件列表

        Returns:
            验证结果字典 {'valid': bool, 'warnings': List[str]}
        """
        warnings = []
        valid = True

        try:
            # Check if any files were generated
            if not generated_files:
                warnings.append("No documentation files were generated")
                valid = False
            else:
                print(f"  ✓ Generated {len(generated_files)} documentation files")

            # Validate each generated file exists and is not empty
            for file_path in generated_files:
                path = Path(file_path)
                if not path.exists():
                    warnings.append(f"Generated file does not exist: {file_path}")
                    valid = False
                elif path.stat().st_size == 0:
                    warnings.append(f"Generated file is empty: {file_path}")
                    valid = False

            # Check documentation coverage
            if len(generated_files) < len(request.doc_types):
                missing_types = len(request.doc_types) - len(generated_files)
                warnings.append(f"{missing_types} documentation type(s) not generated")

            if valid:
                print(f"  ✓ Validation passed")
            else:
                print(f"  ⚠ Validation completed with {len(warnings)} warning(s)")

        except Exception as e:
            print(f"  ✗ Validation failed: {e}")
            valid = False
            warnings.append(str(e))

        return {
            'valid': valid,
            'warnings': warnings
        }

    def _calculate_metrics(self, analysis_results: Dict,
                          generated_files: List[str]) -> Dict:
        """
        计算文档指标

        Args:
            analysis_results: 分析结果
            generated_files: 生成的文件列表

        Returns:
            指标字典
        """
        metrics = {}

        try:
            # Coverage metrics
            total_functions = analysis_results.get('total_functions', 0)
            total_classes = analysis_results.get('total_classes', 0)
            documented_functions = analysis_results.get('documented_functions', 0)
            documented_classes = analysis_results.get('documented_classes', 0)

            metrics['function_coverage'] = (
                documented_functions / total_functions * 100
                if total_functions > 0 else 0
            )
            metrics['class_coverage'] = (
                documented_classes / total_classes * 100
                if total_classes > 0 else 0
            )
            metrics['total_elements'] = total_functions + total_classes
            metrics['documented_elements'] = documented_functions + documented_classes

            # Generation metrics
            metrics['files_generated'] = len(generated_files)
            metrics['avg_file_size'] = 0
            if generated_files:
                total_size = sum(Path(f).stat().st_size for f in generated_files if Path(f).exists())
                metrics['avg_file_size'] = total_size / len(generated_files)

            print(f"  ✓ Function coverage: {metrics['function_coverage']:.1f}%")
            print(f"  ✓ Class coverage: {metrics['class_coverage']:.1f}%")

        except Exception as e:
            print(f"  ⚠ Failed to calculate metrics: {e}")
            metrics['error'] = str(e)

        return metrics

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
