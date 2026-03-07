"""
Plugin Installer - Plugin installation and management system.

Handles plugin installation, uninstallation, updates, and verification
from various sources including git repositories, local files, and
marketplace downloads.
"""

import hashlib
import json
import logging
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from .marketplace_client import MarketplacePluginInfo, MarketplaceClient
from .marketplace_registry import MarketplaceRegistry
from ..plugins.plugin_config import PluginConfig
from ..plugins.plugin_manager import PluginManager
from ..plugins.plugin_loader import PluginLoader, PluginLoadResult


logger = logging.getLogger(__name__)


@dataclass
class InstallationResult:
    """
    Result of a plugin installation operation.

    Attributes:
        plugin_name: Name of the plugin
        success: Whether the operation succeeded
        version: Installed version
        error: Error message if operation failed
        installed_path: Path where plugin was installed
        dependencies_installed: List of dependencies that were installed
        warnings: List of warnings during installation
    """
    plugin_name: str
    success: bool
    version: Optional[str] = None
    error: Optional[str] = None
    installed_path: Optional[Path] = None
    dependencies_installed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plugin_name": self.plugin_name,
            "success": self.success,
            "version": self.version,
            "error": self.error,
            "installed_path": str(self.installed_path) if self.installed_path else None,
            "dependencies_installed": self.dependencies_installed,
            "warnings": self.warnings,
        }


@dataclass
class InstalledPluginInfo:
    """
    Information about an installed plugin.

    Attributes:
        name: Plugin name
        version: Installed version
        installed_at: Installation timestamp
        installed_path: Path where plugin is installed
        source: Original source URL/location
        checksum: File checksum for verification
        dependencies: List of plugin dependencies
        metadata: Full plugin metadata
    """
    name: str
    version: str
    installed_at: float
    installed_path: Path
    source: str
    checksum: str
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "installed_at": self.installed_at,
            "installed_path": str(self.installed_path),
            "source": self.source,
            "checksum": self.checksum,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InstalledPluginInfo":
        """Create from dictionary."""
        data["installed_path"] = Path(data["installed_path"])
        return cls(**data)


class PluginInstaller:
    """
    Manages plugin installation, uninstallation, and updates.

    Responsibilities:
    - Install plugins from various sources (git, local, remote)
    - Uninstall plugins and clean up resources
    - Update installed plugins to newer versions
    - Verify installation integrity
    - Resolve and install dependencies
    - Track installed plugins
    - Integration with PluginManager for post-install operations
    """

    def __init__(self,
                 config: PluginConfig = None,
                 marketplace_client: MarketplaceClient = None,
                 marketplace_registry: MarketplaceRegistry = None,
                 plugin_manager: PluginManager = None):
        """
        Initialize the plugin installer.

        Args:
            config: Optional plugin configuration
            marketplace_client: Optional marketplace client
            marketplace_registry: Optional marketplace registry
            plugin_manager: Optional plugin manager for loading installed plugins
        """
        self.config = config or PluginConfig()
        self.marketplace_client = marketplace_client or MarketplaceClient()
        self.marketplace_registry = marketplace_registry or MarketplaceRegistry()
        self.plugin_manager = plugin_manager or PluginManager(self.config)

        # Installation directories
        self.install_dir = self.config.third_party_plugins_dir
        self.install_dir.mkdir(parents=True, exist_ok=True)

        # Installed plugins registry
        self.registry_path = self.config.plugin_state_dir / "installed_plugins.json"
        self._installed_plugins: Dict[str, InstalledPluginInfo] = {}
        self._lock = threading.Lock()

        # Load installed plugins registry
        self._load_installed_registry()

        # Installation hooks
        self._pre_install_hooks: List[Callable] = []
        self._post_install_hooks: List[Callable] = []
        self._pre_uninstall_hooks: List[Callable] = []
        self._post_uninstall_hooks: List[Callable] = []

    def _load_installed_registry(self) -> None:
        """Load the installed plugins registry from disk."""
        if not self.registry_path.exists():
            logger.info("No installed plugins registry found, starting fresh")
            return

        try:
            with open(self.registry_path, 'r') as f:
                data = json.load(f)

            for plugin_name, plugin_data in data.items():
                self._installed_plugins[plugin_name] = InstalledPluginInfo.from_dict(plugin_data)

            logger.info(f"Loaded {len(self._installed_plugins)} installed plugins from registry")

        except Exception as e:
            logger.error(f"Failed to load installed plugins registry: {e}")

    def _save_installed_registry(self) -> None:
        """Save the installed plugins registry to disk."""
        try:
            self.config.ensure_directories()

            data = {
                name: info.to_dict()
                for name, info in self._installed_plugins.items()
            }

            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug("Saved installed plugins registry")

        except Exception as e:
            logger.error(f"Failed to save installed plugins registry: {e}")

    def install_plugin(self,
                      plugin_name: str,
                      source: str = None,
                      version: str = None,
                      force: bool = False) -> InstallationResult:
        """
        Install a plugin from the marketplace or a custom source.

        Args:
            plugin_name: Name of the plugin to install
            source: Optional source URL/path (uses marketplace if None)
            version: Optional version to install (uses latest if None)
            force: Force reinstallation if already installed

        Returns:
            InstallationResult with installation status
        """
        try:
            # Check if already installed
            if not force and self.is_plugin_installed(plugin_name):
                installed_info = self.get_installed_plugin(plugin_name)
                return InstallationResult(
                    plugin_name=plugin_name,
                    success=False,
                    error=f"Plugin '{plugin_name}' is already installed at version {installed_info.version}",
                    version=installed_info.version
                )

            # Get plugin info from marketplace if no source provided
            if source is None:
                plugin_info = self.marketplace_client.get_plugin_info(plugin_name)
                if not plugin_info:
                    return InstallationResult(
                        plugin_name=plugin_name,
                        success=False,
                        error=f"Plugin '{plugin_name}' not found in marketplace"
                    )
                source = plugin_info.source
                version = version or plugin_info.version

            # Run pre-install hooks
            self._run_pre_install_hooks(plugin_name, source)

            # Install based on source type
            if source.startswith(("http://", "https://")):
                result = self._install_from_url(plugin_name, source, version)
            elif source.startswith("git+") or source.endswith(".git"):
                result = self._install_from_git(plugin_name, source, version)
            elif source.startswith("/") or source.startswith("./") or source.startswith("../"):
                result = self._install_from_local(plugin_name, Path(source), version)
            else:
                # Try to interpret as marketplace plugin
                result = self._install_from_marketplace(plugin_name, version)

            if result.success:
                # Register installed plugin
                with self._lock:
                    self._installed_plugins[plugin_name] = InstalledPluginInfo(
                        name=plugin_name,
                        version=result.version,
                        installed_at=time.time(),
                        installed_path=result.installed_path,
                        source=source,
                        checksum=result.version,  # Use version as simple checksum
                    )
                    self._save_installed_registry()

                # Run post-install hooks
                self._run_post_install_hooks(plugin_name, result.installed_path)

                logger.info(f"Successfully installed plugin: {plugin_name} v{result.version}")

            return result

        except Exception as e:
            error_msg = f"Error installing plugin '{plugin_name}': {e}"
            logger.error(error_msg, exc_info=True)
            return InstallationResult(
                plugin_name=plugin_name,
                success=False,
                error=error_msg
            )

    def _install_from_marketplace(self,
                                  plugin_name: str,
                                  version: str = None) -> InstallationResult:
        """
        Install a plugin from the marketplace registry.

        Args:
            plugin_name: Name of the plugin
            version: Optional version to install

        Returns:
            InstallationResult
        """
        plugin_info = self.marketplace_client.get_plugin_info(plugin_name)

        if not plugin_info:
            return InstallationResult(
                plugin_name=plugin_name,
                success=False,
                error=f"Plugin '{plugin_name}' not found in marketplace"
            )

        # Use the source from marketplace info
        source = plugin_info.source
        target_version = version or plugin_info.version

        # Delegate to appropriate installation method based on source
        if source.startswith(("http://", "https://")):
            return self._install_from_url(plugin_name, source, target_version)
        elif source.startswith("git+") or source.endswith(".git"):
            return self._install_from_git(plugin_name, source, target_version)
        else:
            return InstallationResult(
                plugin_name=plugin_name,
                success=False,
                error=f"Unsupported marketplace source type: {source[:50]}..."
            )

    def _install_from_git(self,
                         plugin_name: str,
                         git_url: str,
                         version: str = None) -> InstallationResult:
        """
        Install a plugin from a Git repository.

        Args:
            plugin_name: Name of the plugin
            git_url: Git repository URL
            version: Optional version/tag/branch to checkout

        Returns:
            InstallationResult
        """
        warnings = []
        install_path = self.install_dir / plugin_name

        try:
            # Remove existing installation if forcing
            if install_path.exists():
                shutil.rmtree(install_path)

            # Clone the repository
            logger.info(f"Cloning plugin '{plugin_name}' from {git_url}")

            # Prepare git command
            if version:
                # Clone specific tag/branch
                cmd = ["git", "clone", "--branch", version, "--depth", "1", git_url, str(install_path)]
            else:
                # Clone latest
                cmd = ["git", "clone", git_url, str(install_path)]

            # Execute git clone
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                return InstallationResult(
                    plugin_name=plugin_name,
                    success=False,
                    error=f"Git clone failed: {result.stderr}"
                )

            # Verify installation
            if not install_path.exists():
                return InstallationResult(
                    plugin_name=plugin_name,
                    success=False,
                    error="Installation directory not created after git clone"
                )

            # Get version from git if not specified
            if not version:
                try:
                    # Try to get git tag
                    result = subprocess.run(
                        ["git", "describe", "--tags", "--abbrev=0"],
                        cwd=install_path,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        version = result.stdout.strip()
                    else:
                        version = "0.0.0"
                        warnings.append("Could not determine version from git tags")
                except Exception as e:
                    version = "0.0.0"
                    warnings.append(f"Error getting version from git: {e}")

            # Install dependencies
            dependencies_installed = self._install_dependencies(plugin_name, install_path)

            # Verify plugin can be loaded
            verification = self._verify_installation(plugin_name, install_path)
            if not verification["valid"]:
                # Clean up failed installation
                shutil.rmtree(install_path, ignore_errors=True)
                return InstallationResult(
                    plugin_name=plugin_name,
                    success=False,
                    error=f"Installation verification failed: {verification['error']}"
                )

            return InstallationResult(
                plugin_name=plugin_name,
                success=True,
                version=version,
                installed_path=install_path,
                dependencies_installed=dependencies_installed,
                warnings=warnings
            )

        except subprocess.TimeoutExpired:
            shutil.rmtree(install_path, ignore_errors=True)
            return InstallationResult(
                plugin_name=plugin_name,
                success=False,
                error="Git clone timed out after 5 minutes"
            )
        except Exception as e:
            shutil.rmtree(install_path, ignore_errors=True)
            return InstallationResult(
                plugin_name=plugin_name,
                success=False,
                error=f"Error installing from git: {e}"
            )

    def _install_from_url(self,
                         plugin_name: str,
                         url: str,
                         version: str = None) -> InstallationResult:
        """
        Install a plugin from a remote URL.

        Args:
            plugin_name: Name of the plugin
            url: URL to download plugin from
            version: Optional version string

        Returns:
            InstallationResult
        """
        install_path = self.install_dir / plugin_name
        temp_dir = None

        try:
            # Create temporary directory for download
            temp_dir = Path(tempfile.mkdtemp(prefix=f"plugin_{plugin_name}_"))

            # Download the plugin
            logger.info(f"Downloading plugin '{plugin_name}' from {url}")

            with urllib.request.urlopen(url, timeout=60) as response:
                # Check if it's a zip file or single file
                content_type = response.headers.get('Content-Type', '')
                filename = url.split('/')[-1]

                if filename.endswith('.zip') or 'zip' in content_type:
                    # Download and extract zip
                    zip_path = temp_dir / "plugin.zip"
                    with open(zip_path, 'wb') as f:
                        f.write(response.read())

                    # Extract zip
                    import zipfile
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)

                    # Find the plugin directory (might be in a subdirectory)
                    extracted_items = list(temp_dir.iterdir())
                    if len(extracted_items) == 1 and extracted_items[0].is_dir():
                        source_path = extracted_items[0]
                    else:
                        source_path = temp_dir

                else:
                    # Single file download
                    return InstallationResult(
                        plugin_name=plugin_name,
                        success=False,
                        error="Only ZIP archive downloads are currently supported"
                    )

            # Remove existing installation
            if install_path.exists():
                shutil.rmtree(install_path)

            # Copy plugin to installation directory
            shutil.copytree(source_path, install_path)

            # Verify installation
            verification = self._verify_installation(plugin_name, install_path)
            if not verification["valid"]:
                shutil.rmtree(install_path, ignore_errors=True)
                return InstallationResult(
                    plugin_name=plugin_name,
                    success=False,
                    error=f"Installation verification failed: {verification['error']}"
                )

            # Install dependencies
            dependencies_installed = self._install_dependencies(plugin_name, install_path)

            return InstallationResult(
                plugin_name=plugin_name,
                success=True,
                version=version or "0.0.0",
                installed_path=install_path,
                dependencies_installed=dependencies_installed
            )

        except urllib.error.URLError as e:
            return InstallationResult(
                plugin_name=plugin_name,
                success=False,
                error=f"Failed to download plugin: {e.reason}"
            )
        except Exception as e:
            return InstallationResult(
                plugin_name=plugin_name,
                success=False,
                error=f"Error installing from URL: {e}"
            )
        finally:
            # Clean up temporary directory
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _install_from_local(self,
                           plugin_name: str,
                           source_path: Path,
                           version: str = None) -> InstallationResult:
        """
        Install a plugin from a local directory.

        Args:
            plugin_name: Name of the plugin
            source_path: Local path to plugin directory
            version: Optional version string

        Returns:
            InstallationResult
        """
        install_path = self.install_dir / plugin_name

        try:
            # Verify source path exists
            if not source_path.exists():
                return InstallationResult(
                    plugin_name=plugin_name,
                    success=False,
                    error=f"Source path does not exist: {source_path}"
                )

            # Remove existing installation
            if install_path.exists():
                shutil.rmtree(install_path)

            # Copy plugin to installation directory
            shutil.copytree(source_path, install_path)

            # Verify installation
            verification = self._verify_installation(plugin_name, install_path)
            if not verification["valid"]:
                shutil.rmtree(install_path, ignore_errors=True)
                return InstallationResult(
                    plugin_name=plugin_name,
                    success=False,
                    error=f"Installation verification failed: {verification['error']}"
                )

            # Install dependencies
            dependencies_installed = self._install_dependencies(plugin_name, install_path)

            return InstallationResult(
                plugin_name=plugin_name,
                success=True,
                version=version or "0.0.0",
                installed_path=install_path,
                dependencies_installed=dependencies_installed
            )

        except Exception as e:
            shutil.rmtree(install_path, ignore_errors=True)
            return InstallationResult(
                plugin_name=plugin_name,
                success=False,
                error=f"Error installing from local path: {e}"
            )

    def _verify_installation(self, plugin_name: str, install_path: Path) -> Dict[str, Any]:
        """
        Verify that a plugin installation is valid.

        Args:
            plugin_name: Name of the plugin
            install_path: Path where plugin is installed

        Returns:
            Dictionary with 'valid' key and optional 'error' key
        """
        # Check if directory exists
        if not install_path.exists():
            return {"valid": False, "error": "Installation directory does not exist"}

        # Check for plugin.py entry point
        plugin_file = install_path / "plugin.py"
        if not plugin_file.exists():
            return {"valid": False, "error": "plugin.py not found in installation directory"}

        # Try to load the plugin
        try:
            loader = PluginLoader(self.config)
            result = loader.load_plugin_from_path(install_path)

            if not result.success:
                return {"valid": False, "error": f"Plugin load failed: {result.error}"}

            return {"valid": True}

        except Exception as e:
            return {"valid": False, "error": f"Verification error: {e}"}

    def _install_dependencies(self, plugin_name: str, install_path: Path) -> List[str]:
        """
        Install plugin dependencies.

        Args:
            plugin_name: Name of the plugin
            install_path: Path where plugin is installed

        Returns:
            List of dependency plugin names that were installed
        """
        installed_deps = []

        try:
            # Load plugin metadata to get dependencies
            loader = PluginLoader(self.config)
            result = loader.load_plugin_from_path(install_path)

            if not result.success or not result.plugin:
                logger.warning(f"Could not load plugin '{plugin_name}' to check dependencies")
                return installed_deps

            metadata = result.plugin.get_metadata()
            dependencies = metadata.dependencies or []

            # Install each dependency
            for dep_name in dependencies:
                if self.is_plugin_installed(dep_name):
                    logger.info(f"Dependency '{dep_name}' already installed")
                    continue

                logger.info(f"Installing dependency '{dep_name}' for plugin '{plugin_name}'")

                # Try to install from marketplace
                dep_result = self.install_plugin(dep_name)

                if dep_result.success:
                    installed_deps.append(dep_name)
                    logger.info(f"Successfully installed dependency '{dep_name}'")
                else:
                    logger.warning(f"Failed to install dependency '{dep_name}': {dep_result.error}")

        except Exception as e:
            logger.error(f"Error installing dependencies for '{plugin_name}': {e}")

        return installed_deps

    def uninstall_plugin(self, plugin_name: str, force: bool = False) -> InstallationResult:
        """
        Uninstall a plugin.

        Args:
            plugin_name: Name of the plugin to uninstall
            force: Force uninstall even if verification fails

        Returns:
            InstallationResult with uninstallation status
        """
        try:
            # Check if plugin is installed
            if not self.is_plugin_installed(plugin_name):
                return InstallationResult(
                    plugin_name=plugin_name,
                    success=False,
                    error=f"Plugin '{plugin_name}' is not installed"
                )

            installed_info = self.get_installed_plugin(plugin_name)
            install_path = installed_info.installed_path

            # Run pre-uninstall hooks
            self._run_pre_uninstall_hooks(plugin_name, install_path)

            # Unload plugin if loaded
            if self.plugin_manager.is_plugin_loaded(plugin_name):
                logger.info(f"Unloading plugin '{plugin_name}' before uninstallation")
                self.plugin_manager.unload_plugin(plugin_name)

            # Remove plugin files
            if install_path.exists():
                shutil.rmtree(install_path)
                logger.info(f"Removed plugin files from {install_path}")
            else:
                logger.warning(f"Plugin installation path not found: {install_path}")

            # Remove from registry
            with self._lock:
                if plugin_name in self._installed_plugins:
                    del self._installed_plugins[plugin_name]
                    self._save_installed_registry()

            # Run post-uninstall hooks
            self._run_post_uninstall_hooks(plugin_name)

            logger.info(f"Successfully uninstalled plugin: {plugin_name}")

            return InstallationResult(
                plugin_name=plugin_name,
                success=True,
                version=installed_info.version
            )

        except Exception as e:
            error_msg = f"Error uninstalling plugin '{plugin_name}': {e}"
            logger.error(error_msg, exc_info=True)

            if not force:
                return InstallationResult(
                    plugin_name=plugin_name,
                    success=False,
                    error=error_msg
                )
            else:
                # Force: remove from registry even if cleanup failed
                with self._lock:
                    if plugin_name in self._installed_plugins:
                        del self._installed_plugins[plugin_name]
                        self._save_installed_registry()

                return InstallationResult(
                    plugin_name=plugin_name,
                    success=True,
                    warnings=["Forced uninstallation: some files may remain"]
                )

    def update_plugin(self, plugin_name: str) -> InstallationResult:
        """
        Update a plugin to the latest version.

        Args:
            plugin_name: Name of the plugin to update

        Returns:
            InstallationResult with update status
        """
        try:
            # Check if plugin is installed
            if not self.is_plugin_installed(plugin_name):
                return InstallationResult(
                    plugin_name=plugin_name,
                    success=False,
                    error=f"Plugin '{plugin_name}' is not installed"
                )

            installed_info = self.get_installed_plugin(plugin_name)
            current_version = installed_info.version
            source = installed_info.source

            # Get latest version from marketplace
            marketplace_info = self.marketplace_client.get_plugin_info(plugin_name)
            if marketplace_info and marketplace_info.version != current_version:
                logger.info(f"Updating plugin '{plugin_name}' from {current_version} to {marketplace_info.version}")

                # Uninstall current version
                uninstall_result = self.uninstall_plugin(plugin_name)
                if not uninstall_result.success:
                    return InstallationResult(
                        plugin_name=plugin_name,
                        success=False,
                        error=f"Failed to uninstall current version: {uninstall_result.error}"
                    )

                # Install new version
                install_result = self.install_plugin(plugin_name, source, marketplace_info.version)

                return install_result
            else:
                return InstallationResult(
                    plugin_name=plugin_name,
                    success=False,
                    error=f"Plugin '{plugin_name}' is already up to date at version {current_version}"
                )

        except Exception as e:
            error_msg = f"Error updating plugin '{plugin_name}': {e}"
            logger.error(error_msg, exc_info=True)
            return InstallationResult(
                plugin_name=plugin_name,
                success=False,
                error=error_msg
            )

    def is_plugin_installed(self, plugin_name: str) -> bool:
        """
        Check if a plugin is installed.

        Args:
            plugin_name: Name of the plugin to check

        Returns:
            True if plugin is installed, False otherwise
        """
        with self._lock:
            return plugin_name in self._installed_plugins

    def get_installed_plugin(self, plugin_name: str) -> Optional[InstalledPluginInfo]:
        """
        Get information about an installed plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            InstalledPluginInfo or None if not found
        """
        with self._lock:
            return self._installed_plugins.get(plugin_name)

    def list_installed_plugins(self) -> List[InstalledPluginInfo]:
        """
        List all installed plugins.

        Returns:
            List of InstalledPluginInfo objects
        """
        with self._lock:
            return list(self._installed_plugins.values())

    def get_installed_plugin_path(self, plugin_name: str) -> Optional[Path]:
        """
        Get the installation path for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Path to plugin installation directory or None if not installed
        """
        installed_info = self.get_installed_plugin(plugin_name)
        return installed_info.installed_path if installed_info else None

    def load_installed_plugin(self, plugin_name: str) -> PluginLoadResult:
        """
        Load an installed plugin using the plugin manager.

        Args:
            plugin_name: Name of the installed plugin to load

        Returns:
            PluginLoadResult
        """
        if not self.is_plugin_installed(plugin_name):
            return PluginLoadResult(
                plugin_name=plugin_name,
                success=False,
                error=f"Plugin '{plugin_name}' is not installed"
            )

        install_path = self.get_installed_plugin_path(plugin_name)

        if not install_path or not install_path.exists():
            return PluginLoadResult(
                plugin_name=plugin_name,
                success=False,
                error=f"Plugin installation path not found: {install_path}"
            )

        return self.plugin_manager.load_plugin_from_path(str(install_path))

    def register_pre_install_hook(self, hook: Callable) -> None:
        """
        Register a function to be called before plugin installation.

        Args:
            hook: Callable function(plugin_name, source)
        """
        self._pre_install_hooks.append(hook)

    def register_post_install_hook(self, hook: Callable) -> None:
        """
        Register a function to be called after plugin installation.

        Args:
            hook: Callable function(plugin_name, install_path)
        """
        self._post_install_hooks.append(hook)

    def register_pre_uninstall_hook(self, hook: Callable) -> None:
        """
        Register a function to be called before plugin uninstallation.

        Args:
            hook: Callable function(plugin_name, install_path)
        """
        self._pre_uninstall_hooks.append(hook)

    def register_post_uninstall_hook(self, hook: Callable) -> None:
        """
        Register a function to be called after plugin uninstallation.

        Args:
            hook: Callable function(plugin_name)
        """
        self._post_uninstall_hooks.append(hook)

    def _run_pre_install_hooks(self, plugin_name: str, source: str) -> None:
        """Run pre-install hooks."""
        for hook in self._pre_install_hooks:
            try:
                hook(plugin_name, source)
            except Exception as e:
                logger.error(f"Error in pre-install hook: {e}")

    def _run_post_install_hooks(self, plugin_name: str, install_path: Path) -> None:
        """Run post-install hooks."""
        for hook in self._post_install_hooks:
            try:
                hook(plugin_name, install_path)
            except Exception as e:
                logger.error(f"Error in post-install hook: {e}")

    def _run_pre_uninstall_hooks(self, plugin_name: str, install_path: Path) -> None:
        """Run pre-uninstall hooks."""
        for hook in self._pre_uninstall_hooks:
            try:
                hook(plugin_name, install_path)
            except Exception as e:
                logger.error(f"Error in pre-uninstall hook: {e}")

    def _run_post_uninstall_hooks(self, plugin_name: str) -> None:
        """Run post-uninstall hooks."""
        for hook in self._post_uninstall_hooks:
            try:
                hook(plugin_name)
            except Exception as e:
                logger.error(f"Error in post-uninstall hook: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get installer statistics.

        Returns:
            Dictionary with installer statistics
        """
        installed = self.list_installed_plugins()

        return {
            "total_installed": len(installed),
            "install_directory": str(self.install_dir),
            "plugins": [
                {
                    "name": info.name,
                    "version": info.version,
                    "installed_at": info.installed_at,
                    "source": info.source,
                }
                for info in installed
            ],
        }
