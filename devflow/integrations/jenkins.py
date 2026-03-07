"""
Jenkins Integration.

Provides integration with Jenkins for triggering and monitoring builds.
"""

import requests
import time
import logging
import base64
from typing import Dict, Any, Optional
from urllib.parse import urljoin

from .base import (
    PipelineIntegration,
    PipelineConfig,
    PipelineRun,
    PipelineStatus,
)

logger = logging.getLogger(__name__)


class Jenkins(PipelineIntegration):
    """
    Jenkins integration for triggering and monitoring builds.

    This class provides methods to:
    - Trigger Jenkins jobs with parameters
    - Monitor build status
    - Fetch build logs
    - Cancel running builds

    Authentication:
    - Requires Jenkins API token or username/password
    - API token should be provided via PipelineConfig.api_token
    - Username can be provided via PipelineConfig.additional_params['username']

    Example:
        ```python
        config = PipelineConfig(
            platform="jenkins",
            api_token="jenkins_api_token",
            base_url="https://jenkins.example.com",
            repository="job-name",
            branch="main"
        )
        jenkins = Jenkins(config)
        run = jenkins.trigger_pipeline(branch="feature-branch")
        ```
    """

    # Jenkins API endpoints
    DEFAULT_BASE_URL = "http://localhost:8080"

    # Build status mapping from Jenkins to PipelineStatus
    STATUS_MAP = {
        "queued": PipelineStatus.QUEUED,
        "queue": PipelineStatus.QUEUED,
        "running": PipelineStatus.RUNNING,
        "success": PipelineStatus.SUCCESS,
        "completed": PipelineStatus.SUCCESS,
        "failure": PipelineStatus.FAILED,
        "failed": PipelineStatus.FAILED,
        "aborted": PipelineStatus.CANCELLED,
        "cancelled": PipelineStatus.CANCELLED,
        "not_built": PipelineStatus.FAILED,
        "unstable": PipelineStatus.FAILED,
        "pending": PipelineStatus.PENDING,
        "unknown": PipelineStatus.UNKNOWN,
    }

    def __init__(self, config: PipelineConfig):
        """
        Initialize Jenkins integration.

        Args:
            config: Pipeline configuration with Jenkins-specific settings

        Raises:
            ValueError: If configuration is invalid
        """
        # Set default base URL if not provided
        if not config.base_url:
            config.base_url = self.DEFAULT_BASE_URL

        # Add Jenkins-specific validation
        if config.enabled and config.api_token:
            if ":" in config.api_token:
                logger.warning(
                    "API token contains ':' which suggests username:password format. "
                    "Consider using username in additional_params and token as api_token."
                )

        super().__init__(config)

        # Extract job name from repository string
        self.job_name = config.repository

        # Setup requests session
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """
        Create configured requests session for Jenkins API.

        Returns:
            Configured requests.Session object
        """
        session = requests.Session()

        # Setup authentication
        username = self.config.additional_params.get("username", "")

        if username:
            # Use username:token format for basic auth
            auth_string = f"{username}:{self.config.api_token}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            session.headers.update({
                "Authorization": f"Basic {encoded_auth}"
            })
        else:
            # Use API token directly (Bearer or token-based auth)
            session.headers.update({
                "Authorization": f"Bearer {self.config.api_token}"
            })

        # Set headers
        session.headers.update({
            "Accept": "application/json",
            "User-Agent": "DevFlow-CI/CD-Integration",
        })

        # Setup SSL verification
        session.verify = self.config.verify_ssl

        return session

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
        retry: int = 0
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Jenkins API with retry logic.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            retry: Current retry attempt

        Returns:
            Parsed JSON response

        Raises:
            ConnectionError: If request fails after retries
            ValueError: If response is invalid
        """
        url = urljoin(self.config.base_url, endpoint)

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=30
            )

            # Check for authentication errors
            if response.status_code == 401 or response.status_code == 403:
                raise ValueError(
                    "Jenkins authentication failed. Check your API token and username."
                )

            # Check for not found
            if response.status_code == 404:
                raise ValueError(
                    f"Jenkins resource not found: {endpoint}. "
                    f"Check your job name and configuration."
                )

            # Check for other errors
            if response.status_code >= 400:
                error_msg = response.text or response.reason
                raise ConnectionError(
                    f"Jenkins API request failed: {response.status_code} - {error_msg}"
                )

            # Try to parse JSON
            try:
                return response.json()
            except ValueError:
                # Return text if not JSON
                return {"text": response.text}

        except requests.exceptions.RequestException as e:
            logger.error(f"Request to Jenkins API failed: {e}")

            if retry < self.config.retry_attempts:
                logger.info(f"Retrying in {self.config.retry_delay}s...")
                time.sleep(self.config.retry_delay)
                return self._make_request(method, endpoint, data, params, retry + 1)

            raise ConnectionError(f"Failed to reach Jenkins API: {e}")

    def _get_queue_info(self, queue_id: str) -> Dict[str, Any]:
        """
        Get information about a queued build.

        Args:
            queue_id: Queue item ID

        Returns:
            Queue information dictionary

        Raises:
            ConnectionError: If unable to reach Jenkins API
        """
        try:
            endpoint = f"/queue/item/{queue_id}/api/json"
            return self._make_request("GET", endpoint)
        except Exception as e:
            logger.error(f"Failed to get queue info for {queue_id}: {e}")
            raise ConnectionError(f"Failed to get Jenkins queue info: {e}")

    def _get_build_info(self, job_name: str, build_number: int) -> Dict[str, Any]:
        """
        Get information about a build.

        Args:
            job_name: Name of the job
            build_number: Build number

        Returns:
            Build information dictionary

        Raises:
            ConnectionError: If unable to reach Jenkins API
        """
        try:
            # Handle folder paths in job names
            job_path = job_name.replace("/job/", "/job/")
            endpoint = f"/job/{job_path}/{build_number}/api/json"
            return self._make_request("GET", endpoint)
        except Exception as e:
            logger.error(f"Failed to get build info for {job_name} #{build_number}: {e}")
            raise ConnectionError(f"Failed to get Jenkins build info: {e}")

    def trigger_job(
        self,
        job_name: str = None,
        parameters: Dict[str, Any] = None,
        branch: str = None,
        commit_sha: str = None
    ) -> PipelineRun:
        """
        Trigger a specific Jenkins job.

        This is a Jenkins-specific method that provides direct control
        over job triggering, unlike the generic trigger_pipeline() method.

        Args:
            job_name: Name of the Jenkins job
            parameters: Dictionary of parameters for the job
            branch: Git branch to build (passed as parameter)
            commit_sha: Specific commit SHA to build

        Returns:
            PipelineRun object with run information

        Raises:
            ValueError: If trigger fails due to invalid parameters
            ConnectionError: If unable to reach Jenkins API

        Example:
            ```python
            jenkins = Jenkins(config)
            run = jenkins.trigger_job(
                job_name="my-project",
                parameters={"ENVIRONMENT": "staging"},
                branch="main"
            )
            ```
        """
        job_name = job_name or self.job_name
        parameters = parameters or {}
        branch = branch or self.config.branch

        if not job_name:
            raise ValueError("Job name is required. Provide via job_name parameter or config.repository")

        logger.info(
            f"Triggering Jenkins job '{job_name}' "
            f"with branch {branch}"
        )

        try:
            # Add branch and commit_sha to parameters if not already present
            if branch and "BRANCH" not in parameters and "branch" not in parameters:
                parameters["BRANCH"] = branch

            if commit_sha and "COMMIT_SHA" not in parameters and "commit_sha" not in parameters:
                parameters["COMMIT_SHA"] = commit_sha

            # Prepare job path
            job_path = job_name.replace("/job/", "/job/")

            # Trigger build with or without parameters
            if parameters:
                # Build with parameters
                endpoint = f"/job/{job_path}/buildWithParameters"
                response = self.session.post(
                    urljoin(self.config.base_url, endpoint),
                    data=parameters,
                    timeout=30
                )
            else:
                # Build without parameters
                endpoint = f"/job/{job_path}/build"
                response = self.session.post(
                    urljoin(self.config.base_url, endpoint),
                    timeout=30
                )

            # Check response
            if response.status_code in [200, 201]:
                # Jenkins returns queue location in headers
                queue_url = response.headers.get("Location", "")

                # Extract queue ID from URL
                queue_id = None
                if "/queue/item/" in queue_url:
                    queue_id = queue_url.split("/queue/item/")[-1].split("/")[0]

                # Generate a run ID (will be updated once build starts)
                run_id = queue_id if queue_id else f"pending-{int(time.time())}"

                # Create PipelineRun object
                run = PipelineRun(
                    run_id=run_id,
                    platform="jenkins",
                    repository=job_name,
                    branch=branch,
                    status=PipelineStatus.QUEUED,
                    created_at=time.time(),
                    updated_at=time.time(),
                    url=f"{self.config.base_url}/queue/item/{queue_id}" if queue_id else None,
                    metadata={
                        "job_name": job_name,
                        "queue_id": queue_id,
                        "parameters": parameters,
                        "commit_sha": commit_sha,
                        "triggered_by": "devflow",
                    }
                )

                # Register the run
                self._register_run(run)

                logger.info(
                    f"Successfully triggered job '{job_name}' "
                    f"with queue ID {queue_id}"
                )
                return run
            else:
                raise ConnectionError(
                    f"Failed to trigger Jenkins job: {response.status_code} - {response.text}"
                )

        except ValueError as e:
            logger.error(f"Failed to trigger job '{job_name}': {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error triggering job '{job_name}': {e}")
            raise ConnectionError(f"Failed to trigger Jenkins job: {e}")

    def trigger_pipeline(
        self,
        branch: str = None,
        parameters: Dict[str, Any] = None,
        commit_sha: str = None
    ) -> PipelineRun:
        """
        Trigger a Jenkins job run (generic interface).

        This method implements the base class interface and delegates to
        trigger_job() for actual Jenkins-specific functionality.

        Args:
            branch: Git branch to build (defaults to config branch)
            parameters: Additional parameters for the job.
                      Can include job_name or other job-specific parameters
            commit_sha: Specific commit SHA to build

        Returns:
            PipelineRun object with run information

        Raises:
            ValueError: If trigger fails due to invalid parameters
            ConnectionError: If unable to reach Jenkins API
        """
        branch = branch or self.config.branch
        parameters = parameters or {}

        logger.info(
            f"Triggering Jenkins job for {self.job_name} "
            f"on branch {branch}"
        )

        try:
            # Extract job name from parameters if provided
            job_name = parameters.get("job_name", self.job_name)

            # Remove job_name from parameters before passing to trigger_job
            job_params = {k: v for k, v in parameters.items() if k != "job_name"}

            # Delegate to trigger_job
            return self.trigger_job(
                job_name=job_name,
                parameters=job_params,
                branch=branch,
                commit_sha=commit_sha
            )

        except ValueError as e:
            logger.error(f"Failed to trigger job: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error triggering job: {e}")
            raise ConnectionError(f"Failed to trigger Jenkins job: {e}")

    def get_build_status(
        self,
        job_name: str = None,
        build_number: int = None,
        poll: bool = False,
        timeout: int = 600,
        interval: int = 10
    ) -> Dict[str, Any]:
        """
        Get detailed status of a build with optional polling.

        This is a Jenkins-specific method that provides comprehensive
        status information beyond the generic get_pipeline_status() method.

        Args:
            job_name: Name of the job
            build_number: Build number
            poll: Whether to continuously poll until completion (default: False)
            timeout: Maximum polling time in seconds (default: 600)
            interval: Polling interval in seconds (default: 10)

        Returns:
            Dictionary containing:
                - status: PipelineStatus enum value
                - jenkins_status: Raw Jenkins status string
                - result: Raw Jenkins result string (if completed)
                - building: Whether the build is still building
                - timestamp: Build start timestamp
                - duration: Build duration in milliseconds
                - url: HTML URL to the build
                - full_display_name: Full build display name
                - number: Build number
                - queue_id: Queue ID if applicable

        Raises:
            ValueError: If build is not found
            ConnectionError: If unable to reach Jenkins API
            TimeoutError: If polling timeout is exceeded

        Example:
            ```python
            # Get current status without polling
            status = jenkins.get_build_status("my-job", 42)

            # Poll until completion with custom timeout
            status = jenkins.get_build_status("my-job", 42, poll=True, timeout=300)
            ```
        """
        job_name = job_name or self.job_name

        if not build_number:
            raise ValueError("Build number is required")

        start_time = time.time()
        last_status = None

        try:
            while True:
                try:
                    build_info = self._get_build_info(job_name, build_number)

                    # Map Jenkins status to PipelineStatus
                    building = build_info.get("building", False)
                    result = build_info.get("result")

                    if building:
                        pipeline_status = PipelineStatus.RUNNING
                        jenkins_status = "running"
                    else:
                        # Use "UNKNOWN" if result is None
                        jenkins_status = (result or "UNKNOWN").lower()
                        pipeline_status = self._map_status(jenkins_status)

                    # Build status dictionary
                    status_info = {
                        "status": pipeline_status,
                        "jenkins_status": jenkins_status,
                        "result": build_info.get("result"),
                        "building": building,
                        "timestamp": build_info.get("timestamp"),
                        "duration": build_info.get("duration"),
                        "url": build_info.get("url"),
                        "full_display_name": build_info.get("fullDisplayName"),
                        "number": build_info.get("number"),
                    }

                    # Log status change if polling
                    if poll and last_status != pipeline_status:
                        logger.info(
                            f"Build {job_name} #{build_number} status: {pipeline_status.name} "
                            f"(Jenkins: {jenkins_status})"
                        )
                        last_status = pipeline_status

                    # If not polling or build is complete, return status
                    if not poll or pipeline_status in [
                        PipelineStatus.SUCCESS,
                        PipelineStatus.FAILED,
                        PipelineStatus.CANCELLED
                    ]:
                        # Update run in active runs if present
                        run_id = str(build_number)
                        with self.lock:
                            if run_id in self.active_runs:
                                self.active_runs[run_id].status = pipeline_status
                                self.active_runs[run_id].updated_at = time.time()

                        return status_info

                    # Check timeout
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        raise TimeoutError(
                            f"Build {job_name} #{build_number} did not complete within {timeout} seconds. "
                            f"Last status: {pipeline_status.name}"
                        )

                    # Wait before next poll
                    time.sleep(interval)

                except ValueError as e:
                    logger.error(f"Failed to get build status: {e}")
                    raise
                except requests.exceptions.RequestException as e:
                    # Retry on network errors during polling
                    if not poll:
                        raise ConnectionError(f"Failed to get build status: {e}")

                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        raise TimeoutError(
                            f"Network errors persisted for {timeout} seconds while polling build {build_number}"
                        )

                    logger.warning(f"Network error during polling, retrying: {e}")
                    time.sleep(interval)

        except (ValueError, ConnectionError, TimeoutError):
            raise
        except Exception as e:
            logger.error(f"Error getting build status: {e}")
            raise ConnectionError(f"Failed to get Jenkins build status: {e}")

    def get_pipeline_status(self, run_id: str) -> PipelineStatus:
        """
        Get the current status of a pipeline run.

        This is the generic interface method.

        Args:
            run_id: Pipeline run identifier (queue ID or build number)

        Returns:
            PipelineStatus enum value

        Raises:
            ValueError: If run_id is not found
            ConnectionError: If unable to reach Jenkins API
        """
        try:
            # Check if this is a tracked run
            run = self.get_run(run_id)
            if run:
                # If we have metadata with build number, get fresh status
                build_number = run.metadata.get("build_number")
                if build_number:
                    status_info = self.get_build_status(
                        job_name=run.repository,
                        build_number=build_number
                    )
                    return status_info["status"]

                # Check if this is a queued job (has queue_id but no build_number yet)
                queue_id = run.metadata.get("queue_id")
                if queue_id:
                    # Check queue status
                    queue_info = self._get_queue_info(queue_id)
                    if queue_info.get("cancelled", False):
                        return PipelineStatus.CANCELLED

                    # Check if build has started
                    executable = queue_info.get("executable", {})
                    if executable:
                        # Update run with build number
                        build_number = executable.get("number")
                        run.metadata["build_number"] = build_number
                        run.url = executable.get("url")
                        run.status = PipelineStatus.RUNNING

                        # Get build status
                        status_info = self.get_build_status(
                            job_name=run.repository,
                            build_number=build_number
                        )
                        return status_info["status"]

                    # Still queued
                    return PipelineStatus.QUEUED

            # Try to parse as build number
            try:
                build_number = int(run_id)
                status_info = self.get_build_status(
                    job_name=self.job_name,
                    build_number=build_number
                )
                return status_info["status"]
            except ValueError:
                # It's a queue ID (not a tracked run), check queue status
                queue_info = self._get_queue_info(run_id)
                if queue_info.get("cancelled", False):
                    return PipelineStatus.CANCELLED

                # Check if build has started
                executable = queue_info.get("executable", {})
                if executable:
                    # Get build status
                    build_number = executable.get("number")
                    status_info = self.get_build_status(
                        job_name=self.job_name,
                        build_number=build_number
                    )
                    return status_info["status"]

                # Still queued
                return PipelineStatus.QUEUED

        except ValueError as e:
            logger.error(f"Failed to get pipeline status: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting pipeline status: {e}")
            raise ConnectionError(f"Failed to get Jenkins pipeline status: {e}")

    def get_pipeline_logs(self, run_id: str) -> str:
        """
        Get logs from a pipeline run.

        Args:
            run_id: Pipeline run identifier (build number)

        Returns:
            Log output as string

        Raises:
            ValueError: If run_id is not found
            ConnectionError: If unable to reach Jenkins API
        """
        try:
            # Check if this is a tracked run with build number
            run = self.get_run(run_id)
            build_number = None

            if run:
                build_number = run.metadata.get("build_number")

            # If not in run metadata, try to parse run_id as build number
            if not build_number:
                try:
                    build_number = int(run_id)
                except ValueError:
                    raise ValueError(
                        f"Cannot get logs for queue ID {run_id}. "
                        f"Build has not started yet or run_id must be a build number."
                    )

            # Get console output
            job_path = self.job_name.replace("/job/", "/job/")
            endpoint = f"/job/{job_path}/{build_number}/consoleText"

            response = self.session.get(
                urljoin(self.config.base_url, endpoint),
                timeout=60
            )

            if response.status_code == 404:
                raise ValueError(f"Build {build_number} not found")

            if response.status_code >= 400:
                raise ConnectionError(
                    f"Failed to get logs: {response.status_code} - {response.reason}"
                )

            return response.text

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error getting pipeline logs: {e}")
            raise ConnectionError(f"Failed to get Jenkins pipeline logs: {e}")

    def cancel_pipeline(self, run_id: str) -> bool:
        """
        Cancel a running pipeline.

        Args:
            run_id: Pipeline run identifier (queue ID or build number)

        Returns:
            True if cancellation was successful

        Raises:
            ValueError: If run_id is not found or pipeline cannot be cancelled
            ConnectionError: If unable to reach Jenkins API
        """
        try:
            # Check if this is a tracked run
            run = self.get_run(run_id)

            if run:
                build_number = run.metadata.get("build_number")
                queue_id = run.metadata.get("queue_id")

                # Cancel build if it has started
                if build_number:
                    job_path = run.repository.replace("/job/", "/job/")
                    endpoint = f"/job/{job_path}/{build_number}/stop"
                    response = self.session.post(
                        urljoin(self.config.base_url, endpoint),
                        timeout=30
                    )

                    if response.status_code in [200, 302]:
                        logger.info(f"Successfully cancelled build {build_number}")

                        with self.lock:
                            run.status = PipelineStatus.CANCELLED
                            run.updated_at = time.time()

                        return True

                # Cancel queue item if still queued
                elif queue_id:
                    endpoint = f"/queue/item/{queue_id}/cancelQueue"
                    response = self.session.post(
                        urljoin(self.config.base_url, endpoint),
                        timeout=30
                    )

                    if response.status_code in [200, 302, 404]:
                        # 404 might mean it already started or was cancelled
                        logger.info(f"Successfully cancelled queue item {queue_id}")

                        with self.lock:
                            run.status = PipelineStatus.CANCELLED
                            run.updated_at = time.time()

                        return True

            # Try to cancel as build number
            try:
                build_number = int(run_id)
                job_path = self.job_name.replace("/job/", "/job/")
                endpoint = f"/job/{job_path}/{build_number}/stop"
                response = self.session.post(
                    urljoin(self.config.base_url, endpoint),
                    timeout=30
                )

                if response.status_code in [200, 302]:
                    logger.info(f"Successfully cancelled build {build_number}")
                    return True

            except ValueError:
                pass

            raise ValueError(f"Could not cancel pipeline {run_id}")

        except ValueError as e:
            logger.error(f"Failed to cancel pipeline: {e}")
            raise
        except Exception as e:
            logger.error(f"Error cancelling pipeline: {e}")
            raise ConnectionError(f"Failed to cancel Jenkins pipeline: {e}")

    def _map_status(self, jenkins_status: str) -> PipelineStatus:
        """
        Map Jenkins status to PipelineStatus enum.

        Args:
            jenkins_status: Jenkins status string

        Returns:
            PipelineStatus enum value
        """
        jenkins_status = jenkins_status.lower().replace(" ", "_")
        return self.STATUS_MAP.get(jenkins_status, PipelineStatus.UNKNOWN)

    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the Jenkins integration.

        Returns:
            Dictionary with health status information
        """
        try:
            # Base health check
            health = super().health_check()

            if health["status"] != "healthy":
                return health

            # Test Jenkins API connection
            try:
                endpoint = "/api/json"
                response = self._make_request("GET", endpoint)

                health["jenkins_version"] = response.get("description", "unknown")
                health["jenkins_url"] = self.config.base_url
                health["jenkins_api"] = "connected"

            except Exception as e:
                health["status"] = "degraded"
                health["jenkins_api"] = f"connection_failed: {str(e)}"

            return health

        except Exception as e:
            return {
                "platform": "jenkins",
                "status": "unhealthy",
                "error": str(e),
            }
