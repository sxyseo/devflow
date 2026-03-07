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


class PipelineStatus(Enum):
    """CI/CD pipeline execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class StateTracker:
    """
    Tracks the state of the entire DevFlow system.

    Maintains state for:
    - All agents and their status
    - All tasks and their progress
    - CI/CD pipelines and their execution state
    - Workflow execution state
    - System metrics
    """

    def __init__(self):
        self.state_file = settings.state_dir / "system_state.json"
        self.lock = threading.Lock()

        # State dictionaries
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.pipelines: Dict[str, Dict[str, Any]] = {}
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.metrics: Dict[str, Any] = {}

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

    def create_pipeline(self, pipeline_id: str, pipeline_type: str, commit_sha: str,
                       branch: str, triggered_by: str = None):
        """Create a new CI/CD pipeline execution."""
        with self.lock:
            self.pipelines[pipeline_id] = {
                "id": pipeline_id,
                "type": pipeline_type,
                "commit_sha": commit_sha,
                "branch": branch,
                "triggered_by": triggered_by,
                "status": PipelineStatus.PENDING.value,
                "created_at": datetime.utcnow().isoformat(),
                "started_at": None,
                "completed_at": None,
                "stages": [],
                "result": None,
                "error": None,
                "metadata": {},
            }
            self.save()

    def update_pipeline_status(self, pipeline_id: str, status: PipelineStatus,
                              stages: List[Dict[str, Any]] = None,
                              result: Any = None, error: str = None,
                              metadata: Dict[str, Any] = None):
        """Update pipeline status."""
        with self.lock:
            if pipeline_id not in self.pipelines:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            pipeline = self.pipelines[pipeline_id]
            pipeline["status"] = status.value

            if status == PipelineStatus.RUNNING and pipeline["started_at"] is None:
                pipeline["started_at"] = datetime.utcnow().isoformat()

            if status in [PipelineStatus.COMPLETED, PipelineStatus.FAILED,
                         PipelineStatus.CANCELLED, PipelineStatus.SKIPPED]:
                pipeline["completed_at"] = datetime.utcnow().isoformat()

            if stages is not None:
                pipeline["stages"] = stages

            if result is not None:
                pipeline["result"] = result

            if error is not None:
                pipeline["error"] = error

            if metadata is not None:
                pipeline["metadata"].update(metadata)

            self.save()

    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent status."""
        return self.agents.get(agent_id)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        return self.tasks.get(task_id)

    def get_pipeline_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get pipeline status."""
        return self.pipelines.get(pipeline_id)

    def get_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get all agents."""
        return self.agents.copy()

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all tasks."""
        return self.tasks.copy()

    def get_all_pipelines(self) -> Dict[str, Dict[str, Any]]:
        """Get all pipelines."""
        return self.pipelines.copy()

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

            total_pipelines = len(self.pipelines)
            completed_pipelines = sum(1 for p in self.pipelines.values()
                                     if p["status"] == PipelineStatus.COMPLETED.value)
            failed_pipelines = sum(1 for p in self.pipelines.values()
                                  if p["status"] == PipelineStatus.FAILED.value)
            running_pipelines = sum(1 for p in self.pipelines.values()
                                   if p["status"] == PipelineStatus.RUNNING.value)

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
                "pipelines": {
                    "total": total_pipelines,
                    "completed": completed_pipelines,
                    "failed": failed_pipelines,
                    "running": running_pipelines,
                    "success_rate": completed_pipelines / total_pipelines if total_pipelines > 0 else 0,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

    def save(self):
        """Save state to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "agents": self.agents,
            "tasks": self.tasks,
            "pipelines": self.pipelines,
            "workflows": self.workflows,
            "metrics": self.metrics,
        }

        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2, default=str)

    def load(self):
        """Load state from disk."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                state = json.load(f)

            self.agents = state.get("agents", {})
            self.tasks = state.get("tasks", {})
            self.pipelines = state.get("pipelines", {})
            self.workflows = state.get("workflows", {})
            self.metrics = state.get("metrics", {})

    def reset(self):
        """Reset all state."""
        with self.lock:
            self.agents.clear()
            self.tasks.clear()
            self.pipelines.clear()
            self.workflows.clear()
            self.metrics.clear()
            self.save()
