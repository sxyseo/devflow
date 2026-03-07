"""
Model Selector - Automatic model selection based on task type, cost, and availability.

Intelligently selects the best model for a given task considering capabilities, cost,
and performance metrics.
"""

import threading
import time
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

from .model_manager import ModelManager, ModelConfig, ModelProviderType


class SelectionStrategy(Enum):
    """Model selection strategies."""
    BALANCED = "balanced"
    COST_OPTIMIZED = "cost_optimized"
    QUALITY_OPTIMIZED = "quality_optimized"
    SPEED_OPTIMIZED = "speed_optimized"


@dataclass
class SelectionCriteria:
    """Criteria for model selection."""
    task_type: str
    max_cost: Optional[float] = None
    strategy: SelectionStrategy = SelectionStrategy.BALANCED
    preferred_providers: List[str] = field(default_factory=list)
    excluded_models: Set[str] = field(default_factory=set)
    require_capability: Optional[str] = None


@dataclass
class SelectionResult:
    """Result of model selection."""
    model_id: str
    provider: str
    score: float
    reason: str
    estimated_cost: float
    estimated_latency: float
    fallback_available: bool


class ModelSelector:
    """
    Selects the best model for a given task.

    Responsibilities:
    - Task-based model selection
    - Cost-aware selection
    - Performance-based selection
    - Fallback model management
    - Selection strategy application
    """

    def __init__(self, model_manager: ModelManager, config_path: Optional[Path] = None):
        """
        Initialize the model selector.

        Args:
            model_manager: ModelManager instance
            config_path: Optional path to selection configuration file
        """
        self.model_manager = model_manager
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
        self.lock = threading.Lock()

        # Performance metrics cache for models
        self.model_metrics: Dict[str, Dict[str, Any]] = {}

        # Track recently used models for fallback
        self.recent_failures: Dict[str, float] = {}

    def _get_default_config_path(self) -> Path:
        """Get default configuration file path."""
        project_root = Path(__file__).parent.parent.parent
        return project_root / "devflow" / "config" / "model_config.json"

    def _load_config(self) -> Dict[str, Any]:
        """
        Load selection configuration from file.

        Returns:
            Configuration dictionary
        """
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {
            "task_mappings": {},
            "agent_mappings": {},
            "fallback_config": {},
            "cost_optimization": {},
            "selection_strategy": {}
        }

    def select_model(self, criteria: SelectionCriteria) -> Optional[SelectionResult]:
        """
        Select the best model based on criteria.

        Args:
            criteria: SelectionCriteria object

        Returns:
            SelectionResult if a suitable model is found, None otherwise
        """
        # Get task mapping
        task_mapping = self.config.get("task_mappings", {}).get(criteria.task_type)

        if not task_mapping:
            # Default to code_generation if no specific mapping
            task_mapping = self.config.get("task_mappings", {}).get("code_generation")

        if not task_mapping:
            return None

        # Get candidate models
        preferred_models = task_mapping.get("preferred_models", [])
        fallback_models = task_mapping.get("fallback_models", [])

        # Combine and deduplicate candidates
        all_candidates = list(dict.fromkeys(preferred_models + fallback_models))

        # Filter by excluded models
        candidates = [
            m for m in all_candidates
            if m not in criteria.excluded_models
        ]

        # Score each candidate
        scored_candidates = []
        for model_ref in candidates:
            provider_name, model_id = self._parse_model_ref(model_ref)

            # Check if model exists and is available
            model = self._get_model_config(provider_name, model_id)
            if not model or not model.available:
                continue

            # Check if model has required capability
            if criteria.require_capability:
                if criteria.require_capability not in model.capabilities:
                    continue

            # Filter by preferred providers
            if criteria.preferred_providers and provider_name not in criteria.preferred_providers:
                continue

            # Check recent failures
            if self._is_model_failing(model_id):
                continue

            # Score the model
            score = self._score_model(model, criteria)

            # Estimate cost and latency
            estimated_cost = self._estimate_task_cost(model, criteria)
            estimated_latency = self._estimate_latency(model, criteria)

            # Check max cost constraint
            if criteria.max_cost and estimated_cost > criteria.max_cost:
                continue

            scored_candidates.append({
                "model_ref": model_ref,
                "model_id": model_id,
                "provider": provider_name,
                "model": model,
                "score": score,
                "estimated_cost": estimated_cost,
                "estimated_latency": estimated_latency
            })

        if not scored_candidates:
            return None

        # Sort by score (descending)
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)

        # Get best candidate
        best = scored_candidates[0]

        # Check if fallback is available
        fallback_available = len(scored_candidates) > 1

        return SelectionResult(
            model_id=best["model_id"],
            provider=best["provider"],
            score=best["score"],
            reason=self._generate_selection_reason(best, criteria),
            estimated_cost=best["estimated_cost"],
            estimated_latency=best["estimated_latency"],
            fallback_available=fallback_available
        )

    def select_model_for_agent(self, agent_type: str,
                              task: str = None,
                              strategy: SelectionStrategy = SelectionStrategy.BALANCED,
                              excluded_models: Set[str] = None) -> Optional[SelectionResult]:
        """
        Select a model for a specific agent type.

        Args:
            agent_type: Type of agent (e.g., 'dev-story', 'code-review')
            task: Optional task description
            strategy: Selection strategy
            excluded_models: Models to exclude from selection

        Returns:
            SelectionResult if a suitable model is found, None otherwise
        """
        # Get agent mapping
        agent_mapping = self.config.get("agent_mappings", {}).get(agent_type)

        if not agent_mapping:
            return None

        task_type = agent_mapping.get("task_type", "analysis")
        model_override = agent_mapping.get("model_override")

        # If model override is specified, use it
        if model_override:
            provider_name, model_id = self._parse_model_ref(model_override)
            model = self._get_model_config(provider_name, model_id)
            if model and model.available:
                return SelectionResult(
                    model_id=model_id,
                    provider=provider_name,
                    score=1.0,
                    reason=f"Model override for {agent_type}",
                    estimated_cost=0.0,
                    estimated_latency=0.0,
                    fallback_available=False
                )

        # Create selection criteria
        criteria = SelectionCriteria(
            task_type=task_type,
            strategy=strategy,
            excluded_models=excluded_models or set()
        )

        return self.select_model(criteria)

    def get_fallback_model(self, current_model_id: str,
                          criteria: SelectionCriteria) -> Optional[SelectionResult]:
        """
        Get a fallback model when the current model fails.

        Args:
            current_model_id: Model that failed
            criteria: Original selection criteria

        Returns:
            SelectionResult for fallback model, None if no fallback available
        """
        # Record failure
        self._record_model_failure(current_model_id)

        # Get task mapping
        task_mapping = self.config.get("task_mappings", {}).get(criteria.task_type)
        if not task_mapping:
            return None

        # Find and exclude the failed model reference
        all_models = (
            task_mapping.get("preferred_models", []) +
            task_mapping.get("fallback_models", [])
        )
        for model_ref in all_models:
            _, model_id = self._parse_model_ref(model_ref)
            if model_id == current_model_id:
                criteria.excluded_models.add(model_ref)
                break

        # Get fallback models
        fallback_models = task_mapping.get("fallback_models", [])

        for model_ref in fallback_models:
            provider_name, model_id = self._parse_model_ref(model_ref)

            # Skip if this is the failed model
            if model_id == current_model_id:
                continue

            # Skip if excluded
            if model_ref in criteria.excluded_models:
                continue

            model = self._get_model_config(provider_name, model_id)
            if not model or not model.available:
                continue

            # Check if there are more fallbacks available
            remaining_fallbacks = [
                m for m in fallback_models
                if m != model_ref and m not in criteria.excluded_models
            ]

            return SelectionResult(
                model_id=model_id,
                provider=provider_name,
                score=0.5,
                reason=f"Fallback model after {current_model_id} failure",
                estimated_cost=self._estimate_task_cost(model, criteria),
                estimated_latency=self._estimate_latency(model, criteria),
                fallback_available=len(remaining_fallbacks) > 0
            )

        return None

    def update_model_metrics(self, model_id: str,
                            latency: float,
                            success: bool,
                            token_count: int = 0):
        """
        Update performance metrics for a model.

        Args:
            model_id: Model identifier
            latency: Request latency in milliseconds
            success: Whether the request was successful
            token_count: Number of tokens processed
        """
        with self.lock:
            if model_id not in self.model_metrics:
                self.model_metrics[model_id] = {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "total_latency": 0.0,
                    "total_tokens": 0,
                    "avg_latency": 0.0,
                    "success_rate": 0.0,
                    "last_updated": time.time()
                }

            metrics = self.model_metrics[model_id]
            metrics["total_requests"] += 1
            metrics["total_latency"] += latency
            metrics["total_tokens"] += token_count

            if success:
                metrics["successful_requests"] += 1
            else:
                metrics["failed_requests"] += 1

            # Update averages
            metrics["avg_latency"] = metrics["total_latency"] / metrics["total_requests"]
            metrics["success_rate"] = metrics["successful_requests"] / metrics["total_requests"]
            metrics["last_updated"] = time.time()

    def get_model_metrics(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metrics for a specific model.

        Args:
            model_id: Model identifier

        Returns:
            Metrics dictionary if available, None otherwise
        """
        return self.model_metrics.get(model_id)

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get metrics for all models.

        Returns:
            Dictionary mapping model_id to metrics
        """
        return self.model_metrics.copy()

    def _parse_model_ref(self, model_ref: str) -> tuple:
        """
        Parse model reference into provider and model_id.

        Args:
            model_ref: Model reference (e.g., 'anthropic/claude-3-5-sonnet-20241022')

        Returns:
            Tuple of (provider, model_id)
        """
        if "/" in model_ref:
            return model_ref.split("/", 1)
        return "", model_ref

    def _get_model_config(self, provider_name: str, model_id: str) -> Optional[ModelConfig]:
        """
        Get model configuration from provider.

        Args:
            provider_name: Name of provider
            model_id: Model identifier

        Returns:
            ModelConfig if found, None otherwise
        """
        # Map provider name to type
        provider_type_map = {
            "anthropic": ModelProviderType.ANTHROPIC,
            "openai": ModelProviderType.OPENAI,
            "local": ModelProviderType.LOCAL
        }

        provider_type = provider_type_map.get(provider_name.lower())
        if not provider_type:
            return None

        provider = self.model_manager.get_provider(provider_type)
        if not provider:
            return None

        return provider.get_model(model_id)

    def _score_model(self, model: ModelConfig, criteria: SelectionCriteria) -> float:
        """
        Score a model based on selection criteria.

        Args:
            model: Model configuration
            criteria: Selection criteria

        Returns:
            Score between 0 and 1
        """
        strategy_config = self.config.get("selection_strategy", {})
        strategies = strategy_config.get("strategies", {})

        # Get strategy weights
        strategy_key = criteria.strategy.value
        strategy_weights = strategies.get(strategy_key, {}).get("weights", {
            "cost": 0.3,
            "speed": 0.3,
            "quality": 0.4
        })

        # Calculate individual scores
        cost_score = self._calculate_cost_score(model, criteria)
        speed_score = self._calculate_speed_score(model, criteria)
        quality_score = self._calculate_quality_score(model, criteria)

        # Weighted score
        score = (
            strategy_weights.get("cost", 0.3) * cost_score +
            strategy_weights.get("speed", 0.3) * speed_score +
            strategy_weights.get("quality", 0.4) * quality_score
        )

        # Boost by priority (lower priority number = higher priority)
        priority_boost = 1.0 / (model.priority or 1)

        return score * priority_boost

    def _calculate_cost_score(self, model: ModelConfig, criteria: SelectionCriteria) -> float:
        """Calculate cost score (lower is better)."""
        total_cost = model.input_cost_per_1k + model.output_cost_per_1k

        # Normalize: assume max cost is $0.10 per 1k tokens
        max_cost = 0.10
        normalized = 1.0 - min(total_cost / max_cost, 1.0)

        return normalized

    def _calculate_speed_score(self, model: ModelConfig, criteria: SelectionCriteria) -> float:
        """Calculate speed score based on metrics and priority."""
        # Use priority as proxy for speed (Haiku/GPT-3.5 are faster)
        priority_speed_map = {
            3: 1.0,  # Fastest (Haiku, GPT-3.5)
            2: 0.7,  # Medium
            1: 0.5   # Slower (Opus, GPT-4)
        }

        return priority_speed_map.get(model.priority, 0.5)

    def _calculate_quality_score(self, model: ModelConfig, criteria: SelectionCriteria) -> float:
        """Calculate quality score based on priority and capabilities."""
        # Priority is inverse: 1 = highest quality
        priority_quality_map = {
            1: 1.0,  # Highest quality (Sonnet, GPT-4 Turbo)
            2: 0.8,  # High quality (Opus, GPT-4)
            3: 0.6   # Good quality (Haiku, GPT-3.5)
        }

        base_score = priority_quality_map.get(model.priority, 0.5)

        # Boost for complex reasoning capability
        if "complex_reasoning" in model.capabilities:
            base_score *= 1.1

        return min(base_score, 1.0)

    def _estimate_task_cost(self, model: ModelConfig, criteria: SelectionCriteria) -> float:
        """
        Estimate cost for a task.

        Args:
            model: Model configuration
            criteria: Selection criteria

        Returns:
            Estimated cost in USD
        """
        # Rough estimate: assume 10k input, 5k output tokens
        estimated_input = 10000
        estimated_output = 5000

        cost_per_1k = model.input_cost_per_1k + model.output_cost_per_1k

        return (estimated_input / 1000) * model.input_cost_per_1k + \
               (estimated_output / 1000) * model.output_cost_per_1k

    def _estimate_latency(self, model: ModelConfig, criteria: SelectionCriteria) -> float:
        """
        Estimate latency for a task.

        Args:
            model: Model configuration
            criteria: Selection criteria

        Returns:
            Estimated latency in milliseconds
        """
        # Use historical metrics if available
        metrics = self.model_metrics.get(model.model_id)
        if metrics and metrics["total_requests"] > 0:
            return metrics["avg_latency"]

        # Default estimates based on priority
        priority_latency_map = {
            1: 3000,   # 3 seconds for premium models
            2: 5000,   # 5 seconds for high-end models
            3: 1000    # 1 second for fast models
        }

        return float(priority_latency_map.get(model.priority, 3000))

    def _generate_selection_reason(self, candidate: Dict[str, Any],
                                   criteria: SelectionCriteria) -> str:
        """Generate human-readable reason for selection."""
        model = candidate["model"]
        strategy = criteria.strategy.value

        reason_parts = [
            f"Selected {model.name}",
            f"via {strategy} strategy"
        ]

        if model.priority == 1:
            reason_parts.append("(premium model)")
        elif model.priority == 3:
            reason_parts.append("(fast model)")

        return " ".join(reason_parts)

    def _is_model_failing(self, model_id: str) -> bool:
        """
        Check if a model is currently failing.

        Args:
            model_id: Model identifier

        Returns:
            True if model is failing, False otherwise
        """
        if model_id not in self.recent_failures:
            return False

        failure_time = self.recent_failures[model_id]
        fallback_config = self.config.get("fallback_config", {})
        cooldown_seconds = fallback_config.get("retry_delay_seconds", 60)

        # Check if cooldown period has passed
        return (time.time() - failure_time) < cooldown_seconds

    def _record_model_failure(self, model_id: str):
        """
        Record a model failure for fallback cooldown.

        Args:
            model_id: Model identifier
        """
        self.recent_failures[model_id] = time.time()

        # Clean old failures
        cutoff = time.time() - 3600  # 1 hour
        self.recent_failures = {
            k: v for k, v in self.recent_failures.items()
            if v > cutoff
        }

    def clear_failures(self):
        """Clear all recorded failures."""
        self.recent_failures.clear()

    def get_available_models_for_task(self, task_type: str) -> List[Dict[str, Any]]:
        """
        Get all available models for a specific task type.

        Args:
            task_type: Type of task

        Returns:
            List of model information dictionaries
        """
        task_mapping = self.config.get("task_mappings", {}).get(task_type)

        if not task_mapping:
            return []

        preferred = task_mapping.get("preferred_models", [])
        fallback = task_mapping.get("fallback_models", [])

        models_info = []

        for model_ref in preferred + fallback:
            provider_name, model_id = self._parse_model_ref(model_ref)
            model = self._get_model_config(provider_name, model_id)

            if model and model.available:
                models_info.append({
                    "model_id": model_id,
                    "provider": provider_name,
                    "name": model.name,
                    "priority": model.priority,
                    "is_preferred": model_ref in preferred
                })

        return models_info
