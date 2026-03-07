"""
DevFlow Configuration Settings

Central configuration for the entire DevFlow system.
"""

import os
from pathlib import Path
from typing import Dict, List, Any
import json


class Settings:
    """Global settings for DevFlow system."""

    def __init__(self):
        # Paths
        self.project_root = Path(__file__).parent.parent.parent
        self.workspace_dir = self.project_root / ".openclaw" / "workspace"
        self.agents_dir = self.project_root / ".openclaw" / "agents"
        self.skills_dir = self.project_root / "skills"
        self.docs_dir = self.project_root / "docs"
        self.logs_dir = self.project_root / ".devflow" / "logs"
        self.state_dir = self.project_root / ".devflow" / "state"
        self.worktrees_dir = Path("/tmp/devflow-worktrees")

        # Agent Settings
        self.max_concurrent_agents = int(os.getenv("MAX_CONCURRENT_AGENTS", "6"))
        self.agent_timeout = int(os.getenv("AGENT_TIMEOUT", "3600"))  # 1 hour
        self.agent_model = os.getenv("AGENT_MODEL", "claude-3-5-sonnet-20241022")

        # Task Settings
        self.max_parallel_tasks = int(os.getenv("MAX_PARALLEL_TASKS", "4"))
        self.task_retry_limit = int(os.getenv("TASK_RETRY_LIMIT", "3"))
        self.task_queue_size = int(os.getenv("TASK_QUEUE_SIZE", "100"))

        # Quality Settings
        self.require_tests = True
        self.test_coverage_threshold = 80.0
        self.require_code_review = True
        self.enable_auto_fix = True
        self.max_fix_iterations = 3

        # Git Settings
        self.main_branch = os.getenv("MAIN_BRANCH", "main")
        self.use_worktrees = True
        self.auto_cleanup_worktrees = True

        # Tmux Settings
        self.tmux_session_prefix = "devflow-"
        self.tmux_auto_attach = False

        # Monitoring Settings
        self.enable_metrics = True
        self.metrics_port = int(os.getenv("METRICS_PORT", "9090"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # BMAD Workflow Settings
        self.bmad_agents = [
            "product-owner",
            "business-analyst",
            "architect",
            "ux-designer",
            "scrum-master",
            "readiness-check",
            "create-story",
            "dev-story",
            "code-review",
            "ux-review",
            "qa-tester",
            "retrospective",
        ]

        # Model Configuration
        self.model_config_path = self.project_root / "devflow" / "config" / "model_config.json"
        self.model_config = self._load_model_config()
        self.provider_api_keys = self._load_provider_api_keys()

    def _load_model_config(self) -> Dict[str, Any]:
        """Load model configuration from model_config.json."""
        default_config = {
            "providers": {},
            "task_mappings": {},
            "agent_mappings": {},
            "fallback_config": {
                "enabled": True,
                "max_attempts": 3,
            },
            "cost_optimization": {
                "enabled": True,
            },
            "performance_tracking": {
                "enabled": True,
            },
            "selection_strategy": {
                "default": "balanced",
            },
        }

        if self.model_config_path.exists():
            try:
                with open(self.model_config_path, 'r') as f:
                    config = json.load(f)
                    return config
            except (json.JSONDecodeError, IOError) as e:
                # Return default config if file is invalid
                return default_config

        return default_config

    def _load_provider_api_keys(self) -> Dict[str, str]:
        """Load API keys for enabled providers from environment variables."""
        api_keys = {}

        if not self.model_config or "providers" not in self.model_config:
            return api_keys

        for provider_id, provider_config in self.model_config.get("providers", {}).items():
            if provider_config.get("enabled", False):
                env_var = provider_config.get("api_key_env")
                if env_var:
                    api_key = os.getenv(env_var)
                    if api_key:
                        api_keys[provider_id] = api_key

        return api_keys

    def ensure_directories(self):
        """Create all necessary directories."""
        dirs = [
            self.workspace_dir,
            self.agents_dir,
            self.logs_dir,
            self.state_dir,
            self.worktrees_dir,
        ]

        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "project_root": str(self.project_root),
            "workspace_dir": str(self.workspace_dir),
            "agents_dir": str(self.agents_dir),
            "skills_dir": str(self.skills_dir),
            "docs_dir": str(self.docs_dir),
            "logs_dir": str(self.logs_dir),
            "state_dir": str(self.state_dir),
            "worktrees_dir": str(self.worktrees_dir),
            "max_concurrent_agents": self.max_concurrent_agents,
            "agent_timeout": self.agent_timeout,
            "agent_model": self.agent_model,
            "max_parallel_tasks": self.max_parallel_tasks,
            "task_retry_limit": self.task_retry_limit,
            "task_queue_size": self.task_queue_size,
            "require_tests": self.require_tests,
            "test_coverage_threshold": self.test_coverage_threshold,
            "require_code_review": self.require_code_review,
            "enable_auto_fix": self.enable_auto_fix,
            "max_fix_iterations": self.max_fix_iterations,
            "main_branch": self.main_branch,
            "use_worktrees": self.use_worktrees,
            "auto_cleanup_worktrees": self.auto_cleanup_worktrees,
            "tmux_session_prefix": self.tmux_session_prefix,
            "enable_metrics": self.enable_metrics,
            "metrics_port": self.metrics_port,
            "log_level": self.log_level,
            "bmad_agents": self.bmad_agents,
            "model_config_path": str(self.model_config_path),
        }

    def save(self, path: Path = None):
        """Save settings to JSON file."""
        if path is None:
            path = self.state_dir / "settings.json"

        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path = None):
        """Load settings from JSON file."""
        settings = cls()

        if path is None:
            path = settings.state_dir / "settings.json"

        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)

            for key, value in data.items():
                if hasattr(settings, key):
                    # Convert string paths back to Path objects
                    if key.endswith('_dir') or key.endswith('_root'):
                        value = Path(value)
                    setattr(settings, key, value)

        return settings


# Global settings instance
settings = Settings()
