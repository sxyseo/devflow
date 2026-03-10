"""
State Tracker - Tracks system state and progress.

Monitors and tracks the state of all agents, tasks, and workflows.
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from enum import Enum

from ..config.settings import settings
from ..utils.git_tracker import GitTracker, CommitType
from ..utils.cost_tracker import CostTracker, CostType


class AgentStatus(Enum):
    """Agent lifecycle status."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    HALTED = "halted"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StateTracker:
    """
    Tracks the state of the entire DevFlow system.

    Maintains state for:
    - All agents and their status
    - All tasks and their progress
    - Workflow execution state
    - System metrics
    """

    def __init__(self):
        self.state_file = settings.state_dir / "system_state.json"
        self.lock = threading.Lock()

        # State dictionaries
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.metrics: Dict[str, Any] = {}

        # Initialize git and cost tracking
        self.git_tracker = GitTracker()
        self.cost_tracker = CostTracker()

        # Load existing state if available
        self.load()

    def register_agent(self, agent_id: str, agent_type: str, session_name: str = None):
        """Register a new agent."""
        with self.lock:
            self.agents[agent_id] = {
                "id": agent_id,
                "type": agent_type,
                "session_name": session_name,
                "status": AgentStatus.IDLE.value,
                "created_at": datetime.utcnow().isoformat(),
                "started_at": None,
                "completed_at": None,
                "current_task": None,
                "tasks_completed": 0,
                "tasks_failed": 0,
                "halt_reason": None,
            }
            self.save()

    def update_agent_status(self, agent_id: str, status: AgentStatus,
                           current_task: str = None, halt_reason: str = None):
        """Update agent status."""
        with self.lock:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not found")

            agent = self.agents[agent_id]
            agent["status"] = status.value

            if status == AgentStatus.RUNNING and agent["started_at"] is None:
                agent["started_at"] = datetime.utcnow().isoformat()

            if status in [AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.HALTED]:
                agent["completed_at"] = datetime.utcnow().isoformat()

            if current_task:
                agent["current_task"] = current_task

            if halt_reason:
                agent["halt_reason"] = halt_reason

            self.save()

    def record_agent_success(self, agent_id: str):
        """Record successful task completion."""
        with self.lock:
            if agent_id in self.agents:
                self.agents[agent_id]["tasks_completed"] += 1
                self.save()

    def record_agent_failure(self, agent_id: str):
        """Record task failure."""
        with self.lock:
            if agent_id in self.agents:
                self.agents[agent_id]["tasks_failed"] += 1
                self.save()

    def create_task(self, task_id: str, task_type: str, description: str,
                   priority: int = 5, dependencies: List[str] = None):
        """Create a new task."""
        with self.lock:
            self.tasks[task_id] = {
                "id": task_id,
                "type": task_type,
                "description": description,
                "priority": priority,
                "dependencies": dependencies or [],
                "status": TaskStatus.PENDING.value,
                "assigned_to": None,
                "created_at": datetime.utcnow().isoformat(),
                "started_at": None,
                "completed_at": None,
                "result": None,
                "error": None,
                "retry_count": 0,
            }
            self.save()

    def assign_task(self, task_id: str, agent_id: str):
        """Assign a task to an agent."""
        with self.lock:
            if task_id not in self.tasks:
                raise ValueError(f"Task {task_id} not found")

            self.tasks[task_id]["assigned_to"] = agent_id
            self.tasks[task_id]["status"] = TaskStatus.ASSIGNED.value
            self.save()

    def update_task_status(self, task_id: str, status: TaskStatus,
                          result: Any = None, error: str = None):
        """Update task status."""
        with self.lock:
            if task_id not in self.tasks:
                raise ValueError(f"Task {task_id} not found")

            task = self.tasks[task_id]
            task["status"] = status.value

            if status == TaskStatus.IN_PROGRESS and task["started_at"] is None:
                task["started_at"] = datetime.utcnow().isoformat()

            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task["completed_at"] = datetime.utcnow().isoformat()

            if result is not None:
                task["result"] = result

            if error is not None:
                task["error"] = error

            self.save()

    def increment_task_retry(self, task_id: str):
        """Increment task retry count."""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]["retry_count"] += 1
                self.save()

    def get_pending_tasks(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get pending tasks sorted by priority."""
        with self.lock:
            pending = [task for task in self.tasks.values()
                      if task["status"] == TaskStatus.PENDING.value]

            # Sort by priority (lower number = higher priority)
            pending.sort(key=lambda x: x["priority"])

            # Check dependencies
            ready_tasks = []
            for task in pending:
                deps_met = all(
                    self.tasks[dep_id]["status"] == TaskStatus.COMPLETED.value
                    for dep_id in task["dependencies"]
                    if dep_id in self.tasks
                )
                if deps_met:
                    ready_tasks.append(task)

            return ready_tasks[:limit] if limit else ready_tasks

    # Git tracking methods

    def record_commit(self, commit_hash: str, message: str, author: str,
                     branch: str, files_changed: List[str] = None,
                     commit_type: CommitType = CommitType.AUTO,
                     task_id: str = None, agent_id: str = None,
                     lines_added: int = 0, lines_deleted: int = 0):
        """Record a git commit."""
        self.git_tracker.record_commit(
            commit_hash=commit_hash,
            message=message,
            author=author,
            branch=branch,
            files_changed=files_changed,
            commit_type=commit_type,
            task_id=task_id,
            agent_id=agent_id,
            lines_added=lines_added,
            lines_deleted=lines_deleted,
        )

    def get_commits_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all commits for a specific task."""
        return self.git_tracker.get_commits_by_task(task_id)

    def get_commits_by_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all commits by a specific agent."""
        return self.git_tracker.get_commits_by_agent(agent_id)

    def get_recent_commits(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent commits."""
        return self.git_tracker.get_recent_commits(limit)

    def get_commit_stats(self) -> Dict[str, Any]:
        """Get git commit statistics."""
        return self.git_tracker.get_commit_stats()

    # Cost tracking methods

    def record_api_call(self, call_id: str, provider: str, model: str,
                       input_tokens: int, output_tokens: int,
                       cost: float, metadata: Dict[str, Any] = None):
        """Record an API call with associated costs."""
        self.cost_tracker.record_api_call(
            call_id=call_id,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            metadata=metadata,
        )

    def record_agent_operation(self, operation_id: str, agent_type: str,
                              operation: str, duration_seconds: float,
                              cost: float = 0.0, metadata: Dict[str, Any] = None):
        """Record an agent operation with associated costs."""
        self.cost_tracker.record_agent_operation(
            operation_id=operation_id,
            agent_type=agent_type,
            operation=operation,
            duration_seconds=duration_seconds,
            cost=cost,
            metadata=metadata,
        )

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get a summary of all costs."""
        return self.cost_tracker.get_cost_summary()

    def get_daily_costs(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily costs for the specified number of days."""
        return self.cost_tracker.get_daily_costs(days)

    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent status."""
        return self.agents.get(agent_id)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        return self.tasks.get(task_id)

    def get_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get all agents."""
        return self.agents.copy()

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all tasks."""
        return self.tasks.copy()

    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics."""
        with self.lock:
            total_tasks = len(self.tasks)
            completed_tasks = sum(1 for t in self.tasks.values()
                                if t["status"] == TaskStatus.COMPLETED.value)
            failed_tasks = sum(1 for t in self.tasks.values()
                             if t["status"] == TaskStatus.FAILED.value)

            total_agents = len(self.agents)
            active_agents = sum(1 for a in self.agents.values()
                              if a["status"] == AgentStatus.RUNNING.value)

            # Get git and cost metrics
            git_stats = self.git_tracker.get_commit_stats()
            cost_summary = self.cost_tracker.get_cost_summary()

            return {
                "tasks": {
                    "total": total_tasks,
                    "completed": completed_tasks,
                    "failed": failed_tasks,
                    "pending": total_tasks - completed_tasks - failed_tasks,
                    "success_rate": completed_tasks / total_tasks if total_tasks > 0 else 0,
                },
                "agents": {
                    "total": total_agents,
                    "active": active_agents,
                    "idle": total_agents - active_agents,
                },
                "git": {
                    "total_commits": git_stats.get("total_commits", 0),
                    "total_lines_added": git_stats.get("total_lines_added", 0),
                    "total_lines_deleted": git_stats.get("total_lines_deleted", 0),
                    "net_lines": git_stats.get("net_lines", 0),
                },
                "costs": {
                    "total_cost": cost_summary["summary"].get("total_cost", 0.0),
                    "daily_cost": cost_summary["summary"].get("daily_cost", 0.0),
                    "api_call_count": cost_summary["summary"].get("api_call_count", 0),
                    "total_tokens": cost_summary["summary"].get("total_tokens", 0),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

    def save(self):
        """Save state to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "agents": self.agents,
            "tasks": self.tasks,
            "workflows": self.workflows,
            "metrics": self.metrics,
        }

        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2, default=str)

        # Save git and cost tracking data
        self.git_tracker.save()
        self.cost_tracker.save()

    def load(self):
        """Load state from disk."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                state = json.load(f)

            self.agents = state.get("agents", {})
            self.tasks = state.get("tasks", {})
            self.workflows = state.get("workflows", {})
            self.metrics = state.get("metrics", {})

        # Load git and cost tracking data
        self.git_tracker.load()
        self.cost_tracker.load()

    def reset(self):
        """Reset all state."""
        with self.lock:
            self.agents.clear()
            self.tasks.clear()
            self.workflows.clear()
            self.metrics.clear()
            self.save()

        # Reset git and cost tracking
        self.git_tracker.reset()
        self.cost_tracker.reset()
