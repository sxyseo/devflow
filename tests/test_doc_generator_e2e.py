#!/usr/bin/env python3
"""
End-to-end test for DocumentationGeneratorAgent.

Tests the complete workflow: analyze → generate → validate
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path to import devflow modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.doc_generator import (
    DocumentationGeneratorAgent,
    DocGenerationRequest,
    DocWorkflowStatus
)


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def test_analyze_phase(agent, source_path):
    """Test the analyze phase of the workflow."""
    print_header("TEST 1: Analyze Phase")

    try:
        print_info(f"Analyzing codebase at: {source_path}")
        analysis = agent.analyze_codebase(source_path)

        # Verify analysis results
        assert 'files' in analysis, "Missing 'files' in analysis results"
        assert 'total_functions' in analysis, "Missing 'total_functions' in analysis results"
        assert 'total_classes' in analysis, "Missing 'total_classes' in analysis results"

        print_success(f"Analysis complete")
        print_success(f"  - Found {analysis['total_functions']} functions")
        print_success(f"  - Found {analysis['total_classes']} classes")
        print_success(f"  - Analyzed {len(analysis['files'])} Python files")

        return True, analysis

    except Exception as e:
        print_error(f"Analysis phase failed: {e}")
        return False, None


def test_generate_phase(agent, request):
    """Test the generate phase of the workflow."""
    print_header("TEST 2: Generate Phase")

    try:
        print_info(f"Generating documentation for: {request.doc_types}")

        # Create output directory if it doesn't exist
        os.makedirs(request.output_path, exist_ok=True)

        # Generate API documentation
        result = agent.generate_api_documentation(
            request.source_path,
            os.path.join(request.output_path, 'api.md')
        )

        # Verify generation results
        assert result.success, "Documentation generation failed"
        assert len(result.files_generated) > 0, "No files were generated"

        print_success(f"Generation complete")
        print_success(f"  - Generated {len(result.files_generated)} file(s)")
        for file_path in result.files_generated:
            print_success(f"  - {file_path}")

        # Verify generated file exists and has meaningful content
        for file_path in result.files_generated:
            assert os.path.exists(file_path), f"Generated file does not exist: {file_path}"

            # Check file has meaningful content
            with open(file_path, 'r') as f:
                content = f.read()

            assert len(content) > 100, f"File too short ({len(content)} bytes): {file_path}"
            assert "##" in content, f"Missing sections in {file_path}"

            # For API docs specifically, check for actual API content
            if 'api' in os.path.basename(file_path).lower():
                assert ("Class:" in content or "Function:" in content or "## File:" in content), \
                    f"Missing API documentation in {file_path}"

            print_success(f"  - File validation passed: {file_path}")

        return True, result

    except Exception as e:
        print_error(f"Generation phase failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_validate_phase(agent, generated_files):
    """Test the validate phase of the workflow."""
    print_header("TEST 3: Validate Phase")

    try:
        print_info(f"Validating {len(generated_files)} generated file(s)")

        # Validate each file
        all_valid = True
        for file_path in generated_files:
            if not os.path.exists(file_path):
                print_error(f"File does not exist: {file_path}")
                all_valid = False
                continue

            if os.path.getsize(file_path) == 0:
                print_error(f"File is empty: {file_path}")
                all_valid = False
                continue

            # Check file has meaningful content
            with open(file_path, 'r') as f:
                content = f.read()
                if len(content) < 100:
                    print_error(f"File has very little content ({len(content)} bytes): {file_path}")
                    all_valid = False
                elif "##" not in content:
                    print_error(f"File missing sections: {file_path}")
                    all_valid = False
                else:
                    print_success(f"File validated: {file_path}")

        if all_valid:
            print_success("All files validated successfully")
        else:
            print_error("Some files failed validation")

        return all_valid

    except Exception as e:
        print_error(f"Validation phase failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metrics_calculation(agent, analysis_results, generated_files):
    """Test metrics calculation."""
    print_header("TEST 4: Metrics Calculation")

    try:
        print_info("Calculating documentation metrics")

        metrics = agent._calculate_metrics(analysis_results, generated_files)

        # Verify metrics
        assert 'function_coverage' in metrics, "Missing 'function_coverage' metric"
        assert 'class_coverage' in metrics, "Missing 'class_coverage' metric"
        assert 'total_elements' in metrics, "Missing 'total_elements' metric"
        assert 'documented_elements' in metrics, "Missing 'documented_elements' metric"
        assert 'files_generated' in metrics, "Missing 'files_generated' metric"

        print_success("Metrics calculated successfully")
        print_success(f"  - Function coverage: {metrics['function_coverage']:.1f}%")
        print_success(f"  - Class coverage: {metrics['class_coverage']:.1f}%")
        print_success(f"  - Total elements: {metrics['total_elements']}")
        print_success(f"  - Documented elements: {metrics['documented_elements']}")
        print_success(f"  - Files generated: {metrics['files_generated']}")

        return True, metrics

    except Exception as e:
        print_error(f"Metrics calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_full_workflow(agent, request):
    """Test the complete end-to-end workflow."""
    print_header("TEST 5: Full End-to-End Workflow")

    try:
        print_info("Running complete workflow: analyze → generate → validate")

        result = agent.run_generation_workflow(request)

        # Verify workflow result
        assert result is not None, "Workflow result is None"
        assert result.status in [DocWorkflowStatus.COMPLETED, DocWorkflowStatus.FAILED], \
            f"Invalid workflow status: {result.status}"

        if result.success:
            print_success("Workflow completed successfully")
            print_success(f"  - Status: {result.status.value}")
            print_success(f"  - Duration: {result.duration:.2f}s")
            print_success(f"  - Files generated: {len(result.files_generated)}")

            if result.metrics:
                print_success(f"  - Metrics calculated: {len(result.metrics)} metrics")

            if result.errors:
                print_warning(f"  - Errors encountered: {len(result.errors)}")
                for error in result.errors:
                    print_warning(f"    - {error}")
        else:
            print_error("Workflow failed")
            if result.errors:
                for error in result.errors:
                    print_error(f"  - {error}")

        return result.success, result

    except Exception as e:
        print_error(f"Workflow execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_task_proposal(agent, source_path):
    """Test task proposal functionality."""
    print_header("TEST 6: Task Proposal")

    try:
        print_info("Generating documentation tasks")

        tasks = agent.propose_documentation_tasks(source_path)

        print_success(f"Task proposal completed")
        print_success(f"  - Generated {len(tasks)} task(s)")

        for task in tasks:
            print_success(f"  - Task {task.task_id}: {task.type}")
            print_success(f"    Priority: {task.priority}")
            print_success(f"    Reason: {task.reason}")

        # Check if tasks file was created
        tasks_file = agent.tasks_dir / 'documentation-tasks.json'
        if tasks_file.exists():
            print_success(f"  - Tasks saved to: {tasks_file}")
        else:
            print_warning(f"  - Tasks file not found: {tasks_file}")

        return True, tasks

    except Exception as e:
        print_error(f"Task proposal failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def main():
    """Run all end-to-end tests."""
    print_header("DocumentationGeneratorAgent E2E Test Suite")

    # Get the project root directory
    project_root = Path(__file__).parent.parent
    source_path = str(project_root / 'devflow' / 'core')

    # Create temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, 'docs')

        print_info(f"Project root: {project_root}")
        print_info(f"Source path: {source_path}")
        print_info(f"Output path: {output_path}")

        # Create agent
        print("\nInitializing DocumentationGeneratorAgent...")
        agent = DocumentationGeneratorAgent(project_path=str(project_root))
        print_success("Agent initialized")

        # Run tests
        test_results = []

        # Test 1: Analyze phase
        success, analysis = test_analyze_phase(agent, source_path)
        test_results.append(("Analyze Phase", success))

        if not success:
            print_error("Analyze phase failed, stopping tests")
            sys.exit(1)

        # Test 2: Generate phase
        request = DocGenerationRequest(
            source_path=source_path,
            output_path=output_path,
            doc_types=['api'],
            force_update=False,
            generate_metrics=True
        )
        success, gen_result = test_generate_phase(agent, request)
        test_results.append(("Generate Phase", success))

        if not success:
            print_error("Generate phase failed, continuing with remaining tests")

        # Test 3: Validate phase
        if gen_result and gen_result.files_generated:
            success = test_validate_phase(agent, gen_result.files_generated)
            test_results.append(("Validate Phase", success))
        else:
            print_warning("Skipping validate phase (no files generated)")
            test_results.append(("Validate Phase", False))

        # Test 4: Metrics calculation
        if gen_result:
            success, metrics = test_metrics_calculation(agent, analysis, gen_result.files_generated)
            test_results.append(("Metrics Calculation", success))
        else:
            print_warning("Skipping metrics calculation (no generation result)")
            test_results.append(("Metrics Calculation", False))

        # Test 5: Full workflow
        success, workflow_result = test_full_workflow(agent, request)
        test_results.append(("Full Workflow", success))

        # Test 6: Task proposal
        success, tasks = test_task_proposal(agent, source_path)
        test_results.append(("Task Proposal", success))

        # Print summary
        print_header("Test Summary")

        passed = sum(1 for _, success in test_results if success)
        total = len(test_results)

        for test_name, success in test_results:
            if success:
                print_success(f"{test_name}")
            else:
                print_error(f"{test_name}")

        print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.ENDC}")

        if passed == total:
            print_success("\n🎉 All tests passed!")
            return 0
        else:
            print_error(f"\n❌ {total - passed} test(s) failed")
            return 1


if __name__ == '__main__':
    sys.exit(main())
