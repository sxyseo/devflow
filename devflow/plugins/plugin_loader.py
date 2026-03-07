"""
Plugin Loader - Discover and load plugins from the filesystem.

Handles plugin discovery, module loading, and instantiation.
"""

import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass

from .base import Plugin, PluginMetadata
from .plugin_config import PluginConfig


logger = logging.getLogger(__name__)


@dataclass
class PluginLoadResult:
    """Result of loading a plugin."""
    plugin_name: str
    success: bool
    plugin: Optional[Plugin] = None
    error: Optional[str] = None
    plugin_path: Optional[Path] = None


class PluginLoader:
    """
    Discovers and loads plugins from the filesystem.

    Handles:
    - Plugin discovery from configured directories
    - Dynamic module loading
    - Plugin instantiation
    - Metadata extraction
    - Error handling and logging
    """

    def __init__(self, config: PluginConfig = None):
        """
        Initialize the plugin loader.

        Args:
            config: Optional plugin configuration. If None, uses default config.
        """
        self.config = config or PluginConfig()
        self._loaded_modules: Dict[str, Any] = {}

    def discover_plugins(self) -> List[Path]:
        """
        Discover all plugin directories.

        Searches configured plugin directories for valid plugins.
        A valid plugin has a plugin.py file or metadata.json.

        Returns:
            List of plugin directory paths
        """
        plugin_dirs = []

        search_paths = self.config.get_plugin_search_paths()

        for search_path in search_paths:
            if not search_path.exists():
                continue

            # Search for plugin directories
            if self.config.discovery_recursive:
                # Recursive search
                for item in search_path.rglob("*"):
                    if item.is_dir() and self._is_plugin_directory(item):
                        plugin_dirs.append(item)
            else:
                # Non-recursive search (immediate children only)
                for item in search_path.iterdir():
                    if item.is_dir() and self._is_plugin_directory(item):
                        plugin_dirs.append(item)

        logger.info(f"Discovered {len(plugin_dirs)} plugin directories")
        return plugin_dirs

    def _is_plugin_directory(self, path: Path) -> bool:
        """
        Check if a directory is a valid plugin directory.

        Args:
            path: Directory path to check

        Returns:
            True if directory contains a valid plugin
        """
        # Check for plugin.py entry point
        plugin_file = path / self.config.plugin_entry_point
        if plugin_file.exists():
            return True

        # Check for metadata.json
        metadata_file = path / self.config.plugin_metadata_file
        if metadata_file.exists():
            return True

        return False

    def load_plugin_from_path(self, plugin_path: Path) -> PluginLoadResult:
        """
        Load a plugin from a directory path.

        Args:
            plugin_path: Path to the plugin directory

        Returns:
            PluginLoadResult with plugin instance or error
        """
        plugin_name = plugin_path.name

        try:
            # Check if plugin is blocked
            if self.config.is_plugin_blocked(plugin_name):
                return PluginLoadResult(
                    plugin_name=plugin_name,
                    success=False,
                    error=f"Plugin '{plugin_name}' is blocked by configuration"
                )

            # Load the plugin module
            plugin_module = self._load_plugin_module(plugin_path)
            if not plugin_module:
                return PluginLoadResult(
                    plugin_name=plugin_name,
                    success=False,
                    error=f"Failed to load plugin module from {plugin_path}"
                )

            # Find the Plugin class in the module
            plugin_class = self._find_plugin_class(plugin_module)
            if not plugin_class:
                return PluginLoadResult(
                    plugin_name=plugin_name,
                    success=False,
                    error=f"No Plugin class found in {plugin_path}"
                )

            # Load plugin configuration
            plugin_config = self.config.get_plugin_config(plugin_name)

            # Instantiate the plugin
            plugin_instance = plugin_class(config=plugin_config)

            # Validate metadata
            metadata = plugin_instance.get_metadata()
            self._validate_plugin_metadata(metadata, plugin_name)

            logger.info(f"Successfully loaded plugin: {plugin_name}")
            return PluginLoadResult(
                plugin_name=plugin_name,
                success=True,
                plugin=plugin_instance,
                plugin_path=plugin_path
            )

        except Exception as e:
            error_msg = f"Error loading plugin '{plugin_name}': {e}"
            logger.error(error_msg, exc_info=True)

            if self.config.log_plugin_errors:
                self._log_plugin_error(plugin_name, error_msg)

            return PluginLoadResult(
                plugin_name=plugin_name,
                success=False,
                error=error_msg,
                plugin_path=plugin_path
            )

    def _load_plugin_module(self, plugin_path: Path) -> Optional[Any]:
        """
        Load a plugin module from a directory.

        Args:
            plugin_path: Path to the plugin directory

        Returns:
            Loaded module or None if loading failed
        """
        plugin_file = plugin_path / self.config.plugin_entry_point

        if not plugin_file.exists():
            logger.error(f"Plugin entry point not found: {plugin_file}")
            return None

        try:
            # Create a unique module name
            module_name = f"plugin_{plugin_path.name}_{id(plugin_path)}"

            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to create module spec for {plugin_file}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Cache the loaded module
            self._loaded_modules[module_name] = module

            return module

        except Exception as e:
            logger.error(f"Failed to load plugin module from {plugin_file}: {e}")
            return None

    def _find_plugin_class(self, module: Any) -> Optional[Type[Plugin]]:
        """
        Find a Plugin class in a module.

        Args:
            module: Loaded module to search

        Returns:
            Plugin class or None if not found
        """
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Check if it's a Plugin subclass (but not Plugin itself)
            if (issubclass(obj, Plugin) and
                obj is not Plugin and
                obj.__module__ == module.__name__):
                return obj

        return None

    def _validate_plugin_metadata(self, metadata: PluginMetadata, plugin_name: str) -> None:
        """
        Validate plugin metadata.

        Args:
            metadata: Plugin metadata to validate
            plugin_name: Name of the plugin (for error messages)

        Raises:
            ValueError: If metadata is invalid
        """
        if not metadata.name:
            raise ValueError(f"Plugin '{plugin_name}' has empty name")

        if not metadata.version:
            raise ValueError(f"Plugin '{plugin_name}' has empty version")

        if not metadata.plugin_type:
            raise ValueError(f"Plugin '{plugin_name}' has empty plugin_type")

        # Version check if strict mode is enabled
        if self.config.strict_version_check:
            # Compare version requirements (simplified check)
            if metadata.devflow_version:
                # In a real implementation, would do proper version comparison
                pass

    def load_all_plugins(self) -> List[PluginLoadResult]:
        """
        Discover and load all available plugins.

        Returns:
            List of PluginLoadResult objects
        """
        results = []
        plugin_dirs = self.discover_plugins()

        for plugin_dir in plugin_dirs:
            # Check if plugin is enabled
            plugin_name = plugin_dir.name
            if not self.config.is_plugin_enabled(plugin_name):
                logger.info(f"Plugin '{plugin_name}' is disabled, skipping")
                continue

            result = self.load_plugin_from_path(plugin_dir)
            results.append(result)

            # Log summary
            if result.success:
                logger.info(f"Loaded plugin: {result.plugin_name}")
            else:
                if not self.config.continue_on_load_error:
                    logger.error(f"Failed to load plugin '{result.plugin_name}': {result.error}")
                    break
                else:
                    logger.warning(f"Failed to load plugin '{result.plugin_name}': {result.error}")

        return results

    def load_plugin_from_module(self, module_path: str) -> PluginLoadResult:
        """
        Load a plugin from a Python module path.

        Args:
            module_path: Dot-separated module path (e.g., "my_package.my_plugin")

        Returns:
            PluginLoadResult with plugin instance or error
        """
        try:
            module = importlib.import_module(module_path)
            plugin_class = self._find_plugin_class(module)

            if not plugin_class:
                return PluginLoadResult(
                    plugin_name=module_path,
                    success=False,
                    error=f"No Plugin class found in module {module_path}"
                )

            # Get plugin name from module path
            plugin_name = module_path.split('.')[-1]
            plugin_config = self.config.get_plugin_config(plugin_name)

            plugin_instance = plugin_class(config=plugin_config)
            metadata = plugin_instance.get_metadata()
            self._validate_plugin_metadata(metadata, plugin_name)

            return PluginLoadResult(
                plugin_name=plugin_name,
                success=True,
                plugin=plugin_instance
            )

        except ImportError as e:
            return PluginLoadResult(
                plugin_name=module_path,
                success=False,
                error=f"Failed to import module {module_path}: {e}"
            )
        except Exception as e:
            return PluginLoadResult(
                plugin_name=module_path,
                success=False,
                error=f"Error loading plugin from module {module_path}: {e}"
            )

    def get_plugin_metadata(self, plugin_path: Path) -> Optional[PluginMetadata]:
        """
        Load plugin metadata without loading the full plugin.

        Args:
            plugin_path: Path to the plugin directory

        Returns:
            PluginMetadata or None if not available
        """
        metadata_file = plugin_path / self.config.plugin_metadata_file

        if not metadata_file.exists():
            return None

        try:
            import json
            with open(metadata_file, 'r') as f:
                data = json.load(f)

            return PluginMetadata(
                name=data.get('name', plugin_path.name),
                version=data.get('version', '0.0.0'),
                description=data.get('description', ''),
                author=data.get('author', ''),
                plugin_type=data.get('plugin_type', 'unknown'),
                dependencies=data.get('dependencies', []),
                devflow_version=data.get('devflow_version', '0.1.0')
            )
        except Exception as e:
            logger.error(f"Failed to load metadata from {metadata_file}: {e}")
            return None

    def _log_plugin_error(self, plugin_name: str, error_message: str) -> None:
        """
        Log a plugin error to the error log file.

        Args:
            plugin_name: Name of the plugin
            error_message: Error message to log
        """
        try:
            self.config.ensure_directories()
            error_log = self.config.plugin_error_log_path

            with open(error_log, 'a') as f:
                import datetime
                timestamp = datetime.datetime.now().isoformat()
                f.write(f"[{timestamp}] {plugin_name}: {error_message}\n")
        except Exception as e:
            logger.error(f"Failed to write to plugin error log: {e}")

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin module from memory.

        Args:
            plugin_name: Name of the plugin to unload

        Returns:
            True if unloaded successfully, False otherwise
        """
        # Find and remove loaded modules
        modules_to_remove = [
            module_name for module_name in self._loaded_modules
            if plugin_name in module_name
        ]

        for module_name in modules_to_remove:
            if module_name in sys.modules:
                del sys.modules[module_name]
            if module_name in self._loaded_modules:
                del self._loaded_modules[module_name]

        return len(modules_to_remove) > 0

    def get_loaded_modules(self) -> List[str]:
        """
        Get list of loaded plugin module names.

        Returns:
            List of module names
        """
        return list(self._loaded_modules.keys())
