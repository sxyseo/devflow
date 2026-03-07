"""
Plugin Manager - Main API for plugin operations.

Provides a unified interface for plugin lifecycle management, including
loading, starting, stopping, and querying plugins.
"""

import logging
import threading
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field

from .base import Plugin, PluginMetadata
from .plugin_loader import PluginLoader, PluginLoadResult
from .plugin_registry import PluginRegistry
from .plugin_config import PluginConfig


logger = logging.getLogger(__name__)


@dataclass
class PluginState:
    """State information for a plugin."""
    plugin: Plugin
    name: str
    loaded_at: float
    initialized: bool = False
    running: bool = False
    load_result: Optional[PluginLoadResult] = None


class PluginManager:
    """
    Manages the lifecycle of plugins.

    Responsibilities:
    - Plugin discovery and loading
    - Plugin initialization and startup
    - Plugin monitoring and health checks
    - Plugin cleanup and resource management
    - Plugin querying and introspection
    """

    def __init__(self, config: PluginConfig = None,
                 loader: PluginLoader = None,
                 registry: PluginRegistry = None):
        """
        Initialize the plugin manager.

        Args:
            config: Optional plugin configuration. If None, uses default config.
            loader: Optional plugin loader. If None, creates a new loader.
            registry: Optional plugin registry. If None, creates a new registry.
        """
        self.config = config or PluginConfig()
        self.loader = loader or PluginLoader(self.config)
        self.registry = registry or PluginRegistry()

        self._plugins: Dict[str, PluginState] = {}
        self._lock = threading.Lock()
        self._startup_hooks: List[Callable] = []
        self._shutdown_hooks: List[Callable] = []

        # Ensure plugin directories exist
        self.config.ensure_directories()

    def load_all_plugins(self) -> List[PluginLoadResult]:
        """
        Discover and load all available plugins.

        Returns:
            List of PluginLoadResult objects containing load results
        """
        results = self.loader.load_all_plugins()

        for result in results:
            if result.success:
                self._register_loaded_plugin(result)

        return results

    def load_plugin(self, plugin_name: str) -> PluginLoadResult:
        """
        Load a specific plugin by name.

        Args:
            plugin_name: Name of the plugin to load

        Returns:
            PluginLoadResult with plugin instance or error
        """
        # Check if already loaded
        if self.is_plugin_loaded(plugin_name):
            logger.info(f"Plugin '{plugin_name}' is already loaded")
            return PluginLoadResult(
                plugin_name=plugin_name,
                success=True,
                plugin=self.get_plugin(plugin_name)
            )

        # Discover plugins to find the plugin path
        plugin_dirs = self.loader.discover_plugins()

        for plugin_dir in plugin_dirs:
            if plugin_dir.name == plugin_name:
                result = self.loader.load_plugin_from_path(plugin_dir)

                if result.success:
                    self._register_loaded_plugin(result)

                return result

        return PluginLoadResult(
            plugin_name=plugin_name,
            success=False,
            error=f"Plugin '{plugin_name}' not found in plugin directories"
        )

    def load_plugin_from_path(self, plugin_path: str) -> PluginLoadResult:
        """
        Load a plugin from a specific path.

        Args:
            plugin_path: Path to the plugin directory

        Returns:
            PluginLoadResult with plugin instance or error
        """
        from pathlib import Path
        path = Path(plugin_path)

        result = self.loader.load_plugin_from_path(path)

        if result.success:
            self._register_loaded_plugin(result)

        return result

    def load_plugin_from_module(self, module_path: str) -> PluginLoadResult:
        """
        Load a plugin from a Python module path.

        Args:
            module_path: Dot-separated module path (e.g., "my_package.my_plugin")

        Returns:
            PluginLoadResult with plugin instance or error
        """
        result = self.loader.load_plugin_from_module(module_path)

        if result.success:
            self._register_loaded_plugin(result)

        return result

    def _register_loaded_plugin(self, result: PluginLoadResult) -> None:
        """
        Register a successfully loaded plugin in the registry and state.

        Args:
            result: PluginLoadResult with loaded plugin
        """
        plugin = result.plugin
        if not plugin:
            return

        # Register in plugin registry
        self.registry.register_plugin(plugin)

        # Store plugin state
        with self._lock:
            self._plugins[result.plugin_name] = PluginState(
                plugin=plugin,
                name=result.plugin_name,
                loaded_at=time.time(),
                load_result=result
            )

        logger.info(f"Registered plugin: {result.plugin_name}")

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin.

        Args:
            plugin_name: Name of the plugin to unload

        Returns:
            True if plugin was unloaded, False otherwise
        """
        plugin_state = self._plugins.get(plugin_name)

        if not plugin_state:
            logger.warning(f"Plugin '{plugin_name}' is not loaded")
            return False

        # Stop plugin if running
        if plugin_state.running:
            self.stop_plugin(plugin_name)

        # Unload from loader
        self.loader.unload_plugin(plugin_name)

        # Unregister from registry
        self.registry.unregister_plugin(plugin_name)

        # Remove from state
        with self._lock:
            del self._plugins[plugin_name]

        logger.info(f"Unloaded plugin: {plugin_name}")
        return True

    def initialize_plugin(self, plugin_name: str) -> bool:
        """
        Initialize a plugin.

        Args:
            plugin_name: Name of the plugin to initialize

        Returns:
            True if plugin was initialized successfully, False otherwise
        """
        plugin_state = self._plugins.get(plugin_name)

        if not plugin_state:
            logger.error(f"Plugin '{plugin_name}' is not loaded")
            return False

        if plugin_state.initialized:
            logger.info(f"Plugin '{plugin_name}' is already initialized")
            return True

        try:
            # Validate dependencies
            metadata = plugin_state.plugin.get_metadata()
            dependencies = metadata.dependencies

            if dependencies:
                # Ensure all dependencies are loaded and initialized
                for dep in dependencies:
                    if not self.is_plugin_loaded(dep):
                        logger.warning(f"Loading dependency '{dep}' for plugin '{plugin_name}'")
                        result = self.load_plugin(dep)
                        if not result.success:
                            logger.error(f"Failed to load dependency '{dep}' for plugin '{plugin_name}'")
                            return False

                    if not self.initialize_plugin(dep):
                        logger.error(f"Failed to initialize dependency '{dep}' for plugin '{plugin_name}'")
                        return False

            # Initialize the plugin
            plugin_state.plugin.initialize()
            plugin_state.initialized = True

            logger.info(f"Initialized plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Error initializing plugin '{plugin_name}': {e}", exc_info=True)
            return False

    def start_plugin(self, plugin_name: str) -> bool:
        """
        Start a plugin.

        Args:
            plugin_name: Name of the plugin to start

        Returns:
            True if plugin was started successfully, False otherwise
        """
        plugin_state = self._plugins.get(plugin_name)

        if not plugin_state:
            logger.error(f"Plugin '{plugin_name}' is not loaded")
            return False

        if plugin_state.running:
            logger.info(f"Plugin '{plugin_name}' is already running")
            return True

        try:
            # Initialize if not already initialized
            if not plugin_state.initialized:
                if not self.initialize_plugin(plugin_name):
                    return False

            # Start the plugin
            plugin_state.plugin.start()
            plugin_state.running = True

            logger.info(f"Started plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Error starting plugin '{plugin_name}': {e}", exc_info=True)
            return False

    def stop_plugin(self, plugin_name: str) -> bool:
        """
        Stop a plugin.

        Args:
            plugin_name: Name of the plugin to stop

        Returns:
            True if plugin was stopped successfully, False otherwise
        """
        plugin_state = self._plugins.get(plugin_name)

        if not plugin_state:
            logger.warning(f"Plugin '{plugin_name}' is not loaded")
            return False

        if not plugin_state.running:
            logger.info(f"Plugin '{plugin_name}' is not running")
            return True

        try:
            # Stop the plugin
            plugin_state.plugin.stop()
            plugin_state.running = False

            logger.info(f"Stopped plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Error stopping plugin '{plugin_name}': {e}", exc_info=True)
            return False

    def restart_plugin(self, plugin_name: str) -> bool:
        """
        Restart a plugin.

        Args:
            plugin_name: Name of the plugin to restart

        Returns:
            True if plugin was restarted successfully, False otherwise
        """
        if self.stop_plugin(plugin_name):
            return self.start_plugin(plugin_name)
        return False

    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """
        Get a plugin by name.

        Args:
            plugin_name: Name of the plugin to get

        Returns:
            Plugin instance or None if not found
        """
        plugin_state = self._plugins.get(plugin_name)
        return plugin_state.plugin if plugin_state else None

    def get_plugin_state(self, plugin_name: str) -> Optional[PluginState]:
        """
        Get the state of a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            PluginState object or None if not found
        """
        return self._plugins.get(plugin_name)

    def list_plugins(self, plugin_type: str = None) -> List[str]:
        """
        List all loaded plugins.

        Args:
            plugin_type: Optional filter by plugin type

        Returns:
            List of plugin names
        """
        if plugin_type:
            plugins = self.registry.get_plugins_by_type(plugin_type)
            return [p.get_metadata().name for p in plugins]

        return list(self._plugins.keys())

    def get_running_plugins(self) -> List[str]:
        """
        Get list of running plugins.

        Returns:
            List of plugin names that are currently running
        """
        return [
            name for name, state in self._plugins.items()
            if state.running
        ]

    def get_idle_plugins(self) -> List[str]:
        """
        Get list of loaded but not running plugins.

        Returns:
            List of plugin names that are loaded but not running
        """
        return [
            name for name, state in self._plugins.items()
            if not state.running
        ]

    def is_plugin_loaded(self, plugin_name: str) -> bool:
        """
        Check if a plugin is loaded.

        Args:
            plugin_name: Name of the plugin to check

        Returns:
            True if plugin is loaded, False otherwise
        """
        return plugin_name in self._plugins

    def is_plugin_running(self, plugin_name: str) -> bool:
        """
        Check if a plugin is running.

        Args:
            plugin_name: Name of the plugin to check

        Returns:
            True if plugin is running, False otherwise
        """
        plugin_state = self._plugins.get(plugin_name)
        return plugin_state.running if plugin_state else False

    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """
        Get metadata for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            PluginMetadata or None if not found
        """
        return self.registry.get_plugin_metadata(plugin_name)

    def get_plugins_by_type(self, plugin_type: str) -> List[Plugin]:
        """
        Get all plugins of a specific type.

        Args:
            plugin_type: Type of plugin to get

        Returns:
            List of plugin instances of the specified type
        """
        return self.registry.get_plugins_by_type(plugin_type)

    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Dictionary with plugin information or None if not found
        """
        plugin_state = self._plugins.get(plugin_name)

        if not plugin_state:
            return None

        metadata = plugin_state.plugin.get_metadata()

        return {
            "name": plugin_state.name,
            "loaded_at": plugin_state.loaded_at,
            "initialized": plugin_state.initialized,
            "running": plugin_state.running,
            "metadata": {
                "name": metadata.name,
                "version": metadata.version,
                "description": metadata.description,
                "author": metadata.author,
                "plugin_type": metadata.plugin_type,
                "dependencies": metadata.dependencies,
                "devflow_version": metadata.devflow_version,
            }
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about plugins.

        Returns:
            Dictionary with plugin metrics
        """
        total = len(self._plugins)
        running = sum(1 for s in self._plugins.values() if s.running)
        idle = total - running

        plugin_types = self.registry.list_plugin_types()
        plugins_by_type = {
            ptype: self.registry.get_plugin_count_by_type(ptype)
            for ptype in plugin_types
        }

        return {
            "total_plugins": total,
            "running": running,
            "idle": idle,
            "plugins_by_type": plugins_by_type,
            "plugin_types": len(plugin_types),
        }

    def start_all_plugins(self) -> Dict[str, bool]:
        """
        Start all loaded plugins.

        Returns:
            Dictionary mapping plugin names to start success status
        """
        results = {}

        # Start plugins in dependency order
        load_order = self.registry.get_load_order(list(self._plugins.keys()))

        for plugin_name in load_order:
            results[plugin_name] = self.start_plugin(plugin_name)

        return results

    def stop_all_plugins(self) -> Dict[str, bool]:
        """
        Stop all running plugins.

        Returns:
            Dictionary mapping plugin names to stop success status
        """
        results = {}

        # Stop in reverse dependency order
        load_order = self.registry.get_load_order(list(self._plugins.keys()))

        for plugin_name in reversed(load_order):
            results[plugin_name] = self.stop_plugin(plugin_name)

        return results

    def cleanup_all_plugins(self) -> None:
        """Clean up all plugins."""
        # Stop all plugins first
        self.stop_all_plugins()

        # Unload all plugins
        plugin_names = list(self._plugins.keys())

        for plugin_name in plugin_names:
            self.unload_plugin(plugin_name)

    def register_startup_hook(self, hook: Callable) -> None:
        """
        Register a function to be called on startup.

        Args:
            hook: Callable function to run on startup
        """
        self._startup_hooks.append(hook)

    def register_shutdown_hook(self, hook: Callable) -> None:
        """
        Register a function to be called on shutdown.

        Args:
            hook: Callable function to run on shutdown
        """
        self._shutdown_hooks.append(hook)

    def run_startup_hooks(self) -> None:
        """Run all registered startup hooks."""
        for hook in self._startup_hooks:
            try:
                hook()
            except Exception as e:
                logger.error(f"Error running startup hook: {e}", exc_info=True)

    def run_shutdown_hooks(self) -> None:
        """Run all registered shutdown hooks."""
        for hook in self._shutdown_hooks:
            try:
                hook()
            except Exception as e:
                logger.error(f"Error running shutdown hook: {e}", exc_info=True)
