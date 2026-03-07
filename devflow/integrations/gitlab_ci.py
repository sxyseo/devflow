"""
GitLab CI Integration.

Provides integration with GitLab CI/CD for triggering and monitoring pipelines.
"""

import requests
import time
import logging
from typing import Dict, Any, Optional
from urllib.parse import urljoin

from .base import (
    PipelineIntegration,
    PipelineConfig,
    PipelineRun,
    PipelineStatus,
)

logger = logging.getLogger(__name__)


class GitLabCI(PipelineIntegration):
    """
    GitLab CI/CD integration for triggering and monitoring pipelines.

    This class provides methods to:
    - Trigger GitLab CI/CD pipelines
    - Monitor pipeline status
    - Fetch pipeline logs
    - Cancel running pipelines

    Authentication:
    - Requires a GitLab Personal Access Token (PAT) with api, read_api, read_repository scopes
    - Token should be provided via PipelineConfig.api_token

    Example:
        ```python
        config = PipelineConfig(
            platform="gitlab",
            api_token="glpat_xxx",
            repository="group/project",
            branch="main"
        )
        gitlab = GitLabCI(config)
        run = gitlab.trigger_pipeline(branch="feature-branch")
        ```
    """

    # GitLab API endpoints
    API_BASE_URL = "https://gitlab.com/api/v4"
    DEFAULT_BASE_URL = API_BASE_URL

    # Pipeline status mapping from GitLab to PipelineStatus
    STATUS_MAP = {
        "created": PipelineStatus.PENDING,
        "waiting_for_resource": PipelineStatus.QUEUED,
        "preparing": PipelineStatus.QUEUED,
        "pending": PipelineStatus.PENDING,
        "running": PipelineStatus.RUNNING,
        "success": PipelineStatus.SUCCESS,
        "failed": PipelineStatus.FAILED,
        "canceled": PipelineStatus.CANCELLED,
        "skipped": PipelineStatus.SUCCESS,
        "manual": PipelineStatus.PENDING,
        "scheduled": PipelineStatus.QUEUED,
    }

    def __init__(self, config: PipelineConfig):
        """
        Initialize GitLab CI integration.

        Args:
            config: Pipeline configuration with GitLab-specific settings

        Raises:
            ValueError: If configuration is invalid
        """
        # Set default base URL if not provided
        if not config.base_url:
            config.base_url = self.DEFAULT_BASE_URL

        # Add GitLab-specific validation
        if config.enabled and config.api_token:
            if not config.api_token.startswith("glpat_") and not config.api_token.startswith("glft-"):
                logger.warning(
                    f"GitLab token format may be invalid. "
                    f"Expected token to start with 'glpat_' or 'glft-', got: {config.api_token[:10]}..."
                )

        super().__init__(config)

        # Parse project path from repository string
        if config.repository:
            self.project_path = self._parse_repository(config.repository)
        else:
            self.project_path = None

        # URL-encode the project path for API calls
        self.encoded_project_path = requests.utils.quote(self.project_path, safe='') if self.project_path else None

        # Setup requests session
        self.session = self._create_session()

    def _parse_repository(self, repository: str) -> str:
        """
        Parse project path from repository string.

        Args:
            repository: Project in format "group/project" or "group/subgroup/project"
                       or full GitLab URL

        Returns:
            Project path string

        Raises:
            ValueError: If repository format is invalid
        """
        if "gitlab.com/" in repository:
            # Extract from URL
            parts = repository.split("gitlab.com/")[-1]
            # Remove .git if present and any trailing slashes
            parts = parts.replace(".git", "").rstrip("/")
            return parts

        # Already in project path format (group/project or group/subgroup/project)
        parts = repository.strip("/")
        if not parts or "/" not in parts:
            raise ValueError(
                f"Invalid repository format: {repository}. "
                f"Expected 'group/project' or full GitLab URL"
            )

        return parts

    def _create_session(self) -> requests.Session:
        """
        Create configured requests session for GitLab API.

        Returns:
            Configured requests.Session object
        """
        session = requests.Session()

        # Set headers - GitLab uses PRIVATE-TOKEN header
        session.headers.update({
            "PRIVATE-TOKEN": self.config.api_token,
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
        Make authenticated request to GitLab API with retry logic.

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

            # Check for rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", self.config.retry_delay))
                logger.warning(f"GitLab rate limit hit, waiting {retry_after}s")
                time.sleep(retry_after)
                if retry < self.config.retry_attempts:
                    return self._make_request(method, endpoint, data, params, retry + 1)

            # Check for authentication errors
            if response.status_code == 401:
                raise ValueError(
                    "GitLab authentication failed. Check your API token."
                )

            # Check for other errors
            if response.status_code >= 400:
                error_msg = response.text or response.reason
                try:
                    error_json = response.json()
                    error_msg = error_json.get("message", error_msg)
                except:
                    pass
                raise ConnectionError(
                    f"GitLab API request failed: {response.status_code} - {error_msg}"
                )

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Request to GitLab API failed: {e}")

            if retry < self.config.retry_attempts:
                logger.info(f"Retrying in {self.config.retry_delay}s...")
                time.sleep(self.config.retry_delay)
                return self._make_request(method, endpoint, data, params, retry + 1)

            raise ConnectionError(f"Failed to reach GitLab API: {e}")

    def trigger_pipeline(
        self,
        branch: str = None,
        parameters: Dict[str, Any] = None,
        commit_sha: str = None
    ) -> PipelineRun:
        """
        Trigger a GitLab CI/CD pipeline run.

        Args:
            branch: Git branch to run pipeline on (defaults to config branch)
            parameters: Additional variables for the pipeline (key-value pairs)
            commit_sha: Specific commit SHA to trigger pipeline for

        Returns:
            PipelineRun object with run information

        Raises:
            ValueError: If trigger fails due to invalid parameters
            ConnectionError: If unable to reach GitLab API

        Example:
            ```python
            gitlab = GitLabCI(config)
            run = gitlab.trigger_pipeline(
                branch="main",
                parameters={"DEPLOY_ENV": "staging"}
            )
            ```
        """
        branch = branch or self.config.branch
        parameters = parameters or {}

        logger.info(
            f"Triggering GitLab CI/CD pipeline for {self.project_path} "
            f"on branch {branch}"
        )

        try:
            # Prepare pipeline trigger payload
            endpoint = f"/projects/{self.encoded_project_path}/pipeline"

            payload = {
                "ref": branch,
            }

            # Add commit SHA if provided
            if commit_sha:
                payload["sha"] = commit_sha

            # Add variables if provided
            if parameters:
                # Convert parameters dict to GitLab variables format
                variables = []
                for key, value in parameters.items():
                    variables.append({
                        "key": str(key),
                        "value": str(value)
                    })
                payload["variables"] = variables

            # Trigger the pipeline
            response = self._make_request("POST", endpoint, data=payload)

            # Extract pipeline information
            pipeline_id = response.get("id")
            if not pipeline_id:
                raise ValueError("GitLab API response did not include pipeline ID")

            # Create PipelineRun object
            run = PipelineRun(
                run_id=str(pipeline_id),
                platform="gitlab",
                repository=self.project_path,
                branch=branch,
                status=self._map_status(response.get("status", "pending")),
                created_at=time.time(),
                updated_at=time.time(),
                url=response.get("web_url"),
                metadata={
                    "sha": response.get("sha"),
                    "ref": response.get("ref"),
                    "created_at": response.get("created_at"),
                    "updated_at": response.get("updated_at"),
                    "source": response.get("source"),
                    "variables": parameters,
                    "triggered_by": "devflow",
                }
            )

            # Register the run
            self._register_run(run)

            logger.info(
                f"Successfully triggered GitLab CI/CD pipeline "
                f"with ID {run.run_id}"
            )
            return run

        except ValueError as e:
            logger.error(f"Failed to trigger GitLab CI/CD pipeline: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error triggering GitLab CI/CD pipeline: {e}")
            raise ConnectionError(f"Failed to trigger GitLab CI/CD pipeline: {e}")

    def get_pipeline_status(self, run_id: str) -> PipelineStatus:
        """
        Get the current status of a pipeline run.

        Args:
            run_id: Pipeline run ID

        Returns:
            PipelineStatus enum value

        Raises:
            ValueError: If run_id is not found
            ConnectionError: If unable to reach GitLab API
        """
        try:
            endpoint = f"/projects/{self.encoded_project_path}/pipelines/{run_id}"
            response = self._make_request("GET", endpoint)

            # Extract and map status
            gitlab_status = response.get("status", "unknown")
            pipeline_status = self._map_status(gitlab_status)

            # Update run in active runs if present
            with self.lock:
                if run_id in self.active_runs:
                    self.active_runs[run_id].status = pipeline_status
                    self.active_runs[run_id].updated_at = time.time()

                    # Update completed_at if pipeline finished
                    if pipeline_status in [PipelineStatus.SUCCESS, PipelineStatus.FAILED, PipelineStatus.CANCELLED]:
                        if not self.active_runs[run_id].completed_at:
                            self.active_runs[run_id].completed_at = time.time()

            return pipeline_status

        except ValueError as e:
            logger.error(f"Failed to get pipeline status: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting pipeline status: {e}")
            raise ConnectionError(f"Failed to get GitLab CI/CD pipeline status: {e}")

    def get_pipeline_details(
        self,
        run_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed information about a pipeline run.

        This is a GitLab-specific method that provides comprehensive
        pipeline information beyond the generic get_pipeline_status() method.

        Args:
            run_id: Pipeline run ID

        Returns:
            Dictionary containing:
                - id: Pipeline ID
                - project_id: Project ID
                - status: PipelineStatus enum value
                - gitlab_status: Raw GitLab status string
                - ref: Branch/tag reference
                - sha: Commit SHA
                - created_at: Pipeline creation timestamp
                - updated_at: Last update timestamp
                - started_at: Pipeline start timestamp (if started)
                - finished_at: Pipeline finish timestamp (if completed)
                - duration: Pipeline duration in seconds (if completed)
                - url: Web URL to the pipeline
                - web_url: Full web URL
                - source: What triggered the pipeline
                - user: User who triggered the pipeline
                - jobs: List of job statuses (if available)
                - variables: Pipeline variables used

        Raises:
            ValueError: If run_id is not found
            ConnectionError: If unable to reach GitLab API

        Example:
            ```python
            details = gitlab.get_pipeline_details("123456")
            print(f"Status: {details['status']}")
            print(f"Duration: {details['duration']}s")
            ```
        """
        try:
            endpoint = f"/projects/{self.encoded_project_path}/pipelines/{run_id}"
            response = self._make_request("GET", endpoint)

            # Extract pipeline information
            gitlab_status = response.get("status", "unknown")
            pipeline_status = self._map_status(gitlab_status)

            details = {
                "id": response.get("id"),
                "project_id": response.get("project_id"),
                "status": pipeline_status,
                "gitlab_status": gitlab_status,
                "ref": response.get("ref"),
                "sha": response.get("sha"),
                "created_at": response.get("created_at"),
                "updated_at": response.get("updated_at"),
                "started_at": response.get("started_at"),
                "finished_at": response.get("finished_at"),
                "duration": response.get("duration"),
                "url": response.get("web_url"),
                "web_url": response.get("web_url"),
                "source": response.get("source"),
                "user": response.get("user", {}).get("name") if response.get("user") else None,
                "variables": response.get("variables", []),
            }

            # Fetch job information if available
            try:
                jobs_endpoint = f"/projects/{self.encoded_project_path}/pipelines/{run_id}/jobs"
                jobs_response = self._make_request("GET", jobs_endpoint, params={"per_page": 100})

                jobs = []
                for job in jobs_response:
                    jobs.append({
                        "id": job.get("id"),
                        "name": job.get("name"),
                        "stage": job.get("stage"),
                        "status": job.get("status"),
                        "created_at": job.get("created_at"),
                        "started_at": job.get("started_at"),
                        "finished_at": job.get("finished_at"),
                        "duration": job.get("duration"),
                        "web_url": job.get("web_url"),
                    })

                details["jobs"] = jobs

            except Exception as e:
                # Jobs are optional - log but don't fail
                logger.debug(f"Could not fetch job details: {e}")
                details["jobs"] = []

            return details

        except ValueError as e:
            logger.error(f"Failed to get pipeline details: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting pipeline details: {e}")
            raise ConnectionError(f"Failed to get GitLab CI/CD pipeline details: {e}")

    def get_pipeline_logs(self, run_id: str) -> str:
        """
        Get logs from a pipeline run.

        Note: GitLab CI/CD stores logs per job, not per pipeline.
        This method returns a summary of jobs and their log URLs.

        Args:
            run_id: Pipeline run ID

        Returns:
            Log output as string with job information and log URLs

        Raises:
            ValueError: If run_id is not found
            ConnectionError: If unable to reach GitLab API
        """
        try:
            # Get pipeline jobs
            jobs_endpoint = f"/projects/{self.encoded_project_path}/pipelines/{run_id}/jobs"
            jobs_response = self._make_request("GET", jobs_endpoint, params={"per_page": 100})

            if not jobs_response:
                return f"No jobs found for pipeline {run_id}"

            # Build log summary with job information
            log_lines = [f"Pipeline {run_id} - Job Logs Summary"]
            log_lines.append("=" * 60)

            for job in jobs_response:
                job_name = job.get("name", "unknown")
                job_id = job.get("id")
                job_status = job.get("status")
                job_stage = job.get("stage")
                job_url = job.get("web_url")

                log_lines.append(f"\nJob: {job_name} (ID: {job_id})")
                log_lines.append(f"  Stage: {job_stage}")
                log_lines.append(f"  Status: {job_status}")
                log_lines.append(f"  Logs: {job_url}")

                # Try to get job trace (actual logs) if job completed/failed
                if job_status in ["success", "failed", "canceled"]:
                    try:
                        trace_endpoint = f"/projects/{self.encoded_project_path}/jobs/{job_id}/trace"
                        trace_response = self.session.get(
                            urljoin(self.config.base_url, trace_endpoint),
                            timeout=30
                        )

                        if trace_response.status_code == 200:
                            log_lines.append(f"\n  --- Job Output ---")
                            log_lines.append(trace_response.text[:500])  # First 500 chars
                            if len(trace_response.text) > 500:
                                log_lines.append(f"\n  ... (truncated, view full logs at {job_url})")
                            log_lines.append(f"  --- End Output ---\n")

                    except Exception as e:
                        logger.debug(f"Could not fetch job trace: {e}")

            return "\n".join(log_lines)

        except ValueError as e:
            logger.error(f"Failed to get pipeline logs: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting pipeline logs: {e}")
            raise ConnectionError(f"Failed to get GitLab CI/CD pipeline logs: {e}")

    def cancel_pipeline(self, run_id: str) -> bool:
        """
        Cancel a running pipeline.

        Args:
            run_id: Pipeline run ID

        Returns:
            True if cancellation was successful

        Raises:
            ValueError: If run_id is not found or pipeline cannot be cancelled
            ConnectionError: If unable to reach GitLab API
        """
        try:
            endpoint = f"/projects/{self.encoded_project_path}/pipelines/{run_id}/cancel"
            self._make_request("POST", endpoint)

            logger.info(f"Successfully cancelled pipeline {run_id}")

            # Update run status
            with self.lock:
                if run_id in self.active_runs:
                    self.active_runs[run_id].status = PipelineStatus.CANCELLED
                    self.active_runs[run_id].updated_at = time.time()

            return True

        except ValueError as e:
            logger.error(f"Failed to cancel pipeline: {e}")
            raise
        except Exception as e:
            logger.error(f"Error cancelling pipeline: {e}")
            raise ConnectionError(f"Failed to cancel GitLab CI/CD pipeline: {e}")

    def retry_pipeline(self, run_id: str) -> PipelineRun:
        """
        Retry a failed or cancelled pipeline.

        This is a GitLab-specific method to re-run a pipeline.

        Args:
            run_id: Pipeline run ID to retry

        Returns:
            New PipelineRun object for the retry

        Raises:
            ValueError: If run_id is not found
            ConnectionError: If unable to reach GitLab API

        Example:
            ```python
            new_run = gitlab.retry_pipeline("123456")
            print(f"Retried as new pipeline: {new_run.run_id}")
            ```
        """
        try:
            endpoint = f"/projects/{self.encoded_project_path}/pipelines/{run_id}/retry"
            response = self._make_request("POST", endpoint)

            # Extract new pipeline information
            pipeline_id = response.get("id")
            if not pipeline_id:
                raise ValueError("GitLab API response did not include pipeline ID")

            # Create PipelineRun object for the new pipeline
            run = PipelineRun(
                run_id=str(pipeline_id),
                platform="gitlab",
                repository=self.project_path,
                branch=response.get("ref", self.config.branch),
                status=self._map_status(response.get("status", "pending")),
                created_at=time.time(),
                updated_at=time.time(),
                url=response.get("web_url"),
                metadata={
                    "sha": response.get("sha"),
                    "ref": response.get("ref"),
                    "created_at": response.get("created_at"),
                    "updated_at": response.get("updated_at"),
                    "source": response.get("source"),
                    "retried_from": run_id,
                    "triggered_by": "devflow",
                }
            )

            # Register the new run
            self._register_run(run)

            logger.info(
                f"Successfully retried pipeline {run_id} "
                f"as new pipeline {run.run_id}"
            )
            return run

        except ValueError as e:
            logger.error(f"Failed to retry pipeline: {e}")
            raise
        except Exception as e:
            logger.error(f"Error retrying pipeline: {e}")
            raise ConnectionError(f"Failed to retry GitLab CI/CD pipeline: {e}")

    def _map_status(self, gitlab_status: str) -> PipelineStatus:
        """
        Map GitLab CI/CD status to PipelineStatus enum.

        Args:
            gitlab_status: GitLab status string

        Returns:
            PipelineStatus enum value
        """
        gitlab_status = gitlab_status.lower().replace(" ", "_")
        return self.STATUS_MAP.get(gitlab_status, PipelineStatus.UNKNOWN)

    def list_pipelines(
        self,
        branch: str = None,
        status: str = None,
        per_page: int = 20
    ) -> list:
        """
        List pipelines for the project.

        Args:
            branch: Filter by branch name (ref)
            status: Filter by status (created, pending, running, success, failed, canceled, skipped)
            per_page: Number of results per page (max 100)

        Returns:
            List of pipeline dictionaries

        Raises:
            ConnectionError: If unable to reach GitLab API
        """
        try:
            endpoint = f"/projects/{self.encoded_project_path}/pipelines"
            params = {"per_page": min(per_page, 100)}

            if branch:
                params["ref"] = branch
            if status:
                params["status"] = status

            response = self._make_request("GET", endpoint, params=params)
            return response

        except Exception as e:
            logger.error(f"Failed to list pipelines: {e}")
            raise ConnectionError(f"Failed to list GitLab CI/CD pipelines: {e}")

    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the GitLab CI integration.

        Returns:
            Dictionary with health status information
        """
        try:
            # Base health check
            health = super().health_check()

            if health["status"] != "healthy":
                return health

            # Test GitLab API connection
            try:
                endpoint = f"/projects/{self.encoded_project_path}"
                self._make_request("GET", endpoint)

                health["repository"] = self.project_path
                health["gitlab_api"] = "connected"

            except Exception as e:
                health["status"] = "degraded"
                health["gitlab_api"] = f"connection_failed: {str(e)}"

            return health

        except Exception as e:
            return {
                "platform": "gitlab",
                "status": "unhealthy",
                "error": str(e),
            }
