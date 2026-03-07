"""
Custom Task Source Plugin Implementation.

This module demonstrates how to create a custom task source plugin for DevFlow.
The plugin provides a file-based task source that reads tasks from JSON files.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from devflow.plugins.task_source_plugin import TaskSourcePlugin
from devflow.plugins.base import PluginMetadata


logger = logging.getLogger(__name__)


class CustomTaskSourcePlugin(TaskSourcePlugin):
    """
    Example custom task source plugin.

    This plugin demonstrates how to create a custom task source that fetches
    tasks from JSON files in a specified directory. It showcases the complete
    task source plugin lifecycle including:

    - Task fetching from external sources
    - Task validation and transformation
    - Polling and automatic task discovery
    - Lifecycle hooks for task events
    - Error handling and recovery

    Features demonstrated:
    - File-based task source
    - JSON task format
    - Configurable polling interval
    - Task deduplication
    - Error handling and logging
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the custom task source plugin.

        Args:
            config: Plugin configuration with optional keys:
                - task_dir: Directory containing task JSON files (default: "./tasks")
                - polling_interval: Seconds between task checks (default: 60)
                - file_pattern: Glob pattern for task files (default: "*.json")
                - auto_process: Automatically process tasks (default: True)
        """
        super().__init__(config)
        self.task_dir = Path(self.config.get('task_dir', './tasks'))
        self.file_pattern = self.config.get('file_pattern', '*.json')
        self.auto_process = self.config.get('auto_process', True)
        self._processed_tasks = set()
        self._last_check = None

    def get_metadata(self) -> PluginMetadata:
        """
        Get plugin metadata.

        Returns:
            PluginMetadata describing this plugin
        """
        return PluginMetadata(
            name="custom-task-source",
            version="1.0.0",
            description="Example custom task source plugin demonstrating file-based task fetching",
            author="DevFlow Team",
            plugin_type="task_source",
            dependencies=[],
            devflow_version="0.1.0"
        )

    def get_source_name(self) -> str:
        """
        Get the task source identifier.

        Returns:
            Task source name string
        """
        return "file-tasks"

    def get_polling_interval(self) -> int:
        """
        Get the polling interval in seconds.

        Returns:
            Polling interval in seconds
        """
        return self.config.get('polling_interval', 60)

    def fetch_tasks(self) -> List[Dict[str, Any]]:
        """
        Fetch tasks from the source.

        This method reads JSON files from the configured task directory
        and returns a list of tasks. It handles file not found errors
        and JSON parsing errors gracefully.

        Returns:
            List of task dictionaries

        Example task file format:
        {
            "id": "task-001",
            "title": "Implement feature X",
            "description": "Detailed description",
            "type": "development",
            "priority": 1,
            "agent_type": "general",
            "tags": ["feature", "frontend"],
            "dependencies": [],
            "timeout": 3600,
            "max_retries": 3
        }
        """
        tasks = []

        try:
            # Ensure task directory exists
            if not self.task_dir.exists():
                logger.warning(f"Task directory does not exist: {self.task_dir}")
                return tasks

            # Find all task files
            task_files = list(self.task_dir.glob(self.file_pattern))

            if not task_files:
                logger.debug(f"No task files found in {self.task_dir}")
                return tasks

            # Read each task file
            for task_file in task_files:
                try:
                    with open(task_file, 'r', encoding='utf-8') as f:
                        task_data = json.load(f)

                    # Add file metadata
                    task_data['_source_file'] = str(task_file)
                    task_data['_source_modified'] = datetime.fromtimestamp(
                        task_file.stat().st_mtime
                    ).isoformat()

                    tasks.append(task_data)
                    logger.debug(f"Loaded task from {task_file.name}")

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in {task_file}: {e}")
                except Exception as e:
                    logger.error(f"Error reading {task_file}: {e}")

            logger.info(f"Fetched {len(tasks)} tasks from {self.task_dir}")
            self._last_check = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"Error fetching tasks: {e}")

        return tasks

    def validate_task(self, task: Dict[str, Any]) -> bool:
        """
        Validate a task before processing.

        Checks that the task has required fields and valid values.
        Implements deduplication by tracking processed task IDs.

        Args:
            task: Task dictionary to validate

        Returns:
            True if task is valid, False otherwise
        """
        # Check required fields
        required_fields = ['id', 'title', 'type']
        for field in required_fields:
            if field not in task:
                logger.warning(f"Task missing required field '{field}': {task.get('id', 'unknown')}")
                return False

        # Check for duplicate tasks
        task_id = task['id']
        if task_id in self._processed_tasks:
            logger.debug(f"Task already processed: {task_id}")
            return False

        # Validate task type
        valid_types = ['development', 'testing', 'deployment', 'maintenance', 'general']
        if task.get('type') not in valid_types:
            logger.warning(f"Invalid task type '{task.get('type')}': {task_id}")
            return False

        # Validate priority
        priority = task.get('priority', 5)
        if not isinstance(priority, int) or priority < 1 or priority > 10:
            logger.warning(f"Invalid priority {priority}: {task_id}")
            return False

        return True

    def transform_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a task from source format to DevFlow format.

        This method converts the task from the file-based format to
        the format expected by DevFlow's task scheduler.

        Args:
            task: Task dictionary in source format

        Returns:
            Task dictionary in DevFlow format
        """
        # Mark task as processed
        self._processed_tasks.add(task['id'])

        # Transform to DevFlow format
        transformed = {
            'id': task['id'],
            'title': task.get('title', task.get('description', '')),
            'description': task.get('description', ''),
            'type': task.get('type', 'general'),
            'priority': task.get('priority', 5),
            'agent_type': task.get('agent_type', 'general'),
            'dependencies': task.get('dependencies', []),
            'timeout': task.get('timeout', 3600),
            'max_retries': task.get('max_retries', 3),
            'input_data': {
                'source': self.get_source_name(),
                'source_file': task.get('_source_file'),
                'tags': task.get('tags', []),
                'metadata': {
                    'created_at': task.get('_source_modified'),
                    'custom_fields': {
                        k: v for k, v in task.items()
                        if k not in ['id', 'title', 'description', 'type',
                                   'priority', 'agent_type', 'dependencies',
                                   'timeout', 'max_retries', 'tags']
                    }
                }
            }
        }

        logger.debug(f"Transformed task {task['id']} to DevFlow format")
        return transformed

    def on_task_created(self, task_id: str, task: Dict[str, Any]) -> None:
        """
        Hook called when a task is created from this source.

        Args:
            task_id: ID of the created task
            task: Task dictionary
        """
        logger.info(f"Task {task_id} created from file source")
        # Could update source file status, send notifications, etc.

    def on_task_started(self, task_id: str) -> None:
        """
        Hook called when a task from this source starts execution.

        Args:
            task_id: ID of the task
        """
        logger.info(f"Task {task_id} from file source started")
        # Could update task status in source file, etc.

    def on_task_completed(self, task_id: str, result: Any) -> None:
        """
        Hook called when a task from this source completes.

        Args:
            task_id: ID of the task
            result: Task result
        """
        logger.info(f"Task {task_id} from file source completed successfully")
        # Could archive source file, update status, etc.

    def on_task_failed(self, task_id: str, error: Exception) -> None:
        """
        Hook called when a task from this source fails.

        Args:
            task_id: ID of the task
            error: Exception that caused the failure
        """
        logger.error(f"Task {task_id} from file source failed: {str(error)}")
        # Could create error report, retry task, etc.

    def initialize(self) -> None:
        """
        Initialize the plugin.

        Called when the plugin is first loaded.
        """
        super().initialize()

        # Create task directory if it doesn't exist
        if not self.task_dir.exists():
            try:
                self.task_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created task directory: {self.task_dir}")

                # Create example task file
                example_task = {
                    "id": "example-task-001",
                    "title": "Example Task from File Source",
                    "description": "This is an example task loaded from a JSON file",
                    "type": "development",
                    "priority": 5,
                    "agent_type": "general",
                    "tags": ["example", "file-source"],
                    "dependencies": [],
                    "timeout": 3600,
                    "max_retries": 3
                }

                example_file = self.task_dir / "example_task.json"
                with open(example_file, 'w', encoding='utf-8') as f:
                    json.dump(example_task, f, indent=2)

                logger.info(f"Created example task file: {example_file}")

            except Exception as e:
                logger.error(f"Failed to create task directory: {e}")

        logger.info(f"CustomTaskSourcePlugin initialized at {datetime.now().isoformat()}")

    def start(self) -> None:
        """
        Start the plugin.

        Called when the plugin should start running.
        """
        super().start()
        logger.info(f"CustomTaskSourcePlugin started - monitoring {self.task_dir}")

    def stop(self) -> None:
        """
        Stop the plugin.

        Called when the plugin should stop running.
        """
        super().stop()
        logger.info("CustomTaskSourcePlugin stopped")

    def get_source_status(self) -> Dict[str, Any]:
        """
        Get the current status of the task source.

        Returns:
            Dictionary with source status information
        """
        return {
            'source_name': self.get_source_name(),
            'task_directory': str(self.task_dir),
            'file_pattern': self.file_pattern,
            'polling_interval': self.get_polling_interval(),
            'last_check': self._last_check,
            'processed_tasks': len(self._processed_tasks),
            'directory_exists': self.task_dir.exists(),
            'task_files': len(list(self.task_dir.glob(self.file_pattern))) if self.task_dir.exists() else 0
        }
