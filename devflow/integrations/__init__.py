"""
CI/CD Integration Package.

Provides integration with popular CI/CD platforms including:
- GitHub Actions
- GitLab CI
- Jenkins
"""

from .base import PipelineIntegration, PipelineConfig, PipelineStatus
from .github_actions import GitHubActions

__all__ = [
    "PipelineIntegration",
    "PipelineConfig",
    "PipelineStatus",
    "GitHubActions",
]
