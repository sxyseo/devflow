"""
Plugin Registry - Register and manage installed plugins.

Provides a centralized registry for all installed and loaded plugins.
"""

import threading
from pathlib import Path
from typing import Dict, List, Optional, Any

from .base import Plugin, PluginMetadata


class PluginRegistry:
    """
    Registry for managing installed plugins.

    Provides:
    - Plugin registration and storage
    - Plugin lookup by name or type
    - Plugin dependency resolution
    - Thread-safe plugin management
    """

    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._plugins_by_type: Dict[str, List[str]] = {}
        self._plugin_metadata: Dict[str, PluginMetadata] = {}
        self._lock = threading.Lock()

    def register_plugin(self, plugin: Plugin) -> None:
        """
        Register a plugin.

        Args:
            plugin: Plugin instance to register
        """
        with self._lock:
            metadata = plugin.get_metadata()
            plugin_name = metadata.name.lower().replace(' ', '-')

            self._plugins[plugin_name] = plugin
            self._plugin_metadata[plugin_name] = metadata

            # Index by type
            plugin_type = metadata.plugin_type
            if plugin_type not in self._plugins_by_type:
                self._plugins_by_type[plugin_type] = []

            if plugin_name not in self._plugins_by_type[plugin_type]:
                self._plugins_by_type[plugin_type].append(plugin_name)

    def unregister_plugin(self, plugin_name: str) -> bool:
        """
        Unregister a plugin.

        Args:
            plugin_name: Name of the plugin to unregister

        Returns:
            True if plugin was unregistered, False if not found
        """
        with self._lock:
            # Normalize plugin name
            plugin_name = plugin_name.lower().replace(' ', '-')

            if plugin_name not in self._plugins:
                return False

            # Get metadata before removing
            metadata = self._plugin_metadata.get(plugin_name)
            if metadata:
                plugin_type = metadata.plugin_type
                # Remove from type index
                if plugin_type in self._plugins_by_type:
                    self._plugins_by_type[plugin_type] = [
                        name for name in self._plugins_by_type[plugin_type]
                        if name != plugin_name
                    ]

                    # Remove empty type lists
                    if not self._plugins_by_type[plugin_type]:
                        del self._plugins_by_type[plugin_type]

            # Remove plugin and metadata
            del self._plugins[plugin_name]
            if plugin_name in self._plugin_metadata:
                del self._plugin_metadata[plugin_name]

            return True

    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """
        Get a plugin by name.

        Args:
            plugin_name: Name of the plugin to get

        Returns:
            Plugin instance or None if not found
        """
        # Try exact match
        if plugin_name in self._plugins:
            return self._plugins[plugin_name]

        # Try fuzzy match
        plugin_key = plugin_name.lower().replace(' ', '-')
        if plugin_key in self._plugins:
            return self._plugins[plugin_key]

        # Try partial match
        for key, plugin in self._plugins.items():
            if plugin_name.lower() in key.lower():
                return plugin

        return None

    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """
        Get metadata for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            PluginMetadata or None if not found
        """
        # Normalize plugin name
        plugin_key = plugin_name.lower().replace(' ', '-')

        return self._plugin_metadata.get(plugin_key)

    def get_plugins_by_type(self, plugin_type: str) -> List[Plugin]:
        """
        Get all plugins of a specific type.

        Args:
            plugin_type: Type of plugin to get (e.g., "agent", "task_source")

        Returns:
            List of plugin instances of the specified type
        """
        plugin_names = self._plugins_by_type.get(plugin_type, [])

        return [
            self._plugins[name]
            for name in plugin_names
            if name in self._plugins
        ]

    def list_plugin_names(self) -> List[str]:
        """
        List all registered plugin names.

        Returns:
            List of plugin names
        """
        return list(self._plugins.keys())

    def list_plugin_types(self) -> List[str]:
        """
        List all plugin types.

        Returns:
            List of plugin types
        """
        return list(self._plugins_by_type.keys())

    def get_plugin_dependencies(self, plugin_name: str) -> List[str]:
        """
        Get dependencies for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            List of plugin dependencies
        """
        metadata = self.get_plugin_metadata(plugin_name)

        if not metadata:
            return []

        return metadata.dependencies

    def resolve_dependencies(self, plugin_name: str, resolved: List[str] = None) -> List[str]:
        """
        Recursively resolve all dependencies for a plugin.

        Args:
            plugin_name: Name of the plugin to resolve dependencies for
            resolved: List of already resolved dependencies (for recursion)

        Returns:
            List of all plugin dependencies in order
        """
        if resolved is None:
            resolved = []

        plugin = self.get_plugin(plugin_name)

        if not plugin:
            return resolved

        for dep in plugin.get_dependencies():
            if dep not in resolved:
                resolved.append(dep)
                self.resolve_dependencies(dep, resolved)

        return resolved

    def validate_dependencies(self, plugin_name: str) -> bool:
        """
        Validate that all dependencies for a plugin are available.

        Args:
            plugin_name: Name of the plugin to validate

        Returns:
            True if all dependencies are available, False otherwise
        """
        plugin = self.get_plugin(plugin_name)

        if not plugin:
            return False

        dependencies = plugin.get_dependencies()
        available_plugins = self.list_plugin_names()

        return all(dep in available_plugins for dep in dependencies)

    def get_load_order(self, plugin_names: List[str] = None) -> List[str]:
        """
        Get the correct load order for plugins based on dependencies.

        Args:
            plugin_names: List of plugin names to order. If None, orders all plugins.

        Returns:
            List of plugin names in dependency order
        """
        if plugin_names is None:
            plugin_names = self.list_plugin_names()

        ordered = []
        visited = set()

        def visit(plugin_name: str):
            if plugin_name in visited:
                return

            visited.add(plugin_name)

            # Visit dependencies first
            plugin = self.get_plugin(plugin_name)
            if plugin:
                for dep in plugin.get_dependencies():
                    if dep in plugin_names:
                        visit(dep)

            ordered.append(plugin_name)

        for plugin_name in plugin_names:
            visit(plugin_name)

        return ordered

    def is_plugin_loaded(self, plugin_name: str) -> bool:
        """
        Check if a plugin is loaded.

        Args:
            plugin_name: Name of the plugin to check

        Returns:
            True if plugin is loaded, False otherwise
        """
        return self.get_plugin(plugin_name) is not None

    def get_plugin_count(self) -> int:
        """
        Get the total number of registered plugins.

        Returns:
            Number of registered plugins
        """
        return len(self._plugins)

    def get_plugin_count_by_type(self, plugin_type: str) -> int:
        """
        Get the number of plugins of a specific type.

        Args:
            plugin_type: Type of plugin to count

        Returns:
            Number of plugins of the specified type
        """
        return len(self._plugins_by_type.get(plugin_type, []))

    def clear(self) -> None:
        """Clear all registered plugins."""
        with self._lock:
            self._plugins.clear()
            self._plugins_by_type.clear()
            self._plugin_metadata.clear()
