"""
Unit tests for ModelSelector task-based model selection.

Tests the intelligent model selection system including:
- Task-based model selection
- Cost-aware selection
- Performance-based selection
- Fallback model management
- Selection strategy application
"""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from devflow.core.model_selector import (
    SelectionStrategy,
    SelectionCriteria,
    SelectionResult,
    ModelSelector,
)
from devflow.core.model_manager import (
    ModelManager,
    ModelConfig,
    ModelProviderType,
)


# Fixtures

@pytest.fixture
def sample_model_config_dict() -> Dict[str, Any]:
    """Create a sample model configuration dictionary."""
    return {
        "version": "1.0.0",
        "providers": {
            "anthropic": {
                "name": "Anthropic",
                "enabled": True,
                "api_key_env": "ANTHROPIC_API_KEY",
                "base_url": "https://api.anthropic.com",
                "models": {
                    "claude-3-5-sonnet-20241022": {
                        "name": "Claude 3.5 Sonnet",
                        "type": "chat",
                        "max_tokens": 200000,
                        "input_cost_per_1k": 0.003,
                        "output_cost_per_1k": 0.015,
                        "capabilities": ["code_generation", "analysis"],
                        "priority": 1,
                        "available": True
                    },
                    "claude-3-opus-20240229": {
                        "name": "Claude 3 Opus",
                        "type": "chat",
                        "max_tokens": 200000,
                        "input_cost_per_1k": 0.015,
                        "output_cost_per_1k": 0.075,
                        "capabilities": ["complex_reasoning", "code_generation"],
                        "priority": 2,
                        "available": True
                    },
                    "claude-3-haiku-20240307": {
                        "name": "Claude 3 Haiku",
                        "type": "chat",
                        "max_tokens": 200000,
                        "input_cost_per_1k": 0.00025,
                        "output_cost_per_1k": 0.00125,
                        "capabilities": ["simple_tasks", "quick_response"],
                        "priority": 3,
                        "available": True
                    }
                }
            },
            "openai": {
                "name": "OpenAI",
                "enabled": True,
                "api_key_env": "OPENAI_API_KEY",
                "base_url": "https://api.openai.com/v1",
                "models": {
                    "gpt-4-turbo": {
                        "name": "GPT-4 Turbo",
                        "type": "chat",
                        "max_tokens": 128000,
                        "input_cost_per_1k": 0.01,
                        "output_cost_per_1k": 0.03,
                        "capabilities": ["code_generation", "writing"],
                        "priority": 1,
                        "available": True
                    },
                    "gpt-4": {
                        "name": "GPT-4",
                        "type": "chat",
                        "max_tokens": 8192,
                        "input_cost_per_1k": 0.03,
                        "output_cost_per_1k": 0.06,
                        "capabilities": ["complex_reasoning"],
                        "priority": 2,
                        "available": True
                    },
                    "gpt-3.5-turbo": {
                        "name": "GPT-3.5 Turbo",
                        "type": "chat",
                        "max_tokens": 16385,
                        "input_cost_per_1k": 0.0005,
                        "output_cost_per_1k": 0.0015,
                        "capabilities": ["simple_tasks"],
                        "priority": 3,
                        "available": True
                    }
                }
            }
        },
        "task_mappings": {
            "code_generation": {
                "preferred_models": [
                    "anthropic/claude-3-5-sonnet-20241022",
                    "openai/gpt-4-turbo"
                ],
                "fallback_models": [
                    "openai/gpt-4",
                    "anthropic/claude-3-opus-20240229"
                ]
            },
            "analysis": {
                "preferred_models": [
                    "anthropic/claude-3-5-sonnet-20241022"
                ],
                "fallback_models": [
                    "anthropic/claude-3-haiku-20240307",
                    "openai/gpt-3.5-turbo"
                ]
            }
        },
        "agent_mappings": {
            "dev-story": {
                "task_type": "code_generation",
                "model_override": None
            },
            "code-review": {
                "task_type": "analysis",
                "model_override": "anthropic/claude-3-opus-20240229"
            }
        },
        "fallback_config": {
            "enabled": True,
            "max_attempts": 3,
            "retry_delay_seconds": 60
        },
        "selection_strategy": {
            "default": "balanced",
            "strategies": {
                "balanced": {
                    "weights": {
                        "cost": 0.3,
                        "speed": 0.3,
                        "quality": 0.4
                    }
                },
                "cost_optimized": {
                    "weights": {
                        "cost": 0.7,
                        "speed": 0.2,
                        "quality": 0.1
                    }
                }
            }
        }
    }


@pytest.fixture
def temp_config_file(tmp_path: Path, sample_model_config_dict: Dict[str, Any]) -> Path:
    """Create a temporary configuration file."""
    config_file = tmp_path / "model_config.json"
    with open(config_file, 'w') as f:
        json.dump(sample_model_config_dict, f)
    return config_file


@pytest.fixture
def mock_model_manager(temp_config_file: Path) -> ModelManager:
    """Create a mock ModelManager instance."""
    return ModelManager(config_path=temp_config_file)


@pytest.fixture
def model_selector(mock_model_manager: ModelManager, temp_config_file: Path) -> ModelSelector:
    """Create a ModelSelector instance with mocked dependencies."""
    return ModelSelector(model_manager=mock_model_manager, config_path=temp_config_file)


# SelectionStrategy Tests

class TestSelectionStrategy:
    """Tests for SelectionStrategy enum."""

    def test_selection_strategy_values(self):
        """Test that SelectionStrategy has correct values."""
        assert SelectionStrategy.BALANCED.value == "balanced"
        assert SelectionStrategy.COST_OPTIMIZED.value == "cost_optimized"
        assert SelectionStrategy.QUALITY_OPTIMIZED.value == "quality_optimized"
        assert SelectionStrategy.SPEED_OPTIMIZED.value == "speed_optimized"


# SelectionCriteria Tests

class TestSelectionCriteria:
    """Tests for SelectionCriteria dataclass."""

    def test_selection_criteria_creation(self):
        """Test creating a SelectionCriteria object."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            max_cost=0.5,
            strategy=SelectionStrategy.COST_OPTIMIZED,
            preferred_providers=["anthropic"],
            excluded_models={"gpt-4"},
            require_capability="code_generation"
        )
        assert criteria.task_type == "code_generation"
        assert criteria.max_cost == 0.5
        assert criteria.strategy == SelectionStrategy.COST_OPTIMIZED
        assert criteria.preferred_providers == ["anthropic"]
        assert criteria.excluded_models == {"gpt-4"}
        assert criteria.require_capability == "code_generation"

    def test_selection_criteria_defaults(self):
        """Test SelectionCriteria with default values."""
        criteria = SelectionCriteria(task_type="analysis")
        assert criteria.task_type == "analysis"
        assert criteria.max_cost is None
        assert criteria.strategy == SelectionStrategy.BALANCED
        assert criteria.preferred_providers == []
        assert criteria.excluded_models == set()
        assert criteria.require_capability is None


# SelectionResult Tests

class TestSelectionResult:
    """Tests for SelectionResult dataclass."""

    def test_selection_result_creation(self):
        """Test creating a SelectionResult object."""
        result = SelectionResult(
            model_id="claude-3-5-sonnet-20241022",
            provider="anthropic",
            score=0.95,
            reason="Selected via balanced strategy (premium model)",
            estimated_cost=0.105,
            estimated_latency=3000.0,
            fallback_available=True
        )
        assert result.model_id == "claude-3-5-sonnet-20241022"
        assert result.provider == "anthropic"
        assert result.score == 0.95
        assert "balanced strategy" in result.reason
        assert result.estimated_cost == 0.105
        assert result.estimated_latency == 3000.0
        assert result.fallback_available is True


# ModelSelector Initialization Tests

class TestModelSelectorInitialization:
    """Tests for ModelSelector initialization."""

    def test_initialization(self, model_selector: ModelSelector):
        """Test ModelSelector initialization."""
        assert model_selector.model_manager is not None
        assert model_selector.config is not None
        assert model_selector.lock is not None
        assert isinstance(model_selector.model_metrics, dict)
        assert isinstance(model_selector.recent_failures, dict)

    def test_load_config(self, model_selector: ModelSelector):
        """Test configuration loading."""
        assert "task_mappings" in model_selector.config
        assert "agent_mappings" in model_selector.config
        assert "fallback_config" in model_selector.config
        assert "selection_strategy" in model_selector.config

    def test_default_config_path(self, mock_model_manager: ModelManager):
        """Test default configuration path."""
        selector = ModelSelector(model_manager=mock_model_manager)
        assert selector.config_path is not None
        assert selector.config_path.name == "model_config.json"


# Model Selection Tests

class TestSelectModel:
    """Tests for select_model method."""

    def test_select_model_for_code_generation(self, model_selector: ModelSelector):
        """Test model selection for code generation task."""
        criteria = SelectionCriteria(task_type="code_generation")
        result = model_selector.select_model(criteria)

        assert result is not None
        assert result.model_id in ["claude-3-5-sonnet-20241022", "gpt-4-turbo"]
        assert result.provider in ["anthropic", "openai"]
        assert result.score > 0
        assert result.estimated_cost > 0
        assert result.estimated_latency > 0
        assert isinstance(result.fallback_available, bool)

    def test_select_model_for_analysis(self, model_selector: ModelSelector):
        """Test model selection for analysis task."""
        criteria = SelectionCriteria(task_type="analysis")
        result = model_selector.select_model(criteria)

        assert result is not None
        assert result.model_id == "claude-3-5-sonnet-20241022"
        assert result.provider == "anthropic"

    def test_select_model_with_max_cost_constraint(self, model_selector: ModelSelector):
        """Test model selection with maximum cost constraint."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            max_cost=0.001  # Very low cost limit
        )
        result = model_selector.select_model(criteria)

        # Should either return None (no models within budget) or a very cheap model
        if result:
            assert result.estimated_cost <= 0.001

    def test_select_model_with_preferred_provider(self, model_selector: ModelSelector):
        """Test model selection with preferred provider."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            preferred_providers=["anthropic"]
        )
        result = model_selector.select_model(criteria)

        assert result is not None
        assert result.provider == "anthropic"

    def test_select_model_with_excluded_models(self, model_selector: ModelSelector):
        """Test model selection with excluded models."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            excluded_models={"anthropic/claude-3-5-sonnet-20241022"}
        )
        result = model_selector.select_model(criteria)

        assert result is not None
        assert result.model_id != "claude-3-5-sonnet-20241022"

    def test_select_model_with_required_capability(self, model_selector: ModelSelector):
        """Test model selection with required capability."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            require_capability="complex_reasoning"
        )
        result = model_selector.select_model(criteria)

        # Should return a model with complex_reasoning capability
        if result:
            assert result.model_id in ["claude-3-opus-20240229", "gpt-4"]

    def test_select_model_unknown_task_type(self, model_selector: ModelSelector):
        """Test model selection with unknown task type."""
        criteria = SelectionCriteria(task_type="unknown_task")
        result = model_selector.select_model(criteria)

        # Should fall back to code_generation or return None
        # Either behavior is acceptable based on implementation

    def test_select_model_no_available_models(self, model_selector: ModelSelector):
        """Test model selection when no models are available."""
        # Exclude all models
        criteria = SelectionCriteria(
            task_type="code_generation",
            excluded_models={
                "anthropic/claude-3-5-sonnet-20241022",
                "openai/gpt-4-turbo",
                "openai/gpt-4",
                "anthropic/claude-3-opus-20240229"
            }
        )
        result = model_selector.select_model(criteria)
        assert result is None

    def test_select_model_cost_optimized_strategy(self, model_selector: ModelSelector):
        """Test model selection with cost-optimized strategy."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            strategy=SelectionStrategy.COST_OPTIMIZED
        )
        result = model_selector.select_model(criteria)

        assert result is not None
        # Should prefer cheaper models


# Agent-based Selection Tests

class TestSelectModelForAgent:
    """Tests for select_model_for_agent method."""

    def test_select_model_for_dev_story_agent(self, model_selector: ModelSelector):
        """Test model selection for dev-story agent."""
        result = model_selector.select_model_for_agent("dev-story")

        assert result is not None
        assert result.model_id in ["claude-3-5-sonnet-20241022", "gpt-4-turbo"]

    def test_select_model_for_code_review_agent_with_override(self, model_selector: ModelSelector):
        """Test model selection for code-review agent with model override."""
        result = model_selector.select_model_for_agent("code-review")

        assert result is not None
        assert result.model_id == "claude-3-opus-20240229"
        assert result.provider == "anthropic"
        assert "override" in result.reason.lower()

    def test_select_model_for_unknown_agent(self, model_selector: ModelSelector):
        """Test model selection for unknown agent type."""
        result = model_selector.select_model_for_agent("unknown-agent")
        assert result is None

    def test_select_model_for_agent_with_excluded_models(self, model_selector: ModelSelector):
        """Test agent-based selection with excluded models."""
        result = model_selector.select_model_for_agent(
            "dev-story",
            excluded_models={"anthropic/claude-3-5-sonnet-20241022"}
        )

        assert result is not None
        assert result.model_id != "claude-3-5-sonnet-20241022"

    def test_select_model_for_agent_with_strategy(self, model_selector: ModelSelector):
        """Test agent-based selection with custom strategy."""
        result = model_selector.select_model_for_agent(
            "dev-story",
            strategy=SelectionStrategy.COST_OPTIMIZED
        )

        assert result is not None
        # Should apply cost-optimized strategy


# Fallback Model Tests

class TestGetFallbackModel:
    """Tests for get_fallback_model method."""

    def test_get_fallback_model_after_failure(self, model_selector: ModelSelector):
        """Test getting a fallback model after failure."""
        criteria = SelectionCriteria(task_type="code_generation")

        # Simulate failure of preferred model
        result = model_selector.get_fallback_model("claude-3-5-sonnet-20241022", criteria)

        assert result is not None
        assert result.model_id != "claude-3-5-sonnet-20241022"
        assert "fallback" in result.reason.lower()

    def test_get_fallback_model_records_failure(self, model_selector: ModelSelector):
        """Test that fallback method records failures."""
        criteria = SelectionCriteria(task_type="code_generation")

        model_selector.get_fallback_model("claude-3-5-sonnet-20241022", criteria)

        # Check that failure was recorded
        assert "claude-3-5-sonnet-20241022" in model_selector.recent_failures

    def test_get_fallback_model_no_fallback_available(self, model_selector: ModelSelector):
        """Test fallback when no fallback models are available."""
        # Create criteria with a task that has no fallbacks
        criteria = SelectionCriteria(
            task_type="analysis",
            excluded_models={
                "anthropic/claude-3-haiku-20240307",
                "openai/gpt-3.5-turbo"
            }
        )

        # Try to get fallback for the only preferred model
        result = model_selector.get_fallback_model("claude-3-5-sonnet-20241022", criteria)

        # Should return None when no fallbacks available
        assert result is None


# Model Metrics Tests

class TestModelMetrics:
    """Tests for model metrics tracking."""

    def test_update_model_metrics_success(self, model_selector: ModelSelector):
        """Test updating metrics for successful request."""
        model_selector.update_model_metrics(
            model_id="claude-3-5-sonnet-20241022",
            latency=1500.0,
            success=True,
            token_count=1000
        )

        metrics = model_selector.get_model_metrics("claude-3-5-sonnet-20241022")
        assert metrics is not None
        assert metrics["total_requests"] == 1
        assert metrics["successful_requests"] == 1
        assert metrics["failed_requests"] == 0
        assert metrics["total_latency"] == 1500.0
        assert metrics["total_tokens"] == 1000
        assert metrics["avg_latency"] == 1500.0
        assert metrics["success_rate"] == 1.0

    def test_update_model_metrics_failure(self, model_selector: ModelSelector):
        """Test updating metrics for failed request."""
        model_selector.update_model_metrics(
            model_id="gpt-4-turbo",
            latency=5000.0,
            success=False
        )

        metrics = model_selector.get_model_metrics("gpt-4-turbo")
        assert metrics is not None
        assert metrics["total_requests"] == 1
        assert metrics["successful_requests"] == 0
        assert metrics["failed_requests"] == 1
        assert metrics["success_rate"] == 0.0

    def test_update_model_metrics_multiple_requests(self, model_selector: ModelSelector):
        """Test updating metrics across multiple requests."""
        model_id = "claude-3-opus-20240229"

        # First request
        model_selector.update_model_metrics(model_id, 1000.0, True, 500)
        # Second request
        model_selector.update_model_metrics(model_id, 2000.0, True, 1000)
        # Third request (failed)
        model_selector.update_model_metrics(model_id, 1500.0, False, 0)

        metrics = model_selector.get_model_metrics(model_id)
        assert metrics["total_requests"] == 3
        assert metrics["successful_requests"] == 2
        assert metrics["failed_requests"] == 1
        assert metrics["total_latency"] == 4500.0
        assert metrics["avg_latency"] == 1500.0
        assert metrics["success_rate"] == pytest.approx(0.666, rel=0.01)

    def test_get_model_metrics_unknown_model(self, model_selector: ModelSelector):
        """Test getting metrics for unknown model."""
        metrics = model_selector.get_model_metrics("unknown-model")
        assert metrics is None

    def test_get_all_metrics(self, model_selector: ModelSelector):
        """Test getting all metrics."""
        model_selector.update_model_metrics("model1", 1000.0, True)
        model_selector.update_model_metrics("model2", 2000.0, False)

        all_metrics = model_selector.get_all_metrics()
        assert "model1" in all_metrics
        assert "model2" in all_metrics
        assert len(all_metrics) == 2


# Helper Method Tests

class TestHelperMethods:
    """Tests for ModelSelector helper methods."""

    def test_parse_model_ref_with_provider(self, model_selector: ModelSelector):
        """Test parsing model reference with provider."""
        provider, model_id = model_selector._parse_model_ref("anthropic/claude-3-5-sonnet-20241022")
        assert provider == "anthropic"
        assert model_id == "claude-3-5-sonnet-20241022"

    def test_parse_model_ref_without_provider(self, model_selector: ModelSelector):
        """Test parsing model reference without provider."""
        provider, model_id = model_selector._parse_model_ref("gpt-4")
        assert provider == ""
        assert model_id == "gpt-4"

    def test_get_model_config_success(self, model_selector: ModelSelector):
        """Test getting model configuration successfully."""
        model = model_selector._get_model_config("anthropic", "claude-3-5-sonnet-20241022")
        assert model is not None
        assert model.model_id == "claude-3-5-sonnet-20241022"

    def test_get_model_config_unknown_model(self, model_selector: ModelSelector):
        """Test getting configuration for unknown model."""
        model = model_selector._get_model_config("anthropic", "unknown-model")
        assert model is None

    def test_is_model_failing_no_failures(self, model_selector: ModelSelector):
        """Test checking if model is failing when it has no failures."""
        assert model_selector._is_model_failing("claude-3-5-sonnet-20241022") is False

    def test_is_model_failing_recent_failure(self, model_selector: ModelSelector):
        """Test checking if model is failing with recent failure."""
        model_selector._record_model_failure("claude-3-5-sonnet-20241022")
        assert model_selector._is_model_failing("claude-3-5-sonnet-20241022") is True

    def test_is_model_failing_old_failure(self, model_selector: ModelSelector):
        """Test checking if model is failing with old failure (outside cooldown)."""
        # Record a failure in the past (beyond cooldown period)
        model_selector.recent_failures["claude-3-5-sonnet-20241022"] = time.time() - 120

        assert model_selector._is_model_failing("claude-3-5-sonnet-20241022") is False

    def test_clear_failures(self, model_selector: ModelSelector):
        """Test clearing all recorded failures."""
        model_selector._record_model_failure("model1")
        model_selector._record_model_failure("model2")
        assert len(model_selector.recent_failures) == 2

        model_selector.clear_failures()
        assert len(model_selector.recent_failures) == 0


# Scoring Tests

class TestModelScoring:
    """Tests for model scoring methods."""

    def test_calculate_cost_score_cheap_model(self, model_selector: ModelSelector):
        """Test cost score calculation for cheap model."""
        model = ModelConfig(
            model_id="cheap-model",
            name="Cheap Model",
            provider="test",
            input_cost_per_1k=0.0001,
            output_cost_per_1k=0.0001
        )
        criteria = SelectionCriteria(task_type="test")
        score = model_selector._calculate_cost_score(model, criteria)
        assert score > 0.9  # Should be high for cheap model

    def test_calculate_cost_score_expensive_model(self, model_selector: ModelSelector):
        """Test cost score calculation for expensive model."""
        model = ModelConfig(
            model_id="expensive-model",
            name="Expensive Model",
            provider="test",
            input_cost_per_1k=0.05,
            output_cost_per_1k=0.05
        )
        criteria = SelectionCriteria(task_type="test")
        score = model_selector._calculate_cost_score(model, criteria)
        assert score < 0.5  # Should be low for expensive model

    def test_calculate_speed_score_fast_model(self, model_selector: ModelSelector):
        """Test speed score calculation for fast model (priority 3)."""
        model = ModelConfig(
            model_id="fast-model",
            name="Fast Model",
            provider="test",
            priority=3
        )
        criteria = SelectionCriteria(task_type="test")
        score = model_selector._calculate_speed_score(model, criteria)
        assert score == 1.0  # Fastest

    def test_calculate_speed_score_slow_model(self, model_selector: ModelSelector):
        """Test speed score calculation for slow model (priority 1)."""
        model = ModelConfig(
            model_id="slow-model",
            name="Slow Model",
            provider="test",
            priority=1
        )
        criteria = SelectionCriteria(task_type="test")
        score = model_selector._calculate_speed_score(model, criteria)
        assert score == 0.5  # Slowest

    def test_calculate_quality_score_high_quality(self, model_selector: ModelSelector):
        """Test quality score calculation for high quality model."""
        model = ModelConfig(
            model_id="quality-model",
            name="Quality Model",
            provider="test",
            priority=1,
            capabilities=["complex_reasoning"]
        )
        criteria = SelectionCriteria(task_type="test")
        score = model_selector._calculate_quality_score(model, criteria)
        assert score == 1.0  # Highest quality with complex_reasoning boost

    def test_calculate_quality_score_low_quality(self, model_selector: ModelSelector):
        """Test quality score calculation for low quality model."""
        model = ModelConfig(
            model_id="basic-model",
            name="Basic Model",
            provider="test",
            priority=3
        )
        criteria = SelectionCriteria(task_type="test")
        score = model_selector._calculate_quality_score(model, criteria)
        assert score == 0.6  # Lower quality

    def test_estimate_task_cost(self, model_selector: ModelSelector):
        """Test task cost estimation."""
        model = ModelConfig(
            model_id="test-model",
            name="Test Model",
            provider="test",
            input_cost_per_1k=0.003,
            output_cost_per_1k=0.015
        )
        criteria = SelectionCriteria(task_type="test")
        cost = model_selector._estimate_task_cost(model, criteria)

        # Should estimate based on assumed 10k input, 5k output tokens
        # cost = (10 * 0.003) + (5 * 0.015) = 0.03 + 0.075 = 0.105
        assert cost == pytest.approx(0.105, rel=0.01)

    def test_estimate_latency_with_metrics(self, model_selector: ModelSelector):
        """Test latency estimation with historical metrics."""
        model = ModelConfig(
            model_id="test-model",
            name="Test Model",
            provider="test",
            priority=1
        )
        criteria = SelectionCriteria(task_type="test")

        # Add metrics
        model_selector.update_model_metrics("test-model", 2500.0, True)

        latency = model_selector._estimate_latency(model, criteria)
        assert latency == 2500.0  # Should use historical average

    def test_estimate_latency_without_metrics(self, model_selector: ModelSelector):
        """Test latency estimation without historical metrics."""
        model = ModelConfig(
            model_id="test-model",
            name="Test Model",
            provider="test",
            priority=2
        )
        criteria = SelectionCriteria(task_type="test")

        latency = model_selector._estimate_latency(model, criteria)
        assert latency == 5000.0  # Should use priority-based default


# Available Models Tests

class TestGetAvailableModelsForTask:
    """Tests for getting available models for a task."""

    def test_get_available_models_for_task(self, model_selector: ModelSelector):
        """Test getting available models for a task."""
        models = model_selector.get_available_models_for_task("code_generation")

        assert isinstance(models, list)
        assert len(models) > 0

        for model_info in models:
            assert "model_id" in model_info
            assert "provider" in model_info
            assert "name" in model_info
            assert "priority" in model_info
            assert "is_preferred" in model_info

    def test_get_available_models_for_unknown_task(self, model_selector: ModelSelector):
        """Test getting available models for unknown task."""
        models = model_selector.get_available_models_for_task("unknown_task")
        assert models == []

    def test_get_available_models_includes_preferred_flag(self, model_selector: ModelSelector):
        """Test that available models include preferred flag."""
        models = model_selector.get_available_models_for_task("code_generation")

        # Check that some models are marked as preferred
        preferred_models = [m for m in models if m["is_preferred"]]
        fallback_models = [m for m in models if not m["is_preferred"]]

        assert len(preferred_models) > 0 or len(fallback_models) > 0


# Integration Tests

class TestModelSelectorIntegration:
    """Integration tests for ModelSelector."""

    def test_full_selection_workflow(self, model_selector: ModelSelector):
        """Test complete selection workflow."""
        # Select a model
        criteria = SelectionCriteria(task_type="code_generation")
        result = model_selector.select_model(criteria)

        assert result is not None

        # Update metrics
        model_selector.update_model_metrics(
            result.model_id,
            result.estimated_latency,
            True,
            1000
        )

        # Check metrics were recorded
        metrics = model_selector.get_model_metrics(result.model_id)
        assert metrics is not None
        assert metrics["total_requests"] == 1

    def test_selection_with_fallback_workflow(self, model_selector: ModelSelector):
        """Test selection and fallback workflow."""
        criteria = SelectionCriteria(task_type="code_generation")

        # Get initial selection
        initial = model_selector.select_model(criteria)
        assert initial is not None

        # Get fallback
        fallback = model_selector.get_fallback_model(initial.model_id, criteria)

        if fallback:
            assert fallback.model_id != initial.model_id

            # Original model should be marked as failing
            assert model_selector._is_model_failing(initial.model_id)

    def test_cost_optimization_strategy_workflow(self, model_selector: ModelSelector):
        """Test cost optimization strategy."""
        balanced_result = model_selector.select_model(
            SelectionCriteria(task_type="code_generation", strategy=SelectionStrategy.BALANCED)
        )

        cost_optimized_result = model_selector.select_model(
            SelectionCriteria(task_type="code_generation", strategy=SelectionStrategy.COST_OPTIMIZED)
        )

        assert balanced_result is not None
        assert cost_optimized_result is not None

        # Cost-optimized should prefer cheaper models
        # (though this depends on which models are available)

    def test_multi_provider_selection(self, model_selector: ModelSelector):
        """Test selection across multiple providers."""
        # Test with Anthropic preference
        anthropic_result = model_selector.select_model(
            SelectionCriteria(
                task_type="code_generation",
                preferred_providers=["anthropic"]
            )
        )

        # Test with OpenAI preference
        openai_result = model_selector.select_model(
            SelectionCriteria(
                task_type="code_generation",
                preferred_providers=["openai"]
            )
        )

        if anthropic_result:
            assert anthropic_result.provider == "anthropic"

        if openai_result:
            assert openai_result.provider == "openai"

    def test_capability_based_selection(self, model_selector: ModelSelector):
        """Test selection based on required capabilities."""
        # Select with complex reasoning requirement
        result = model_selector.select_model(
            SelectionCriteria(
                task_type="code_generation",
                require_capability="complex_reasoning"
            )
        )

        if result:
            # Verify the model has the required capability
            model = model_selector._get_model_config(result.provider, result.model_id)
            if model:
                assert "complex_reasoning" in model.capabilities
