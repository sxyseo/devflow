"""
Agent Plugin - Base class and utilities for agent plugins.

Provides specialized functionality for plugins that extend DevFlow's agent capabilities.
Agent plugins can register custom agent types, provide custom agent configurations,
and extend agent behavior.
"""

from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass

from .base import AgentPlugin as BaseAgentPlugin, PluginMetadata


@dataclass
class AgentConfig:
    """Configuration for an agent type."""
    agent_type: str
    model: str = "claude-3-5-sonnet-20241022"
    max_tasks: int = 1
    timeout: int = 3600
    skills: List[str] = None
    system_prompt: str = ""

    def __post_init__(self):
        if self.skills is None:
            self.skills = []


class AgentPlugin(BaseAgentPlugin):
    """
    Base class for agent plugins.

    Agent plugins extend DevFlow's agent capabilities by providing custom agent
    implementations or modifications to existing agents.

    To create a custom agent plugin:
    1. Inherit from this class
    2. Implement get_metadata() to describe your plugin
    3. Implement get_agent_type() to specify the agent type identifier
    4. Implement get_agent_config() to provide default configuration
    5. Optionally override register_agent() for custom registration logic

    Example:
        class MyCustomAgentPlugin(AgentPlugin):
            def get_metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="my-custom-agent",
                    version="1.0.0",
                    description="My custom agent plugin",
                    author="Your Name",
                    plugin_type="agent"
                )

            def get_agent_type(self) -> str:
                return "my-custom-agent"

            def get_agent_config(self) -> Dict[str, Any]:
                return {
                    "model": "claude-3-5-sonnet-20241022",
                    "skills": ["custom-skill"],
                    "system_prompt": "You are a custom agent."
                }
    """

    def get_agent_config(self) -> Dict[str, Any]:
        """
        Get default configuration for the agent.

        Returns:
            Dictionary of default agent configuration. Should include:
            - model: Model name to use
            - skills: List of skills the agent has
            - system_prompt: System prompt for the agent
            - max_tasks: Maximum concurrent tasks (optional)
            - timeout: Task timeout in seconds (optional)
        """
        return {}

    def register_agent(self, agent_manager) -> None:
        """
        Register the agent with the agent manager.

        This method is called when the plugin is loaded. It registers the
        agent type and configuration with the AgentManager.

        Args:
            agent_manager: The AgentManager instance to register with
        """
        agent_type = self.get_agent_type()
        config = self.get_agent_config()

        # Register the agent configuration with the agent manager
        if hasattr(agent_manager, 'register_agent_type'):
            agent_manager.register_agent_type(
                agent_type=agent_type,
                config=config
            )

    def on_agent_created(self, agent_id: str, agent_type: str) -> None:
        """
        Hook called when a new agent is created.

        Override this method to perform custom initialization when
        an agent of this type is created.

        Args:
            agent_id: ID of the created agent
            agent_type: Type of the created agent
        """
        pass

    def on_agent_started(self, agent_id: str, task: str) -> None:
        """
        Hook called when an agent starts a task.

        Override this method to perform custom actions when an agent
        of this type starts a task.

        Args:
            agent_id: ID of the agent
            task: Task description
        """
        pass

    def on_agent_completed(self, agent_id: str, result: Any) -> None:
        """
        Hook called when an agent completes a task.

        Override this method to perform custom actions when an agent
        of this type completes a task.

        Args:
            agent_id: ID of the agent
            result: Task result
        """
        pass

    def on_agent_failed(self, agent_id: str, error: Exception) -> None:
        """
        Hook called when an agent fails.

        Override this method to perform custom error handling when an
        agent of this type fails.

        Args:
            agent_id: ID of the agent
            error: Exception that caused the failure
        """
        pass


class AgentPluginRegistry:
    """
    Registry for managing agent plugins.

    Provides a centralized registry for agent plugins and handles
    integration with the AgentManager.
    """

    def __init__(self):
        self._agent_plugins: Dict[str, AgentPlugin] = {}
        self._agent_configs: Dict[str, Dict[str, Any]] = {}

    def register_agent_plugin(self, plugin: AgentPlugin) -> None:
        """
        Register an agent plugin.

        Args:
            plugin: AgentPlugin instance to register
        """
        agent_type = plugin.get_agent_type()
        self._agent_plugins[agent_type] = plugin
        self._agent_configs[agent_type] = plugin.get_agent_config()

    def unregister_agent_plugin(self, agent_type: str) -> bool:
        """
        Unregister an agent plugin.

        Args:
            agent_type: Agent type to unregister

        Returns:
            True if plugin was unregistered, False if not found
        """
        if agent_type in self._agent_plugins:
            del self._agent_plugins[agent_type]
            if agent_type in self._agent_configs:
                del self._agent_configs[agent_type]
            return True
        return False

    def get_agent_plugin(self, agent_type: str) -> Optional[AgentPlugin]:
        """
        Get an agent plugin by type.

        Args:
            agent_type: Agent type to get

        Returns:
            AgentPlugin instance or None if not found
        """
        return self._agent_plugins.get(agent_type)

    def get_agent_config(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """
        Get agent configuration from a plugin.

        Args:
            agent_type: Agent type to get configuration for

        Returns:
            Agent configuration dictionary or None if not found
        """
        return self._agent_configs.get(agent_type)

    def list_agent_types(self) -> List[str]:
        """
        List all registered agent types.

        Returns:
            List of agent type identifiers
        """
        return list(self._agent_plugins.keys())

    def get_all_agent_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all agent configurations from plugins.

        Returns:
            Dictionary mapping agent types to their configurations
        """
        return self._agent_configs.copy()

    def integrate_with_agent_manager(self, agent_manager) -> None:
        """
        Integrate all registered agent plugins with an AgentManager.

        Args:
            agent_manager: AgentManager instance to integrate with
        """
        for plugin in self._agent_plugins.values():
            try:
                plugin.register_agent(agent_manager)
            except Exception as e:
                # Log error but continue with other plugins
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to register agent plugin {plugin.get_agent_type()}: {e}")


# Global agent plugin registry instance
agent_plugin_registry = AgentPluginRegistry()
