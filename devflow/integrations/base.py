"""
CI/CD Pipeline Integration Base.

Abstract base class for CI/CD platform integrations.
Provides common interface and functionality for all integrations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List
import threading
import time
import logging

logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    """Status of a CI/CD pipeline run."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


@dataclass
class PipelineConfig:
    """Configuration for a CI/CD integration."""
    platform: str
    enabled: bool = True
    api_token: Optional[str] = None
    base_url: Optional[str] = None
    repository: Optional[str] = None
    branch: str = "main"
    timeout: int = 3600
    retry_attempts: int = 3
    retry_delay: int = 5
    webhook_url: Optional[str] = None
    verify_ssl: bool = True
    additional_params: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """
        Validate configuration.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.enabled:
            return True

        if not self.platform:
            raise ValueError("Platform name is required")

        if not self.api_token:
            raise ValueError(f"API token is required for {self.platform}")

        if not self.repository:
            raise ValueError(f"Repository is required for {self.platform}")

        return True


@dataclass
class PipelineRun:
    """Information about a pipeline run."""
    run_id: str
    platform: str
    repository: str
    branch: str
    status: PipelineStatus
    created_at: float
    updated_at: float
    completed_at: Optional[float] = None
    url: Optional[str] = None
    logs_url: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "platform": self.platform,
            "repository": self.repository,
            "branch": self.branch,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "url": self.url,
            "logs_url": self.logs_url,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


class PipelineIntegration(ABC):
    """
    Abstract base class for CI/CD platform integrations.

    Responsibilities:
    - Trigger pipeline/workflow/job runs
    - Monitor pipeline status
    - Handle authentication and configuration
    - Provide common interface for all platforms

    All platform-specific integrations must inherit from this class
    and implement the abstract methods.
    """

    def __init__(self, config: PipelineConfig):
        """
        Initialize the integration.

        Args:
            config: Pipeline configuration
        """
        self.config = config
        self.lock = threading.Lock()
        self.active_runs: Dict[str, PipelineRun] = {}
        self._validate_config()

    def _validate_config(self):
        """Validate configuration on initialization."""
        try:
            self.config.validate()
        except ValueError as e:
            logger.error(f"Invalid {self.config.platform} configuration: {e}")
            raise

    @abstractmethod
    def trigger_pipeline(
        self,
        branch: str = None,
        parameters: Dict[str, Any] = None,
        commit_sha: str = None
    ) -> PipelineRun:
        """
        Trigger a pipeline run.

        Args:
            branch: Git branch to run pipeline on (defaults to config branch)
            parameters: Additional parameters for the pipeline
            commit_sha: Specific commit SHA to trigger pipeline for

        Returns:
            PipelineRun object with run information

        Raises:
            ValueError: If trigger fails due to invalid parameters
            ConnectionError: If unable to reach platform API
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    def get_pipeline_status(self, run_id: str) -> PipelineStatus:
        """
        Get the current status of a pipeline run.

        Args:
            run_id: Pipeline run identifier

        Returns:
            PipelineStatus enum value

        Raises:
            ValueError: If run_id is not found
            ConnectionError: If unable to reach platform API
        """
        pass

    @abstractmethod
    def get_pipeline_logs(self, run_id: str) -> str:
        """
        Get logs from a pipeline run.

        Args:
            run_id: Pipeline run identifier

        Returns:
            Log output as string

        Raises:
            ValueError: If run_id is not found
            ConnectionError: If unable to reach platform API
        """
        pass

    @abstractmethod
    def cancel_pipeline(self, run_id: str) -> bool:
        """
        Cancel a running pipeline.

        Args:
            run_id: Pipeline run identifier

        Returns:
            True if cancellation was successful

        Raises:
            ValueError: If run_id is not found or pipeline cannot be cancelled
            ConnectionError: If unable to reach platform API
        """
        pass

    def monitor_pipeline(
        self,
        run_id: str,
        callback: Optional[callable] = None,
        poll_interval: int = 30
    ) -> PipelineRun:
        """
        Monitor a pipeline run until completion.

        Args:
            run_id: Pipeline run identifier
            callback: Optional callback function called on status updates
            poll_interval: Seconds between status checks

        Returns:
            PipelineRun object with final status

        Raises:
            ValueError: If run_id is not found
            TimeoutError: If pipeline exceeds configured timeout
        """
        start_time = time.time()
        timeout = self.config.timeout

        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"Pipeline {run_id} exceeded timeout of {timeout}s"
                )

            # Get current status
            status = self.get_pipeline_status(run_id)

            # Update run info
            with self.lock:
                if run_id in self.active_runs:
                    self.active_runs[run_id].status = status
                    self.active_runs[run_id].updated_at = time.time()

            # Call callback if provided
            if callback:
                callback(run_id, status)

            # Check if complete
            if status in [PipelineStatus.SUCCESS, PipelineStatus.FAILED, PipelineStatus.CANCELLED]:
                with self.lock:
                    if run_id in self.active_runs:
                        self.active_runs[run_id].completed_at = time.time()
                break

            # Wait before next poll
            time.sleep(poll_interval)

        return self.active_runs.get(run_id)

    def get_active_runs(self) -> List[PipelineRun]:
        """
        Get all active pipeline runs.

        Returns:
            List of PipelineRun objects
        """
        with self.lock:
            return list(self.active_runs.values())

    def get_run(self, run_id: str) -> Optional[PipelineRun]:
        """
        Get a specific pipeline run.

        Args:
            run_id: Pipeline run identifier

        Returns:
            PipelineRun object or None if not found
        """
        return self.active_runs.get(run_id)

    def cleanup_completed_runs(self, max_age: int = 86400):
        """
        Remove completed runs older than max_age seconds.

        Args:
            max_age: Maximum age in seconds (default: 24 hours)
        """
        current_time = time.time()
        with self.lock:
            to_remove = []
            for run_id, run in self.active_runs.items():
                if run.status in [PipelineStatus.SUCCESS, PipelineStatus.FAILED, PipelineStatus.CANCELLED]:
                    if run.completed_at and (current_time - run.completed_at) > max_age:
                        to_remove.append(run_id)

            for run_id in to_remove:
                del self.active_runs[run_id]

    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the integration.

        Returns:
            Dictionary with health status information
        """
        try:
            # Platform-specific health check would go here
            # For now, just verify configuration
            self.config.validate()

            return {
                "platform": self.config.platform,
                "status": "healthy",
                "active_runs": len(self.active_runs),
                "repository": self.config.repository,
            }
        except Exception as e:
            return {
                "platform": self.config.platform,
                "status": "unhealthy",
                "error": str(e),
            }

    def _register_run(self, run: PipelineRun):
        """
        Register a pipeline run.

        Args:
            run: PipelineRun object
        """
        with self.lock:
            self.active_runs[run.run_id] = run

    def _unregister_run(self, run_id: str):
        """
        Unregister a pipeline run.

        Args:
            run_id: Pipeline run identifier
        """
        with self.lock:
            if run_id in self.active_runs:
                del self.active_runs[run_id]
