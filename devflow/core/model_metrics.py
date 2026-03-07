"""
Model Metrics - Performance monitoring and tracking for AI models.

Tracks latency, cost, success rate, and other performance metrics for model usage.
"""

import time
import threading
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json
from pathlib import Path


class MetricType(Enum):
    """Types of metrics that can be tracked."""
    LATENCY = "latency"
    COST = "cost"
    SUCCESS_RATE = "success_rate"
    TOKEN_USAGE = "token_usage"
    ERROR_RATE = "error_rate"
    throughput = "throughput"


@dataclass
class MetricRecord:
    """Single metric record."""
    timestamp: float
    model_id: str
    provider: str
    latency_ms: float
    cost_usd: float
    input_tokens: int
    output_tokens: int
    success: bool
    error_message: Optional[str] = None
    task_type: Optional[str] = None
    agent_type: Optional[str] = None


@dataclass
class ModelStatistics:
    """Aggregated statistics for a model."""
    model_id: str
    provider: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    total_cost_usd: float
    avg_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    avg_input_tokens: int
    avg_output_tokens: int
    success_rate: float
    error_rate: float
    last_updated: float
    latencies: List[float] = field(default_factory=list)
    costs: List[float] = field(default_factory=list)


@dataclass
class MetricsSummary:
    """Summary of metrics across all models."""
    total_requests: int
    total_cost_usd: float
    total_tokens: int
    overall_success_rate: float
    most_used_model: str
    fastest_model: str
    most_cost_effective_model: str
    model_count: int


class ModelMetrics:
    """
    Tracks performance metrics for AI models.

    Responsibilities:
    - Record model usage and performance
    - Calculate statistics (latency percentiles, success rate, cost)
    - Provide aggregations and summaries
    - Export metrics for analysis
    - Support metrics persistence
    """

    def __init__(self, max_records: int = 10000):
        """
        Initialize the model metrics tracker.

        Args:
            max_records: Maximum number of records to keep in memory
        """
        self.max_records = max_records
        self.records: List[MetricRecord] = []
        self.model_stats: Dict[str, ModelStatistics] = {}
        self.lock = threading.Lock()
        self.provider_costs: Dict[str, float] = defaultdict(float)

    def record_request(self,
                      model_id: str,
                      provider: str,
                      latency_ms: float,
                      cost_usd: float = 0.0,
                      input_tokens: int = 0,
                      output_tokens: int = 0,
                      success: bool = True,
                      error_message: Optional[str] = None,
                      task_type: Optional[str] = None,
                      agent_type: Optional[str] = None) -> None:
        """
        Record a model request.

        Args:
            model_id: Model identifier
            provider: Provider name
            latency_ms: Request latency in milliseconds
            cost_usd: Cost in USD
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            success: Whether the request was successful
            error_message: Error message if failed
            task_type: Type of task (e.g., 'code_generation', 'analysis')
            agent_type: Type of agent (e.g., 'dev-story', 'code-review')
        """
        record = MetricRecord(
            timestamp=time.time(),
            model_id=model_id,
            provider=provider,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            success=success,
            error_message=error_message,
            task_type=task_type,
            agent_type=agent_type
        )

        with self.lock:
            self.records.append(record)

            # Trim records if exceeding max
            if len(self.records) > self.max_records:
                self.records = self.records[-self.max_records:]

            # Update provider costs
            self.provider_costs[provider] += cost_usd

            # Update model statistics
            self._update_model_stats(record)

    def get_model_statistics(self, model_id: str) -> Optional[ModelStatistics]:
        """
        Get statistics for a specific model.

        Args:
            model_id: Model identifier

        Returns:
            ModelStatistics if available, None otherwise
        """
        with self.lock:
            return self.model_stats.get(model_id)

    def get_all_statistics(self) -> Dict[str, ModelStatistics]:
        """
        Get statistics for all models.

        Returns:
            Dictionary mapping model_id to ModelStatistics
        """
        with self.lock:
            return self.model_stats.copy()

    def get_summary(self) -> MetricsSummary:
        """
        Get overall metrics summary.

        Returns:
            MetricsSummary object with overall statistics
        """
        with self.lock:
            if not self.records:
                return MetricsSummary(
                    total_requests=0,
                    total_cost_usd=0.0,
                    total_tokens=0,
                    overall_success_rate=0.0,
                    most_used_model="",
                    fastest_model="",
                    most_cost_effective_model="",
                    model_count=0
                )

            total_requests = len(self.records)
            successful = sum(1 for r in self.records if r.success)
            total_cost = sum(r.cost_usd for r in self.records)
            total_tokens = sum(r.input_tokens + r.output_tokens for r in self.records)

            # Find most used model
            model_counts = defaultdict(int)
            for r in self.records:
                model_counts[r.model_id] += 1
            most_used = max(model_counts.items(), key=lambda x: x[1])[0] if model_counts else ""

            # Find fastest model (by average latency)
            fastest = ""
            if self.model_stats:
                fastest = min(self.model_stats.items(),
                            key=lambda x: x[1].avg_latency_ms)[0]

            # Find most cost effective (lowest cost per request)
            cost_effective = ""
            if self.model_stats:
                cost_effective = min(self.model_stats.items(),
                                   key=lambda x: x[1].avg_cost_usd)[0]

            return MetricsSummary(
                total_requests=total_requests,
                total_cost_usd=total_cost,
                total_tokens=total_tokens,
                overall_success_rate=successful / total_requests if total_requests > 0 else 0.0,
                most_used_model=most_used,
                fastest_model=fastest,
                most_cost_effective_model=cost_effective,
                model_count=len(self.model_stats)
            )

    def get_latency_percentiles(self, model_id: str) -> Optional[Dict[str, float]]:
        """
        Get latency percentiles for a model.

        Args:
            model_id: Model identifier

        Returns:
            Dictionary with p50, p95, p99 latencies, or None if not available
        """
        stats = self.get_model_statistics(model_id)
        if not stats:
            return None

        return {
            "p50": stats.p50_latency_ms,
            "p95": stats.p95_latency_ms,
            "p99": stats.p99_latency_ms
        }

    def get_success_rate(self, model_id: str, window_minutes: int = 60) -> float:
        """
        Get success rate for a model within a time window.

        Args:
            model_id: Model identifier
            window_minutes: Time window in minutes (default: 60)

        Returns:
            Success rate as a percentage (0-100)
        """
        with self.lock:
            cutoff = time.time() - (window_minutes * 60)
            model_records = [
                r for r in self.records
                if r.model_id == model_id and r.timestamp >= cutoff
            ]

            if not model_records:
                return 0.0

            successful = sum(1 for r in model_records if r.success)
            return (successful / len(model_records)) * 100

    def get_cost_by_provider(self) -> Dict[str, float]:
        """
        Get total cost broken down by provider.

        Returns:
            Dictionary mapping provider name to total cost in USD
        """
        with self.lock:
            return self.provider_costs.copy()

    def get_top_models_by_usage(self, limit: int = 5) -> List[Tuple[str, int]]:
        """
        Get top models by usage count.

        Args:
            limit: Maximum number of models to return

        Returns:
            List of (model_id, usage_count) tuples
        """
        with self.lock:
            model_counts = defaultdict(int)
            for r in self.records:
                model_counts[r.model_id] += 1

            sorted_models = sorted(model_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_models[:limit]

    def get_recent_errors(self, limit: int = 10) -> List[MetricRecord]:
        """
        Get recent error records.

        Args:
            limit: Maximum number of error records to return

        Returns:
            List of MetricRecord objects with success=False
        """
        with self.lock:
            errors = [r for r in self.records if not r.success]
            return errors[-limit:] if errors else []

    def export_metrics(self, filepath: Optional[Path] = None) -> Dict[str, Any]:
        """
        Export metrics to JSON format.

        Args:
            filepath: Optional path to save metrics file

        Returns:
            Dictionary containing all metrics
        """
        with self.lock:
            export_data = {
                "timestamp": time.time(),
                "summary": {
                    "total_requests": len(self.records),
                    "total_cost_usd": sum(r.cost_usd for r in self.records),
                    "total_tokens": sum(r.input_tokens + r.output_tokens for r in self.records),
                    "provider_costs": self.provider_costs
                },
                "models": {}
            }

            for model_id, stats in self.model_stats.items():
                export_data["models"][model_id] = {
                    "provider": stats.provider,
                    "total_requests": stats.total_requests,
                    "successful_requests": stats.successful_requests,
                    "failed_requests": stats.failed_requests,
                    "avg_latency_ms": stats.avg_latency_ms,
                    "min_latency_ms": stats.min_latency_ms,
                    "max_latency_ms": stats.max_latency_ms,
                    "p50_latency_ms": stats.p50_latency_ms,
                    "p95_latency_ms": stats.p95_latency_ms,
                    "p99_latency_ms": stats.p99_latency_ms,
                    "total_cost_usd": stats.total_cost_usd,
                    "avg_cost_usd": stats.avg_cost_usd,
                    "total_input_tokens": stats.total_input_tokens,
                    "total_output_tokens": stats.total_output_tokens,
                    "success_rate": stats.success_rate,
                    "error_rate": stats.error_rate,
                    "last_updated": stats.last_updated
                }

            if filepath:
                with open(filepath, 'w') as f:
                    json.dump(export_data, f, indent=2)

            return export_data

    def import_metrics(self, data: Dict[str, Any]) -> None:
        """
        Import metrics from JSON format.

        Args:
            data: Dictionary containing metrics data
        """
        # This is a simplified import - in production you'd want more validation
        with self.lock:
            self.provider_costs = data.get("summary", {}).get("provider_costs", {})

            # Note: We don't restore individual records on import
            # Statistics would need to be recalculated if needed

    def reset_metrics(self, model_id: Optional[str] = None) -> None:
        """
        Reset metrics for a specific model or all models.

        Args:
            model_id: Optional model ID to reset. If None, resets all metrics.
        """
        with self.lock:
            if model_id:
                # Reset specific model
                if model_id in self.model_stats:
                    del self.model_stats[model_id]
                self.records = [r for r in self.records if r.model_id != model_id]
            else:
                # Reset all
                self.records.clear()
                self.model_stats.clear()
                self.provider_costs.clear()

    def _update_model_stats(self, record: MetricRecord) -> None:
        """
        Update statistics for a model based on a new record.

        Args:
            record: MetricRecord to incorporate into statistics
        """
        model_id = record.model_id

        if model_id not in self.model_stats:
            self.model_stats[model_id] = ModelStatistics(
                model_id=model_id,
                provider=record.provider,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_latency_ms=0.0,
                min_latency_ms=float('inf'),
                max_latency_ms=0.0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                total_cost_usd=0.0,
                avg_cost_usd=0.0,
                total_input_tokens=0,
                total_output_tokens=0,
                avg_input_tokens=0,
                avg_output_tokens=0,
                success_rate=0.0,
                error_rate=0.0,
                last_updated=record.timestamp
            )

        stats = self.model_stats[model_id]
        stats.total_requests += 1

        if record.success:
            stats.successful_requests += 1
        else:
            stats.failed_requests += 1

        # Update latency
        stats.latencies.append(record.latency_ms)
        stats.min_latency_ms = min(stats.min_latency_ms, record.latency_ms)
        stats.max_latency_ms = max(stats.max_latency_ms, record.latency_ms)

        # Update cost
        stats.costs.append(record.cost_usd)
        stats.total_cost_usd += record.cost_usd

        # Update tokens
        stats.total_input_tokens += record.input_tokens
        stats.total_output_tokens += record.output_tokens

        # Calculate averages
        stats.avg_latency_ms = sum(stats.latencies) / len(stats.latencies)
        stats.avg_cost_usd = stats.total_cost_usd / stats.total_requests
        stats.avg_input_tokens = stats.total_input_tokens / stats.total_requests
        stats.avg_output_tokens = stats.total_output_tokens / stats.total_requests

        # Calculate rates
        stats.success_rate = stats.successful_requests / stats.total_requests
        stats.error_rate = stats.failed_requests / stats.total_requests

        # Calculate percentiles
        sorted_latencies = sorted(stats.latencies)
        n = len(sorted_latencies)
        if n > 0:
            stats.p50_latency_ms = sorted_latencies[int(n * 0.5)]
            stats.p95_latency_ms = sorted_latencies[int(n * 0.95)] if n >= 20 else sorted_latencies[-1]
            stats.p99_latency_ms = sorted_latencies[int(n * 0.99)] if n >= 100 else sorted_latencies[-1]

        stats.last_updated = record.timestamp

    def get_metrics_by_task_type(self, task_type: str) -> Dict[str, ModelStatistics]:
        """
        Get statistics filtered by task type.

        Args:
            task_type: Task type to filter by

        Returns:
            Dictionary mapping model_id to ModelStatistics
        """
        with self.lock:
            task_records = [r for r in self.records if r.task_type == task_type]

            if not task_records:
                return {}

            # Build temporary stats for this task type
            task_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
                "latencies": [],
                "costs": [],
                "total_requests": 0,
                "successful": 0,
                "failed": 0,
                "total_cost": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "provider": ""
            })

            for record in task_records:
                stats = task_stats[record.model_id]
                stats["latencies"].append(record.latency_ms)
                stats["costs"].append(record.cost_usd)
                stats["total_requests"] += 1
                stats["total_cost"] += record.cost_usd
                stats["total_input_tokens"] += record.input_tokens
                stats["total_output_tokens"] += record.output_tokens
                stats["provider"] = record.provider

                if record.success:
                    stats["successful"] += 1
                else:
                    stats["failed"] += 1

            # Convert to ModelStatistics objects
            result = {}
            for model_id, stats in task_stats.items():
                sorted_latencies = sorted(stats["latencies"])
                n = len(sorted_latencies)

                result[model_id] = ModelStatistics(
                    model_id=model_id,
                    provider=stats["provider"],
                    total_requests=stats["total_requests"],
                    successful_requests=stats["successful"],
                    failed_requests=stats["failed"],
                    avg_latency_ms=sum(stats["latencies"]) / n if n > 0 else 0.0,
                    min_latency_ms=min(stats["latencies"]) if stats["latencies"] else 0.0,
                    max_latency_ms=max(stats["latencies"]) if stats["latencies"] else 0.0,
                    p50_latency_ms=sorted_latencies[int(n * 0.5)] if n > 0 else 0.0,
                    p95_latency_ms=sorted_latencies[int(n * 0.95)] if n >= 20 else (sorted_latencies[-1] if n > 0 else 0.0),
                    p99_latency_ms=sorted_latencies[int(n * 0.99)] if n >= 100 else (sorted_latencies[-1] if n > 0 else 0.0),
                    total_cost_usd=stats["total_cost"],
                    avg_cost_usd=stats["total_cost"] / n if n > 0 else 0.0,
                    total_input_tokens=stats["total_input_tokens"],
                    total_output_tokens=stats["total_output_tokens"],
                    avg_input_tokens=stats["total_input_tokens"] / n if n > 0 else 0,
                    avg_output_tokens=stats["total_output_tokens"] / n if n > 0 else 0,
                    success_rate=stats["successful"] / n if n > 0 else 0.0,
                    error_rate=stats["failed"] / n if n > 0 else 0.0,
                    last_updated=time.time()
                )

            return result

    def get_metrics_by_agent_type(self, agent_type: str) -> Dict[str, ModelStatistics]:
        """
        Get statistics filtered by agent type.

        Args:
            agent_type: Agent type to filter by

        Returns:
            Dictionary mapping model_id to ModelStatistics
        """
        with self.lock:
            agent_records = [r for r in self.records if r.agent_type == agent_type]

            if not agent_records:
                return {}

            # Build temporary stats for this agent type
            agent_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
                "latencies": [],
                "costs": [],
                "total_requests": 0,
                "successful": 0,
                "failed": 0,
                "total_cost": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "provider": ""
            })

            for record in agent_records:
                stats = agent_stats[record.model_id]
                stats["latencies"].append(record.latency_ms)
                stats["costs"].append(record.cost_usd)
                stats["total_requests"] += 1
                stats["total_cost"] += record.cost_usd
                stats["total_input_tokens"] += record.input_tokens
                stats["total_output_tokens"] += record.output_tokens
                stats["provider"] = record.provider

                if record.success:
                    stats["successful"] += 1
                else:
                    stats["failed"] += 1

            # Convert to ModelStatistics objects
            result = {}
            for model_id, stats in agent_stats.items():
                sorted_latencies = sorted(stats["latencies"])
                n = len(sorted_latencies)

                result[model_id] = ModelStatistics(
                    model_id=model_id,
                    provider=stats["provider"],
                    total_requests=stats["total_requests"],
                    successful_requests=stats["successful"],
                    failed_requests=stats["failed"],
                    avg_latency_ms=sum(stats["latencies"]) / n if n > 0 else 0.0,
                    min_latency_ms=min(stats["latencies"]) if stats["latencies"] else 0.0,
                    max_latency_ms=max(stats["latencies"]) if stats["latencies"] else 0.0,
                    p50_latency_ms=sorted_latencies[int(n * 0.5)] if n > 0 else 0.0,
                    p95_latency_ms=sorted_latencies[int(n * 0.95)] if n >= 20 else (sorted_latencies[-1] if n > 0 else 0.0),
                    p99_latency_ms=sorted_latencies[int(n * 0.99)] if n >= 100 else (sorted_latencies[-1] if n > 0 else 0.0),
                    total_cost_usd=stats["total_cost"],
                    avg_cost_usd=stats["total_cost"] / n if n > 0 else 0.0,
                    total_input_tokens=stats["total_input_tokens"],
                    total_output_tokens=stats["total_output_tokens"],
                    avg_input_tokens=stats["total_input_tokens"] / n if n > 0 else 0,
                    avg_output_tokens=stats["total_output_tokens"] / n if n > 0 else 0,
                    success_rate=stats["successful"] / n if n > 0 else 0.0,
                    error_rate=stats["failed"] / n if n > 0 else 0.0,
                    last_updated=time.time()
                )

            return result
