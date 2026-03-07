"""
GitHub Actions Integration.

Provides integration with GitHub Actions for triggering and monitoring workflows.
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


class GitHubActions(PipelineIntegration):
    """
    GitHub Actions integration for triggering and monitoring workflows.

    This class provides methods to:
    - Trigger GitHub Actions workflows via repository_dispatch or workflow_dispatch
    - Monitor workflow run status
    - Fetch workflow logs
    - Cancel running workflows

    Authentication:
    - Requires a GitHub Personal Access Token (PAT) with repo scope
    - Token should be provided via PipelineConfig.api_token

    Example:
        ```python
        config = PipelineConfig(
            platform="github",
            api_token="ghp_xxx",
            repository="owner/repo",
            branch="main"
        )
        github = GitHubActions(config)
        run = github.trigger_pipeline(branch="feature-branch")
        ```
    """

    # GitHub API endpoints
    API_BASE_URL = "https://api.github.com"
    DEFAULT_BASE_URL = API_BASE_URL

    # Workflow status mapping from GitHub Actions to PipelineStatus
    STATUS_MAP = {
        "queued": PipelineStatus.QUEUED,
        "in_progress": PipelineStatus.RUNNING,
        "completed": PipelineStatus.SUCCESS,
        "success": PipelineStatus.SUCCESS,
        "failure": PipelineStatus.FAILED,
        "failed": PipelineStatus.FAILED,
        "cancelled": PipelineStatus.CANCELLED,
        "timed_out": PipelineStatus.FAILED,
        "action_required": PipelineStatus.PENDING,
        "pending": PipelineStatus.PENDING,
        "waiting": PipelineStatus.PENDING,
    }

    def __init__(self, config: PipelineConfig):
        """
        Initialize GitHub Actions integration.

        Args:
            config: Pipeline configuration with GitHub-specific settings

        Raises:
            ValueError: If configuration is invalid
        """
        # Set default base URL if not provided
        if not config.base_url:
            config.base_url = self.DEFAULT_BASE_URL

        # Add GitHub-specific validation
        if config.enabled and config.api_token:
            if not config.api_token.startswith("ghp_") and not config.api_token.startswith("github_pat_"):
                logger.warning(
                    f"GitHub token format may be invalid. "
                    f"Expected token to start with 'ghp_' or 'github_pat_', got: {config.api_token[:10]}..."
                )

        super().__init__(config)

        # Parse owner and repo from repository string
        if config.repository:
            self.owner, self.repo = self._parse_repository(config.repository)
        else:
            self.owner = None
            self.repo = None

        # Setup requests session
        self.session = self._create_session()

    def _parse_repository(self, repository: str) -> tuple:
        """
        Parse owner and repo from repository string.

        Args:
            repository: Repository in format "owner/repo" or "https://github.com/owner/repo"

        Returns:
            Tuple of (owner, repo)

        Raises:
            ValueError: If repository format is invalid
        """
        if "github.com/" in repository:
            # Extract from URL
            parts = repository.split("github.com/")[-1].split("/")
            if len(parts) >= 2:
                return parts[0], parts[1].replace(".git", "")

        # Parse from owner/repo format
        parts = repository.split("/")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid repository format: {repository}. "
                f"Expected 'owner/repo' or full GitHub URL"
            )

        return parts[0], parts[1]

    def _create_session(self) -> requests.Session:
        """
        Create configured requests session for GitHub API.

        Returns:
            Configured requests.Session object
        """
        session = requests.Session()

        # Set headers
        session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.config.api_token}",
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
        Make authenticated request to GitHub API with retry logic.

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
            if response.status_code == 403 and "rate limit" in response.text.lower():
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"GitHub rate limit hit, waiting {retry_after}s")
                time.sleep(retry_after)
                if retry < self.config.retry_attempts:
                    return self._make_request(method, endpoint, data, params, retry + 1)

            # Check for authentication errors
            if response.status_code == 401:
                raise ValueError(
                    "GitHub authentication failed. Check your API token."
                )

            # Check for other errors
            if response.status_code >= 400:
                error_msg = response.text or response.reason
                raise ConnectionError(
                    f"GitHub API request failed: {response.status_code} - {error_msg}"
                )

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Request to GitHub API failed: {e}")

            if retry < self.config.retry_attempts:
                logger.info(f"Retrying in {self.config.retry_delay}s...")
                time.sleep(self.config.retry_delay)
                return self._make_request(method, endpoint, data, params, retry + 1)

            raise ConnectionError(f"Failed to reach GitHub API: {e}")

    def _get_workflow_id(self, workflow_name: str = None) -> Optional[str]:
        """
        Get workflow ID by name.

        Args:
            workflow_name: Name of the workflow file (e.g., "ci.yml")

        Returns:
            Workflow ID or None if not found
        """
        try:
            endpoint = f"/repos/{self.owner}/{self.repo}/actions/workflows"
            response = self._make_request("GET", endpoint)

            for workflow in response.get("workflows", []):
                if workflow_name:
                    if workflow_name in workflow.get("name", "") or \
                       workflow_name in workflow.get("path", ""):
                        return str(workflow.get("id"))
                else:
                    # Return first workflow if no name specified
                    return str(workflow.get("id"))

            return None

        except Exception as e:
            logger.error(f"Failed to get workflow ID: {e}")
            return None

    def trigger_workflow(
        self,
        workflow_id: str,
        branch: str = None,
        inputs: Dict[str, Any] = None,
        commit_sha: str = None
    ) -> PipelineRun:
        """
        Trigger a specific GitHub Actions workflow via API.

        This is a GitHub Actions-specific method that provides direct control
        over workflow triggering, unlike the generic trigger_pipeline() method.

        Args:
            workflow_id: The ID or filename of the workflow to trigger
            branch: Git branch to run workflow on (defaults to config branch)
            inputs: Dictionary of input parameters for the workflow
            commit_sha: Specific commit SHA to trigger workflow for

        Returns:
            PipelineRun object with run information

        Raises:
            ValueError: If trigger fails due to invalid parameters
            ConnectionError: If unable to reach GitHub API

        Example:
            ```python
            github = GitHubActions(config)
            run = github.trigger_workflow(
                workflow_id="ci.yml",
                branch="main",
                inputs={"environment": "staging"}
            )
            ```
        """
        branch = branch or self.config.branch
        inputs = inputs or {}

        logger.info(
            f"Triggering GitHub Actions workflow '{workflow_id}' "
            f"for {self.owner}/{self.repo} on branch {branch}"
        )

        try:
            # Resolve workflow_id if it's a filename
            if not workflow_id.isdigit():
                # It's a workflow filename, not an ID
                workflow_id = self._get_workflow_id(workflow_id)

            if not workflow_id:
                raise ValueError(
                    f"Could not find workflow '{workflow_id}'. "
                    f"Please verify the workflow exists in the repository."
                )

            # Prepare workflow_dispatch payload
            endpoint = f"/repos/{self.owner}/{self.repo}/actions/workflows/{workflow_id}/dispatches"

            payload = {
                "ref": branch,
            }

            # Add inputs if workflow supports them
            if inputs:
                payload["inputs"] = inputs

            # Trigger the workflow
            self._make_request("POST", endpoint, data=payload)

            # Get the latest workflow run for this branch
            # We need to wait a moment for GitHub to register the run
            time.sleep(2)

            runs_endpoint = f"/repos/{self.owner}/{self.repo}/actions/runs"
            params = {
                "branch": branch,
                "per_page": 1
            }
            response = self._make_request("GET", runs_endpoint, params=params)

            runs = response.get("workflow_runs", [])
            if not runs:
                raise ValueError("Failed to retrieve workflow run after trigger")

            run_data = runs[0]

            # Create PipelineRun object
            run = PipelineRun(
                run_id=str(run_data["id"]),
                platform="github",
                repository=f"{self.owner}/{self.repo}",
                branch=branch,
                status=self._map_status(run_data.get("status", "queued")),
                created_at=time.time(),
                updated_at=time.time(),
                url=run_data.get("html_url"),
                logs_url=run_data.get("logs_url"),
                metadata={
                    "workflow_id": workflow_id,
                    "workflow_name": run_data.get("name"),
                    "event": run_data.get("event"),
                    "commit_sha": commit_sha or run_data.get("head_sha"),
                    "triggered_by": "devflow",
                    "inputs": inputs,
                }
            )

            # Register the run
            self._register_run(run)

            logger.info(
                f"Successfully triggered workflow '{workflow_id}' "
                f"with run ID {run.run_id}"
            )
            return run

        except ValueError as e:
            logger.error(f"Failed to trigger workflow '{workflow_id}': {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error triggering workflow '{workflow_id}': {e}")
            raise ConnectionError(f"Failed to trigger GitHub Actions workflow: {e}")

    def trigger_pipeline(
        self,
        branch: str = None,
        parameters: Dict[str, Any] = None,
        commit_sha: str = None
    ) -> PipelineRun:
        """
        Trigger a GitHub Actions workflow run (generic interface).

        This method implements the base class interface and delegates to
        trigger_workflow() for actual GitHub Actions-specific functionality.

        Args:
            branch: Git branch to run workflow on (defaults to config branch)
            parameters: Additional parameters for the workflow.
                      Can include workflow_name, workflow_id, or inputs
            commit_sha: Specific commit SHA to trigger workflow for

        Returns:
            PipelineRun object with run information

        Raises:
            ValueError: If trigger fails due to invalid parameters
            ConnectionError: If unable to reach GitHub API
        """
        branch = branch or self.config.branch
        parameters = parameters or {}

        logger.info(
            f"Triggering GitHub Actions workflow for {self.owner}/{self.repo} "
            f"on branch {branch}"
        )

        try:
            # Extract workflow identifier from parameters
            workflow_identifier = (
                parameters.get("workflow_id") or
                parameters.get("workflow_name") or
                self._get_workflow_id()
            )

            if not workflow_identifier:
                raise ValueError(
                    f"Could not determine workflow to trigger. "
                    f"Please specify workflow_name or workflow_id in parameters."
                )

            # Extract inputs if provided
            inputs = parameters.get("inputs", {})

            # Delegate to trigger_workflow
            return self.trigger_workflow(
                workflow_id=workflow_identifier,
                branch=branch,
                inputs=inputs,
                commit_sha=commit_sha
            )

        except ValueError as e:
            logger.error(f"Failed to trigger workflow: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error triggering workflow: {e}")
            raise ConnectionError(f"Failed to trigger GitHub Actions workflow: {e}")

    def get_workflow_status(
        self,
        run_id: str,
        poll: bool = False,
        timeout: int = 600,
        interval: int = 10
    ) -> Dict[str, Any]:
        """
        Get detailed status of a workflow run with optional polling.

        This is a GitHub Actions-specific method that provides comprehensive
        status information beyond the generic get_pipeline_status() method.

        Args:
            run_id: Workflow run ID
            poll: Whether to continuously poll until completion (default: False)
            timeout: Maximum polling time in seconds (default: 600)
            interval: Polling interval in seconds (default: 10)

        Returns:
            Dictionary containing:
                - status: PipelineStatus enum value
                - github_status: Raw GitHub status string
                - conclusion: Raw GitHub conclusion string (if completed)
                - created_at: Workflow creation timestamp
                - updated_at: Last update timestamp
                - started_at: Workflow start timestamp (if started)
                - completed_at: Workflow completion timestamp (if completed)
                - url: HTML URL to the workflow run
                - name: Workflow name
                - run_number: Workflow run number
                - run_attempt: Run attempt number
                - event: Event that triggered the workflow
                - commit_sha: Commit SHA that triggered the workflow
                - branch: Branch name
                - actor: User/actor who triggered the workflow
                - workflow_id: Workflow ID
                - jobs: List of job statuses (if available)

        Raises:
            ValueError: If run_id is not found
            ConnectionError: If unable to reach GitHub API
            TimeoutError: If polling timeout is exceeded

        Example:
            ```python
            # Get current status without polling
            status = github.get_workflow_status("123456789")

            # Poll until completion with custom timeout
            status = github.get_workflow_status("123456789", poll=True, timeout=300)
            ```
        """
        start_time = time.time()
        last_status = None

        try:
            while True:
                try:
                    endpoint = f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}"
                    response = self._make_request("GET", endpoint)

                    # Extract status information
                    github_status = response.get("status", "unknown")
                    conclusion = response.get("conclusion")

                    # Map to PipelineStatus
                    if github_status == "completed" and conclusion:
                        pipeline_status = self._map_status(conclusion)
                    else:
                        pipeline_status = self._map_status(github_status)

                    # Build detailed status dictionary
                    status_info = {
                        "status": pipeline_status,
                        "github_status": github_status,
                        "conclusion": conclusion,
                        "created_at": response.get("created_at"),
                        "updated_at": response.get("updated_at"),
                        "started_at": response.get("run_started_at"),
                        "completed_at": response.get("updated_at") if github_status == "completed" else None,
                        "url": response.get("html_url"),
                        "name": response.get("name"),
                        "run_number": response.get("run_number"),
                        "run_attempt": response.get("run_attempt"),
                        "event": response.get("event"),
                        "commit_sha": response.get("head_sha"),
                        "branch": response.get("head_branch"),
                        "actor": response.get("triggering_actor", {}).get("login") if response.get("triggering_actor") else None,
                        "workflow_id": response.get("workflow_id"),
                    }

                    # Add job information if available
                    try:
                        jobs_endpoint = f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/jobs"
                        jobs_response = self._make_request("GET", jobs_endpoint, params={"per_page": 100})

                        jobs = []
                        for job in jobs_response.get("jobs", []):
                            jobs.append({
                                "id": job.get("id"),
                                "name": job.get("name"),
                                "status": job.get("status"),
                                "conclusion": job.get("conclusion"),
                                "started_at": job.get("started_at"),
                                "completed_at": job.get("completed_at"),
                            })

                        status_info["jobs"] = jobs

                    except Exception as e:
                        # Jobs are optional - log but don't fail
                        logger.debug(f"Could not fetch job details: {e}")
                        status_info["jobs"] = []

                    # Log status change if polling
                    if poll and last_status != pipeline_status:
                        logger.info(
                            f"Workflow {run_id} status: {pipeline_status.name} "
                            f"(GitHub: {github_status}"
                            + (f" / {conclusion}" if conclusion else "") + ")"
                        )
                        last_status = pipeline_status

                    # If not polling or workflow is complete, return status
                    if not poll or pipeline_status in [
                        PipelineStatus.SUCCESS,
                        PipelineStatus.FAILED,
                        PipelineStatus.CANCELLED
                    ]:
                        # Update run in active runs if present
                        with self.lock:
                            if run_id in self.active_runs:
                                self.active_runs[run_id].status = pipeline_status
                                self.active_runs[run_id].updated_at = time.time()

                        return status_info

                    # Check timeout
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        raise TimeoutError(
                            f"Workflow {run_id} did not complete within {timeout} seconds. "
                            f"Last status: {pipeline_status.name}"
                        )

                    # Wait before next poll
                    time.sleep(interval)

                except ValueError as e:
                    logger.error(f"Failed to get workflow status: {e}")
                    raise
                except requests.exceptions.RequestException as e:
                    # Retry on network errors during polling
                    if not poll:
                        raise ConnectionError(f"Failed to get workflow status: {e}")

                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        raise TimeoutError(
                            f"Network errors persisted for {timeout} seconds while polling workflow {run_id}"
                        )

                    logger.warning(f"Network error during polling, retrying: {e}")
                    time.sleep(interval)

        except (ValueError, ConnectionError, TimeoutError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting workflow status: {e}")
            raise ConnectionError(f"Failed to get GitHub Actions workflow status: {e}")

    def get_pipeline_status(self, run_id: str) -> PipelineStatus:
        """
        Get the current status of a workflow run.

        This is the generic interface method that delegates to get_workflow_status().

        Args:
            run_id: Workflow run ID

        Returns:
            PipelineStatus enum value

        Raises:
            ValueError: If run_id is not found
            ConnectionError: If unable to reach GitHub API
        """
        try:
            status_info = self.get_workflow_status(run_id, poll=False)
            return status_info["status"]

        except ValueError as e:
            logger.error(f"Failed to get workflow status: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting workflow status: {e}")
            raise ConnectionError(f"Failed to get GitHub Actions workflow status: {e}")

    def get_pipeline_logs(self, run_id: str) -> str:
        """
        Get logs from a workflow run.

        Args:
            run_id: Workflow run ID

        Returns:
            Log output as string

        Raises:
            ValueError: If run_id is not found
            ConnectionError: If unable to reach GitHub API
        """
        try:
            endpoint = f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/logs"

            # Make request with accept header for logs
            headers = {"Accept": "application/vnd.github.v3+json"}
            response = self.session.get(
                urljoin(self.config.base_url, endpoint),
                headers=headers,
                timeout=60
            )

            if response.status_code == 404:
                raise ValueError(f"Workflow run {run_id} not found")

            if response.status_code >= 400:
                raise ConnectionError(
                    f"Failed to get logs: {response.status_code} - {response.reason}"
                )

            # GitHub returns logs as a zip file
            # For now, return a message about log availability
            if response.headers.get("Content-Type") == "application/zip":
                return (
                    f"Logs are available for download at: "
                    f"{self.config.base_url}/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/logs\n"
                    f"Use the GitHub UI or API to download the full log archive."
                )

            return response.text

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error getting workflow logs: {e}")
            raise ConnectionError(f"Failed to get GitHub Actions workflow logs: {e}")

    def cancel_pipeline(self, run_id: str) -> bool:
        """
        Cancel a running workflow.

        Args:
            run_id: Workflow run ID

        Returns:
            True if cancellation was successful

        Raises:
            ValueError: If run_id is not found or workflow cannot be cancelled
            ConnectionError: If unable to reach GitHub API
        """
        try:
            endpoint = f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/cancel"
            self._make_request("POST", endpoint)

            logger.info(f"Successfully cancelled workflow run {run_id}")

            # Update run status
            with self.lock:
                if run_id in self.active_runs:
                    self.active_runs[run_id].status = PipelineStatus.CANCELLED
                    self.active_runs[run_id].updated_at = time.time()

            return True

        except ValueError as e:
            logger.error(f"Failed to cancel workflow: {e}")
            raise
        except Exception as e:
            logger.error(f"Error cancelling workflow: {e}")
            raise ConnectionError(f"Failed to cancel GitHub Actions workflow: {e}")

    def _map_status(self, github_status: str) -> PipelineStatus:
        """
        Map GitHub Actions status to PipelineStatus enum.

        Args:
            github_status: GitHub status string

        Returns:
            PipelineStatus enum value
        """
        github_status = github_status.lower().replace(" ", "_")
        return self.STATUS_MAP.get(github_status, PipelineStatus.UNKNOWN)

    def get_workflow_runs(
        self,
        branch: str = None,
        status: str = None,
        per_page: int = 30
    ) -> list:
        """
        List workflow runs for the repository.

        Args:
            branch: Filter by branch name
            status: Filter by status (completed, success, failure, etc.)
            per_page: Number of results per page (max 100)

        Returns:
            List of workflow run dictionaries

        Raises:
            ConnectionError: If unable to reach GitHub API
        """
        try:
            endpoint = f"/repos/{self.owner}/{self.repo}/actions/runs"
            params = {"per_page": min(per_page, 100)}

            if branch:
                params["branch"] = branch
            if status:
                params["status"] = status

            response = self._make_request("GET", endpoint, params=params)
            return response.get("workflow_runs", [])

        except Exception as e:
            logger.error(f"Failed to get workflow runs: {e}")
            raise ConnectionError(f"Failed to list GitHub Actions workflow runs: {e}")

    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the GitHub Actions integration.

        Returns:
            Dictionary with health status information
        """
        try:
            # Base health check
            health = super().health_check()

            if health["status"] != "healthy":
                return health

            # Test GitHub API connection
            try:
                endpoint = f"/repos/{self.owner}/{self.repo}"
                self._make_request("GET", endpoint)

                health["repository"] = f"{self.owner}/{self.repo}"
                health["github_api"] = "connected"

            except Exception as e:
                health["status"] = "degraded"
                health["github_api"] = f"connection_failed: {str(e)}"

            return health

        except Exception as e:
            return {
                "platform": "github",
                "status": "unhealthy",
                "error": str(e),
            }
