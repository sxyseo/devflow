"""
Plugin Configuration System

Configuration management for the DevFlow plugin system.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


class PluginConfig:
    """Configuration for the DevFlow plugin system."""

    def __init__(self):
        # Get project root from settings or current file location
        self.project_root = Path(__file__).parent.parent.parent

        # Plugin Directories
        self.builtin_plugins_dir = self.project_root / "devflow" / "plugins" / "builtin"
        self.user_plugins_dir = self.project_root / "devflow" / "plugins" / "user"
        self.third_party_plugins_dir = Path.home() / ".devflow" / "plugins"
        self.plugin_state_dir = self.project_root / ".devflow" / "plugins"

        # Plugin Loading Settings
        self.auto_load_plugins = True
        self.enabled_plugins: List[str] = []
        self.disabled_plugins: List[str] = []
        self.load_builtin_plugins = True
        self.load_user_plugins = True
        self.load_third_party_plugins = True

        # Plugin Discovery Settings
        self.discovery_recursive = True
        self.max_plugin_depth = 3
        self.plugin_entry_point = "plugin.py"
        self.plugin_metadata_file = "metadata.json"

        # Plugin Security Settings
        self.sandbox_mode = False
        self.allowed_plugin_paths: List[str] = []
        self.blocked_plugins: List[str] = []
        self.require_signature = False
        self.verify_checksum = False

        # Plugin Validation Settings
        self.strict_version_check = False
        self.min_devflow_version = "0.1.0"
        self.auto_resolve_dependencies = True
        self.allow_circular_dependencies = False

        # Plugin Runtime Settings
        self.plugin_timeout = int(os.getenv("PLUGIN_TIMEOUT", "300"))  # 5 minutes
        self.max_plugin_memory = int(os.getenv("MAX_PLUGIN_MEMORY", "512"))  # MB
        self.max_concurrent_plugins = int(os.getenv("MAX_CONCURRENT_PLUGINS", "10"))
        self.plugin_startup_timeout = int(os.getenv("PLUGIN_STARTUP_TIMEOUT", "30"))  # seconds

        # Plugin Error Handling
        self.continue_on_load_error = False
        self.log_plugin_errors = True
        self.plugin_error_log_path = self.plugin_state_dir / "errors.log"

        # Plugin Hot Reload
        self.enable_hot_reload = False
        self.hot_reload_interval = int(os.getenv("HOT_RELOAD_INTERVAL", "60"))  # seconds

    def ensure_directories(self):
        """Create all necessary plugin directories."""
        dirs = [
            self.builtin_plugins_dir,
            self.user_plugins_dir,
            self.third_party_plugins_dir,
            self.plugin_state_dir,
        ]

        for directory in dirs:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.warning(f"Failed to create plugin directory {directory}: {e}")

    def get_plugin_search_paths(self) -> List[Path]:
        """
        Get list of directories to search for plugins.

        Returns:
            List of plugin directory paths based on configuration
        """
        paths = []

        if self.load_builtin_plugins:
            paths.append(self.builtin_plugins_dir)

        if self.load_user_plugins:
            paths.append(self.user_plugins_dir)

        if self.load_third_party_plugins:
            paths.append(self.third_party_plugins_dir)

        # Filter to only existing directories
        return [p for p in paths if p.exists()]

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """
        Check if a plugin is enabled.

        Args:
            plugin_name: Name of the plugin to check

        Returns:
            True if plugin is enabled, False if disabled
        """
        # Explicitly disabled plugins take precedence
        if plugin_name in self.disabled_plugins:
            return False

        # If no enabled list, all plugins are enabled (except disabled)
        if not self.enabled_plugins:
            return True

        # Plugin must be in enabled list
        return plugin_name in self.enabled_plugins

    def is_plugin_blocked(self, plugin_name: str) -> bool:
        """
        Check if a plugin is blocked for security reasons.

        Args:
            plugin_name: Name of the plugin to check

        Returns:
            True if plugin is blocked, False otherwise
        """
        return plugin_name in self.blocked_plugins

    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin configuration dictionary
        """
        plugin_config_path = self.plugin_state_dir / f"{plugin_name}.json"

        if plugin_config_path.exists():
            try:
                with open(plugin_config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load plugin config for {plugin_name}: {e}")

        return {}

    def save_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> None:
        """
        Save configuration for a specific plugin.

        Args:
            plugin_name: Name of the plugin
            config: Configuration dictionary to save
        """
        self.ensure_directories()
        plugin_config_path = self.plugin_state_dir / f"{plugin_name}.json"

        try:
            with open(plugin_config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save plugin config for {plugin_name}: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert plugin configuration to dictionary."""
        return {
            "project_root": str(self.project_root),
            "builtin_plugins_dir": str(self.builtin_plugins_dir),
            "user_plugins_dir": str(self.user_plugins_dir),
            "third_party_plugins_dir": str(self.third_party_plugins_dir),
            "plugin_state_dir": str(self.plugin_state_dir),
            "auto_load_plugins": self.auto_load_plugins,
            "enabled_plugins": self.enabled_plugins,
            "disabled_plugins": self.disabled_plugins,
            "load_builtin_plugins": self.load_builtin_plugins,
            "load_user_plugins": self.load_user_plugins,
            "load_third_party_plugins": self.load_third_party_plugins,
            "discovery_recursive": self.discovery_recursive,
            "max_plugin_depth": self.max_plugin_depth,
            "plugin_entry_point": self.plugin_entry_point,
            "plugin_metadata_file": self.plugin_metadata_file,
            "sandbox_mode": self.sandbox_mode,
            "allowed_plugin_paths": self.allowed_plugin_paths,
            "blocked_plugins": self.blocked_plugins,
            "require_signature": self.require_signature,
            "verify_checksum": self.verify_checksum,
            "strict_version_check": self.strict_version_check,
            "min_devflow_version": self.min_devflow_version,
            "auto_resolve_dependencies": self.auto_resolve_dependencies,
            "allow_circular_dependencies": self.allow_circular_dependencies,
            "plugin_timeout": self.plugin_timeout,
            "max_plugin_memory": self.max_plugin_memory,
            "max_concurrent_plugins": self.max_concurrent_plugins,
            "plugin_startup_timeout": self.plugin_startup_timeout,
            "continue_on_load_error": self.continue_on_load_error,
            "log_plugin_errors": self.log_plugin_errors,
            "plugin_error_log_path": str(self.plugin_error_log_path),
            "enable_hot_reload": self.enable_hot_reload,
            "hot_reload_interval": self.hot_reload_interval,
        }

    def save(self, path: Optional[Path] = None) -> None:
        """
        Save plugin configuration to JSON file.

        Args:
            path: Optional path to save config. Defaults to plugin_state_dir/plugins.json
        """
        self.ensure_directories()

        if path is None:
            path = self.plugin_state_dir / "plugins.json"

        try:
            with open(path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            logger.info(f"Plugin configuration saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save plugin configuration: {e}")

    @classmethod
    def load(cls, path: Optional[Path] = None) -> 'PluginConfig':
        """
        Load plugin configuration from JSON file.

        Args:
            path: Optional path to load config from. Defaults to plugin_state_dir/plugins.json

        Returns:
            PluginConfig instance with loaded configuration
        """
        config = cls()

        if path is None:
            path = config.plugin_state_dir / "plugins.json"

        if path.exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)

                for key, value in data.items():
                    if hasattr(config, key):
                        # Convert string paths back to Path objects
                        if key.endswith('_dir') or key.endswith('_root') or key.endswith('_path'):
                            value = Path(value)
                        setattr(config, key, value)

                logger.info(f"Plugin configuration loaded from {path}")
            except Exception as e:
                logger.error(f"Failed to load plugin configuration: {e}")

        return config

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update configuration from dictionary.

        Args:
            data: Dictionary of configuration values to update
        """
        for key, value in data.items():
            if hasattr(self, key):
                # Convert string paths back to Path objects
                if key.endswith('_dir') or key.endswith('_root') or key.endswith('_path'):
                    value = Path(value)
                setattr(self, key, value)


# Global plugin configuration instance
plugin_config = PluginConfig()
