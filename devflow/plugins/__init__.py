"""
Plugin System - Extensible plugin architecture.

Provides the framework for defining, loading, and managing plugins.
"""

from .base import Plugin, AgentPlugin, TaskSourcePlugin

__all__ = [
    'Plugin',
    'AgentPlugin',
    'TaskSourcePlugin',
]
