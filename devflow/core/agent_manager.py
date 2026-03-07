"""
Agent Manager - Manages AI agent lifecycle.

Creates, configures, and manages AI agents for various tasks.
"""

import asyncio
import threading
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import json

from .state_tracker import StateTracker, AgentStatus, TaskStatus
from .session_manager import SessionManager, SessionInfo
from ..config.settings import settings
from ..plugins.plugin_registry import PluginRegistry
from ..plugins.agent_plugin import AgentPlugin


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    agent_type: str
    model: str = "claude-3-5-sonnet-20241022"
    max_tasks: int = 1
    timeout: int = 3600
    skills: List[str] = field(default_factory=list)
    system_prompt: str = ""


class AgentManager:
    """
    Manages the lifecycle of AI agents.

    Responsibilities:
    - Agent creation and configuration
    - Task assignment to agents
    - Agent monitoring and health checks
    - Agent cleanup and resource management
    """

    def __init__(self, state_tracker: StateTracker, session_manager: SessionManager,
                 plugin_registry: PluginRegistry = None):
        self.state = state_tracker
        self.sessions = session_manager
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.agent_configs: Dict[str, AgentConfig] = self._load_agent_configs()
        self.plugin_registry = plugin_registry or PluginRegistry()
        self.lock = threading.Lock()

    def register_agent_type(self, agent_type: str, config: Dict[str, Any] = None,
                            agent_class: Type = None) -> None:
        """
        Register a custom agent type from a plugin.

        Args:
            agent_type: Unique identifier for the agent type
            config: Optional agent configuration dictionary
            agent_class: Optional custom agent class
        """
        if config is None:
            config = {}

        # Convert dict config to AgentConfig
        agent_config = AgentConfig(
            agent_type=agent_type,
            model=config.get("model", "claude-3-5-sonnet-20241022"),
            max_tasks=config.get("max_tasks", 1),
            timeout=config.get("timeout", 3600),
            skills=config.get("skills", []),
            system_prompt=config.get("system_prompt", "")
        )

        self.agent_configs[agent_type] = agent_config

    def load_agent_types_from_plugins(self) -> int:
        """
        Load agent types from registered plugins.

        Returns:
            Number of agent types loaded from plugins
        """
        if not self.plugin_registry:
            return 0

        agent_plugins = self.plugin_registry.get_plugins_by_type("agent")
        loaded_count = 0

        for plugin in agent_plugins:
            try:
                # Register the agent type from the plugin
                if hasattr(plugin, 'register_agent'):
                    plugin.register_agent(self)
                    loaded_count += 1
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to load agent plugin {plugin.get_metadata().name}: {e}")

        return loaded_count

    def _load_agent_configs(self) -> Dict[str, AgentConfig]:
        """Load agent configurations."""
        configs = {}

        # Default configurations for BMAD agents
        configs["product-owner"] = AgentConfig(
            agent_type="planning",
            skills=["requirements-analysis", "product-design"],
            system_prompt="You are a Product Owner agent focused on clarifying requirements and defining product vision."
        )

        configs["business-analyst"] = AgentConfig(
            agent_type="planning",
            skills=["prd-writing", "user-journey-mapping"],
            system_prompt="You are a Business Analyst agent focused on creating comprehensive PRDs with user journeys."
        )

        configs["architect"] = AgentConfig(
            agent_type="planning",
            skills=["system-design", "architecture"],
            system_prompt="You are a System Architect agent focused on designing robust, scalable architectures."
        )

        configs["ux-designer"] = AgentConfig(
            agent_type="planning",
            skills=["ux-design", "user-research"],
            system_prompt="You are a UX Designer agent focused on creating intuitive user experiences."
        )

        configs["scrum-master"] = AgentConfig(
            agent_type="planning",
            skills=["task-breakdown", "story-writing"],
            system_prompt="You are a Scrum Master agent focused on breaking down epics into actionable stories."
        )

        configs["dev-story"] = AgentConfig(
            agent_type="development",
            skills=["tdd", "implementation", "testing"],
            system_prompt="You are a Developer agent focused on TDD, clean code, and test coverage."
        )

        configs["code-review"] = AgentConfig(
            agent_type="quality",
            skills=["code-review", "adversarial-review"],
            system_prompt="You are a Code Reviewer agent focused on finding issues and improving code quality."
        )

        configs["qa-tester"] = AgentConfig(
            agent_type="quality",
            skills=["testing", "validation"],
            system_prompt="You are a QA Tester agent focused on thorough testing and validation."
        )

        return configs

    def create_agent(self, agent_id: str, agent_type: str,
                    task: str, session_name: str = None) -> str:
        """
        Create a new agent.

        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of agent (e.g., 'planning', 'development')
            task: Task description
            session_name: Optional tmux session name

        Returns:
            Agent ID
        """
        # Register agent in state tracker
        self.state.register_agent(agent_id, agent_type, session_name)

        # Get agent configuration
        config = self.agent_configs.get(agent_type)
        if not config:
            config = AgentConfig(agent_type=agent_type)

        # Store agent info
        with self.lock:
            self.agents[agent_id] = {
                "id": agent_id,
                "type": agent_type,
                "config": config,
                "task": task,
                "session_name": session_name,
                "created_at": time.time(),
            }

        return agent_id

    def spawn_agent_session(self, agent_id: str) -> SessionInfo:
        """
        Spawn a tmux session for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            SessionInfo object
        """
        agent_info = self.agents.get(agent_id)
        if not agent_info:
            raise ValueError(f"Agent {agent_id} not found")

        # Create tmux session
        session = self.sessions.create_session(
            agent_id=agent_id,
            agent_type=agent_info["type"],
            task=agent_info["task"]
        )

        # Update agent info
        with self.lock:
            agent_info["session_name"] = session.name
            agent_info["session_created_at"] = time.time()

        # Update state
        self.state.update_agent_status(agent_id, AgentStatus.RUNNING)

        return session

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent information."""
        return self.agents.get(agent_id)

    def get_agents_by_type(self, agent_type: str) -> List[Dict[str, Any]]:
        """Get all agents of a specific type."""
        return [
            agent for agent in self.agents.values()
            if agent["type"] == agent_type
        ]

    def get_idle_agents(self, agent_type: str = None) -> List[str]:
        """Get idle agents available for work."""
        all_agents = self.state.get_all_agents()

        idle = []
        for agent_id, agent_info in all_agents.items():
            if agent_info["status"] == AgentStatus.IDLE.value:
                if agent_type is None or agent_info["type"] == agent_type:
                    idle.append(agent_id)

        return idle

    def update_agent_status(self, agent_id: str, status: AgentStatus,
                           current_task: str = None, halt_reason: str = None):
        """Update agent status."""
        self.state.update_agent_status(agent_id, status, current_task, halt_reason)

    def cleanup_agent(self, agent_id: str):
        """Clean up an agent and its resources."""
        agent_info = self.agents.get(agent_id)
        if not agent_info:
            return

        # Kill tmux session if exists
        session_name = agent_info.get("session_name")
        if session_name:
            self.sessions.kill_session(session_name)

        # Remove from agents dict
        with self.lock:
            if agent_id in self.agents:
                del self.agents[agent_id]

    def cleanup_all_agents(self):
        """Clean up all agents."""
        agent_ids = list(self.agents.keys())

        for agent_id in agent_ids:
            self.cleanup_agent(agent_id)

    def get_agent_metrics(self) -> Dict[str, Any]:
        """Get metrics about agents."""
        all_agents = self.state.get_all_agents()

        total = len(all_agents)
        idle = sum(1 for a in all_agents.values() if a["status"] == AgentStatus.IDLE.value)
        running = sum(1 for a in all_agents.values() if a["status"] == AgentStatus.RUNNING.value)
        halted = sum(1 for a in all_agents.values() if a["status"] == AgentStatus.HALTED.value)
        completed = sum(1 for a in all_agents.values() if a["status"] == AgentStatus.COMPLETED.value)
        failed = sum(1 for a in all_agents.values() if a["status"] == AgentStatus.FAILED.value)

        total_tasks = sum(a.get("tasks_completed", 0) for a in all_agents.values())
        total_failures = sum(a.get("tasks_failed", 0) for a in all_agents.values())

        return {
            "total_agents": total,
            "idle": idle,
            "running": running,
            "halted": halted,
            "completed": completed,
            "failed": failed,
            "total_tasks_completed": total_tasks,
            "total_tasks_failed": total_failures,
            "success_rate": total_tasks / (total_tasks + total_failures) if (total_tasks + total_failures) > 0 else 0,
        }

    def get_available_agent_types(self) -> List[str]:
        """Get list of available agent types."""
        return list(self.agent_configs.keys())

    def get_agent_type_config(self, agent_type: str) -> Optional[AgentConfig]:
        """
        Get configuration for a specific agent type.

        Args:
            agent_type: Type of agent to get configuration for

        Returns:
            AgentConfig object or None if not found
        """
        return self.agent_configs.get(agent_type)

    def has_agent_type(self, agent_type: str) -> bool:
        """
        Check if an agent type is available.

        Args:
            agent_type: Type of agent to check

        Returns:
            True if agent type is available, False otherwise
        """
        return agent_type in self.agent_configs

    def get_plugin_agent_types(self) -> List[str]:
        """
        Get list of agent types provided by plugins.

        Returns:
            List of agent type identifiers from plugins
        """
        if not self.plugin_registry:
            return []

        agent_plugins = self.plugin_registry.get_plugins_by_type("agent")
        return [
            plugin.get_agent_type()
            for plugin in agent_plugins
            if hasattr(plugin, 'get_agent_type')
        ]
