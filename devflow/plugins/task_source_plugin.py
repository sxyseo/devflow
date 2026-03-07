"""
Task Source Plugin - Base class and utilities for task source plugins.

Provides specialized functionality for plugins that provide custom task sources.
Task source plugins can fetch tasks from external systems like Jira, GitHub Issues,
databases, APIs, or any other source.
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from threading import Thread, Lock
import time
import logging

from .base import TaskSourcePlugin as BaseTaskSourcePlugin, PluginMetadata


logger = logging.getLogger(__name__)


@dataclass
class TaskSourceConfig:
    """Configuration for a task source."""
    source_name: str
    enabled: bool = True
    polling_interval: int = 60
    priority: int = 5
    agent_type: str = "general"
    timeout: int = 3600
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskSourcePlugin(BaseTaskSourcePlugin):
    """
    Base class for task source plugins.

    Task source plugins provide custom sources of tasks for DevFlow to process.
    They can fetch tasks from external systems, databases, APIs, or other sources.

    To create a custom task source plugin:
    1. Inherit from this class
    2. Implement get_metadata() to describe your plugin
    3. Implement get_source_name() to specify the source identifier
    4. Implement fetch_tasks() to retrieve tasks from your source
    5. Optionally override get_polling_interval() to control polling frequency
    6. Optionally override validate_task() for custom task validation
    7. Optionally override transform_task() to convert tasks to DevFlow format

    Example:
        class MyTaskSourcePlugin(TaskSourcePlugin):
            def get_metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="my-task-source",
                    version="1.0.0",
                    description="My custom task source",
                    author="Your Name",
                    plugin_type="task_source"
                )

            def get_source_name(self) -> str:
                return "my-tasks"

            def fetch_tasks(self) -> List[Dict[str, Any]]:
                # Fetch tasks from your source
                return [
                    {
                        "id": "task-1",
                        "title": "Example task",
                        "type": "development",
                        "description": "Task description"
                    }
                ]

            def get_polling_interval(self) -> int:
                return 30  # Poll every 30 seconds
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the task source plugin.

        Args:
            config: Optional plugin configuration dictionary
        """
        super().__init__(config)
        self._task_scheduler = None
        self._polling_thread = None
        self._polling_lock = Lock()
        self._polling = False

    def get_task_source_config(self) -> TaskSourceConfig:
        """
        Get default configuration for the task source.

        Returns:
            TaskSourceConfig object with default configuration
        """
        return TaskSourceConfig(
            source_name=self.get_source_name(),
            polling_interval=self.get_polling_interval()
        )

    def register_task_source(self, task_scheduler) -> None:
        """
        Register the task source with the task scheduler.

        This method is called when the plugin is loaded. It registers the
        task source with the TaskScheduler and starts polling for tasks.

        Args:
            task_scheduler: The TaskScheduler instance to register with
        """
        self._task_scheduler = task_scheduler
        source_name = self.get_source_name()

        # Register the task source
        if hasattr(task_scheduler, 'register_task_source'):
            task_scheduler.register_task_source(
                source_name=source_name,
                fetch_callback=self._fetch_and_create_tasks,
                polling_interval=self.get_polling_interval()
            )

    def unregister_task_source(self) -> None:
        """
        Unregister the task source from the task scheduler.

        This method is called when the plugin is unloaded. It stops
        polling for tasks and cleans up resources.
        """
        self._stop_polling()

        if self._task_scheduler and hasattr(self._task_scheduler, 'unregister_task_source'):
            self._task_scheduler.unregister_task_source(self.get_source_name())
            self._task_scheduler = None

    def start_polling(self) -> None:
        """
        Start the polling thread for this task source.

        This method starts a background thread that periodically fetches
        tasks from the source and creates them in the scheduler.
        """
        with self._polling_lock:
            if self._polling:
                return

            self._polling = True
            self._polling_thread = Thread(
                target=self._polling_loop,
                daemon=True,
                name=f"task-source-{self.get_source_name()}"
            )
            self._polling_thread.start()

    def stop_polling(self) -> None:
        """
        Stop the polling thread for this task source.

        This method stops the background polling thread and waits for
        it to terminate.
        """
        self._stop_polling()

    def _stop_polling(self) -> None:
        """Internal method to stop polling."""
        with self._polling_lock:
            self._polling = False

        if self._polling_thread:
            self._polling_thread.join(timeout=5)
            self._polling_thread = None

    def _polling_loop(self) -> None:
        """Internal polling loop that runs in a separate thread."""
        interval = self.get_polling_interval()

        while self._polling:
            try:
                self._fetch_and_create_tasks()
            except Exception as e:
                logger.error(f"Error polling task source {self.get_source_name()}: {e}")

            # Wait for the next interval or until polling is stopped
            for _ in range(interval):
                if not self._polling:
                    break
                time.sleep(1)

    def _fetch_and_create_tasks(self) -> List[str]:
        """
        Fetch tasks from the source and create them in the scheduler.

        This method is called periodically by the polling loop. It fetches
        tasks from the source, validates them, transforms them, and creates
        them in the task scheduler.

        Returns:
            List of task IDs that were created
        """
        if not self._task_scheduler:
            logger.warning(f"Task source {self.get_source_name()} not registered with scheduler")
            return []

        try:
            # Fetch tasks from the source
            raw_tasks = self.fetch_tasks()

            # Process each task
            created_task_ids = []
            for raw_task in raw_tasks:
                try:
                    # Validate the task
                    if not self.validate_task(raw_task):
                        logger.warning(f"Invalid task from {self.get_source_name()}: {raw_task.get('id', 'unknown')}")
                        continue

                    # Transform the task to DevFlow format
                    task = self.transform_task(raw_task)

                    # Create the task in the scheduler
                    task_id = self._create_task_in_scheduler(task)
                    if task_id:
                        created_task_ids.append(task_id)

                except Exception as e:
                    logger.error(f"Error processing task from {self.get_source_name()}: {e}")

            return created_task_ids

        except Exception as e:
            logger.error(f"Error fetching tasks from {self.get_source_name()}: {e}")
            return []

    def _create_task_in_scheduler(self, task: Dict[str, Any]) -> Optional[str]:
        """
        Create a task in the task scheduler.

        Args:
            task: Task dictionary in DevFlow format

        Returns:
            Task ID if created successfully, None otherwise
        """
        if not self._task_scheduler:
            return None

        try:
            # Extract task parameters
            task_id = self._task_scheduler.create_task(
                task_type=task.get('type', 'general'),
                description=task.get('title', task.get('description', '')),
                agent_type=task.get('agent_type', 'general'),
                priority=task.get('priority', 5),
                dependencies=task.get('dependencies', []),
                input_data=task.get('input_data', {}),
                timeout=task.get('timeout', 3600),
                max_retries=task.get('max_retries', 3)
            )

            logger.info(f"Created task {task_id} from source {self.get_source_name()}")
            return task_id

        except Exception as e:
            logger.error(f"Error creating task from {self.get_source_name()}: {e}")
            return None

    def on_task_created(self, task_id: str, task: Dict[str, Any]) -> None:
        """
        Hook called when a task is created from this source.

        Override this method to perform custom actions when a task
        is created from this source.

        Args:
            task_id: ID of the created task
            task: Task dictionary
        """
        pass

    def on_task_started(self, task_id: str) -> None:
        """
        Hook called when a task from this source starts execution.

        Override this method to perform custom actions when a task
        from this source starts.

        Args:
            task_id: ID of the task
        """
        pass

    def on_task_completed(self, task_id: str, result: Any) -> None:
        """
        Hook called when a task from this source completes.

        Override this method to perform custom actions when a task
        from this source completes.

        Args:
            task_id: ID of the task
            result: Task result
        """
        pass

    def on_task_failed(self, task_id: str, error: Exception) -> None:
        """
        Hook called when a task from this source fails.

        Override this method to perform custom error handling when a
        task from this source fails.

        Args:
            task_id: ID of the task
            error: Exception that caused the failure
        """
        pass


class TaskSourceRegistry:
    """
    Registry for managing task source plugins.

    Provides a centralized registry for task source plugins and handles
    integration with the TaskScheduler.
    """

    def __init__(self):
        self._task_sources: Dict[str, TaskSourcePlugin] = {}
        self._task_source_configs: Dict[str, TaskSourceConfig] = {}
        self._lock = Lock()

    def register_task_source_plugin(self, plugin: TaskSourcePlugin) -> None:
        """
        Register a task source plugin.

        Args:
            plugin: TaskSourcePlugin instance to register
        """
        source_name = plugin.get_source_name()

        with self._lock:
            self._task_sources[source_name] = plugin
            self._task_source_configs[source_name] = plugin.get_task_source_config()

    def unregister_task_source_plugin(self, source_name: str) -> bool:
        """
        Unregister a task source plugin.

        Args:
            source_name: Task source name to unregister

        Returns:
            True if plugin was unregistered, False if not found
        """
        with self._lock:
            if source_name in self._task_sources:
                plugin = self._task_sources[source_name]
                plugin.unregister_task_source()
                del self._task_sources[source_name]
                if source_name in self._task_source_configs:
                    del self._task_source_configs[source_name]
                return True
            return False

    def get_task_source_plugin(self, source_name: str) -> Optional[TaskSourcePlugin]:
        """
        Get a task source plugin by name.

        Args:
            source_name: Task source name to get

        Returns:
            TaskSourcePlugin instance or None if not found
        """
        return self._task_sources.get(source_name)

    def get_task_source_config(self, source_name: str) -> Optional[TaskSourceConfig]:
        """
        Get task source configuration from a plugin.

        Args:
            source_name: Task source name to get configuration for

        Returns:
            TaskSourceConfig object or None if not found
        """
        return self._task_source_configs.get(source_name)

    def list_task_sources(self) -> List[str]:
        """
        List all registered task source names.

        Returns:
            List of task source names
        """
        with self._lock:
            return list(self._task_sources.keys())

    def get_all_task_source_configs(self) -> Dict[str, TaskSourceConfig]:
        """
        Get all task source configurations from plugins.

        Returns:
            Dictionary mapping task source names to their configurations
        """
        with self._lock:
            return self._task_source_configs.copy()

    def integrate_with_task_scheduler(self, task_scheduler) -> None:
        """
        Integrate all registered task source plugins with a TaskScheduler.

        Args:
            task_scheduler: TaskScheduler instance to integrate with
        """
        with self._lock:
            for plugin in self._task_sources.values():
                try:
                    plugin.register_task_source(task_scheduler)
                    plugin.start_polling()
                except Exception as e:
                    logger.error(f"Failed to register task source plugin {plugin.get_source_name()}: {e}")

    def stop_all_polling(self) -> None:
        """Stop polling for all task source plugins."""
        with self._lock:
            for plugin in self._task_sources.values():
                try:
                    plugin.stop_polling()
                except Exception as e:
                    logger.error(f"Failed to stop polling for task source {plugin.get_source_name()}: {e}")


# Global task source plugin registry instance
task_source_registry = TaskSourceRegistry()
