"""
Plugin System - Extensible plugin architecture.

Provides the framework for defining, loading, and managing plugins.
"""

from .base import Plugin, AgentPlugin as BaseAgentPlugin, TaskSourcePlugin
from .agent_plugin import AgentPlugin, AgentPluginRegistry, agent_plugin_registry
from .plugin_config import PluginConfig, plugin_config
from .plugin_registry import PluginRegistry

__all__ = [
    'Plugin',
    'BaseAgentPlugin',
    'AgentPlugin',
    'TaskSourcePlugin',
    'PluginConfig',
    'plugin_config',
    'PluginRegistry',
    'AgentPluginRegistry',
    'agent_plugin_registry',
]
