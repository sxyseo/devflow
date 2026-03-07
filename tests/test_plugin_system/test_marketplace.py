"""
End-to-end test for installing a plugin from the marketplace.

This test verifies the complete marketplace workflow:
1. Query marketplace for available plugins
2. Install a plugin from the marketplace
3. Verify plugin is loaded and functional
4. Uninstall the plugin
5. Verify cleanup is complete
"""

import os
import sys
import tempfile
import shutil
import json
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from devflow.marketplace.marketplace_client import MarketplaceClient, MarketplacePluginInfo
from devflow.marketplace.plugin_installer import PluginInstaller, InstallationResult
from devflow.marketplace.marketplace_registry import MarketplaceRegistry
from devflow.plugins.plugin_manager import PluginManager
from devflow.plugins.plugin_config import PluginConfig
from devflow.plugins.agent_plugin import AgentPlugin
from devflow.plugins.base import PluginMetadata


class TestMarketplaceE2E:
    """End-to-end test suite for marketplace plugin installation."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        temp_dir = tempfile.mkdtemp(prefix="test_marketplace_")
        state_dir = Path(temp_dir) / "state"
        install_dir = Path(temp_dir) / "plugins"
        cache_dir = Path(temp_dir) / "cache"

        state_dir.mkdir(parents=True)
        install_dir.mkdir(parents=True)
        cache_dir.mkdir(parents=True)

        yield {
            "temp_dir": temp_dir,
            "state_dir": state_dir,
            "install_dir": install_dir,
            "cache_dir": cache_dir
        }

        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def plugin_config(self, temp_dirs):
        """Create a plugin config for testing."""
        config = PluginConfig()
        config.plugin_state_dir = temp_dirs["state_dir"]
        config.third_party_plugins_dir = temp_dirs["install_dir"]
        config.builtin_plugins_dir = Path(temp_dirs["temp_dir"]) / "builtin"
        config.user_plugins_dir = Path(temp_dirs["temp_dir"]) / "user"
        config.ensure_directories()
        return config

    @pytest.fixture
    def marketplace_client(self, temp_dirs):
        """Create a marketplace client for testing."""
        # Use a custom registry for testing
        test_registry_path = Path(__file__).parent.parent.parent / "devflow" / "marketplace" / "registry.json"

        client = MarketplaceClient(cache_dir=temp_dirs["cache_dir"])
        return client

    @pytest.fixture
    def marketplace_registry(self):
        """Create a marketplace registry for testing."""
        return MarketplaceRegistry()

    @pytest.fixture
    def plugin_manager(self, plugin_config):
        """Create a plugin manager for testing."""
        return PluginManager(config=plugin_config)

    @pytest.fixture
    def plugin_installer(self, plugin_config, marketplace_client, marketplace_registry, plugin_manager):
        """Create a plugin installer for testing."""
        return PluginInstaller(
            config=plugin_config,
            marketplace_client=marketplace_client,
            marketplace_registry=marketplace_registry,
            plugin_manager=plugin_manager
        )

    def test_query_marketplace_for_plugins(self, marketplace_client):
        """
        Test Step 1: Query marketplace for available plugins.

        Verifies:
        - Marketplace client can discover plugins
        - Plugin information is retrieved correctly
        - Local registry plugins are available
        """
        # Discover all plugins
        plugins = marketplace_client.discover_plugins()

        # Verify plugins were discovered
        assert len(plugins) > 0, "Should discover at least one plugin"

        # Verify plugin structure
        plugin = plugins[0]
        assert isinstance(plugin, MarketplacePluginInfo), "Plugin should be MarketplacePluginInfo instance"
        assert plugin.name, "Plugin should have a name"
        assert plugin.version, "Plugin should have a version"
        assert plugin.plugin_type in ["agent", "task_source", "integration"], \
            "Plugin type should be valid"

        # Verify expected example plugins exist
        plugin_names = [p.name for p in plugins]
        assert "custom-agent" in plugin_names, "custom-agent plugin should be available"
        assert "custom-task-source" in plugin_names, "custom-task-source plugin should be available"

        # Get marketplace statistics
        stats = marketplace_client.get_statistics()
        assert stats["total_plugins"] > 0, "Should have plugins in statistics"
        assert "plugins_by_type" in stats, "Statistics should include type breakdown"

    def test_get_plugin_info_from_marketplace(self, marketplace_client):
        """
        Test Step 2: Get specific plugin information from marketplace.

        Verifies:
        - Can query for specific plugin by name
        - Plugin metadata is complete
        - Source information is available
        """
        # Get custom-agent plugin info
        plugin_info = marketplace_client.get_plugin_info("custom-agent")

        # Verify plugin info was retrieved
        assert plugin_info is not None, "Plugin info should be retrievable"
        assert plugin_info.name == "custom-agent", "Plugin name should match"
        assert plugin_info.version == "1.0.0", "Plugin version should match"
        assert plugin_info.plugin_type == "agent", "Plugin type should be 'agent'"
        assert plugin_info.source, "Plugin should have a source"
        assert plugin_info.source.startswith("local:"), "Source should be local for test plugin"

        # Verify metadata
        assert plugin_info.description, "Plugin should have description"
        assert plugin_info.author, "Plugin should have author"
        assert len(plugin_info.keywords) > 0, "Plugin should have keywords"

    def test_search_plugins_in_marketplace(self, marketplace_client):
        """
        Test Step 3: Search for plugins in marketplace.

        Verifies:
        - Can search plugins by query
        - Can filter plugins by type
        - Search results are relevant
        """
        # Search for agent plugins
        agent_plugins = marketplace_client.search_plugins("agent", plugin_type="agent")

        # Verify search results
        assert len(agent_plugins) > 0, "Should find agent plugins"

        # Verify all results are agent plugins
        for plugin in agent_plugins:
            assert plugin.plugin_type == "agent", "Search results should match type filter"

        # Search for custom agent specifically
        custom_plugins = marketplace_client.search_plugins("custom")
        assert len(custom_plugins) > 0, "Should find plugins with 'custom' in name/description"

        # Verify plugin name matches
        plugin_names = [p.name for p in custom_plugins]
        assert any("custom" in name.lower() for name in plugin_names), \
            "Search should find plugins with 'custom' in name"

    def test_install_local_plugin_from_marketplace(self, plugin_installer, marketplace_client):
        """
        Test Step 4: Install a local plugin from marketplace.

        Verifies:
        - Plugin can be installed from marketplace source
        - Installation result is successful
        - Plugin files are copied to install directory
        - Plugin appears in installed plugins list
        """
        # Get plugin info from marketplace
        plugin_info = marketplace_client.get_plugin_info("custom-agent")
        assert plugin_info is not None, "Plugin should exist in marketplace"

        # Parse local source path
        # Source format: "local:examples/plugins/custom_agent"
        source_path = plugin_info.source.replace("local:", "")
        source_path = Path(__file__).parent.parent.parent / source_path

        # Verify source exists
        assert source_path.exists(), f"Source path should exist: {source_path}"

        # Install plugin from local path
        result = plugin_installer.install_plugin(
            "custom-agent",
            source=str(source_path)
        )

        # Verify installation succeeded
        assert result.success, f"Installation should succeed: {result.error}"
        assert result.plugin_name == "custom-agent", "Plugin name should match"
        assert result.installed_path is not None, "Installation path should be set"
        assert result.installed_path.exists(), "Installation directory should exist"

        # Verify plugin appears in installed list
        assert plugin_installer.is_plugin_installed("custom-agent"), \
            "Plugin should appear in installed list"

        installed_info = plugin_installer.get_installed_plugin("custom-agent")
        assert installed_info is not None, "Should retrieve installed plugin info"
        assert installed_info.name == "custom-agent", "Installed plugin name should match"
        assert installed_info.installed_path == result.installed_path, \
            "Installed path should match installation result"

    def test_load_installed_plugin(self, plugin_installer, plugin_manager, marketplace_client):
        """
        Test Step 5: Load an installed plugin.

        Verifies:
        - Installed plugin can be loaded
        - Plugin is registered in plugin manager
        - Plugin metadata is accessible
        """
        # Get plugin info and install
        plugin_info = marketplace_client.get_plugin_info("custom-agent")
        source_path = plugin_info.source.replace("local:", "")
        source_path = Path(__file__).parent.parent.parent / source_path

        install_result = plugin_installer.install_plugin(
            "custom-agent",
            source=str(source_path)
        )

        assert install_result.success, "Plugin should be installed"

        # Load the installed plugin
        load_result = plugin_installer.load_installed_plugin("custom-agent")

        # Verify plugin loaded successfully
        assert load_result.success, f"Plugin should load: {load_result.error}"
        assert load_result.plugin_name == "custom-agent", "Loaded plugin name should match"

        # Verify plugin is in plugin manager
        assert plugin_manager.is_plugin_loaded("custom-agent"), \
            "Plugin should be loaded in plugin manager"

        # Verify plugin metadata
        metadata = plugin_manager.get_plugin_metadata("custom-agent")
        assert metadata is not None, "Plugin metadata should be available"
        assert metadata.name == "custom-agent", "Metadata name should match"
        assert metadata.plugin_type == "agent", "Metadata type should be 'agent'"

    def test_verify_installed_plugin_functionality(self, plugin_installer, plugin_manager, marketplace_client):
        """
        Test Step 6: Verify installed plugin is functional.

        Verifies:
        - Plugin can be initialized
        - Plugin can be started
        - Plugin agents can be registered
        """
        # Install plugin
        plugin_info = marketplace_client.get_plugin_info("custom-agent")
        source_path = plugin_info.source.replace("local:", "")
        source_path = Path(__file__).parent.parent.parent / source_path

        install_result = plugin_installer.install_plugin(
            "custom-agent",
            source=str(source_path)
        )

        assert install_result.success, "Plugin should be installed"

        # Load plugin
        load_result = plugin_installer.load_installed_plugin("custom-agent")
        assert load_result.success, "Plugin should load"

        # Initialize plugin
        init_success = plugin_manager.initialize_plugin("custom-agent")
        assert init_success, "Plugin should initialize"

        # Verify plugin state
        plugin_state = plugin_manager.get_plugin_state("custom-agent")
        assert plugin_state is not None, "Plugin state should be available"
        assert plugin_state.initialized, "Plugin should be initialized"

        # Start plugin
        start_success = plugin_manager.start_plugin("custom-agent")
        assert start_success, "Plugin should start"

        # Verify plugin is running
        assert plugin_manager.is_plugin_running("custom-agent"), \
            "Plugin should be running"

        # Get plugin info
        info = plugin_manager.get_plugin_info("custom-agent")
        assert info is not None, "Plugin info should be available"
        assert info["metadata"]["name"] == "custom-agent", "Info should match"

    def test_uninstall_plugin(self, plugin_installer, plugin_manager, marketplace_client):
        """
        Test Step 7: Uninstall a plugin.

        Verifies:
        - Plugin can be uninstalled
        - Plugin files are removed
        - Plugin is removed from registry
        - Plugin is unloaded if loaded
        """
        # Install and load plugin
        plugin_info = marketplace_client.get_plugin_info("custom-agent")
        source_path = plugin_info.source.replace("local:", "")
        source_path = Path(__file__).parent.parent.parent / source_path

        install_result = plugin_installer.install_plugin(
            "custom-agent",
            source=str(source_path)
        )
        assert install_result.success, "Plugin should be installed"

        load_result = plugin_installer.load_installed_plugin("custom-agent")
        assert load_result.success, "Plugin should load"

        installed_path = install_result.installed_path

        # Uninstall plugin
        uninstall_result = plugin_installer.uninstall_plugin("custom-agent")

        # Verify uninstallation succeeded
        assert uninstall_result.success, f"Uninstallation should succeed: {uninstall_result.error}"
        assert uninstall_result.plugin_name == "custom-agent", "Plugin name should match"

        # Verify plugin is not in installed list
        assert not plugin_installer.is_plugin_installed("custom-agent"), \
            "Plugin should not appear in installed list"

        assert plugin_installer.get_installed_plugin("custom-agent") is None, \
            "Should not retrieve installed plugin info"

        # Verify files are removed
        assert not installed_path.exists(), \
            "Installation directory should be removed"

        # Verify plugin is unloaded from plugin manager
        assert not plugin_manager.is_plugin_loaded("custom-agent"), \
            "Plugin should be unloaded from plugin manager"

    def test_complete_marketplace_workflow(self, plugin_installer, plugin_manager, marketplace_client):
        """
        Complete end-to-end test of the marketplace workflow.

        This test runs through the entire lifecycle:
        1. Query marketplace for plugins
        2. Get plugin info
        3. Install plugin
        4. Load plugin
        5. Verify plugin functionality
        6. Uninstall plugin
        7. Verify cleanup
        """
        # Step 1: Query marketplace
        plugins = marketplace_client.discover_plugins()
        assert len(plugins) > 0, "Should discover plugins"
        plugin_names = [p.name for p in plugins]
        assert "custom-agent" in plugin_names, "custom-agent should be available"

        # Step 2: Get plugin info
        plugin_info = marketplace_client.get_plugin_info("custom-agent")
        assert plugin_info is not None, "Should get plugin info"
        assert plugin_info.name == "custom-agent", "Plugin name should match"

        # Step 3: Install plugin
        source_path = plugin_info.source.replace("local:", "")
        source_path = Path(__file__).parent.parent.parent / source_path

        install_result = plugin_installer.install_plugin(
            "custom-agent",
            source=str(source_path)
        )
        assert install_result.success, "Installation should succeed"
        assert plugin_installer.is_plugin_installed("custom-agent"), \
            "Plugin should be installed"

        installed_path = install_result.installed_path
        assert installed_path.exists(), "Installation directory should exist"

        # Step 4: Load plugin
        load_result = plugin_installer.load_installed_plugin("custom-agent")
        assert load_result.success, "Plugin should load"
        assert plugin_manager.is_plugin_loaded("custom-agent"), \
            "Plugin should be loaded"

        # Step 5: Verify plugin functionality
        init_success = plugin_manager.initialize_plugin("custom-agent")
        assert init_success, "Plugin should initialize"

        start_success = plugin_manager.start_plugin("custom-agent")
        assert start_success, "Plugin should start"

        assert plugin_manager.is_plugin_running("custom-agent"), \
            "Plugin should be running"

        metadata = plugin_manager.get_plugin_metadata("custom-agent")
        assert metadata.name == "custom-agent", "Metadata should match"

        # Step 6: Uninstall plugin
        uninstall_result = plugin_installer.uninstall_plugin("custom-agent")
        assert uninstall_result.success, "Uninstallation should succeed"

        # Step 7: Verify cleanup
        assert not plugin_installer.is_plugin_installed("custom-agent"), \
            "Plugin should not be installed"

        assert not plugin_manager.is_plugin_loaded("custom-agent"), \
            "Plugin should be unloaded"

        assert not installed_path.exists(), \
            "Installation directory should be removed"

        # Verify installer statistics
        stats = plugin_installer.get_statistics()
        assert stats["total_installed"] == 0, "No plugins should be installed"

    def test_install_multiple_plugins(self, plugin_installer, marketplace_client):
        """
        Test installing multiple plugins from marketplace.

        Verifies:
        - Multiple plugins can be installed
        - Each plugin is tracked separately
        - All plugins can be managed independently
        """
        # Install custom-agent
        agent_plugin_info = marketplace_client.get_plugin_info("custom-agent")
        agent_source = agent_plugin_info.source.replace("local:", "")
        agent_source = Path(__file__).parent.parent.parent / agent_source

        result1 = plugin_installer.install_plugin(
            "custom-agent",
            source=str(agent_source)
        )
        assert result1.success, "Agent plugin should install"

        # Install custom-task-source
        task_plugin_info = marketplace_client.get_plugin_info("custom-task-source")
        task_source = task_plugin_info.source.replace("local:", "")
        task_source = Path(__file__).parent.parent.parent / task_source

        result2 = plugin_installer.install_plugin(
            "custom-task-source",
            source=str(task_source)
        )
        assert result2.success, "Task source plugin should install"

        # Verify both are installed
        assert plugin_installer.is_plugin_installed("custom-agent"), \
            "Agent plugin should be installed"
        assert plugin_installer.is_plugin_installed("custom-task-source"), \
            "Task source plugin should be installed"

        # List installed plugins
        installed = plugin_installer.list_installed_plugins()
        installed_names = [p.name for p in installed]
        assert "custom-agent" in installed_names, "Agent plugin should be in list"
        assert "custom-task-source" in installed_names, "Task source plugin should be in list"
        assert len(installed) == 2, "Should have exactly 2 plugins"

        # Uninstall both
        uninstall1 = plugin_installer.uninstall_plugin("custom-agent")
        uninstall2 = plugin_installer.uninstall_plugin("custom-task-source")

        assert uninstall1.success, "Agent plugin should uninstall"
        assert uninstall2.success, "Task source plugin should uninstall"

        # Verify cleanup
        assert len(plugin_installer.list_installed_plugins()) == 0, \
            "All plugins should be uninstalled"

    def test_marketplace_error_handling(self, plugin_installer, marketplace_client):
        """
        Test error handling in marketplace operations.

        Verifies:
        - Installing non-existent plugin fails gracefully
        - Uninstalling non-installed plugin fails gracefully
        - System remains stable after errors
        """
        # Try to install non-existent plugin
        result = plugin_installer.install_plugin("non-existent-plugin")
        assert not result.success, "Installation should fail"
        assert result.error is not None, "Should have error message"

        # Try to uninstall non-installed plugin
        result = plugin_installer.uninstall_plugin("non-existent-plugin")
        assert not result.success, "Uninstallation should fail"
        assert result.error is not None, "Should have error message"

        # Verify system is still functional
        plugins = marketplace_client.discover_plugins()
        assert len(plugins) > 0, "Marketplace client should still work"

        stats = plugin_installer.get_statistics()
        assert stats is not None, "Should still get statistics"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
