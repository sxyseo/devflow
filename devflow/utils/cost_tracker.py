"""
Cost Tracker - Tracks API costs and resource usage.

Monitors and tracks costs for API calls, agent operations, and system resources.
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from enum import Enum

from ..config.settings import settings


class CostType(Enum):
    """Types of costs to track."""
    API_CALL = "api_call"
    AGENT_OPERATION = "agent_operation"
    TOKEN_USAGE = "token_usage"
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    OTHER = "other"


class CostTracker:
    """
    Tracks costs for the DevFlow system.

    Maintains cost tracking for:
    - API calls (Claude, OpenAI, etc.)
    - Agent operations
    - Token usage
    - System resources
    """

    def __init__(self):
        self.cost_file = settings.state_dir / "costs.json"
        self.lock = threading.Lock()

        # Cost tracking dictionaries
        self.api_calls: Dict[str, Dict[str, Any]] = {}
        self.agent_operations: Dict[str, Dict[str, Any]] = {}
        self.token_usage: Dict[str, Dict[str, Any]] = {}
        self.resource_costs: Dict[str, Dict[str, Any]] = {}
        self.summary: Dict[str, Any] = {
            "total_cost": 0.0,
            "daily_cost": 0.0,
            "api_call_count": 0,
            "agent_operation_count": 0,
            "total_tokens": 0,
        }

        # Load existing costs if available
        self.load()

    def record_api_call(self, call_id: str, provider: str, model: str,
                       input_tokens: int, output_tokens: int,
                       cost: float, metadata: Dict[str, Any] = None):
        """Record an API call with associated costs."""
        with self.lock:
            self.api_calls[call_id] = {
                "id": call_id,
                "type": CostType.API_CALL.value,
                "provider": provider,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost": cost,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }

            self.summary["api_call_count"] += 1
            self.summary["total_tokens"] += input_tokens + output_tokens
            self.summary["total_cost"] += cost
            self.summary["daily_cost"] += cost

            self.save()

    def record_agent_operation(self, operation_id: str, agent_type: str,
                              operation: str, duration_seconds: float,
                              cost: float = 0.0, metadata: Dict[str, Any] = None):
        """Record an agent operation with associated costs."""
        with self.lock:
            self.agent_operations[operation_id] = {
                "id": operation_id,
                "type": CostType.AGENT_OPERATION.value,
                "agent_type": agent_type,
                "operation": operation,
                "duration_seconds": duration_seconds,
                "cost": cost,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }

            self.summary["agent_operation_count"] += 1
            self.summary["total_cost"] += cost
            self.summary["daily_cost"] += cost

            self.save()

    def record_token_usage(self, usage_id: str, provider: str, model: str,
                          tokens: int, cost_per_token: float,
                          metadata: Dict[str, Any] = None):
        """Record token usage with associated costs."""
        with self.lock:
            cost = tokens * cost_per_token

            self.token_usage[usage_id] = {
                "id": usage_id,
                "type": CostType.TOKEN_USAGE.value,
                "provider": provider,
                "model": model,
                "tokens": tokens,
                "cost_per_token": cost_per_token,
                "total_cost": cost,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }

            self.summary["total_tokens"] += tokens
            self.summary["total_cost"] += cost
            self.summary["daily_cost"] += cost

            self.save()

    def record_resource_cost(self, resource_id: str, cost_type: CostType,
                           amount: float, unit: str, cost: float,
                           metadata: Dict[str, Any] = None):
        """Record a resource cost (compute, storage, network, etc.)."""
        with self.lock:
            self.resource_costs[resource_id] = {
                "id": resource_id,
                "type": cost_type.value,
                "amount": amount,
                "unit": unit,
                "cost": cost,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }

            self.summary["total_cost"] += cost
            self.summary["daily_cost"] += cost

            self.save()

    def get_api_call(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific API call."""
        return self.api_calls.get(call_id)

    def get_agent_operation(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific agent operation."""
        return self.agent_operations.get(operation_id)

    def get_api_calls_by_provider(self, provider: str) -> List[Dict[str, Any]]:
        """Get all API calls for a specific provider."""
        with self.lock:
            return [call for call in self.api_calls.values()
                   if call["provider"] == provider]

    def get_api_calls_by_model(self, model: str) -> List[Dict[str, Any]]:
        """Get all API calls for a specific model."""
        with self.lock:
            return [call for call in self.api_calls.values()
                   if call["model"] == model]

    def get_agent_operations_by_type(self, agent_type: str) -> List[Dict[str, Any]]:
        """Get all operations for a specific agent type."""
        with self.lock:
            return [op for op in self.agent_operations.values()
                   if op["agent_type"] == agent_type]

    def get_costs_by_time_range(self, start_time: str, end_time: str
                               ) -> Dict[str, List[Dict[str, Any]]]:
        """Get all costs within a time range."""
        with self.lock:
            result = {
                "api_calls": [],
                "agent_operations": [],
                "token_usage": [],
                "resource_costs": [],
            }

            for call in self.api_calls.values():
                if start_time <= call["timestamp"] <= end_time:
                    result["api_calls"].append(call)

            for op in self.agent_operations.values():
                if start_time <= op["timestamp"] <= end_time:
                    result["agent_operations"].append(op)

            for usage in self.token_usage.values():
                if start_time <= usage["timestamp"] <= end_time:
                    result["token_usage"].append(usage)

            for cost in self.resource_costs.values():
                if start_time <= cost["timestamp"] <= end_time:
                    result["resource_costs"].append(cost)

            return result

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get a summary of all costs."""
        with self.lock:
            # Calculate costs by provider
            provider_costs = {}
            for call in self.api_calls.values():
                provider = call["provider"]
                if provider not in provider_costs:
                    provider_costs[provider] = {
                        "total_cost": 0.0,
                        "total_tokens": 0,
                        "call_count": 0,
                    }
                provider_costs[provider]["total_cost"] += call["cost"]
                provider_costs[provider]["total_tokens"] += call["total_tokens"]
                provider_costs[provider]["call_count"] += 1

            # Calculate costs by model
            model_costs = {}
            for call in self.api_calls.values():
                model = call["model"]
                if model not in model_costs:
                    model_costs[model] = {
                        "total_cost": 0.0,
                        "total_tokens": 0,
                        "call_count": 0,
                    }
                model_costs[model]["total_cost"] += call["cost"]
                model_costs[model]["total_tokens"] += call["total_tokens"]
                model_costs[model]["call_count"] += 1

            # Calculate costs by agent type
            agent_costs = {}
            for op in self.agent_operations.values():
                agent_type = op["agent_type"]
                if agent_type not in agent_costs:
                    agent_costs[agent_type] = {
                        "total_cost": 0.0,
                        "operation_count": 0,
                        "total_duration": 0.0,
                    }
                agent_costs[agent_type]["total_cost"] += op["cost"]
                agent_costs[agent_type]["operation_count"] += 1
                agent_costs[agent_type]["total_duration"] += op["duration_seconds"]

            return {
                "summary": self.summary.copy(),
                "by_provider": provider_costs,
                "by_model": model_costs,
                "by_agent_type": agent_costs,
                "timestamp": datetime.utcnow().isoformat(),
            }

    def get_daily_costs(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily costs for the specified number of days."""
        with self.lock:
            from datetime import timedelta

            daily_costs = []
            for i in range(days):
                date = datetime.utcnow() - timedelta(days=i)
                date_str = date.strftime("%Y-%m-%d")

                # Calculate costs for this day
                day_cost = 0.0
                day_tokens = 0
                day_calls = 0

                for call in self.api_calls.values():
                    if call["timestamp"].startswith(date_str):
                        day_cost += call["cost"]
                        day_tokens += call["total_tokens"]
                        day_calls += 1

                for op in self.agent_operations.values():
                    if op["timestamp"].startswith(date_str):
                        day_cost += op["cost"]

                for usage in self.token_usage.values():
                    if usage["timestamp"].startswith(date_str):
                        day_cost += usage["total_cost"]
                        day_tokens += usage["tokens"]

                for cost in self.resource_costs.values():
                    if cost["timestamp"].startswith(date_str):
                        day_cost += cost["cost"]

                daily_costs.append({
                    "date": date_str,
                    "total_cost": day_cost,
                    "total_tokens": day_tokens,
                    "api_call_count": day_calls,
                })

            return daily_costs

    def reset_daily_cost(self):
        """Reset daily cost counter."""
        with self.lock:
            self.summary["daily_cost"] = 0.0
            self.save()

    def save(self):
        """Save costs to disk."""
        self.cost_file.parent.mkdir(parents=True, exist_ok=True)

        costs = {
            "api_calls": self.api_calls,
            "agent_operations": self.agent_operations,
            "token_usage": self.token_usage,
            "resource_costs": self.resource_costs,
            "summary": self.summary,
        }

        with open(self.cost_file, 'w') as f:
            json.dump(costs, f, indent=2, default=str)

    def load(self):
        """Load costs from disk."""
        if self.cost_file.exists():
            with open(self.cost_file, 'r') as f:
                costs = json.load(f)

            self.api_calls = costs.get("api_calls", {})
            self.agent_operations = costs.get("agent_operations", {})
            self.token_usage = costs.get("token_usage", {})
            self.resource_costs = costs.get("resource_costs", {})
            self.summary = costs.get("summary", self.summary)

    def reset(self):
        """Reset all cost tracking."""
        with self.lock:
            self.api_calls.clear()
            self.agent_operations.clear()
            self.token_usage.clear()
            self.resource_costs.clear()
            self.summary = {
                "total_cost": 0.0,
                "daily_cost": 0.0,
                "api_call_count": 0,
                "agent_operation_count": 0,
                "total_tokens": 0,
            }
            self.save()
