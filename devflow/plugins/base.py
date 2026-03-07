"""
Plugin Base Classes - Base classes for all plugin types.

Defines the plugin interface and common functionality for all plugins.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    name: str
    version: str
    description: str
    author: str
    plugin_type: str
    dependencies: List[str] = field(default_factory=list)
    devflow_version: str = "0.1.0"  # Minimum DevFlow version required


class Plugin(ABC):
    """
    Base class for all plugins.

    All plugins must inherit from this class and implement the required methods.
    Plugins are isolated units of functionality that can extend DevFlow's capabilities.

    Provides:
    - Plugin metadata management
    - Plugin lifecycle methods (initialize, start, stop)
    - Plugin configuration handling
    - Plugin dependency management
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the plugin.

        Args:
            config: Optional plugin configuration dictionary
        """
        self.config = config or {}
        self._initialized = False
        self._running = False

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """
        Get the plugin's metadata.

        Returns:
            PluginMetadata object containing plugin information
        """
        pass

    def initialize(self) -> None:
        """
        Initialize the plugin.

        Called when the plugin is first loaded. Override this method
        to perform any initialization logic.
        """
        self._initialized = True

    def start(self) -> None:
        """
        Start the plugin.

        Called when the plugin should start running. Override this method
        to implement the plugin's main functionality.
        """
        if not self._initialized:
            self.initialize()
        self._running = True

    def stop(self) -> None:
        """
        Stop the plugin.

        Called when the plugin should stop running. Override this method
        to implement cleanup logic.
        """
        self._running = False

    def is_initialized(self) -> bool:
        """Check if the plugin is initialized."""
        return self._initialized

    def is_running(self) -> bool:
        """Check if the plugin is running."""
        return self._running

    def get_dependencies(self) -> List[str]:
        """
        Get the plugin's dependencies.

        Returns:
            List of plugin names this plugin depends on
        """
        return self.get_metadata().dependencies

    def validate_dependencies(self, available_plugins: List[str]) -> bool:
        """
        Validate that all dependencies are available.

        Args:
            available_plugins: List of available plugin names

        Returns:
            True if all dependencies are available, False otherwise
        """
        dependencies = self.get_dependencies()
        return all(dep in available_plugins for dep in dependencies)


class AgentPlugin(Plugin):
    """
    Base class for agent plugins.

    Agent plugins extend DevFlow's agent capabilities by providing
    custom agent implementations or modifications to existing agents.

    Provides:
    - Agent registration and management
    - Custom agent type definitions
    - Agent behavior extensions
    """

    @abstractmethod
    def get_agent_type(self) -> str:
        """
        Get the agent type this plugin provides.

        Returns:
            Agent type identifier (e.g., "custom-code-reviewer")
        """
        pass

    @abstractmethod
    def get_agent_class(self):
        """
        Get the agent class this plugin provides.

        Returns:
            Agent class that implements the agent interface
        """
        pass

    def get_agent_config(self) -> Dict[str, Any]:
        """
        Get default configuration for the agent.

        Returns:
            Dictionary of default agent configuration
        """
        return {}

    def register_agent(self, agent_manager) -> None:
        """
        Register the agent with the agent manager.

        Args:
            agent_manager: The agent manager to register with
        """
        agent_type = self.get_agent_type()
        agent_class = self.get_agent_class()
        config = self.get_agent_config()

        # Register the agent type and class
        if hasattr(agent_manager, 'register_agent_type'):
            agent_manager.register_agent_type(agent_type, agent_class, config)


class TaskSourcePlugin(Plugin):
    """
    Base class for task source plugins.

    Task source plugins provide custom sources of tasks for DevFlow to process.
    They can fetch tasks from external systems, databases, APIs, or other sources.

    Provides:
    - Task source registration
    - Custom task polling/fetching logic
    - Task format transformation
    """

    @abstractmethod
    def get_source_name(self) -> str:
        """
        Get the name of this task source.

        Returns:
            Task source name (e.g., "jira", "github-issues")
        """
        pass

    @abstractmethod
    def fetch_tasks(self) -> List[Dict[str, Any]]:
        """
        Fetch tasks from the source.

        Returns:
            List of task dictionaries. Each task should contain at least:
            - id: Unique task identifier
            - title: Task title/description
            - type: Task type
            - metadata: Additional task metadata
        """
        pass

    def get_polling_interval(self) -> int:
        """
        Get the polling interval in seconds.

        Returns:
            Number of seconds between task fetches
        """
        return 60  # Default: poll every minute

    def validate_task(self, task: Dict[str, Any]) -> bool:
        """
        Validate a task before processing.

        Args:
            task: Task dictionary to validate

        Returns:
            True if task is valid, False otherwise
        """
        required_fields = ['id', 'title', 'type']
        return all(field in task for field in required_fields)

    def transform_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a task from the source format to DevFlow format.

        Args:
            task: Task in source format

        Returns:
            Task in DevFlow format
        """
        # Default implementation returns task as-is
        return task

    def register_task_source(self, task_scheduler) -> None:
        """
        Register the task source with the task scheduler.

        Args:
            task_scheduler: The task scheduler to register with
        """
        source_name = self.get_source_name()

        # Register the task source
        if hasattr(task_scheduler, 'register_task_source'):
            task_scheduler.register_task_source(
                source_name,
                self.fetch_tasks,
                self.get_polling_interval()
            )
