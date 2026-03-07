"""
Pipeline Monitor - Tracks and monitors CI/CD pipeline execution.

Provides real-time monitoring of pipeline progress, stage completion,
and metrics collection.
"""

import threading
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ..core.state_tracker import StateTracker, PipelineStatus
from ..core.task_scheduler import TaskScheduler, TaskPriority


class StageStatus(Enum):
    """Pipeline stage execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineStage:
    """A stage within a CI/CD pipeline."""
    name: str
    stage_type: str
    order: int
    status: str = StageStatus.PENDING.value
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration: Optional[float] = None
    logs: List[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "stage_type": self.stage_type,
            "order": self.order,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration": self.duration,
            "logs": self.logs,
            "error": self.error,
            "metadata": self.metadata,
        }


class PipelineMonitor:
    """
    Monitors CI/CD pipeline execution and progress.

    Features:
    - Real-time pipeline tracking
    - Stage-level monitoring
    - Automatic status updates
    - Metrics collection
    - Event notifications
    """

    def __init__(self, state_tracker: StateTracker, integrations: Dict[str, Any] = None,
                 task_scheduler: TaskScheduler = None):
        """
        Initialize the pipeline monitor.

        Args:
            state_tracker: StateTracker instance for system state
            integrations: Dictionary of platform name to integration instance
                         (e.g., {"github": github_integration_instance})
            task_scheduler: Optional TaskScheduler for creating investigation tasks
        """
        self.state = state_tracker
        self.integrations = integrations or {}
        self.scheduler = task_scheduler
        self.lock = threading.Lock()
        self._running = False
        self._monitor_thread = None

        # Polling configuration
        self._poll_interval = 30  # seconds between status polls
        self._health_check_interval = 60  # seconds between health checks

        # Auto-investigation settings
        self._auto_investigate = True  # Automatically create investigation tasks on failure

        # Callbacks for pipeline events
        self._on_pipeline_start: Optional[Callable] = None
        self._on_pipeline_complete: Optional[Callable] = None
        self._on_pipeline_fail: Optional[Callable] = None
        self._on_stage_start: Optional[Callable] = None
        self._on_stage_complete: Optional[Callable] = None

    def start(self, poll_interval: int = 30):
        """
        Start the pipeline monitor.

        Args:
            poll_interval: Seconds between status polls (default: 30)
        """
        if self._running:
            return

        self._poll_interval = poll_interval
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def register_integration(self, platform: str, integration: Any):
        """
        Register a CI/CD platform integration.

        Args:
            platform: Platform name (e.g., "github", "gitlab", "jenkins")
            integration: Integration instance
        """
        self.integrations[platform] = integration

    def unregister_integration(self, platform: str):
        """
        Unregister a CI/CD platform integration.

        Args:
            platform: Platform name to remove
        """
        if platform in self.integrations:
            del self.integrations[platform]

    def stop(self):
        """Stop the pipeline monitor."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
            self._monitor_thread = None

    def track_pipeline(self, pipeline_id: str, pipeline_type: str,
                      commit_sha: str, branch: str,
                      stages: List[Dict[str, Any]] = None,
                      triggered_by: str = None,
                      platform: str = None,
                      run_id: str = None) -> str:
        """
        Start tracking a new pipeline.

        Args:
            pipeline_id: Unique pipeline identifier
            pipeline_type: Type of pipeline (e.g., "ci", "cd", "deploy")
            commit_sha: Git commit SHA being built
            branch: Git branch name
            stages: List of stage definitions
            triggered_by: User or system that triggered the pipeline
            platform: CI/CD platform name (e.g., "github", "gitlab")
            run_id: External pipeline run ID for polling

        Returns:
            Pipeline ID
        """
        # Create pipeline in state tracker
        self.state.create_pipeline(
            pipeline_id=pipeline_id,
            pipeline_type=pipeline_type,
            commit_sha=commit_sha,
            branch=branch,
            triggered_by=triggered_by,
        )

        # Store platform and run_id in metadata for polling
        if platform or run_id:
            metadata = {}
            if platform:
                metadata["platform"] = platform
            if run_id:
                metadata["run_id"] = run_id

            self.state.update_pipeline_status(
                pipeline_id,
                PipelineStatus.PENDING,
                metadata=metadata,
            )

        # Initialize stages if provided
        if stages:
            self._initialize_stages(pipeline_id, stages)

        return pipeline_id

    def _initialize_stages(self, pipeline_id: str, stage_defs: List[Dict[str, Any]]):
        """Initialize pipeline stages."""
        with self.lock:
            pipeline = self.state.get_pipeline_status(pipeline_id)
            if not pipeline:
                return

            stages = []
            for idx, stage_def in enumerate(stage_defs):
                stage = PipelineStage(
                    name=stage_def.get("name", f"stage_{idx}"),
                    stage_type=stage_def.get("type", "generic"),
                    order=idx,
                    metadata=stage_def.get("metadata", {}),
                )
                stages.append(stage.to_dict())

            # Update pipeline with stages
            self.state.update_pipeline_status(
                pipeline_id,
                PipelineStatus.PENDING,
                stages=stages,
            )

    def start_pipeline(self, pipeline_id: str):
        """
        Mark a pipeline as started.

        Args:
            pipeline_id: Pipeline identifier
        """
        self.state.update_pipeline_status(pipeline_id, PipelineStatus.RUNNING)

        # Trigger callback if set
        if self._on_pipeline_start:
            try:
                self._on_pipeline_start(pipeline_id)
            except Exception as e:
                pass  # Don't let callback errors break monitoring

    def complete_pipeline(self, pipeline_id: str, result: Any = None):
        """
        Mark a pipeline as completed.

        Args:
            pipeline_id: Pipeline identifier
            result: Optional result data
        """
        self.state.update_pipeline_status(
            pipeline_id,
            PipelineStatus.COMPLETED,
            result=result,
        )

        # Trigger callback if set
        if self._on_pipeline_complete:
            try:
                self._on_pipeline_complete(pipeline_id, result)
            except Exception as e:
                pass

    def fail_pipeline(self, pipeline_id: str, error: str, auto_investigate: bool = None):
        """
        Mark a pipeline as failed.

        Args:
            pipeline_id: Pipeline identifier
            error: Error message or details
            auto_investigate: Override auto-investigation setting for this failure
        """
        # Update pipeline status
        self.state.update_pipeline_status(
            pipeline_id,
            PipelineStatus.FAILED,
            error=error,
        )

        # Create investigation task if enabled
        should_investigate = auto_investigate if auto_investigate is not None else self._auto_investigate
        if should_investigate and self.scheduler:
            self._create_investigation_task(pipeline_id, error)

        # Trigger callback if set
        if self._on_pipeline_fail:
            try:
                self._on_pipeline_fail(pipeline_id, error)
            except Exception:
                pass

    def start_stage(self, pipeline_id: str, stage_name: str):
        """
        Mark a pipeline stage as started.

        Args:
            pipeline_id: Pipeline identifier
            stage_name: Name of the stage
        """
        with self.lock:
            pipeline = self.state.get_pipeline_status(pipeline_id)
            if not pipeline:
                return

            stages = pipeline.get("stages", [])
            for stage in stages:
                if stage["name"] == stage_name:
                    stage["status"] = StageStatus.RUNNING.value
                    stage["started_at"] = time.time()
                    break

            self.state.update_pipeline_status(
                pipeline_id,
                PipelineStatus(pipeline["status"]),
                stages=stages,
            )

        # Trigger callback if set
        if self._on_stage_start:
            try:
                self._on_stage_start(pipeline_id, stage_name)
            except Exception as e:
                pass

    def complete_stage(self, pipeline_id: str, stage_name: str,
                      logs: List[str] = None, metadata: Dict[str, Any] = None):
        """
        Mark a pipeline stage as completed.

        Args:
            pipeline_id: Pipeline identifier
            stage_name: Name of the stage
            logs: Optional stage logs
            metadata: Optional stage metadata
        """
        with self.lock:
            pipeline = self.state.get_pipeline_status(pipeline_id)
            if not pipeline:
                return

            stages = pipeline.get("stages", [])
            for stage in stages:
                if stage["name"] == stage_name:
                    stage["status"] = StageStatus.COMPLETED.value
                    stage["completed_at"] = time.time()
                    if stage["started_at"]:
                        stage["duration"] = stage["completed_at"] - stage["started_at"]
                    if logs:
                        stage["logs"] = logs
                    if metadata:
                        stage["metadata"].update(metadata)
                    break

            self.state.update_pipeline_status(
                pipeline_id,
                PipelineStatus(pipeline["status"]),
                stages=stages,
            )

        # Trigger callback if set
        if self._on_stage_complete:
            try:
                self._on_stage_complete(pipeline_id, stage_name)
            except Exception as e:
                pass

    def fail_stage(self, pipeline_id: str, stage_name: str, error: str):
        """
        Mark a pipeline stage as failed.

        Args:
            pipeline_id: Pipeline identifier
            stage_name: Name of the stage
            error: Error message
        """
        with self.lock:
            pipeline = self.state.get_pipeline_status(pipeline_id)
            if not pipeline:
                return

            stages = pipeline.get("stages", [])
            for stage in stages:
                if stage["name"] == stage_name:
                    stage["status"] = StageStatus.FAILED.value
                    stage["completed_at"] = time.time()
                    if stage["started_at"]:
                        stage["duration"] = stage["completed_at"] - stage["started_at"]
                    stage["error"] = error
                    break

            self.state.update_pipeline_status(
                pipeline_id,
                PipelineStatus(pipeline["status"]),
                stages=stages,
            )

    def skip_stage(self, pipeline_id: str, stage_name: str, reason: str = None):
        """
        Mark a pipeline stage as skipped.

        Args:
            pipeline_id: Pipeline identifier
            stage_name: Name of the stage
            reason: Optional reason for skipping
        """
        with self.lock:
            pipeline = self.state.get_pipeline_status(pipeline_id)
            if not pipeline:
                return

            stages = pipeline.get("stages", [])
            for stage in stages:
                if stage["name"] == stage_name:
                    stage["status"] = StageStatus.SKIPPED.value
                    if reason:
                        stage["metadata"]["skip_reason"] = reason
                    break

            self.state.update_pipeline_status(
                pipeline_id,
                PipelineStatus(pipeline["status"]),
                stages=stages,
            )

    def _create_investigation_task(self, pipeline_id: str, error: str):
        """
        Create an investigation task for a failed pipeline.

        Args:
            pipeline_id: Pipeline identifier
            error: Error message
        """
        if not self.scheduler:
            return

        try:
            # Get pipeline details for context
            pipeline = self.state.get_pipeline_status(pipeline_id)
            if not pipeline:
                return

            # Collect failure context
            context = {
                "pipeline_id": pipeline_id,
                "pipeline_type": pipeline.get("pipeline_type", "unknown"),
                "commit_sha": pipeline.get("commit_sha", ""),
                "branch": pipeline.get("branch", ""),
                "error": error,
                "failed_stages": [],
            }

            # Find failed stages
            for stage in pipeline.get("stages", []):
                if stage.get("status") == StageStatus.FAILED.value:
                    context["failed_stages"].append({
                        "name": stage.get("name"),
                        "error": stage.get("error"),
                        "logs": stage.get("logs", []),
                    })

            # Create investigation task
            task_id = self.scheduler.create_task(
                task_type="investigation",
                description=f"Investigate pipeline failure: {pipeline_id}",
                agent_type="investigator",
                priority=TaskPriority.HIGH.value,
                input_data={
                    "failure_context": context,
                    "pipeline_id": pipeline_id,
                    "investigation_type": "pipeline_failure",
                },
            )

            # Store investigation task ID in pipeline metadata
            metadata = pipeline.get("metadata", {})
            metadata["investigation_task_id"] = task_id
            self.state.update_pipeline_status(
                pipeline_id,
                PipelineStatus(pipeline["status"]),
                metadata=metadata,
            )

        except Exception as e:
            # Don't let investigation task creation break pipeline monitoring
            pass

    def set_auto_investigate(self, enabled: bool):
        """
        Enable or disable automatic investigation task creation.

        Args:
            enabled: Whether to auto-create investigation tasks on failure
        """
        self._auto_investigate = enabled

    def _monitor_loop(self):
        """Main monitoring loop - polls active pipelines for status updates."""
        health_check_counter = 0

        while self._running:
            try:
                # Poll active pipelines for status updates
                self._poll_active_pipelines()

                # Periodic health checks (less frequent than polling)
                health_check_counter += 1
                if health_check_counter >= (self._health_check_interval // self._poll_interval):
                    self._check_pipeline_health()
                    health_check_counter = 0

                # Sleep before next poll
                time.sleep(self._poll_interval)

            except Exception as e:
                # Log error but continue monitoring
                time.sleep(self._poll_interval)

    def _poll_active_pipelines(self):
        """
        Poll all active pipelines to update their status.

        This method:
        1. Gets all pipelines from state tracker
        2. Filters for active (non-terminal) pipelines
        3. For each pipeline with an integration, polls for current status
        4. Updates state tracker with new status
        5. Triggers callbacks on status changes
        """
        pipelines = self.state.get_all_pipelines()

        for pipeline_id, pipeline in pipelines.items():
            try:
                status = pipeline.get("status")

                # Skip completed/failed/cancelled pipelines
                if status in [
                    PipelineStatus.COMPLETED.value,
                    PipelineStatus.FAILED.value,
                    PipelineStatus.CANCELLED.value,
                ]:
                    continue

                # Get integration for this pipeline
                integration = self._get_pipeline_integration(pipeline)
                if not integration:
                    continue

                # Get external run ID from metadata
                run_id = pipeline.get("metadata", {}).get("run_id")
                if not run_id:
                    continue

                # Poll integration for current status
                try:
                    current_status = integration.get_pipeline_status(run_id)

                    # Map integration status to state tracker status
                    new_status = self._map_integration_status(current_status)

                    # Update if status changed
                    if new_status != status:
                        self._update_pipeline_status_from_poll(
                            pipeline_id, pipeline, new_status, current_status
                        )

                except Exception as e:
                    # Log error but don't stop monitoring other pipelines
                    pass

            except Exception as e:
                # Log error but continue monitoring other pipelines
                pass

    def _get_pipeline_integration(self, pipeline: Dict[str, Any]) -> Optional[Any]:
        """
        Get the integration instance for a pipeline.

        Args:
            pipeline: Pipeline dictionary from state tracker

        Returns:
            Integration instance or None
        """
        # Get platform from pipeline metadata
        platform = pipeline.get("metadata", {}).get("platform")
        if not platform:
            return None

        return self.integrations.get(platform)

    def _map_integration_status(self, integration_status) -> PipelineStatus:
        """
        Map integration-specific status to PipelineStatus enum.

        Args:
            integration_status: Status from integration (can be enum or string)

        Returns:
            PipelineStatus enum value
        """
        # Handle if integration returns string
        if isinstance(integration_status, str):
            status_map = {
                "pending": PipelineStatus.PENDING,
                "queued": PipelineStatus.PENDING,
                "running": PipelineStatus.RUNNING,
                "success": PipelineStatus.COMPLETED,
                "completed": PipelineStatus.COMPLETED,
                "failed": PipelineStatus.FAILED,
                "failure": PipelineStatus.FAILED,
                "cancelled": PipelineStatus.FAILED,
                "canceled": PipelineStatus.FAILED,
            }
            return status_map.get(integration_status.lower(), PipelineStatus.RUNNING)

        # Handle if integration returns PipelineStatus enum
        if hasattr(integration_status, "value"):
            # Map integration status to our status
            value = integration_status.value
            if value in ["success", "completed"]:
                return PipelineStatus.COMPLETED
            elif value in ["failed", "failure"]:
                return PipelineStatus.FAILED
            elif value == "cancelled":
                return PipelineStatus.FAILED
            elif value == "running":
                return PipelineStatus.RUNNING
            else:
                return PipelineStatus.RUNNING

        return PipelineStatus.RUNNING

    def _update_pipeline_status_from_poll(
        self,
        pipeline_id: str,
        pipeline: Dict[str, Any],
        new_status: PipelineStatus,
        integration_status
    ):
        """
        Update pipeline status based on poll results and trigger callbacks.

        Args:
            pipeline_id: Pipeline identifier
            pipeline: Pipeline dictionary
            new_status: New PipelineStatus enum value
            integration_status: Original status from integration
        """
        old_status = pipeline.get("status")

        # Update in state tracker
        self.state.update_pipeline_status(pipeline_id, new_status)

        # Trigger appropriate callbacks
        if new_status == PipelineStatus.COMPLETED:
            if self._on_pipeline_complete:
                try:
                    self._on_pipeline_complete(pipeline_id, {"status": str(integration_status)})
                except Exception:
                    pass

        elif new_status == PipelineStatus.FAILED:
            if self._on_pipeline_fail:
                try:
                    error_msg = getattr(integration_status, "value", str(integration_status))
                    self._on_pipeline_fail(pipeline_id, error_msg)
                except Exception:
                    pass

    def _check_pipeline_health(self):
        """Check health of running pipelines."""
        pipelines = self.state.get_all_pipelines()

        for pipeline_id, pipeline in pipelines.items():
            status = pipeline.get("status")

            # Check for pipelines stuck in RUNNING for too long
            if status == PipelineStatus.RUNNING.value:
                started_at = pipeline.get("started_at")
                if started_at:
                    # Convert ISO string to timestamp if needed
                    if isinstance(started_at, str):
                        started_at = datetime.fromisoformat(started_at).timestamp()

                    elapsed = time.time() - started_at

                    # Timeout after 1 hour (configurable)
                    if elapsed > 3600:
                        self.fail_pipeline(
                            pipeline_id,
                            f"Pipeline timed out after {elapsed:.0f} seconds"
                        )

    def get_pipeline_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a pipeline.

        Args:
            pipeline_id: Pipeline identifier

        Returns:
            Pipeline status dictionary or None
        """
        return self.state.get_pipeline_status(pipeline_id)

    def get_all_pipelines(self) -> Dict[str, Dict[str, Any]]:
        """Get all pipelines."""
        return self.state.get_all_pipelines()

    def get_running_pipelines(self) -> List[Dict[str, Any]]:
        """Get all currently running pipelines."""
        pipelines = self.state.get_all_pipelines()
        return [
            p for p in pipelines.values()
            if p["status"] == PipelineStatus.RUNNING.value
        ]

    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """
        Get pipeline metrics.

        Returns:
            Dictionary with pipeline metrics
        """
        all_pipelines = self.state.get_all_pipelines()

        total = len(all_pipelines)
        running = sum(1 for p in all_pipelines.values()
                     if p["status"] == PipelineStatus.RUNNING.value)
        completed = sum(1 for p in all_pipelines.values()
                       if p["status"] == PipelineStatus.COMPLETED.value)
        failed = sum(1 for p in all_pipelines.values()
                    if p["status"] == PipelineStatus.FAILED.value)

        # Calculate average duration for completed pipelines
        durations = []
        for p in all_pipelines.values():
            if p["started_at"] and p["completed_at"]:
                started = p["started_at"]
                completed = p["completed_at"]

                # Handle both ISO string and timestamp formats
                if isinstance(started, str):
                    started = datetime.fromisoformat(started).timestamp()
                if isinstance(completed, str):
                    completed = datetime.fromisoformat(completed).timestamp()

                durations.append(completed - started)

        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "total": total,
            "running": running,
            "completed": completed,
            "failed": failed,
            "success_rate": completed / total if total > 0 else 0,
            "average_duration": avg_duration,
        }

    def on_pipeline_start(self, callback: Callable[[str], None]):
        """Register callback for pipeline start events."""
        self._on_pipeline_start = callback

    def on_pipeline_complete(self, callback: Callable[[str, Any], None]):
        """Register callback for pipeline completion events."""
        self._on_pipeline_complete = callback

    def on_pipeline_fail(self, callback: Callable[[str, str], None]):
        """Register callback for pipeline failure events."""
        self._on_pipeline_fail = callback

    def on_stage_start(self, callback: Callable[[str, str], None]):
        """Register callback for stage start events."""
        self._on_stage_start = callback

    def on_stage_complete(self, callback: Callable[[str, str], None]):
        """Register callback for stage completion events."""
        self._on_stage_complete = callback
