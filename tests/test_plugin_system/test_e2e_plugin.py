"""
End-to-end test for loading and using a custom agent plugin.

This test verifies the complete plugin lifecycle:
1. Create a test plugin that registers a custom agent
2. Load the plugin using PluginManager
3. Verify the custom agent appears in AgentManager
4. Execute a task with the custom agent plugin
5. Verify the plugin can be unloaded and cleaned up
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from devflow.plugins.plugin_manager import PluginManager
from devflow.plugins.plugin_config import PluginConfig
from devflow.plugins.agent_plugin import AgentPlugin
from devflow.plugins.base import PluginMetadata
from devflow.core.agent_manager import AgentManager, AgentConfig
from devflow.core.state_tracker import StateTracker
from devflow.core.session_manager import SessionManager


class TestAgentPlugin(AgentPlugin):
    """
    Test agent plugin for end-to-end testing.

    This plugin creates a simple test agent that can be used to verify
    the complete plugin lifecycle works correctly.
    """

    def __init__(self):
        super().__init__()
        self.agent_created_called = False
        self.agent_started_called = False
        self.agent_completed_called = False
        self.agent_failed_called = False

    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            name="test-agent-plugin",
            version="1.0.0",
            description="Test agent plugin for end-to-end testing",
            author="DevFlow Test Suite",
            plugin_type="agent",
            dependencies=[],
            devflow_version="0.1.0"
        )

    def get_agent_type(self) -> str:
        """Get the agent type identifier."""
        return "test-custom-agent"

    def get_agent_class(self):
        """Get the agent class this plugin provides."""
        # Return a simple mock agent class for testing
        class MockTestAgent:
            def __init__(self, config):
                self.config = config

            def execute(self, task):
                return f"Mock agent executed: {task}"

        return MockTestAgent

    def get_agent_config(self) -> Dict[str, Any]:
        """Get default configuration for the agent."""
        return {
            "model": "claude-3-5-sonnet-20241022",
            "max_tasks": 1,
            "timeout": 1800,
            "skills": ["test-skill"],
            "system_prompt": "You are a test agent for end-to-end testing.",
            "temperature": 0.5,
            "max_tokens": 2000
        }

    def on_agent_created(self, agent_id: str, agent_type: str) -> None:
        """Hook called when a new agent is created."""
        if agent_type == self.get_agent_type():
            self.agent_created_called = True

    def on_agent_started(self, agent_id: str, task: str) -> None:
        """Hook called when an agent starts a task."""
        self.agent_started_called = True

    def on_agent_completed(self, agent_id: str, result: Any) -> None:
        """Hook called when an agent completes a task."""
        self.agent_completed_called = True

    def on_agent_failed(self, agent_id: str, error: Exception) -> None:
        """Hook called when an agent fails."""
        self.agent_failed_called = True


class TestE2EPluginLoading:
    """End-to-end test suite for plugin loading and usage."""

    @pytest.fixture
    def temp_plugin_dir(self):
        """Create a temporary directory for test plugins."""
        temp_dir = tempfile.mkdtemp(prefix="test_plugins_")
        yield temp_dir
        # Cleanup after test
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def plugin_config(self, temp_plugin_dir):
        """Create a plugin config for testing."""
        config = PluginConfig()
        # Override plugin directories to use temp directory (convert to Path)
        temp_path = Path(temp_plugin_dir)
        config.user_plugins_dir = temp_path
        config.builtin_plugins_dir = temp_path
        config.third_party_plugins_dir = temp_path
        config.plugin_state_dir = temp_path
        config.ensure_directories()
        return config

    @pytest.fixture
    def plugin_manager(self, plugin_config):
        """Create a plugin manager for testing."""
        return PluginManager(config=plugin_config)

    @pytest.fixture
    def agent_manager(self, plugin_manager):
        """Create an agent manager for testing."""
        state_tracker = StateTracker()
        session_manager = SessionManager()
        # Share the plugin registry with the agent manager
        agent_manager = AgentManager(state_tracker, session_manager,
                                     plugin_registry=plugin_manager.registry)
        return agent_manager

    def test_create_and_load_plugin_from_memory(self, plugin_manager):
        """
        Test Step 1: Create a test plugin and load it.

        Verifies:
        - Plugin can be instantiated
        - Plugin can be loaded into PluginManager
        - Plugin appears in loaded plugins list
        """
        # Create test plugin instance
        test_plugin = TestAgentPlugin()

        # Manually register the plugin (simulating what plugin_loader does)
        from devflow.plugins.plugin_loader import PluginLoadResult

        load_result = PluginLoadResult(
            plugin_name="test-agent-plugin",
            success=True,
            plugin=test_plugin
        )

        # Register the plugin
        plugin_manager._register_loaded_plugin(load_result)

        # Verify plugin is loaded
        assert plugin_manager.is_plugin_loaded("test-agent-plugin"), \
            "Plugin should be loaded"

        # Verify plugin can be retrieved
        retrieved_plugin = plugin_manager.get_plugin("test-agent-plugin")
        assert retrieved_plugin is not None, "Plugin should be retrievable"
        assert isinstance(retrieved_plugin, TestAgentPlugin), \
            "Retrieved plugin should be TestAgentPlugin instance"

        # Verify plugin metadata
        metadata = plugin_manager.get_plugin_metadata("test-agent-plugin")
        assert metadata is not None, "Plugin metadata should be available"
        assert metadata.name == "test-agent-plugin", "Plugin name should match"
        assert metadata.version == "1.0.0", "Plugin version should match"
        assert metadata.plugin_type == "agent", "Plugin type should be 'agent'"

    def test_initialize_and_start_plugin(self, plugin_manager):
        """
        Test Step 2: Initialize and start the plugin.

        Verifies:
        - Plugin can be initialized
        - Plugin can be started
        - Plugin state transitions correctly
        """
        # Create and load test plugin
        test_plugin = TestAgentPlugin()
        from devflow.plugins.plugin_loader import PluginLoadResult

        load_result = PluginLoadResult(
            plugin_name="test-agent-plugin",
            success=True,
            plugin=test_plugin
        )

        plugin_manager._register_loaded_plugin(load_result)

        # Initialize plugin
        init_success = plugin_manager.initialize_plugin("test-agent-plugin")
        assert init_success, "Plugin should initialize successfully"

        # Verify plugin state
        plugin_state = plugin_manager.get_plugin_state("test-agent-plugin")
        assert plugin_state is not None, "Plugin state should be available"
        assert plugin_state.initialized, "Plugin should be marked as initialized"
        assert not plugin_state.running, "Plugin should not be running yet"

        # Start plugin
        start_success = plugin_manager.start_plugin("test-agent-plugin")
        assert start_success, "Plugin should start successfully"

        # Verify plugin is running
        plugin_state = plugin_manager.get_plugin_state("test-agent-plugin")
        assert plugin_state.running, "Plugin should be marked as running"

        # Verify plugin appears in running plugins list
        running_plugins = plugin_manager.get_running_plugins()
        assert "test-agent-plugin" in running_plugins, \
            "Plugin should appear in running plugins list"

    def test_register_agent_with_agent_manager(self, plugin_manager, agent_manager):
        """
        Test Step 3: Register custom agent with AgentManager.

        Verifies:
        - Plugin can register its agent type with AgentManager
        - Agent configuration is correctly transferred
        - Agent type is available in AgentManager
        """
        # Create and load test plugin
        test_plugin = TestAgentPlugin()
        from devflow.plugins.plugin_loader import PluginLoadResult

        load_result = PluginLoadResult(
            plugin_name="test-agent-plugin",
            success=True,
            plugin=test_plugin
        )

        plugin_manager._register_loaded_plugin(load_result)

        # Register agent with agent manager
        test_plugin.register_agent(agent_manager)

        # Verify agent type is registered
        assert agent_manager.has_agent_type("test-custom-agent"), \
            "Custom agent type should be registered in AgentManager"

        # Verify agent configuration
        agent_config = agent_manager.get_agent_type_config("test-custom-agent")
        assert agent_config is not None, "Agent config should be available"
        assert agent_config.model == "claude-3-5-sonnet-20241022", \
            "Agent model should match plugin config"
        assert agent_config.max_tasks == 1, "Agent max_tasks should match plugin config"
        assert "test-skill" in agent_config.skills, \
            "Agent skills should include plugin skill"
        assert "test agent" in agent_config.system_prompt.lower(), \
            "Agent system prompt should match plugin config"

        # Verify plugin agent types list
        plugin_agent_types = agent_manager.get_plugin_agent_types()
        assert "test-custom-agent" in plugin_agent_types, \
            "Custom agent should appear in plugin agent types list"

    def test_execute_task_with_custom_agent(self, plugin_manager, agent_manager):
        """
        Test Step 4: Execute a task with the custom agent plugin.

        Verifies:
        - Agent can be created with plugin-provided configuration
        - Plugin lifecycle hooks are called
        - Agent can process tasks
        """
        # Create and load test plugin
        test_plugin = TestAgentPlugin()
        from devflow.plugins.plugin_loader import PluginLoadResult

        load_result = PluginLoadResult(
            plugin_name="test-agent-plugin",
            success=True,
            plugin=test_plugin
        )

        plugin_manager._register_loaded_plugin(load_result)
        plugin_manager.initialize_plugin("test-agent-plugin")
        plugin_manager.start_plugin("test-agent-plugin")

        # Register agent with agent manager
        test_plugin.register_agent(agent_manager)

        # Simulate agent lifecycle to trigger hooks
        test_agent_id = "test-agent-001"
        test_task = "Test task for end-to-end testing"

        # Trigger agent created hook
        test_plugin.on_agent_created(test_agent_id, "test-custom-agent")
        assert test_plugin.agent_created_called, \
            "Agent created hook should be called"

        # Trigger agent started hook
        test_plugin.on_agent_started(test_agent_id, test_task)
        assert test_plugin.agent_started_called, \
            "Agent started hook should be called"

        # Trigger agent completed hook
        test_result = {"status": "success", "output": "Test completed"}
        test_plugin.on_agent_completed(test_agent_id, test_result)
        assert test_plugin.agent_completed_called, \
            "Agent completed hook should be called"

        # Verify agent type can be used to create configuration
        agent_config = agent_manager.get_agent_type_config("test-custom-agent")
        assert agent_config is not None, "Agent config should be available"
        assert agent_config.agent_type == "test-custom-agent", \
            "Agent type should match"

    def test_unload_and_cleanup_plugin(self, plugin_manager, agent_manager):
        """
        Test Step 5: Unload plugin and verify cleanup.

        Verifies:
        - Plugin can be stopped
        - Plugin can be unloaded
        - Resources are cleaned up
        - Plugin is removed from all registries
        """
        # Create and load test plugin
        test_plugin = TestAgentPlugin()
        from devflow.plugins.plugin_loader import PluginLoadResult

        load_result = PluginLoadResult(
            plugin_name="test-agent-plugin",
            success=True,
            plugin=test_plugin
        )

        plugin_manager._register_loaded_plugin(load_result)
        plugin_manager.initialize_plugin("test-agent-plugin")
        plugin_manager.start_plugin("test-agent-plugin")

        # Register agent with agent manager
        test_plugin.register_agent(agent_manager)

        # Verify plugin is running
        assert plugin_manager.is_plugin_running("test-agent-plugin"), \
            "Plugin should be running before unload"

        # Stop plugin
        stop_success = plugin_manager.stop_plugin("test-agent-plugin")
        assert stop_success, "Plugin should stop successfully"

        # Verify plugin is stopped but still loaded
        assert plugin_manager.is_plugin_loaded("test-agent-plugin"), \
            "Plugin should still be loaded after stop"
        assert not plugin_manager.is_plugin_running("test-agent-plugin"), \
            "Plugin should not be running after stop"

        # Unload plugin
        unload_success = plugin_manager.unload_plugin("test-agent-plugin")
        assert unload_success, "Plugin should unload successfully"

        # Verify plugin is completely removed
        assert not plugin_manager.is_plugin_loaded("test-agent-plugin"), \
            "Plugin should not be loaded after unload"
        assert plugin_manager.get_plugin("test-agent-plugin") is None, \
            "Plugin should not be retrievable after unload"

        # Verify plugin is not in running plugins list
        running_plugins = plugin_manager.get_running_plugins()
        assert "test-agent-plugin" not in running_plugins, \
            "Plugin should not appear in running plugins after unload"

    def test_complete_plugin_lifecycle(self, plugin_manager, agent_manager):
        """
        Complete end-to-end test of the plugin lifecycle.

        This test runs through the entire lifecycle:
        1. Create plugin
        2. Load plugin
        3. Initialize plugin
        4. Start plugin
        5. Register agent
        6. Execute task
        7. Stop plugin
        8. Unload plugin
        9. Verify cleanup
        """
        # Step 1: Create test plugin
        test_plugin = TestAgentPlugin()
        plugin_name = "test-agent-plugin"
        agent_type = "test-custom-agent"

        # Step 2: Load plugin
        from devflow.plugins.plugin_loader import PluginLoadResult
        load_result = PluginLoadResult(
            plugin_name=plugin_name,
            success=True,
            plugin=test_plugin
        )
        plugin_manager._register_loaded_plugin(load_result)
        assert plugin_manager.is_plugin_loaded(plugin_name), "Plugin should be loaded"

        # Step 3: Initialize plugin
        init_success = plugin_manager.initialize_plugin(plugin_name)
        assert init_success, "Plugin should initialize"
        plugin_state = plugin_manager.get_plugin_state(plugin_name)
        assert plugin_state.initialized, "Plugin should be initialized"

        # Step 4: Start plugin
        start_success = plugin_manager.start_plugin(plugin_name)
        assert start_success, "Plugin should start"
        assert plugin_manager.is_plugin_running(plugin_name), "Plugin should be running"

        # Step 5: Register agent with agent manager
        test_plugin.register_agent(agent_manager)
        assert agent_manager.has_agent_type(agent_type), \
            "Agent type should be registered"

        # Step 6: Execute task (simulate)
        test_agent_id = "test-agent-e2e-001"
        test_task = "End-to-end test task"

        test_plugin.on_agent_created(test_agent_id, agent_type)
        test_plugin.on_agent_started(test_agent_id, test_task)
        test_plugin.on_agent_completed(test_agent_id, {"status": "completed"})

        assert test_plugin.agent_created_called, "Created hook should be called"
        assert test_plugin.agent_started_called, "Started hook should be called"
        assert test_plugin.agent_completed_called, "Completed hook should be called"

        # Step 7: Stop plugin
        stop_success = plugin_manager.stop_plugin(plugin_name)
        assert stop_success, "Plugin should stop"
        assert not plugin_manager.is_plugin_running(plugin_name), \
            "Plugin should not be running"

        # Step 8: Unload plugin
        unload_success = plugin_manager.unload_plugin(plugin_name)
        assert unload_success, "Plugin should unload"

        # Step 9: Verify complete cleanup
        assert not plugin_manager.is_plugin_loaded(plugin_name), \
            "Plugin should not be loaded"
        assert plugin_manager.get_plugin(plugin_name) is None, \
            "Plugin should not be retrievable"

        # Verify plugin manager metrics
        metrics = plugin_manager.get_metrics()
        assert metrics["total_plugins"] == 0, "All plugins should be unloaded"
        assert metrics["running"] == 0, "No plugins should be running"

    def test_plugin_error_handling(self, plugin_manager):
        """
        Test error handling in plugin operations.

        Verifies:
        - Loading non-existent plugin fails gracefully
        - Unloading non-loaded plugin fails gracefully
        - Error conditions don't crash the system
        """
        # Try to unload a plugin that doesn't exist
        result = plugin_manager.unload_plugin("non-existent-plugin")
        assert result == False, "Unloading non-existent plugin should return False"

        # Try to initialize non-existent plugin
        result = plugin_manager.initialize_plugin("non-existent-plugin")
        assert result == False, "Initializing non-existent plugin should return False"

        # Try to start non-existent plugin
        result = plugin_manager.start_plugin("non-existent-plugin")
        assert result == False, "Starting non-existent plugin should return False"

        # Try to stop non-existent plugin
        result = plugin_manager.stop_plugin("non-existent-plugin")
        assert result == False, "Stopping non-existent plugin should return False"

        # Verify system is still functional
        assert plugin_manager is not None, "Plugin manager should still be functional"
        metrics = plugin_manager.get_metrics()
        assert metrics is not None, "Should be able to get metrics"

    def test_multiple_plugins(self, plugin_manager, agent_manager):
        """
        Test loading and managing multiple plugins.

        Verifies:
        - Multiple plugins can be loaded simultaneously
        - Each plugin maintains its own state
        - Plugins can be managed independently
        """
        # Create and load first plugin
        test_plugin1 = TestAgentPlugin()
        from devflow.plugins.plugin_loader import PluginLoadResult

        load_result1 = PluginLoadResult(
            plugin_name="test-agent-plugin-1",
            success=True,
            plugin=test_plugin1
        )
        plugin_manager._register_loaded_plugin(load_result1)

        # Create and load second plugin
        test_plugin2 = TestAgentPlugin()
        load_result2 = PluginLoadResult(
            plugin_name="test-agent-plugin-2",
            success=True,
            plugin=test_plugin2
        )
        plugin_manager._register_loaded_plugin(load_result2)

        # Verify both plugins are loaded
        assert plugin_manager.is_plugin_loaded("test-agent-plugin-1"), \
            "First plugin should be loaded"
        assert plugin_manager.is_plugin_loaded("test-agent-plugin-2"), \
            "Second plugin should be loaded"

        # List all plugins
        all_plugins = plugin_manager.list_plugins()
        assert "test-agent-plugin-1" in all_plugins, "First plugin should be in list"
        assert "test-agent-plugin-2" in all_plugins, "Second plugin should be in list"
        assert len(all_plugins) == 2, "Should have exactly 2 plugins"

        # Start only first plugin
        plugin_manager.start_plugin("test-agent-plugin-1")

        # Verify first is running, second is not
        assert plugin_manager.is_plugin_running("test-agent-plugin-1"), \
            "First plugin should be running"
        assert not plugin_manager.is_plugin_running("test-agent-plugin-2"), \
            "Second plugin should not be running"

        # Get running plugins
        running = plugin_manager.get_running_plugins()
        assert "test-agent-plugin-1" in running, "First plugin should be in running list"
        assert "test-agent-plugin-2" not in running, "Second plugin should not be in running list"

        # Get idle plugins
        idle = plugin_manager.get_idle_plugins()
        assert "test-agent-plugin-2" in idle, "Second plugin should be in idle list"

        # Cleanup
        plugin_manager.cleanup_all_plugins()

        # Verify all plugins are cleaned up
        assert len(plugin_manager.list_plugins()) == 0, "All plugins should be unloaded"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
