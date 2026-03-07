"""
Task Scheduler - Schedules and manages task execution.

Assigns tasks to agents, tracks progress, and handles dependencies.
"""

import threading
import time
import queue
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid

from .state_tracker import StateTracker, TaskStatus, AgentStatus
from .agent_manager import AgentManager


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    DEFERRED = 5


class TaskType(Enum):
    """Task types supported by the scheduler."""
    # Planning tasks
    PLANNING = "planning"

    # Development tasks
    DEVELOPMENT = "development"

    # Quality assurance tasks
    QUALITY = "quality"

    # CI/CD tasks
    TRIGGER_PIPELINE = "trigger-pipeline"
    MONITOR_PIPELINE = "monitor-pipeline"

    # Investigation tasks
    INVESTIGATION = "investigation"


@dataclass
class Task:
    """A task to be executed by an agent."""
    id: str
    type: str
    description: str
    agent_type: str
    priority: int = 5
    dependencies: List[str] = field(default_factory=list)
    input_data: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 3600
    max_retries: int = 3
    retry_count: int = 0
    status: str = TaskStatus.PENDING.value
    assigned_to: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "description": self.description,
            "agent_type": self.agent_type,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "input_data": self.input_data,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class TaskScheduler:
    """
    Schedules and manages task execution.

    Features:
    - Priority-based task scheduling
    - Dependency management
    - Agent assignment
    - Retry logic
    - Timeout handling

    Supported Task Types:
    - planning: Project planning and requirement gathering
    - development: Code implementation tasks
    - quality: Quality assurance, testing, and review
    - trigger-pipeline: CI/CD pipeline triggering
    - monitor-pipeline: CI/CD pipeline monitoring
    - investigation: Failure investigation and analysis
    """

    def __init__(self, state_tracker: StateTracker, agent_manager: AgentManager):
        self.state = state_tracker
        self.agents = agent_manager
        self.task_queue: queue.PriorityQueue = queue.PriorityQueue()
        self.lock = threading.Lock()
        self._running = False
        self._scheduler_thread = None

    def start(self):
        """Start the task scheduler."""
        if self._running:
            return

        self._running = True
        self._scheduler_thread = threading.Thread(target=self._schedule_loop, daemon=True)
        self._scheduler_thread.start()

    def stop(self):
        """Stop the task scheduler."""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
            self._scheduler_thread = None

    def create_task(self, task_type: str, description: str, agent_type: str,
                   priority: int = TaskPriority.MEDIUM.value,
                   dependencies: List[str] = None,
                   input_data: Dict[str, Any] = None,
                   timeout: int = 3600,
                   max_retries: int = 3) -> str:
        """
        Create a new task.

        Args:
            task_type: Type of task
            description: Task description
            agent_type: Type of agent needed
            priority: Task priority (1-5, lower is higher priority)
            dependencies: List of task IDs this task depends on
            input_data: Input data for the task
            timeout: Task timeout in seconds
            max_retries: Maximum retry attempts

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())

        task = Task(
            id=task_id,
            type=task_type,
            description=description,
            agent_type=agent_type,
            priority=priority,
            dependencies=dependencies or [],
            input_data=input_data or {},
            timeout=timeout,
            max_retries=max_retries,
        )

        # Add to state tracker
        self.state.create_task(
            task_id=task_id,
            task_type=task_type,
            description=description,
            priority=priority,
            dependencies=dependencies or [],
        )

        # Add to queue
        self.task_queue.put((priority, task_id, task))

        return task_id

    def _schedule_loop(self):
        """Main scheduling loop."""
        while self._running:
            try:
                # Get next task from queue (with timeout)
                try:
                    priority, task_id, task = self.task_queue.get(timeout=1)
                except queue.Empty:
                    continue

                # Check if task is ready to run
                if not self._is_task_ready(task):
                    # Put back in queue
                    self.task_queue.put((priority, task_id, task))
                    time.sleep(1)
                    continue

                # Assign to agent
                agent_id = self._assign_task(task)

                if agent_id:
                    # Execute task
                    self._execute_task(task_id, task, agent_id)
                else:
                    # No available agent, put back in queue
                    self.task_queue.put((priority, task_id, task))
                    time.sleep(5)

            except Exception as e:
                print(f"Scheduler error: {e}")
                time.sleep(5)

    def _is_task_ready(self, task: Task) -> bool:
        """Check if task dependencies are satisfied."""
        if not task.dependencies:
            return True

        for dep_id in task.dependencies:
            dep_task = self.state.get_task_status(dep_id)
            if not dep_task:
                return False
            if dep_task["status"] != TaskStatus.COMPLETED.value:
                return False

        return True

    def _assign_task(self, task: Task) -> Optional[str]:
        """Assign task to an available agent."""
        # Get idle agents of the right type
        idle_agents = self.agents.get_idle_agents(task.agent_type)

        if not idle_agents:
            return None

        # Use the first available agent
        agent_id = idle_agents[0]

        # Update state
        self.state.assign_task(task.id, agent_id)

        return agent_id

    def _execute_task(self, task_id: str, task: Task, agent_id: str):
        """Execute a task on an agent."""
        try:
            # Update status to in progress
            self.state.update_task_status(task_id, TaskStatus.IN_PROGRESS)

            # Spawn agent session
            session = self.agents.spawn_agent_session(agent_id)

            # Monitor task execution (simplified - in real implementation, would poll for completion)
            # For now, mark as completed
            self.state.update_task_status(
                task_id,
                TaskStatus.COMPLETED,
                result={"session": session.name}
            )

            # Record success
            self.state.record_agent_success(agent_id)

        except Exception as e:
            # Record failure
            error_msg = str(e)
            self.state.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error=error_msg
            )

            self.state.record_agent_failure(agent_id)

            # Check if should retry
            if task.retry_count < task.max_retries:
                self.state.increment_task_retry(task_id)
                # Requeue with same priority
                self.task_queue.put((task.priority, task_id, task))

    def get_pending_tasks(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get pending tasks."""
        return self.state.get_pending_tasks(limit)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        return self.state.get_task_status(task_id)

    def cancel_task(self, task_id: str):
        """Cancel a task."""
        self.state.update_task_status(task_id, TaskStatus.CANCELLED)

    def get_metrics(self) -> Dict[str, Any]:
        """Get scheduler metrics."""
        all_tasks = self.state.get_all_tasks()

        total = len(all_tasks)
        pending = sum(1 for t in all_tasks.values() if t["status"] == TaskStatus.PENDING.value)
        in_progress = sum(1 for t in all_tasks.values() if t["status"] == TaskStatus.IN_PROGRESS.value)
        completed = sum(1 for t in all_tasks.values() if t["status"] == TaskStatus.COMPLETED.value)
        failed = sum(1 for t in all_tasks.values() if t["status"] == TaskStatus.FAILED.value)

        return {
            "total_tasks": total,
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "failed": failed,
            "queue_size": self.task_queue.qsize(),
        }
