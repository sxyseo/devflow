# Plugin Development Guide

Learn how to develop plugins for DevFlow's plugin system.

## Table of Contents

- [Getting Started](#getting-started)
- [Plugin Structure](#plugin-structure)
- [Plugin Types](#plugin-types)
  - [Agent Plugins](#agent-plugins)
  - [Task Source Plugins](#task-source-plugins)
  - [Integration Plugins](#integration-plugins)
- [Best Practices](#best-practices)
- [Testing Plugins](#testing-plugins)
- [Debugging Plugins](#debugging-plugins)
- [Publishing Plugins](#publishing-plugins)

---

## Getting Started

### Prerequisites

- Python 3.8 or higher
- DevFlow installed
- Basic understanding of Python classes and inheritance

### Creating Your First Plugin

1. **Create a plugin directory:**

```bash
mkdir my-first-plugin
cd my-first-plugin
```

2. **Create the plugin entry point:**

```python
# plugin.py
from devflow.plugins.base import Plugin, PluginMetadata

class MyFirstPlugin(Plugin):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-first-plugin",
            version="1.0.0",
            description="My first DevFlow plugin",
            author="Your Name",
            plugin_type="custom"
        )

    def initialize(self) -> None:
        super().initialize()
        print("MyFirstPlugin initialized!")

    def start(self) -> None:
        super().start()
        print("MyFirstPlugin started!")

    def stop(self) -> None:
        print("MyFirstPlugin stopped!")
        super().stop()
```

3. **Test the plugin:**

```python
from devflow.plugins.plugin_manager import PluginManager

manager = PluginManager()
result = manager.load_plugin_from_path("./my-first-plugin")

if result.success:
    manager.start_plugin(result.plugin_name)
    # Do work...
    manager.stop_plugin(result.plugin_name)
```

---

## Plugin Structure

### Basic Structure

A minimal plugin has the following structure:

```
my-plugin/
├── plugin.py           # Required: Plugin entry point
├── metadata.json       # Optional: Plugin metadata
├── README.md           # Recommended: Plugin documentation
├── requirements.txt    # Optional: Plugin dependencies
└── tests/              # Recommended: Plugin tests
    └── test_plugin.py
```

### Plugin Entry Point

The `plugin.py` file is the main entry point for your plugin. It must:

1. Import the appropriate base class
2. Define a plugin class that inherits from the base class
3. Implement all required abstract methods
4. Export the plugin class

```python
from devflow.plugins.base import Plugin, PluginMetadata
from typing import Dict, Any

class MyPlugin(Plugin):
    """My custom plugin."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-plugin",
            version="1.0.0",
            description="My plugin description",
            author="Your Name",
            plugin_type="custom"
        )

    def initialize(self) -> None:
        super().initialize()
        # Initialization logic

    def start(self) -> None:
        super().start()
        # Startup logic

    def stop(self) -> None:
        # Cleanup logic
        super().stop()
```

### Plugin Metadata

You can provide plugin metadata in two ways:

**Option 1: In code (required)**

```python
def get_metadata(self) -> PluginMetadata:
    return PluginMetadata(
        name="my-plugin",
        version="1.0.0",
        description="My plugin description",
        author="Your Name",
        plugin_type="custom",
        dependencies=[],
        devflow_version="0.1.0"
    )
```

**Option 2: In metadata.json (optional)**

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "My plugin description",
  "author": "Your Name",
  "plugin_type": "custom",
  "dependencies": [],
  "devflow_version": "0.1.0"
}
```

### Plugin Configuration

Plugins can receive configuration through the constructor:

```python
class MyPlugin(Plugin):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.api_key = self.config.get('api_key', '')
        self.timeout = self.config.get('timeout', 30)
```

Configuration can be provided when loading the plugin:

```python
config = {
    'api_key': 'your-key',
    'timeout': 60
}

plugin = MyPlugin(config)
```

---

## Plugin Types

### Agent Plugins

Agent plugins extend DevFlow's agent capabilities by providing custom agent implementations.

#### When to Use

- You need a specialized agent type
- You want to customize agent behavior
- You need custom agent lifecycle management

#### Implementation

```python
from devflow.plugins.agent_plugin import AgentPlugin
from devflow.plugins.base import PluginMetadata
from typing import Dict, Any

class MyAgentPlugin(AgentPlugin):
    """Custom agent plugin."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-agent",
            version="1.0.0",
            description="My custom agent",
            author="Your Name",
            plugin_type="agent"
        )

    def get_agent_type(self) -> str:
        """Return the agent type identifier."""
        return "my-custom-agent"

    def get_agent_class(self):
        """Return the agent class."""
        return MyCustomAgent

    def get_agent_config(self) -> Dict[str, Any]:
        """Return default agent configuration."""
        return {
            "model": "claude-3-5-sonnet-20241022",
            "skills": ["custom-skill"],
            "system_prompt": "You are a custom agent."
        }

    def on_agent_created(self, agent_id: str, agent_type: str) -> None:
        """Called when an agent is created."""
        print(f"Agent {agent_id} created")

    def on_agent_started(self, agent_id: str, task: str) -> None:
        """Called when an agent starts a task."""
        print(f"Agent {agent_id} started: {task}")

    def on_agent_completed(self, agent_id: str, result: Any) -> None:
        """Called when an agent completes a task."""
        print(f"Agent {agent_id} completed")

    def on_agent_failed(self, agent_id: str, error: Exception) -> None:
        """Called when an agent fails."""
        print(f"Agent {agent_id} failed: {error}")
```

#### Best Practices

1. **Agent Configuration**: Provide sensible defaults
2. **Lifecycle Hooks**: Use lifecycle hooks for initialization and cleanup
3. **Error Handling**: Implement proper error handling in lifecycle hooks
4. **Logging**: Use Python's logging module for debugging
5. **Resource Management**: Clean up resources in `on_agent_failed` and `stop()`

---

### Task Source Plugins

Task source plugins provide custom sources of tasks for DevFlow to process.

#### When to Use

- You need to fetch tasks from external systems
- You want to integrate with task management tools
- You need custom task polling/fetching logic

#### Implementation

```python
from devflow.plugins.task_source_plugin import TaskSourcePlugin
from devflow.plugins.base import PluginMetadata
from typing import Dict, Any, List

class MyTaskSource(TaskSourcePlugin):
    """Custom task source plugin."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-task-source",
            version="1.0.0",
            description="My custom task source",
            author="Your Name",
            plugin_type="task_source"
        )

    def get_source_name(self) -> str:
        """Return the task source identifier."""
        return "my-tasks"

    def fetch_tasks(self) -> List[Dict[str, Any]]:
        """Fetch tasks from the source."""
        # Implement your task fetching logic
        return [
            {
                "id": "task-1",
                "title": "Example task",
                "type": "development",
                "description": "Task description"
            }
        ]

    def get_polling_interval(self) -> int:
        """Return the polling interval in seconds."""
        return 60  # Poll every minute

    def validate_task(self, task: Dict[str, Any]) -> bool:
        """Validate a task before processing."""
        required_fields = ['id', 'title', 'type']
        return all(field in task for field in required_fields)

    def transform_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Transform task from source format to DevFlow format."""
        return {
            'id': task['id'],
            'title': task['title'],
            'description': task.get('description', ''),
            'type': task['type'],
            'priority': task.get('priority', 5),
            'agent_type': task.get('agent_type', 'general')
        }

    def on_task_created(self, task_id: str, task: Dict[str, Any]) -> None:
        """Called when a task is created from this source."""
        print(f"Task {task_id} created")

    def on_task_started(self, task_id: str) -> None:
        """Called when a task from this source starts."""
        print(f"Task {task_id} started")

    def on_task_completed(self, task_id: str, result: Any) -> None:
        """Called when a task from this source completes."""
        print(f"Task {task_id} completed")

    def on_task_failed(self, task_id: str, error: Exception) -> None:
        """Called when a task from this source fails."""
        print(f"Task {task_id} failed: {error}")
```

#### Best Practices

1. **Polling Interval**: Choose appropriate polling intervals to avoid overwhelming external systems
2. **Task Validation**: Always validate tasks before processing
3. **Error Handling**: Implement robust error handling for external API failures
4. **Deduplication**: Track processed tasks to avoid duplicates
5. **Rate Limiting**: Respect rate limits of external APIs
6. **Logging**: Log task fetching activities for debugging

---

### Integration Plugins

Integration plugins enable DevFlow to connect with external tools, services, and platforms.

#### When to Use

- You need to integrate with external services
- You want to handle webhooks from external systems
- You need to send notifications to external services

#### Implementation

```python
from devflow.plugins.integration_plugin import IntegrationPlugin
from devflow.plugins.base import PluginMetadata
from typing import Dict, Any

class MyIntegration(IntegrationPlugin):
    """Custom integration plugin."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-integration",
            version="1.0.0",
            description="My custom integration",
            author="Your Name",
            plugin_type="integration"
        )

    def get_integration_name(self) -> str:
        """Return the integration name."""
        return "my-service"

    def get_integration_type(self) -> str:
        """Return the integration type."""
        return "cicd"  # or "vcs", "notification", etc.

    def get_required_config_fields(self) -> List[str]:
        """Return required configuration fields."""
        return ['api_url', 'api_key']

    def connect(self) -> bool:
        """Establish connection to the service."""
        if not self.validate_config():
            return False

        # Test connection
        try:
            response = self._test_api_connection()
            return response.status_code == 200
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from the service."""
        super().disconnect()
        # Cleanup resources

    def test_connection(self) -> bool:
        """Test the connection."""
        try:
            # Implement health check
            return True
        except Exception:
            return False

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Handle incoming webhook."""
        try:
            # Process webhook
            event_type = payload.get('event_type')

            if event_type == 'build_completed':
                self._handle_build_completed(payload)

            return {
                'success': True,
                'message': 'Webhook processed'
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }

    def get_supported_webhook_events(self) -> List[str]:
        """Return supported webhook events."""
        return ['build_completed', 'build_failed']

    def send_notification(self, message: str, level: str = "info") -> bool:
        """Send a notification through the integration."""
        try:
            # Implement notification sending
            return True
        except Exception as e:
            print(f"Failed to send notification: {e}")
            return False

    def get_health_check(self) -> Dict[str, Any]:
        """Return health check information."""
        return {
            'status': 'healthy' if self.is_connected() else 'unhealthy',
            'message': 'Integration is working' if self.is_connected() else 'Integration disconnected',
            'details': {
                'integration_name': self.get_integration_name(),
                'integration_type': self.get_integration_type()
            }
        }
```

#### Best Practices

1. **Connection Management**: Implement proper connection pooling and reuse
2. **Authentication**: Store credentials securely (use environment variables)
3. **Webhook Security**: Validate webhook signatures
4. **Error Handling**: Implement retry logic for transient failures
5. **Rate Limiting**: Respect API rate limits
6. **Health Checks**: Implement proper health check endpoints
7. **Timeout Handling**: Set appropriate timeouts for API calls

---

## Best Practices

### Code Organization

1. **Separate Concerns**: Keep business logic separate from plugin framework code
2. **Use Type Hints**: Add type hints for better IDE support and documentation
3. **Document Your Code**: Use docstrings for all public methods
4. **Follow PEP 8**: Adhere to Python style guidelines

### Error Handling

```python
def fetch_tasks(self) -> List[Dict[str, Any]]:
    try:
        # Fetch tasks
        tasks = self._api_call()
        return tasks
    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return []
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

class MyPlugin(Plugin):
    def initialize(self) -> None:
        logger.info("Initializing plugin")
        # ...

    def start(self) -> None:
        logger.debug("Starting plugin")
        # ...
        logger.info("Plugin started successfully")
```

### Configuration Management

```python
class MyPlugin(Plugin):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.api_key = self._get_required_config('api_key')
        self.timeout = self.config.get('timeout', 30)
        self.retry_count = self.config.get('retry_count', 3)

    def _get_required_config(self, key: str) -> Any:
        if key not in self.config:
            raise ValueError(f"Required configuration '{key}' is missing")
        return self.config[key]
```

### Resource Management

```python
class MyPlugin(Plugin):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._connection = None
        self._thread = None

    def start(self) -> None:
        super().start()
        self._connection = self._create_connection()
        self._thread = self._start_background_thread()

    def stop(self) -> None:
        if self._thread:
            self._stop_background_thread(self._thread)
        if self._connection:
            self._close_connection(self._connection)
        super().stop()
```

### Thread Safety

```python
import threading

class MyPlugin(Plugin):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._lock = threading.Lock()
        self._data = {}

    def update_data(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def get_data(self, key: str) -> Any:
        with self._lock:
            return self._data.get(key)
```

---

## Testing Plugins

### Unit Tests

Create tests for your plugin logic:

```python
import unittest
from devflow.plugins.base import PluginMetadata
from my_plugin import MyPlugin

class TestMyPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = MyPlugin()

    def test_metadata(self):
        metadata = self.plugin.get_metadata()
        self.assertIsInstance(metadata, PluginMetadata)
        self.assertEqual(metadata.name, "my-plugin")
        self.assertEqual(metadata.version, "1.0.0")

    def test_initialization(self):
        self.plugin.initialize()
        self.assertTrue(self.plugin.is_initialized())

    def test_lifecycle(self):
        self.plugin.initialize()
        self.plugin.start()
        self.assertTrue(self.plugin.is_running())
        self.plugin.stop()
        self.assertFalse(self.plugin.is_running())
```

### Integration Tests

Test plugin loading and lifecycle:

```python
import unittest
from devflow.plugins.plugin_manager import PluginManager

class TestPluginLoading(unittest.TestCase):
    def test_load_plugin(self):
        manager = PluginManager()
        result = manager.load_plugin_from_path("./my-plugin")
        self.assertTrue(result.success)

    def test_plugin_lifecycle(self):
        manager = PluginManager()
        result = manager.load_plugin_from_path("./my-plugin")

        if result.success:
            self.assertTrue(manager.initialize_plugin(result.plugin_name))
            self.assertTrue(manager.start_plugin(result.plugin_name))
            self.assertTrue(manager.stop_plugin(result.plugin_name))
```

### Test Discovery

Organize tests in a standard structure:

```
my-plugin/
├── plugin.py
├── tests/
│   ├── __init__.py
│   ├── test_plugin.py
│   └── test_integration.py
└── requirements.txt
```

Run tests:

```bash
python -m pytest tests/
```

---

## Debugging Plugins

### Enable Debug Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Use Python Debugger

```python
def start(self) -> None:
    import pdb; pdb.set_trace()
    # Your code here
```

### Check Plugin State

```python
from devflow.plugins.plugin_manager import PluginManager

manager = PluginManager()
result = manager.load_plugin_from_path("./my-plugin")

if result.success:
    # Get plugin info
    info = manager.get_plugin_info(result.plugin_name)
    print(f"Plugin info: {info}")

    # Check state
    state = manager.get_plugin_state(result.plugin_name)
    print(f"Plugin state: initialized={state.initialized}, running={state.running}")
```

### View Plugin Errors

Check the plugin error log:

```bash
# Error log location
~/.devflow/plugins/error.log

# View recent errors
tail -f ~/.devflow/plugins/error.log
```

---

## Publishing Plugins

### Plugin Package Structure

```
my-plugin/
├── plugin.py
├── metadata.json
├── README.md
├── LICENSE
├── requirements.txt
├── setup.py
└── tests/
```

### README.md

Create comprehensive documentation:

```markdown
# My Plugin

## Description
Brief description of what your plugin does.

## Installation
```bash
# Copy plugin to plugins directory
cp -r my-plugin ~/.devflow/plugins/
```

## Configuration
```json
{
  "api_key": "your-key",
  "timeout": 30
}
```

## Usage
```python
from devflow.plugins.plugin_manager import PluginManager

manager = PluginManager()
manager.load_plugin("my-plugin")
manager.start_plugin("my-plugin")
```

## Examples
Provide usage examples...
```

### Versioning

Use semantic versioning:

- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

Example: `1.2.3`

- MAJOR = 1
- MINOR = 2
- PATCH = 3

### License

Choose an appropriate license (MIT, Apache 2.0, etc.) and include it in your plugin.

### Distribution

You can distribute plugins in several ways:

1. **Direct Copy**: Copy plugin directory to DevFlow plugins directory
2. **Git Repository**: Clone from a Git repository
3. **PyPI Package**: Publish as a Python package (for complex plugins)

Example setup.py:

```python
from setuptools import setup, find_packages

setup(
    name="devflow-my-plugin",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'devflow>=0.1.0',
    ],
    python_requires='>=3.8',
)
```
