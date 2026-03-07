"""
Batch Processor - Groups and processes similar tasks efficiently.

Reduces API usage by batching similar operations together.
"""

import threading
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid


class BatchStrategy(Enum):
    """Batching strategies for grouping tasks."""
    BY_TYPE = "type"
    BY_PRIORITY = "priority"
    BY_SIZE = "size"
    BY_TIME = "time"


@dataclass
class BatchableTask:
    """A task that can be batched with similar tasks."""
    id: str
    type: str
    data: Dict[str, Any]
    priority: int = 5
    created_at: float = field(default_factory=time.time)
    batch_id: Optional[str] = None
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "priority": self.priority,
            "created_at": self.created_at,
            "batch_id": self.batch_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class Batch:
    """A batch of tasks to process together."""
    id: str
    strategy: BatchStrategy
    grouping_key: str
    tasks: List[BatchableTask] = field(default_factory=list)
    max_size: int = 10
    max_wait_time: float = 5.0
    created_at: float = field(default_factory=time.time)
    status: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "strategy": self.strategy.value,
            "grouping_key": self.grouping_key,
            "tasks": [task.to_dict() for task in self.tasks],
            "max_size": self.max_size,
            "max_wait_time": self.max_wait_time,
            "created_at": self.created_at,
            "status": self.status,
        }


class BatchProcessor:
    """
    Groups and processes similar tasks efficiently.

    Features:
    - Multiple batching strategies (type, priority, size, time)
    - Configurable batch sizes and wait times
    - Thread-safe operations
    - Automatic batch creation and processing
    - Batch metrics and statistics
    """

    def __init__(self, default_max_size: int = 10, default_max_wait: float = 5.0):
        """
        Initialize the batch processor.

        Args:
            default_max_size: Default maximum batch size
            default_max_wait: Default maximum wait time in seconds
        """
        self.default_max_size = default_max_size
        self.default_max_wait = default_max_wait

        self.pending_tasks: List[BatchableTask] = []
        self.batches: Dict[str, Batch] = {}

        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)

        self._running = False
        self._processor_thread = None
        self._batch_handler: Optional[Callable[[List[BatchableTask]], Dict[str, Any]]] = None

        # Metrics
        self.total_tasks = 0
        self.total_batches = 0
        self.completed_tasks = 0
        self.failed_tasks = 0

    def start(self, auto_process: bool = True):
        """
        Start the batch processor.

        Args:
            auto_process: Whether to automatically process batches
        """
        if self._running:
            return

        self._running = True

        if auto_process:
            self._processor_thread = threading.Thread(
                target=self._process_loop, daemon=True
            )
            self._processor_thread.start()

    def stop(self):
        """Stop the batch processor."""
        self._running = False

        with self.condition:
            self.condition.notify_all()

        if self._processor_thread:
            self._processor_thread.join(timeout=5)
            self._processor_thread = None

    def set_batch_handler(self, handler: Callable[[List[BatchableTask]], Dict[str, Any]]):
        """
        Set the batch processing handler.

        Args:
            handler: Function that processes a batch of tasks and returns results
        """
        self._batch_handler = handler

    def add_task(self, task_type: str, data: Dict[str, Any],
                 priority: int = 5) -> str:
        """
        Add a task to be batched.

        Args:
            task_type: Type of the task
            data: Task data
            priority: Task priority (1-5, lower is higher priority)

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())

        task = BatchableTask(
            id=task_id,
            type=task_type,
            data=data,
            priority=priority,
        )

        with self.lock:
            self.pending_tasks.append(task)
            self.total_tasks += 1
            self.condition.notify_all()

        return task_id

    def create_batch(self, strategy: BatchStrategy = BatchStrategy.BY_TYPE,
                    grouping_key: Optional[str] = None,
                    max_size: Optional[int] = None,
                    max_wait_time: Optional[float] = None) -> Optional[str]:
        """
        Create a batch from pending tasks.

        Args:
            strategy: Batching strategy to use
            grouping_key: Key to group tasks by (if applicable)
            max_size: Maximum batch size
            max_wait_time: Maximum wait time before processing

        Returns:
            Batch ID or None if no tasks available
        """
        with self.lock:
            if not self.pending_tasks:
                return None

            max_size = max_size or self.default_max_size
            max_wait_time = max_wait_time or self.default_max_wait

            # Filter and group tasks based on strategy
            tasks_to_batch = self._get_tasks_for_batch(strategy, grouping_key, max_size)

            if not tasks_to_batch:
                return None

            # Determine grouping key
            if not grouping_key:
                if strategy == BatchStrategy.BY_TYPE:
                    grouping_key = tasks_to_batch[0].type
                elif strategy == BatchStrategy.BY_PRIORITY:
                    grouping_key = str(tasks_to_batch[0].priority)
                else:
                    grouping_key = "default"

            # Create batch
            batch_id = str(uuid.uuid4())
            batch = Batch(
                id=batch_id,
                strategy=strategy,
                grouping_key=grouping_key,
                tasks=tasks_to_batch,
                max_size=max_size,
                max_wait_time=max_wait_time,
            )

            # Update tasks
            for task in tasks_to_batch:
                task.batch_id = batch_id
                self.pending_tasks.remove(task)

            self.batches[batch_id] = batch
            self.total_batches += 1

            return batch_id

    def _get_tasks_for_batch(self, strategy: BatchStrategy,
                            grouping_key: Optional[str],
                            max_size: int) -> List[BatchableTask]:
        """
        Get tasks that match the batching criteria.

        Args:
            strategy: Batching strategy
            grouping_key: Key to group by
            max_size: Maximum number of tasks

        Returns:
            List of tasks to batch
        """
        tasks = []

        for task in self.pending_tasks:
            if len(tasks) >= max_size:
                break

            should_include = False

            if strategy == BatchStrategy.BY_TYPE:
                should_include = (grouping_key is None or
                                 task.type == grouping_key)
            elif strategy == BatchStrategy.BY_PRIORITY:
                should_include = (grouping_key is None or
                                 str(task.priority) == grouping_key)
            elif strategy == BatchStrategy.BY_SIZE:
                should_include = True
            elif strategy == BatchStrategy.BY_TIME:
                # Group tasks created within the time window
                if not tasks:
                    should_include = True
                else:
                    time_diff = task.created_at - tasks[0].created_at
                    should_include = time_diff <= self.default_max_wait

            if should_include:
                tasks.append(task)

        return tasks

    def _process_loop(self):
        """Main processing loop for automatic batch processing."""
        while self._running:
            try:
                with self.lock:
                    # Wait for tasks or timeout
                    if not self.pending_tasks:
                        self.condition.wait(timeout=1)

                    # Try to create and process batches
                    batch_id = self.create_batch()

                    if batch_id:
                        batch = self.batches.get(batch_id)
                        if batch and len(batch.tasks) >= batch.max_size:
                            # Batch is full, process immediately
                            self._process_batch(batch_id)
                        else:
                            # Wait for more tasks or timeout
                            time.sleep(0.1)

                # Check for batches that need processing (timeout reached)
                self._check_batch_timeouts()

            except Exception as e:
                # Handle error
                time.sleep(1)

    def _check_batch_timeouts(self):
        """Check if any batches have exceeded their wait time."""
        current_time = time.time()

        with self.lock:
            for batch_id, batch in list(self.batches.items()):
                if batch.status == "pending":
                    elapsed = current_time - batch.created_at
                    if elapsed >= batch.max_wait_time or len(batch.tasks) >= batch.max_size:
                        self._process_batch(batch_id)

    def process_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Process a batch manually.

        Args:
            batch_id: ID of the batch to process

        Returns:
            Processing results
        """
        with self.lock:
            batch = self.batches.get(batch_id)
            if not batch:
                return {"error": "Batch not found"}

            return self._process_batch(batch_id)

    def _process_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Internal method to process a batch.

        Args:
            batch_id: ID of the batch to process

        Returns:
            Processing results
        """
        batch = self.batches.get(batch_id)
        if not batch:
            return {"error": "Batch not found"}

        batch.status = "processing"
        results = {}
        completed = 0
        failed = 0

        try:
            if self._batch_handler:
                # Use custom handler
                handler_results = self._batch_handler(batch.tasks)

                for task, result in zip(batch.tasks, handler_results.get("results", [])):
                    if result.get("success"):
                        task.status = "completed"
                        task.result = result.get("data")
                        completed += 1
                    else:
                        task.status = "failed"
                        task.error = result.get("error", "Unknown error")
                        failed += 1
            else:
                # Default processing - mark all as completed
                for task in batch.tasks:
                    task.status = "completed"
                    task.result = {"batched": True}
                    completed += 1

            batch.status = "completed"
            results["success"] = True
            results["completed"] = completed
            results["failed"] = failed

        except Exception as e:
            batch.status = "failed"
            for task in batch.tasks:
                task.status = "failed"
                task.error = str(e)
                failed += 1

            results["success"] = False
            results["error"] = str(e)
            results["completed"] = completed
            results["failed"] = failed

        self.completed_tasks += completed
        self.failed_tasks += failed

        return results

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task.

        Args:
            task_id: Task ID

        Returns:
            Task status or None if not found
        """
        with self.lock:
            # Check pending tasks
            for task in self.pending_tasks:
                if task.id == task_id:
                    return task.to_dict()

            # Check batches
            for batch in self.batches.values():
                for task in batch.tasks:
                    if task.id == task_id:
                        return task.to_dict()

            return None

    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a batch.

        Args:
            batch_id: Batch ID

        Returns:
            Batch status or None if not found
        """
        with self.lock:
            batch = self.batches.get(batch_id)
            if batch:
                return batch.to_dict()
            return None

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get batch processor metrics.

        Returns:
            Metrics dictionary
        """
        with self.lock:
            pending_count = len(self.pending_tasks)
            active_batches = sum(1 for b in self.batches.values()
                               if b.status in ["pending", "processing"])

            return {
                "total_tasks": self.total_tasks,
                "pending_tasks": pending_count,
                "total_batches": self.total_batches,
                "active_batches": active_batches,
                "completed_tasks": self.completed_tasks,
                "failed_tasks": self.failed_tasks,
                "success_rate": (
                    self.completed_tasks / max(1, self.completed_tasks + self.failed_tasks)
                ),
            }
