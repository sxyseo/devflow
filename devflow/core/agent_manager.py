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
from .model_manager import ModelManager
from .model_selector import ModelSelector, SelectionStrategy, SelectionResult
from ..config.settings import settings


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    agent_type: str
    model: Optional[str] = None  # Model selected dynamically via ModelSelector
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

    def __init__(self, state_tracker: StateTracker, session_manager: SessionManager):
        self.state = state_tracker
        self.sessions = session_manager
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.agent_configs: Dict[str, AgentConfig] = self._load_agent_configs()
        self.lock = threading.Lock()

        # Initialize model manager and selector
        self.model_manager = ModelManager()
        self.model_selector = ModelSelector(self.model_manager)

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

        # Select model for this agent type using ModelSelector
        selection_result = self.model_selector.select_model_for_agent(
            agent_type=agent_type,
            task=task,
            strategy=SelectionStrategy.BALANCED
        )

        # Update config with selected model
        if selection_result:
            config.model = selection_result.model_id
        else:
            # Fallback to None if no model selected
            config.model = None

        # Store agent info
        with self.lock:
            self.agents[agent_id] = {
                "id": agent_id,
                "type": agent_type,
                "config": config,
                "task": task,
                "session_name": session_name,
                "created_at": time.time(),
                "model_selection": selection_result,
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

    def handle_model_failure(self, agent_id: str, failed_model_id: str,
                            error: Exception = None) -> Optional[SelectionResult]:
        """
        Handle model failure by triggering fallback to an alternative model.

        Args:
            agent_id: Agent identifier
            failed_model_id: Model that failed
            error: Optional exception that caused the failure

        Returns:
            SelectionResult for fallback model if available, None otherwise
        """
        agent_info = self.agents.get(agent_id)
        if not agent_info:
            raise ValueError(f"Agent {agent_id} not found")

        # Get original selection result
        original_selection = agent_info.get("model_selection")
        if not original_selection:
            return None

        # Get agent type and task
        agent_type = agent_info["type"]
        task = agent_info["task"]

        # Build selection criteria for fallback
        from .model_selector import SelectionCriteria, SelectionStrategy

        # Get excluded models from agent's fallback history
        excluded_models = agent_info.get("excluded_models", set()).copy()
        excluded_models.add(failed_model_id)

        # Create criteria based on original selection
        criteria = SelectionCriteria(
            task_type=self._infer_task_type(agent_type),
            strategy=SelectionStrategy.BALANCED,
            excluded_models=excluded_models
        )

        # Get fallback model from selector
        fallback_result = self.model_selector.get_fallback_model(
            current_model_id=failed_model_id,
            criteria=criteria
        )

        if not fallback_result:
            # No fallback available - mark agent as failed
            self.state.update_agent_status(
                agent_id,
                AgentStatus.FAILED,
                halt_reason=f"Model {failed_model_id} failed and no fallback available"
            )
            return None

        # Update agent configuration with fallback model
        with self.lock:
            config = agent_info["config"]
            config.model = fallback_result.model_id

            # Update model selection result
            agent_info["model_selection"] = fallback_result

            # Track fallback history
            fallback_history = agent_info.get("fallback_history", [])
            fallback_history.append({
                "from_model": failed_model_id,
                "to_model": fallback_result.model_id,
                "timestamp": time.time(),
                "error": str(error) if error else "Unknown error"
            })
            agent_info["fallback_history"] = fallback_history

            # Update excluded models
            agent_info["excluded_models"] = excluded_models

            # Increment fallback count
            agent_info["fallback_count"] = agent_info.get("fallback_count", 0) + 1

        # Log the fallback (could integrate with proper logging system)
        print(f"Model fallback triggered for agent {agent_id}: "
              f"{failed_model_id} -> {fallback_result.model_id}")

        return fallback_result

    def _infer_task_type(self, agent_type: str) -> str:
        """
        Infer task type from agent type.

        Args:
            agent_type: Agent type identifier

        Returns:
            Task type string
        """
        # Map agent types to task types
        task_type_map = {
            "planning": "analysis",
            "development": "code_generation",
            "quality": "code_review",
        }

        # Check if it's a known agent type
        for known_agent, task_type in self._get_agent_task_mappings().items():
            if agent_type == known_agent:
                return task_type

        return "analysis"  # Default

    def _get_agent_task_mappings(self) -> Dict[str, str]:
        """Get mappings from agent type to task type."""
        # Planning agents
        planning_agents = ["product-owner", "business-analyst", "architect",
                          "ux-designer", "scrum-master"]

        # Development agents
        dev_agents = ["dev-story"]

        # Quality agents
        quality_agents = ["code-review", "qa-tester"]

        mappings = {}
        for agent in planning_agents:
            mappings[agent] = "analysis"
        for agent in dev_agents:
            mappings[agent] = "code_generation"
        for agent in quality_agents:
            mappings[agent] = "code_review"

        return mappings

    def get_agent_fallback_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get fallback information for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Dictionary with fallback info, or None if agent not found
        """
        agent_info = self.agents.get(agent_id)
        if not agent_info:
            return None

        return {
            "current_model": agent_info["config"].model,
            "fallback_count": agent_info.get("fallback_count", 0),
            "fallback_history": agent_info.get("fallback_history", []),
            "excluded_models": list(agent_info.get("excluded_models", set())),
            "original_model": agent_info.get("model_selection").model_id if agent_info.get("model_selection") else None
        }

    def reset_agent_model(self, agent_id: str) -> bool:
        """
        Reset an agent to its original model selection.

        Args:
            agent_id: Agent identifier

        Returns:
            True if reset successful, False otherwise
        """
        agent_info = self.agents.get(agent_id)
        if not agent_info:
            return False

        with self.lock:
            # Clear fallback state
            agent_info["excluded_models"] = set()
            agent_info["fallback_history"] = []
            agent_info["fallback_count"] = 0

            # Reselect model from scratch
            agent_type = agent_info["type"]
            task = agent_info["task"]

            selection_result = self.model_selector.select_model_for_agent(
                agent_type=agent_type,
                task=task,
                strategy=SelectionStrategy.BALANCED
            )

            if selection_result:
                agent_info["config"].model = selection_result.model_id
                agent_info["model_selection"] = selection_result
                return True

        return False
