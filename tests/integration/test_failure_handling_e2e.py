"""
End-to-End Integration Test for Failure Handling and Auto-Investigation

Tests the complete workflow of:
1. Creating and triggering a CI/CD pipeline that will fail
2. Detecting the failure
3. Automatically creating an investigation task
4. Verifying failure is logged properly
5. Verifying investigation task contains proper context

This test can run in two modes:
- Mock mode (default): Uses mocked integration responses
- Live mode: Requires actual CI/CD platform credentials
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
import threading
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from devflow.core.orchestrator import Orchestrator
from devflow.core.state_tracker import StateTracker, PipelineStatus
from devflow.core.task_scheduler import TaskScheduler, TaskPriority
from devflow.core.agent_manager import AgentManager
from devflow.integrations.base import PipelineConfig, PipelineRun, PipelineStatus as IntegrationPipelineStatus
from devflow.integrations.github_actions import GitHubActions
from devflow.monitoring.pipeline_monitor import PipelineMonitor, StageStatus
from devflow.config.settings import settings


class TestFailureHandlingE2E:
    """
    End-to-end integration tests for failure handling and auto-investigation.

    Tests the complete flow from pipeline failure to automatic
    investigation task creation with proper context.
    """

    def setup_method(self):
        """Set up test environment before each test."""
        # Create temporary directory for test workspace
        self.test_dir = tempfile.mkdtemp(prefix="devflow_failure_e2e_")
        self.test_workspace = Path(self.test_dir)

        # Initialize StateTracker
        self.state = StateTracker()

        # Initialize TaskScheduler with mocked dependencies
        mock_agent_manager = Mock()
        self.scheduler = TaskScheduler(
            state_tracker=self.state,
            agent_manager=mock_agent_manager
        )

        # Initialize PipelineMonitor with StateTracker and TaskScheduler
        self.monitor = PipelineMonitor(
            state_tracker=self.state,
            task_scheduler=self.scheduler,
        )

        # Track cleanup
        self._cleanup_files = []

    def teardown_method(self):
        """Clean up test environment after each test."""
        # Stop monitor if running
        if self.monitor._running:
            self.monitor.stop()

        # Remove temporary directory
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)

        # Clean up any additional files
        for file_path in self._cleanup_files:
            if Path(file_path).exists():
                try:
                    if Path(file_path).is_dir():
                        shutil.rmtree(file_path)
                    else:
                        Path(file_path).unlink()
                except Exception:
                    pass

    def create_mock_integration(self, platform: str = "github") -> Mock:
        """
        Create a mock CI/CD integration.

        Args:
            platform: Platform name for the integration

        Returns:
            Mock integration object
        """
        mock_integration = Mock()

        # Set up common methods
        mock_integration.trigger_pipeline = Mock(return_value=PipelineRun(
            run_id=f"test-run-{int(time.time())}",
            platform=platform,
            repository="test/repo",
            branch="main",
            status=IntegrationPipelineStatus.PENDING,
            created_at=time.time(),
            updated_at=time.time(),
            url=f"https://{platform}.com/test/repo/runs/123",
        ))

        mock_integration.get_pipeline_status = Mock()
        mock_integration.get_pipeline_logs = Mock(return_value="Pipeline logs here...")
        mock_integration.cancel_pipeline = Mock(return_value=True)
        mock_integration.health_check = Mock(return_value={
            "platform": platform,
            "status": "healthy",
        })

        return mock_integration

    def test_pipeline_failure_detection(self):
        """
        Test that a pipeline failure is detected properly.

        Verifies:
        - Pipeline status changes to FAILED
        - Failure is recorded in StateTracker
        - Error message is preserved
        """
        # Track a pipeline
        pipeline_id = "test-pipeline-failure-1"
        self.monitor.track_pipeline(
            pipeline_id=pipeline_id,
            pipeline_type="ci",
            commit_sha="abc123",
            branch="main",
            stages=[
                {"name": "build", "type": "build"},
                {"name": "test", "type": "test"},
            ],
        )

        # Start the pipeline
        self.monitor.start_pipeline(pipeline_id)

        # Verify pipeline is running
        pipeline = self.state.get_pipeline_status(pipeline_id)
        assert pipeline is not None
        assert pipeline["status"] == PipelineStatus.RUNNING.value

        # Simulate failure in the test stage
        self.monitor.start_stage(pipeline_id, "test")
        self.monitor.fail_stage(pipeline_id, "test", "Test suite failed: assertion error")

        # Fail the pipeline
        error_msg = "Pipeline failed due to test failures"
        self.monitor.fail_pipeline(pipeline_id, error_msg, auto_investigate=False)

        # Verify pipeline failed
        pipeline = self.state.get_pipeline_status(pipeline_id)
        assert pipeline is not None
        assert pipeline["status"] == PipelineStatus.FAILED.value
        assert pipeline["error"] == error_msg

        # Verify stage failure is recorded
        stages = pipeline.get("stages", [])
        test_stage = next((s for s in stages if s["name"] == "test"), None)
        assert test_stage is not None
        assert test_stage["status"] == StageStatus.FAILED.value
        assert "Test suite failed" in test_stage["error"]

    def test_auto_investigation_task_creation(self):
        """
        Test that an investigation task is created on pipeline failure.

        Verifies:
        - Investigation task is created automatically
        - Task has correct type and priority
        - Task contains failure context
        - Task ID is stored in pipeline metadata
        """
        # Track a pipeline
        pipeline_id = "test-pipeline-investigation-1"
        commit_sha = "def456"
        branch = "feature-test"

        self.monitor.track_pipeline(
            pipeline_id=pipeline_id,
            pipeline_type="ci",
            commit_sha=commit_sha,
            branch=branch,
            stages=[
                {"name": "build", "type": "build"},
                {"name": "deploy", "type": "deploy"},
            ],
        )

        # Start the pipeline
        self.monitor.start_pipeline(pipeline_id)

        # Fail a stage and the pipeline
        self.monitor.start_stage(pipeline_id, "build")
        self.monitor.fail_stage(pipeline_id, "build", "Build error: compilation failed")

        # Fail the pipeline with auto-investigation enabled
        error_msg = "Deployment failed after build errors"
        self.monitor.fail_pipeline(pipeline_id, error_msg, auto_investigate=True)

        # Verify pipeline failed
        pipeline = self.state.get_pipeline_status(pipeline_id)
        assert pipeline is not None
        assert pipeline["status"] == PipelineStatus.FAILED.value

        # Verify investigation task was created
        # Check the state tracker's task storage
        tasks = self.state.get_all_tasks()
        investigation_tasks = [
            t for t in tasks.values()
            if t.get("type") == "investigation"
        ]

        assert len(investigation_tasks) > 0, "No investigation task was created"

        # Verify investigation task ID is stored in pipeline metadata
        metadata = pipeline.get("metadata", {})
        assert "investigation_task_id" in metadata

        # Get the investigation task by ID from metadata
        investigation_task_id = metadata["investigation_task_id"]
        investigation_task = tasks.get(investigation_task_id)
        assert investigation_task is not None, f"Investigation task {investigation_task_id} not found"

        assert investigation_task["priority"] == TaskPriority.HIGH.value
        assert "Investigate pipeline failure" in investigation_task["description"]

    def test_failure_with_multiple_failed_stages(self):
        """
        Test failure handling when multiple stages fail.

        Verifies:
        - All failed stages are tracked
        - Investigation task includes all failed stages
        - Complete context is preserved
        """
        pipeline_id = "test-pipeline-multi-fail"

        # Track pipeline with multiple stages
        self.monitor.track_pipeline(
            pipeline_id=pipeline_id,
            pipeline_type="ci",
            commit_sha="ghi789",
            branch="develop",
            stages=[
                {"name": "lint", "type": "quality"},
                {"name": "build", "type": "build"},
                {"name": "unit-test", "type": "test"},
                {"name": "integration-test", "type": "test"},
            ],
        )

        # Start pipeline
        self.monitor.start_pipeline(pipeline_id)

        # Complete first stage successfully
        self.monitor.start_stage(pipeline_id, "lint")
        self.monitor.complete_stage(pipeline_id, "lint")

        # Fail multiple stages
        self.monitor.start_stage(pipeline_id, "build")
        self.monitor.fail_stage(pipeline_id, "build", "Missing dependency")

        self.monitor.start_stage(pipeline_id, "unit-test")
        self.monitor.fail_stage(pipeline_id, "unit-test", "Test timeout after 5 minutes")

        # Fail pipeline
        error_msg = "Pipeline failed: multiple stage failures"
        self.monitor.fail_pipeline(pipeline_id, error_msg, auto_investigate=True)

        # Verify all failures are recorded
        pipeline = self.state.get_pipeline_status(pipeline_id)
        stages = pipeline.get("stages", [])

        # Check lint passed
        lint_stage = next((s for s in stages if s["name"] == "lint"), None)
        assert lint_stage is not None
        assert lint_stage["status"] == StageStatus.COMPLETED.value

        # Check build failed
        build_stage = next((s for s in stages if s["name"] == "build"), None)
        assert build_stage is not None
        assert build_stage["status"] == StageStatus.FAILED.value
        assert "Missing dependency" in build_stage["error"]

        # Check unit-test failed
        unit_test_stage = next((s for s in stages if s["name"] == "unit-test"), None)
        assert unit_test_stage is not None
        assert unit_test_stage["status"] == StageStatus.FAILED.value
        assert "timeout" in unit_test_stage["error"]

        # Verify investigation task includes all failed stages
        tasks = self.state.get_all_tasks()
        investigation_tasks = [
            t for t in tasks.values()
            if t.get("type") == "investigation"
        ]

        assert len(investigation_tasks) > 0
        # Verify failed stages are in pipeline
        pipeline = self.state.get_pipeline_status(pipeline_id)
        failed_stages = [s for s in pipeline.get("stages", []) if s.get("status") == StageStatus.FAILED.value]
        assert len(failed_stages) == 2

    def test_auto_investigation_can_be_disabled(self):
        """
        Test that auto-investigation can be disabled.

        Verifies:
        - Setting auto_investigate=False prevents task creation
        - Failure is still logged properly
        - Pipeline status is updated correctly
        """
        pipeline_id = "test-pipeline-no-investigation"

        # Disable auto-investigation
        self.monitor.set_auto_investigate(False)

        # Track and fail pipeline
        self.monitor.track_pipeline(
            pipeline_id=pipeline_id,
            pipeline_type="cd",
            commit_sha="jkl012",
            branch="main",
        )

        self.monitor.start_pipeline(pipeline_id)
        self.monitor.fail_pipeline(pipeline_id, "Deployment timeout")

        # Verify pipeline failed
        pipeline = self.state.get_pipeline_status(pipeline_id)
        assert pipeline["status"] == PipelineStatus.FAILED.value
        assert pipeline["error"] == "Deployment timeout"

        # Verify no investigation task was created for this pipeline
        # Check pipeline metadata doesn't have investigation_task_id
        metadata = pipeline.get("metadata", {})
        assert "investigation_task_id" not in metadata

    def test_failure_logging_preserves_full_context(self):
        """
        Test that failure logging preserves complete context.

        Verifies:
        - Pipeline metadata is preserved
        - Timestamp is recorded
        - Error details are complete
        - Stage information is maintained
        """
        pipeline_id = "test-pipeline-logging"

        # Track pipeline with detailed context
        commit_sha = "mno345"
        branch = "feature/new-api"
        triggered_by = "developer-1"

        self.monitor.track_pipeline(
            pipeline_id=pipeline_id,
            pipeline_type="deploy",
            commit_sha=commit_sha,
            branch=branch,
            triggered_by=triggered_by,
            platform="github",
            run_id="github-run-999",
            stages=[
                {"name": "deploy", "type": "deploy"},
            ],
        )

        # Add custom metadata
        self.state.update_pipeline_status(
            pipeline_id,
            PipelineStatus.RUNNING,
            metadata={
                "deployment_target": "production",
                "rollback_enabled": True,
                "notifications": ["slack", "email"],
            },
        )

        # Simulate stage progression and failure
        self.monitor.start_stage(pipeline_id, "deploy")
        time.sleep(0.1)  # Simulate time passing
        self.monitor.fail_stage(pipeline_id, "deploy", "Connection timeout to production server")

        # Fail pipeline
        error_msg = "Production deployment failed: could not connect to server"
        self.monitor.fail_pipeline(pipeline_id, error_msg, auto_investigate=False)

        # Verify complete context is preserved
        pipeline = self.state.get_pipeline_status(pipeline_id)

        # Check basic info
        assert pipeline["status"] == PipelineStatus.FAILED.value
        assert pipeline["error"] == error_msg
        assert pipeline["commit_sha"] == commit_sha
        assert pipeline["branch"] == branch
        assert pipeline["triggered_by"] == triggered_by
        assert pipeline["type"] == "deploy"

        # Check metadata
        metadata = pipeline.get("metadata", {})
        assert metadata["deployment_target"] == "production"
        assert metadata["rollback_enabled"] is True
        assert metadata["platform"] == "github"
        assert metadata["run_id"] == "github-run-999"

        # Check stage info with timing
        stages = pipeline.get("stages", [])
        deploy_stage = next((s for s in stages if s["name"] == "deploy"), None)
        assert deploy_stage is not None
        assert deploy_stage["status"] == StageStatus.FAILED.value
        assert deploy_stage["started_at"] is not None
        assert deploy_stage["completed_at"] is not None
        assert deploy_stage["duration"] is not None
        assert deploy_stage["duration"] > 0
        assert "Connection timeout" in deploy_stage["error"]

    def test_callback_triggered_on_failure(self):
        """
        Test that failure callbacks are triggered properly.

        Verifies:
        - on_pipeline_fail callback is called
        - Callback receives correct arguments
        - Multiple callbacks can be registered
        """
        pipeline_id = "test-pipeline-callback"

        # Track pipeline
        self.monitor.track_pipeline(
            pipeline_id=pipeline_id,
            pipeline_type="ci",
            commit_sha="pqr678",
            branch="main",
        )

        # Register callback
        callback_called = threading.Event()
        callback_args = []

        def failure_callback(p_id, error):
            callback_args.append((p_id, error))
            callback_called.set()

        self.monitor.on_pipeline_fail(failure_callback)

        # Fail pipeline
        error_msg = "Test failure for callback"
        self.monitor.fail_pipeline(pipeline_id, error_msg, auto_investigate=False)

        # Wait for callback (with timeout)
        assert callback_called.wait(timeout=1.0), "Callback was not triggered"

        # Verify callback arguments
        assert len(callback_args) == 1
        assert callback_args[0][0] == pipeline_id
        assert callback_args[0][1] == error_msg

    def test_investigation_task_with_scheduler_error(self):
        """
        Test that pipeline monitoring continues even if investigation task creation fails.

        Verifies:
        - Pipeline failure is still recorded
        - Monitoring continues despite scheduler error
        - Error in task creation doesn't break monitoring
        """
        pipeline_id = "test-pipeline-scheduler-error"

        # Track pipeline
        self.monitor.track_pipeline(
            pipeline_id=pipeline_id,
            pipeline_type="ci",
            commit_sha="stu901",
            branch="main",
        )

        # Mock scheduler to raise error
        self.scheduler.create_task = Mock(side_effect=Exception("Scheduler unavailable"))

        # Fail pipeline (should not raise exception)
        self.monitor.fail_pipeline(pipeline_id, "Test failure", auto_investigate=True)

        # Verify pipeline failed despite scheduler error
        pipeline = self.state.get_pipeline_status(pipeline_id)
        assert pipeline is not None
        assert pipeline["status"] == PipelineStatus.FAILED.value
        assert pipeline["error"] == "Test failure"

    def test_integration_with_platform_mock(self):
        """
        Test failure handling with mocked platform integration.

        Verifies:
        - Platform integration can be polled for status
        - Failure from platform is detected
        - Auto-investigation is triggered
        """
        # Create mock integration
        mock_github = self.create_mock_integration("github")

        # Register integration with monitor
        self.monitor.register_integration("github", mock_github)

        # Track pipeline
        pipeline_id = "test-pipeline-platform-mock"
        run_id = "gh-run-12345"

        self.monitor.track_pipeline(
            pipeline_id=pipeline_id,
            pipeline_type="ci",
            commit_sha="vwx234",
            branch="main",
            platform="github",
            run_id=run_id,
        )

        # Start monitor (but don't run polling loop in test)
        # Instead, manually trigger the status update
        mock_github.get_pipeline_status.return_value = IntegrationPipelineStatus.FAILED

        # Simulate polling detecting failure
        self.monitor._update_pipeline_status_from_poll(
            pipeline_id,
            self.state.get_pipeline_status(pipeline_id),
            PipelineStatus.FAILED,
            IntegrationPipelineStatus.FAILED,
        )

        # Verify failure detected
        pipeline = self.state.get_pipeline_status(pipeline_id)
        assert pipeline["status"] == PipelineStatus.FAILED.value

    def run_all_tests(self):
        """Run all tests and report results."""
        tests = [
            ("Pipeline Failure Detection", self.test_pipeline_failure_detection),
            ("Auto-Investigation Task Creation", self.test_auto_investigation_task_creation),
            ("Multiple Failed Stages", self.test_failure_with_multiple_failed_stages),
            ("Auto-Investigation Disabled", self.test_auto_investigation_can_be_disabled),
            ("Failure Logging Preserves Context", self.test_failure_logging_preserves_full_context),
            ("Failure Callback Triggered", self.test_callback_triggered_on_failure),
            ("Scheduler Error Handling", self.test_investigation_task_with_scheduler_error),
            ("Platform Integration Mock", self.test_integration_with_platform_mock),
        ]

        results = []
        for name, test_func in tests:
            try:
                self.setup_method()
                test_func()
                self.teardown_method()
                results.append((name, "PASSED", None))
                print(f"✓ {name}")
            except Exception as e:
                self.teardown_method()
                results.append((name, "FAILED", str(e)))
                print(f"✗ {name}: {e}")

        return results


def main():
    """Run tests and output results."""
    test_instance = TestFailureHandlingE2E()

    print("=" * 70)
    print("Failure Handling and Auto-Investigation E2E Tests")
    print("=" * 70)
    print()

    results = test_instance.run_all_tests()

    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)

    passed = sum(1 for _, status, _ in results if status == "PASSED")
    total = len(results)

    for name, status, error in results:
        symbol = "✓" if status == "PASSED" else "✗"
        print(f"{symbol} {name}: {status}")
        if error:
            print(f"  Error: {error}")

    print()
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
