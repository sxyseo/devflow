"""
Custom Agent Plugin Implementation.

This module demonstrates how to create a custom agent plugin for DevFlow.
The plugin provides a specialized code reviewer agent with custom behavior.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from devflow.plugins.agent_plugin import AgentPlugin
from devflow.plugins.base import PluginMetadata


logger = logging.getLogger(__name__)


# Simple default agent class for demonstration
class DefaultCodeReviewerAgent:
    """Default agent class for the custom code reviewer plugin."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.agent_id = None

    def execute(self, task: str) -> Any:
        """Execute a code review task."""
        # This is a placeholder - in a real implementation, this would
        # interface with an actual AI model or agent system
        return f"Code review completed for: {task}"


class CustomAgentPlugin(AgentPlugin):
    """
    Example custom agent plugin.

    This plugin demonstrates how to create a custom agent that extends
    DevFlow's capabilities. It implements a code reviewer agent with
    custom behavior and lifecycle hooks.

    Features demonstrated:
    - Custom agent type registration
    - Agent configuration
    - Lifecycle hooks (on created, started, completed, failed)
    - Custom metadata
    """

    def get_metadata(self) -> PluginMetadata:
        """
        Get plugin metadata.

        Returns:
            PluginMetadata describing this plugin
        """
        return PluginMetadata(
            name="custom-agent",
            version="1.0.0",
            description="Example custom agent plugin demonstrating code review capabilities",
            author="DevFlow Team",
            plugin_type="agent",
            dependencies=[],
            devflow_version="0.1.0"
        )

    def get_agent_type(self) -> str:
        """
        Get the agent type identifier.

        Returns:
            Agent type string
        """
        return "custom-code-reviewer"

    def get_agent_class(self):
        """
        Get the agent class this plugin provides.

        Returns:
            Agent class that implements the agent interface
        """
        return DefaultCodeReviewerAgent

    def get_agent_config(self) -> Dict[str, Any]:
        """
        Get default configuration for the agent.

        Returns:
            Dictionary of agent configuration
        """
        return {
            "model": "claude-3-5-sonnet-20241022",
            "max_tasks": 3,
            "timeout": 1800,
            "skills": [
                "code-review",
                "security-analysis",
                "performance-analysis"
            ],
            "system_prompt": """You are an expert code reviewer with deep knowledge of:
- Software architecture and design patterns
- Security best practices and vulnerability detection
- Performance optimization techniques
- Code maintainability and readability

When reviewing code:
1. Identify potential bugs and edge cases
2. Suggest improvements for performance and readability
3. Check for security vulnerabilities
4. Verify adherence to coding standards
5. Provide clear, actionable feedback

Be constructive and educational in your feedback.""",
            "temperature": 0.3,
            "max_tokens": 4000
        }

    def initialize(self) -> None:
        """
        Initialize the plugin.

        Called when the plugin is first loaded.
        """
        super().initialize()
        logger.info(f"CustomAgentPlugin initialized at {datetime.now().isoformat()}")

    def start(self) -> None:
        """
        Start the plugin.

        Called when the plugin should start running.
        """
        super().start()
        logger.info("CustomAgentPlugin started - ready to review code")

    def stop(self) -> None:
        """
        Stop the plugin.

        Called when the plugin should stop running.
        """
        super().stop()
        logger.info("CustomAgentPlugin stopped")

    def register_agent(self, agent_manager) -> None:
        """
        Register the agent with the agent manager.

        Args:
            agent_manager: The AgentManager instance
        """
        super().register_agent(agent_manager)
        logger.info(f"Registered custom agent type: {self.get_agent_type()}")

    def on_agent_created(self, agent_id: str, agent_type: str) -> None:
        """
        Hook called when a new agent is created.

        Args:
            agent_id: ID of the created agent
            agent_type: Type of the created agent
        """
        if agent_type == self.get_agent_type():
            logger.info(f"Custom code reviewer agent created: {agent_id}")
            # Custom initialization logic could go here
            # For example: setting up specialized tools, loading review templates, etc.

    def on_agent_started(self, agent_id: str, task: str) -> None:
        """
        Hook called when an agent starts a task.

        Args:
            agent_id: ID of the agent
            task: Task description
        """
        logger.info(f"Agent {agent_id} started task: {task[:100]}...")
        # Could track task start time, initialize task-specific resources, etc.

    def on_agent_completed(self, agent_id: str, result: Any) -> None:
        """
        Hook called when an agent completes a task.

        Args:
            agent_id: ID of the agent
            result: Task result
        """
        logger.info(f"Agent {agent_id} completed task successfully")
        # Could process results, update metrics, trigger notifications, etc.

    def on_agent_failed(self, agent_id: str, error: Exception) -> None:
        """
        Hook called when an agent fails.

        Args:
            agent_id: ID of the agent
            error: Exception that caused the failure
        """
        logger.error(f"Agent {agent_id} failed with error: {str(error)}")
        # Could implement custom error handling, retry logic, alerts, etc.
