"""
Plugin System - Extensible plugin architecture.

Provides the framework for defining, loading, and managing plugins.
"""

from .base import Plugin, AgentPlugin, TaskSourcePlugin
from .plugin_config import PluginConfig, plugin_config

__all__ = [
    'Plugin',
    'AgentPlugin',
    'TaskSourcePlugin',
    'PluginConfig',
    'plugin_config',
]
