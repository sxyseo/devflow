# Plugin API Reference

Complete API reference for DevFlow's plugin system.

## Table of Contents

- [Base Classes](#base-classes)
  - [Plugin](#plugin)
  - [AgentPlugin](#agentplugin)
  - [TaskSourcePlugin](#tasksourceplugin)
  - [IntegrationPlugin](#integrationplugin)
- [Plugin Manager](#plugin-manager)
- [Plugin Registry](#plugin-registry)
- [Plugin Loader](#plugin-loader)
- [Plugin Configuration](#plugin-configuration)
- [Data Classes](#data-classes)

---

## Base Classes

### Plugin

The base class for all plugins. All plugin types must inherit from this class.

```python
from devflow.plugins.base import Plugin, PluginMetadata

class MyPlugin(Plugin):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-plugin",
            version="1.0.0",
            description="My plugin description",
            author="Your Name",
            plugin_type="custom"
        )
```

#### Methods

##### `get_metadata() -> PluginMetadata`

Get the plugin's metadata. This method must be implemented by all plugins.

**Returns:** `PluginMetadata` object containing:
- `name` (str): Plugin name
- `version` (str): Plugin version (semantic versioning)
- `description` (str): Plugin description
- `author` (str): Plugin author
- `plugin_type` (str): Plugin type identifier
- `dependencies` (List[str], optional): List of plugin dependencies
- `devflow_version` (str, optional): Minimum DevFlow version required

##### `initialize() -> None`

Called when the plugin is first loaded. Override this method to perform initialization logic.

**Example:**
```python
def initialize(self) -> None:
    super().initialize()
    # Custom initialization logic
    self._setup_resources()
```

##### `start() -> None`

Called when the plugin should start running. Override this method to implement the plugin's main functionality.

**Example:**
```python
def start(self) -> None:
    super().start()
    # Custom startup logic
    self._start_background_thread()
```

##### `stop() -> None`

Called when the plugin should stop running. Override this method to implement cleanup logic.

**Example:**
```python
def stop(self) -> None:
    # Custom cleanup logic
    self._cleanup_resources()
    super().stop()
```

##### `get_dependencies() -> List[str]`

Get the plugin's dependencies.

**Returns:** List of plugin names this plugin depends on

##### `validate_dependencies(available_plugins: List[str]) -> bool`

Validate that all dependencies are available.

**Parameters:**
- `available_plugins`: List of available plugin names

**Returns:** `True` if all dependencies are available, `False` otherwise

---

### AgentPlugin

Base class for agent plugins. Extends `Plugin` to provide agent-specific functionality.

```python
from devflow.plugins.agent_plugin import AgentPlugin
from devflow.plugins.base import PluginMetadata

class MyAgentPlugin(AgentPlugin):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-agent",
            version="1.0.0",
            description="My custom agent",
            author="Your Name",
            plugin_type="agent"
        )

    def get_agent_type(self) -> str:
        return "my-custom-agent"

    def get_agent_class(self):
        return MyAgentClass
```

#### Methods

##### `get_agent_type() -> str`

Get the agent type identifier.

**Returns:** Agent type string (e.g., "custom-code-reviewer")

##### `get_agent_class()`

Get the agent class this plugin provides.

**Returns:** Agent class that implements the agent interface

##### `get_agent_config() -> Dict[str, Any]`

Get default configuration for the agent.

**Returns:** Dictionary with default configuration:
- `model` (str): Model name
- `max_tasks` (int): Maximum concurrent tasks
- `timeout` (int): Task timeout in seconds
- `skills` (List[str]): List of agent skills
- `system_prompt` (str): System prompt for the agent

##### `register_agent(agent_manager) -> None`

Register the agent with the agent manager.

**Parameters:**
- `agent_manager`: The AgentManager instance

##### `on_agent_created(agent_id: str, agent_type: str) -> None`

Hook called when a new agent is created.

**Parameters:**
- `agent_id`: ID of the created agent
- `agent_type`: Type of the created agent

##### `on_agent_started(agent_id: str, task: str) -> None`

Hook called when an agent starts a task.

**Parameters:**
- `agent_id`: ID of the agent
- `task`: Task description

##### `on_agent_completed(agent_id: str, result: Any) -> None`

Hook called when an agent completes a task.

**Parameters:**
- `agent_id`: ID of the agent
- `result`: Task result

##### `on_agent_failed(agent_id: str, error: Exception) -> None`

Hook called when an agent fails.

**Parameters:**
- `agent_id`: ID of the agent
- `error`: Exception that caused the failure

---

### TaskSourcePlugin

Base class for task source plugins. Extends `Plugin` to provide task fetching capabilities.

```python
from devflow.plugins.task_source_plugin import TaskSourcePlugin
from devflow.plugins.base import PluginMetadata

class MyTaskSource(TaskSourcePlugin):
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
        return [{"id": "task-1", "title": "Example", "type": "development"}]
```

#### Methods

##### `get_source_name() -> str`

Get the name of this task source.

**Returns:** Task source name (e.g., "jira", "github-issues")

##### `fetch_tasks() -> List[Dict[str, Any]]`

Fetch tasks from the source.

**Returns:** List of task dictionaries. Each task should contain:
- `id` (str): Unique task identifier
- `title` (str): Task title/description
- `type` (str): Task type
- Additional metadata as needed

##### `get_polling_interval() -> int`

Get the polling interval in seconds.

**Returns:** Number of seconds between task fetches (default: 60)

##### `validate_task(task: Dict[str, Any]) -> bool`

Validate a task before processing.

**Parameters:**
- `task`: Task dictionary to validate

**Returns:** `True` if task is valid, `False` otherwise

##### `transform_task(task: Dict[str, Any]) -> Dict[str, Any]`

Transform a task from source format to DevFlow format.

**Parameters:**
- `task`: Task in source format

**Returns:** Task in DevFlow format

##### `register_task_source(task_scheduler) -> None`

Register the task source with the task scheduler.

**Parameters:**
- `task_scheduler`: The TaskScheduler instance

##### `start_polling() -> None`

Start the polling thread for this task source.

##### `stop_polling() -> None`

Stop the polling thread for this task source.

##### `on_task_created(task_id: str, task: Dict[str, Any]) -> None`

Hook called when a task is created from this source.

**Parameters:**
- `task_id`: ID of the created task
- `task`: Task dictionary

##### `on_task_started(task_id: str) -> None`

Hook called when a task from this source starts execution.

**Parameters:**
- `task_id`: ID of the task

##### `on_task_completed(task_id: str, result: Any) -> None`

Hook called when a task from this source completes.

**Parameters:**
- `task_id`: ID of the task
- `result`: Task result

##### `on_task_failed(task_id: str, error: Exception) -> None`

Hook called when a task from this source fails.

**Parameters:**
- `task_id`: ID of the task
- `error`: Exception that caused the failure

---

### IntegrationPlugin

Base class for integration plugins. Extends `Plugin` to provide external service integration.

```python
from devflow.plugins.integration_plugin import IntegrationPlugin
from devflow.plugins.base import PluginMetadata

class MyIntegration(IntegrationPlugin):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-integration",
            version="1.0.0",
            description="My custom integration",
            author="Your Name",
            plugin_type="integration"
        )

    def get_integration_name(self) -> str:
        return "my-service"

    def get_integration_type(self) -> str:
        return "cicd"

    def connect(self) -> bool:
        # Establish connection
        return True
```

#### Methods

##### `get_integration_name() -> str`

Get the name of this integration.

**Returns:** Integration name (e.g., "github", "jenkins", "slack")

##### `get_integration_type() -> str`

Get the type of this integration.

**Returns:** Integration type (e.g., "vcs", "cicd", "notification", "project-management")

##### `validate_config() -> bool`

Validate the integration configuration.

**Returns:** `True` if configuration is valid, `False` otherwise

##### `get_required_config_fields() -> List[str]`

Get the list of required configuration fields.

**Returns:** List of required configuration field names

##### `get_optional_config_fields() -> List[str]`

Get the list of optional configuration fields.

**Returns:** List of optional configuration field names

##### `connect() -> bool`

Establish connection to the integration service.

**Returns:** `True` if connection successful, `False` otherwise

##### `disconnect() -> None`

Disconnect from the integration service.

##### `test_connection() -> bool`

Test the connection to the integration service.

**Returns:** `True` if connection is working, `False` otherwise

##### `get_status() -> IntegrationStatus`

Get the current connection status.

**Returns:** Current `IntegrationStatus` (DISCONNECTED, CONNECTING, CONNECTED, ERROR)

##### `is_connected() -> bool`

Check if the integration is connected.

**Returns:** `True` if connected, `False` otherwise

##### `get_connection()`

Get the connection object for the integration.

**Returns:** Connection object or `None` if not connected

##### `handle_webhook(payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]`

Handle an incoming webhook from the integration service.

**Parameters:**
- `payload`: Webhook payload data
- `headers`: HTTP headers from the webhook request

**Returns:** Response dictionary with:
- `success` (bool): Boolean indicating if handling was successful
- `message` (str, optional): Message describing the result

##### `get_supported_webhook_events() -> List[str]`

Get the list of supported webhook event types.

**Returns:** List of webhook event types this integration can handle

##### `send_notification(message: str, level: str = "info") -> bool`

Send a notification through the integration.

**Parameters:**
- `message`: The notification message
- `level`: Notification level (info, warning, error, success)

**Returns:** `True` if notification sent successfully, `False` otherwise

##### `get_api_client()`

Get or create an API client for the integration.

**Returns:** API client instance or `None`

##### `get_health_check() -> Dict[str, Any]`

Get health check information for the integration.

**Returns:** Dictionary with:
- `status` (str): Health status (healthy, degraded, unhealthy)
- `message` (str): Status message
- `details` (Dict, optional): Additional diagnostic information

##### `register_integration(integration_manager) -> None`

Register the integration with the integration manager.

**Parameters:**
- `integration_manager`: The integration manager to register with

---

## Plugin Manager

The `PluginManager` class provides the main API for plugin lifecycle management.

```python
from devflow.plugins.plugin_manager import PluginManager
from devflow.plugins.plugin_config import PluginConfig

config = PluginConfig()
manager = PluginManager(config)
```

### Methods

#### Loading Plugins

##### `load_all_plugins() -> List[PluginLoadResult]`

Discover and load all available plugins.

**Returns:** List of `PluginLoadResult` objects

##### `load_plugin(plugin_name: str) -> PluginLoadResult`

Load a specific plugin by name.

**Parameters:**
- `plugin_name`: Name of the plugin to load

**Returns:** `PluginLoadResult` with plugin instance or error

##### `load_plugin_from_path(plugin_path: str) -> PluginLoadResult`

Load a plugin from a specific path.

**Parameters:**
- `plugin_path`: Path to the plugin directory

**Returns:** `PluginLoadResult` with plugin instance or error

##### `load_plugin_from_module(module_path: str) -> PluginLoadResult`

Load a plugin from a Python module path.

**Parameters:**
- `module_path`: Dot-separated module path (e.g., "my_package.my_plugin")

**Returns:** `PluginLoadResult` with plugin instance or error

#### Plugin Lifecycle

##### `initialize_plugin(plugin_name: str) -> bool`

Initialize a plugin.

**Parameters:**
- `plugin_name`: Name of the plugin to initialize

**Returns:** `True` if successful, `False` otherwise

##### `start_plugin(plugin_name: str) -> bool`

Start a plugin.

**Parameters:**
- `plugin_name`: Name of the plugin to start

**Returns:** `True` if successful, `False` otherwise

##### `stop_plugin(plugin_name: str) -> bool`

Stop a plugin.

**Parameters:**
- `plugin_name`: Name of the plugin to stop

**Returns:** `True` if successful, `False` otherwise

##### `restart_plugin(plugin_name: str) -> bool`

Restart a plugin.

**Parameters:**
- `plugin_name`: Name of the plugin to restart

**Returns:** `True` if successful, `False` otherwise

##### `unload_plugin(plugin_name: str) -> bool`

Unload a plugin.

**Parameters:**
- `plugin_name`: Name of the plugin to unload

**Returns:** `True` if successful, `False` otherwise

#### Querying Plugins

##### `get_plugin(plugin_name: str) -> Optional[Plugin]`

Get a plugin by name.

**Parameters:**
- `plugin_name`: Name of the plugin to get

**Returns:** Plugin instance or `None` if not found

##### `get_plugin_state(plugin_name: str) -> Optional[PluginState]`

Get the state of a plugin.

**Parameters:**
- `plugin_name`: Name of the plugin

**Returns:** `PluginState` object or `None` if not found

##### `list_plugins(plugin_type: str = None) -> List[str]`

List all loaded plugins.

**Parameters:**
- `plugin_type`: Optional filter by plugin type

**Returns:** List of plugin names

##### `get_running_plugins() -> List[str]`

Get list of running plugins.

**Returns:** List of plugin names that are currently running

##### `get_idle_plugins() -> List[str]`

Get list of loaded but not running plugins.

**Returns:** List of plugin names that are loaded but not running

##### `is_plugin_loaded(plugin_name: str) -> bool`

Check if a plugin is loaded.

**Parameters:**
- `plugin_name`: Name of the plugin to check

**Returns:** `True` if plugin is loaded, `False` otherwise

##### `is_plugin_running(plugin_name: str) -> bool`

Check if a plugin is running.

**Parameters:**
- `plugin_name`: Name of the plugin to check

**Returns:** `True` if plugin is running, `False` otherwise

##### `get_plugin_metadata(plugin_name: str) -> Optional[PluginMetadata]`

Get metadata for a plugin.

**Parameters:**
- `plugin_name`: Name of the plugin

**Returns:** `PluginMetadata` or `None` if not found

##### `get_plugin_info(plugin_name: str) -> Optional[Dict[str, Any]]`

Get detailed information about a plugin.

**Parameters:**
- `plugin_name`: Name of the plugin

**Returns:** Dictionary with plugin information or `None` if not found

##### `get_plugins_by_type(plugin_type: str) -> List[Plugin]`

Get all plugins of a specific type.

**Parameters:**
- `plugin_type`: Type of plugin to get

**Returns:** List of plugin instances of the specified type

##### `get_metrics() -> Dict[str, Any]`

Get metrics about plugins.

**Returns:** Dictionary with plugin metrics

#### Bulk Operations

##### `start_all_plugins() -> Dict[str, bool]`

Start all loaded plugins.

**Returns:** Dictionary mapping plugin names to start success status

##### `stop_all_plugins() -> Dict[str, bool]`

Stop all running plugins.

**Returns:** Dictionary mapping plugin names to stop success status

##### `cleanup_all_plugins() -> None`

Clean up all plugins.

#### Hooks

##### `register_startup_hook(hook: Callable) -> None`

Register a function to be called on startup.

**Parameters:**
- `hook`: Callable function to run on startup

##### `register_shutdown_hook(hook: Callable) -> None`

Register a function to be called on shutdown.

**Parameters:**
- `hook`: Callable function to run on shutdown

---

## Plugin Registry

The `PluginRegistry` class provides a centralized registry for all installed and loaded plugins.

```python
from devflow.plugins.plugin_registry import PluginRegistry

registry = PluginRegistry()
```

### Methods

##### `register_plugin(plugin: Plugin) -> None`

Register a plugin.

**Parameters:**
- `plugin`: Plugin instance to register

##### `unregister_plugin(plugin_name: str) -> bool`

Unregister a plugin.

**Parameters:**
- `plugin_name`: Name of the plugin to unregister

**Returns:** `True` if plugin was unregistered, `False` if not found

##### `get_plugin(plugin_name: str) -> Optional[Plugin]`

Get a plugin by name.

**Parameters:**
- `plugin_name`: Name of the plugin to get

**Returns:** Plugin instance or `None` if not found

##### `get_plugin_metadata(plugin_name: str) -> Optional[PluginMetadata]`

Get metadata for a plugin.

**Parameters:**
- `plugin_name`: Name of the plugin

**Returns:** `PluginMetadata` or `None` if not found

##### `get_plugins_by_type(plugin_type: str) -> List[Plugin]`

Get all plugins of a specific type.

**Parameters:**
- `plugin_type`: Type of plugin to get

**Returns:** List of plugin instances of the specified type

##### `list_plugin_names() -> List[str]`

List all registered plugin names.

**Returns:** List of plugin names

##### `list_plugin_types() -> List[str]`

List all plugin types.

**Returns:** List of plugin types

##### `get_plugin_dependencies(plugin_name: str) -> List[str]`

Get dependencies for a plugin.

**Parameters:**
- `plugin_name`: Name of the plugin

**Returns:** List of plugin dependencies

##### `resolve_dependencies(plugin_name: str, resolved: List[str] = None) -> List[str]`

Recursively resolve all dependencies for a plugin.

**Parameters:**
- `plugin_name`: Name of the plugin to resolve dependencies for
- `resolved`: List of already resolved dependencies (for recursion)

**Returns:** List of all plugin dependencies in order

##### `validate_dependencies(plugin_name: str) -> bool`

Validate that all dependencies for a plugin are available.

**Parameters:**
- `plugin_name`: Name of the plugin to validate

**Returns:** `True` if all dependencies are available, `False` otherwise

##### `get_load_order(plugin_names: List[str] = None) -> List[str]`

Get the correct load order for plugins based on dependencies.

**Parameters:**
- `plugin_names`: List of plugin names to order. If `None`, orders all plugins.

**Returns:** List of plugin names in dependency order

##### `is_plugin_loaded(plugin_name: str) -> bool`

Check if a plugin is loaded.

**Parameters:**
- `plugin_name`: Name of the plugin to check

**Returns:** `True` if plugin is loaded, `False` otherwise

##### `get_plugin_count() -> int`

Get the total number of registered plugins.

**Returns:** Number of registered plugins

##### `get_plugin_count_by_type(plugin_type: str) -> int`

Get the number of plugins of a specific type.

**Parameters:**
- `plugin_type`: Type of plugin to count

**Returns:** Number of plugins of the specified type

##### `clear() -> None`

Clear all registered plugins.

---

## Plugin Loader

The `PluginLoader` class discovers and loads plugins from the filesystem.

```python
from devflow.plugins.plugin_loader import PluginLoader
from devflow.plugins.plugin_config import PluginConfig

config = PluginConfig()
loader = PluginLoader(config)
```

### Methods

##### `discover_plugins() -> List[Path]`

Discover all plugin directories.

**Returns:** List of plugin directory paths

##### `load_plugin_from_path(plugin_path: Path) -> PluginLoadResult`

Load a plugin from a directory path.

**Parameters:**
- `plugin_path`: Path to the plugin directory

**Returns:** `PluginLoadResult` with plugin instance or error

##### `load_all_plugins() -> List[PluginLoadResult]`

Discover and load all available plugins.

**Returns:** List of `PluginLoadResult` objects

##### `load_plugin_from_module(module_path: str) -> PluginLoadResult`

Load a plugin from a Python module path.

**Parameters:**
- `module_path`: Dot-separated module path (e.g., "my_package.my_plugin")

**Returns:** `PluginLoadResult` with plugin instance or error

##### `get_plugin_metadata(plugin_path: Path) -> Optional[PluginMetadata]`

Load plugin metadata without loading the full plugin.

**Parameters:**
- `plugin_path`: Path to the plugin directory

**Returns:** `PluginMetadata` or `None` if not available

##### `unload_plugin(plugin_name: str) -> bool`

Unload a plugin module from memory.

**Parameters:**
- `plugin_name`: Name of the plugin to unload

**Returns:** `True` if unloaded successfully, `False` otherwise

##### `get_loaded_modules() -> List[str]`

Get list of loaded plugin module names.

**Returns:** List of module names

---

## Plugin Configuration

The `PluginConfig` class manages plugin system configuration.

```python
from devflow.plugins.plugin_config import PluginConfig

config = PluginConfig()
```

### Configuration Options

#### Search Paths

- `plugin_directories`: List of directories to search for plugins
- `discovery_recursive`: Enable recursive plugin discovery (default: `True`)

#### Plugin Files

- `plugin_entry_point`: Plugin entry point file (default: `"plugin.py"`)
- `plugin_metadata_file`: Plugin metadata file (default: `"metadata.json"`)

#### Loading Behavior

- `continue_on_load_error`: Continue loading if a plugin fails (default: `True`)
- `strict_version_check`: Enable strict version checking (default: `False`)

#### Logging

- `log_plugin_errors`: Log plugin errors to file (default: `True`)
- `plugin_error_log_path`: Path to error log file

#### Plugin State

- `plugin_state_dir`: Directory for plugin state files

### Methods

##### `get_plugin_search_paths() -> List[Path]`

Get all plugin search paths.

**Returns:** List of directory paths to search for plugins

##### `is_plugin_enabled(plugin_name: str) -> bool`

Check if a plugin is enabled.

**Parameters:**
- `plugin_name`: Name of the plugin

**Returns:** `True` if enabled, `False` otherwise

##### `is_plugin_blocked(plugin_name: str) -> bool`

Check if a plugin is blocked.

**Parameters:**
- `plugin_name`: Name of the plugin

**Returns:** `True` if blocked, `False` otherwise

##### `get_plugin_config(plugin_name: str) -> Dict[str, Any]`

Get configuration for a specific plugin.

**Parameters:**
- `plugin_name`: Name of the plugin

**Returns:** Plugin configuration dictionary

##### `ensure_directories() -> None`

Ensure all required directories exist.

---

## Data Classes

### PluginMetadata

Metadata for a plugin.

```python
@dataclass
class PluginMetadata:
    name: str
    version: str
    description: str
    author: str
    plugin_type: str
    dependencies: List[str] = field(default_factory=list)
    devflow_version: str = "0.1.0"
```

### PluginLoadResult

Result of loading a plugin.

```python
@dataclass
class PluginLoadResult:
    plugin_name: str
    success: bool
    plugin: Optional[Plugin] = None
    error: Optional[str] = None
    plugin_path: Optional[Path] = None
```

### PluginState

State information for a plugin.

```python
@dataclass
class PluginState:
    plugin: Plugin
    name: str
    loaded_at: float
    initialized: bool = False
    running: bool = False
    load_result: Optional[PluginLoadResult] = None
```

### AgentConfig

Configuration for an agent type.

```python
@dataclass
class AgentConfig:
    agent_type: str
    model: str = "claude-3-5-sonnet-20241022"
    max_tasks: int = 1
    timeout: int = 3600
    skills: List[str] = None
    system_prompt: str = ""
```

### TaskSourceConfig

Configuration for a task source.

```python
@dataclass
class TaskSourceConfig:
    source_name: str
    enabled: bool = True
    polling_interval: int = 60
    priority: int = 5
    agent_type: str = "general"
    timeout: int = 3600
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### IntegrationStatus

Status of an integration connection.

```python
class IntegrationStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
```
