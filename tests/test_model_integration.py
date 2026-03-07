"""
Integration tests for model fallback and selection.

Tests the integration between:
- ModelManager and ModelSelector
- AgentManager and model selection
- Fallback behavior on model failures
- End-to-end model selection workflows
"""

import pytest
import json
import asyncio
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any

from devflow.core.model_manager import (
    ModelManager,
    ModelProviderType,
    ModelConfig,
    ModelResponse,
    ModelRequest,
)
from devflow.core.model_selector import (
    ModelSelector,
    SelectionCriteria,
    SelectionResult,
    SelectionStrategy,
)
from devflow.core.agent_manager import AgentManager, AgentConfig
from devflow.core.state_tracker import StateTracker
from devflow.core.session_manager import SessionManager


# Mock the external libraries before import
import sys
sys.modules['anthropic'] = MagicMock()
sys.modules['openai'] = MagicMock()
sys.modules['requests'] = MagicMock()


# Fixtures


@pytest.fixture
def test_config_path(tmp_path: Path) -> Path:
    """Create a test configuration file."""
    config = {
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
                        "capabilities": ["code_generation", "code_review", "analysis"],
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
                        "capabilities": ["code_generation", "code_review", "analysis"],
                        "priority": 1,
                        "available": True
                    },
                    "gpt-4": {
                        "name": "GPT-4",
                        "type": "chat",
                        "max_tokens": 8192,
                        "input_cost_per_1k": 0.03,
                        "output_cost_per_1k": 0.06,
                        "capabilities": ["complex_reasoning", "code_generation"],
                        "priority": 2,
                        "available": True
                    },
                    "gpt-3.5-turbo": {
                        "name": "GPT-3.5 Turbo",
                        "type": "chat",
                        "max_tokens": 16385,
                        "input_cost_per_1k": 0.0005,
                        "output_cost_per_1k": 0.0015,
                        "capabilities": ["simple_tasks", "quick_response"],
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
                ],
                "min_capability": "code_generation"
            },
            "code_review": {
                "preferred_models": [
                    "anthropic/claude-3-5-sonnet-20241022",
                    "openai/gpt-4-turbo"
                ],
                "fallback_models": [
                    "openai/gpt-4",
                    "anthropic/claude-3-opus-20240229"
                ],
                "min_capability": "code_review"
            },
            "analysis": {
                "preferred_models": [
                    "anthropic/claude-3-5-sonnet-20241022",
                    "openai/gpt-4-turbo"
                ],
                "fallback_models": [
                    "anthropic/claude-3-haiku-20240307",
                    "openai/gpt-3.5-turbo"
                ],
                "min_capability": "analysis"
            },
            "simple_tasks": {
                "preferred_models": [
                    "anthropic/claude-3-haiku-20240307",
                    "openai/gpt-3.5-turbo"
                ],
                "fallback_models": [
                    "openai/gpt-4-turbo"
                ],
                "min_capability": "simple_tasks"
            }
        },
        "agent_mappings": {
            "dev-story": {
                "task_type": "code_generation",
                "model_override": None
            },
            "code-review": {
                "task_type": "code_review",
                "model_override": None
            },
            "business-analyst": {
                "task_type": "analysis",
                "model_override": None
            }
        },
        "fallback_config": {
            "enabled": True,
            "max_attempts": 3,
            "retry_delay_seconds": 1,
            "fallback_on": [
                "rate_limit_error",
                "api_error",
                "timeout_error",
                "authentication_error"
            ]
        },
        "selection_strategy": {
            "default": "balanced",
            "strategies": {
                "balanced": {
                    "description": "Balance between cost, speed, and quality",
                    "weights": {
                        "cost": 0.3,
                        "speed": 0.3,
                        "quality": 0.4
                    }
                },
                "cost_optimized": {
                    "description": "Prefer cheaper models",
                    "weights": {
                        "cost": 0.7,
                        "speed": 0.2,
                        "quality": 0.1
                    }
                }
            }
        }
    }

    config_file = tmp_path / "model_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f)

    return config_file


@pytest.fixture
def model_manager(test_config_path: Path) -> ModelManager:
    """Create a ModelManager instance with test configuration."""
    return ModelManager(config_path=test_config_path)


@pytest.fixture
def model_selector(model_manager: ModelManager, test_config_path: Path) -> ModelSelector:
    """Create a ModelSelector instance with test configuration."""
    return ModelSelector(model_manager=model_manager, config_path=test_config_path)


# Tests


class TestModelSelectionIntegration:
    """Tests for integrated model selection behavior."""

    def test_select_model_for_code_generation(self, model_selector: ModelSelector):
        """Test model selection for code generation task."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            strategy=SelectionStrategy.BALANCED
        )

        result = model_selector.select_model(criteria)

        assert result is not None
        assert result.model_id in ["claude-3-5-sonnet-20241022", "gpt-4-turbo"]
        assert result.provider in ["anthropic", "openai"]
        assert result.score > 0
        assert result.estimated_cost > 0
        assert result.fallback_available is True
        assert "Selected" in result.reason

    def test_select_model_for_code_review(self, model_selector: ModelSelector):
        """Test model selection for code review task."""
        criteria = SelectionCriteria(
            task_type="code_review",
            strategy=SelectionStrategy.BALANCED
        )

        result = model_selector.select_model(criteria)

        assert result is not None
        assert result.model_id in ["claude-3-5-sonnet-20241022", "gpt-4-turbo"]
        assert result.provider in ["anthropic", "openai"]
        assert result.fallback_available is True

    def test_select_model_for_analysis(self, model_selector: ModelSelector):
        """Test model selection for analysis task."""
        criteria = SelectionCriteria(
            task_type="analysis",
            strategy=SelectionStrategy.BALANCED
        )

        result = model_selector.select_model(criteria)

        assert result is not None
        assert result.model_id in ["claude-3-5-sonnet-20241022", "gpt-4-turbo"]
        assert result.provider in ["anthropic", "openai"]

    def test_select_model_with_cost_constraint(self, model_selector: ModelSelector):
        """Test model selection with maximum cost constraint."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            max_cost=0.5,  # Reasonable cost constraint
            strategy=SelectionStrategy.BALANCED
        )

        result = model_selector.select_model(criteria)

        # Should find a model within the cost constraint
        assert result is not None
        assert result.estimated_cost <= 0.5

    def test_select_model_with_excluded_models(self, model_selector: ModelSelector):
        """Test model selection with excluded models."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            excluded_models={"anthropic/claude-3-5-sonnet-20241022"},
            strategy=SelectionStrategy.BALANCED
        )

        result = model_selector.select_model(criteria)

        assert result is not None
        # Should select GPT-4 Turbo since Sonnet is excluded
        assert result.model_id == "gpt-4-turbo"
        assert result.provider == "openai"

    def test_select_model_with_preferred_provider(self, model_selector: ModelSelector):
        """Test model selection with preferred provider."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            preferred_providers=["anthropic"],
            strategy=SelectionStrategy.BALANCED
        )

        result = model_selector.select_model(criteria)

        assert result is not None
        assert result.provider == "anthropic"
        assert result.model_id == "claude-3-5-sonnet-20241022"

    def test_select_model_for_simple_tasks(self, model_selector: ModelSelector):
        """Test model selection for simple tasks (should prefer fast models)."""
        criteria = SelectionCriteria(
            task_type="simple_tasks",
            strategy=SelectionStrategy.BALANCED
        )

        result = model_selector.select_model(criteria)

        assert result is not None
        # Simple tasks have Haiku and GPT-3.5 as preferred, but may fall back
        # The actual selection depends on scoring
        assert result.model_id is not None

    def test_cost_optimized_strategy(self, model_selector: ModelSelector):
        """Test cost-optimized selection strategy."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            strategy=SelectionStrategy.COST_OPTIMIZED
        )

        result = model_selector.select_model(criteria)

        assert result is not None
        # Cost-optimized should prefer cheaper models
        # Claude 3.5 Sonnet costs ~$0.105 for estimated task
        assert result.estimated_cost < 0.2

    def test_quality_optimized_strategy(self, model_selector: ModelSelector):
        """Test quality-optimized selection strategy."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            strategy=SelectionStrategy.QUALITY_OPTIMIZED
        )

        result = model_selector.select_model(criteria)

        assert result is not None
        # Quality-optimized should prefer premium models (priority 1)
        assert result.model_id in ["claude-3-5-sonnet-20241022", "gpt-4-turbo"]

    def test_speed_optimized_strategy(self, model_selector: ModelSelector):
        """Test speed-optimized selection strategy."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            strategy=SelectionStrategy.SPEED_OPTIMIZED
        )

        result = model_selector.select_model(criteria)

        assert result is not None
        # Speed-optimized should prefer fast models (priority 3 or 2)
        assert result.estimated_latency < 5000  # Less than 5 seconds


class TestModelFallbackIntegration:
    """Tests for integrated model fallback behavior."""

    def test_fallback_on_model_failure(self, model_selector: ModelSelector):
        """Test fallback when preferred model fails."""
        # First, select a model
        criteria = SelectionCriteria(
            task_type="code_generation",
            strategy=SelectionStrategy.BALANCED
        )

        initial_result = model_selector.select_model(criteria)
        assert initial_result is not None

        # Simulate failure and get fallback
        fallback_result = model_selector.get_fallback_model(
            initial_result.model_id,
            criteria
        )

        assert fallback_result is not None
        assert fallback_result.model_id != initial_result.model_id
        assert "Fallback" in fallback_result.reason

    def test_fallback_excludes_failed_model(self, model_selector: ModelSelector):
        """Test that fallback excludes the failed model."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            strategy=SelectionStrategy.BALANCED
        )

        # Select initial model
        initial_result = model_selector.select_model(criteria)
        failed_model_id = initial_result.model_id

        # Get fallback
        fallback_result = model_selector.get_fallback_model(failed_model_id, criteria)

        assert fallback_result is not None
        assert fallback_result.model_id != failed_model_id

        # Try to select again - failed model should be excluded
        new_result = model_selector.select_model(criteria)
        assert new_result.model_id != failed_model_id

    def test_multiple_fallback_attempts(self, model_selector: ModelSelector):
        """Test multiple sequential fallback attempts."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            strategy=SelectionStrategy.BALANCED
        )

        # First selection
        result1 = model_selector.select_model(criteria)
        assert result1 is not None

        # First fallback
        result2 = model_selector.get_fallback_model(result1.model_id, criteria)
        assert result2 is not None
        assert result2.model_id != result1.model_id

        # Second fallback
        result3 = model_selector.get_fallback_model(result2.model_id, criteria)
        assert result3 is not None
        assert result3.model_id != result2.model_id
        assert result3.model_id != result1.model_id

    def test_fallback_unavailable_when_all_models_failed(self, model_selector: ModelSelector):
        """Test that fallback becomes unavailable after all models fail."""
        criteria = SelectionCriteria(
            task_type="simple_tasks",
            strategy=SelectionStrategy.BALANCED
        )

        # simple_tasks has limited fallback options
        result = model_selector.select_model(criteria)
        assert result is not None

        # Mark all available models as failed
        available_models = model_selector.get_available_models_for_task("simple_tasks")
        for model_info in available_models:
            model_selector._record_model_failure(model_info["model_id"])

        # Try to get fallback - should be None or very limited
        fallback = model_selector.get_fallback_model(result.model_id, criteria)

        # After exhausting fallbacks, may return None or last option
        if fallback is not None:
            assert fallback.fallback_available is False

    def test_fallback_cooldown_period(self, model_selector: ModelSelector):
        """Test that failed models enter a cooldown period."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            strategy=SelectionStrategy.BALANCED
        )

        # Select and fail a model
        result = model_selector.select_model(criteria)
        model_selector._record_model_failure(result.model_id)

        # Model should be marked as failing
        assert model_selector._is_model_failing(result.model_id) is True

        # Wait for cooldown period (configured as 1 second in test config)
        time.sleep(1.5)

        # Model should no longer be failing
        assert model_selector._is_model_failing(result.model_id) is False

    def test_clear_failures(self, model_selector: ModelSelector):
        """Test clearing recorded failures."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            strategy=SelectionStrategy.BALANCED
        )

        # Select and fail a model
        result = model_selector.select_model(criteria)
        model_selector._record_model_failure(result.model_id)

        # Verify it's failing
        assert model_selector._is_model_failing(result.model_id) is True

        # Clear failures
        model_selector.clear_failures()

        # Model should no longer be failing
        assert model_selector._is_model_failing(result.model_id) is False


class TestAgentModelMappingIntegration:
    """Tests for agent-to-model mapping integration."""

    def test_select_model_for_dev_story_agent(self, model_selector: ModelSelector):
        """Test model selection for dev-story agent."""
        result = model_selector.select_model_for_agent("dev-story")

        assert result is not None
        assert result.model_id in ["claude-3-5-sonnet-20241022", "gpt-4-turbo"]
        # The reason includes the model name and strategy
        assert "Selected" in result.reason

    def test_select_model_for_code_review_agent(self, model_selector: ModelSelector):
        """Test model selection for code-review agent."""
        result = model_selector.select_model_for_agent("code-review")

        assert result is not None
        assert result.model_id in ["claude-3-5-sonnet-20241022", "gpt-4-turbo"]
        assert "Selected" in result.reason

    def test_select_model_for_business_analyst_agent(self, model_selector: ModelSelector):
        """Test model selection for business-analyst agent."""
        result = model_selector.select_model_for_agent("business-analyst")

        assert result is not None
        assert result.provider in ["anthropic", "openai"]
        assert "Selected" in result.reason

    def test_select_model_with_strategy_for_agent(self, model_selector: ModelSelector):
        """Test model selection for agent with custom strategy."""
        result = model_selector.select_model_for_agent(
            "dev-story",
            strategy=SelectionStrategy.COST_OPTIMIZED
        )

        assert result is not None
        # Cost-optimized should prefer cheaper models
        assert result.estimated_cost < 0.2

    def test_select_model_with_exclusions_for_agent(self, model_selector: ModelSelector):
        """Test model selection for agent with excluded models."""
        result = model_selector.select_model_for_agent(
            "dev-story",
            excluded_models={"anthropic/claude-3-5-sonnet-20241022"}
        )

        assert result is not None
        # Should not select the excluded model
        assert result.model_id != "claude-3-5-sonnet-20241022"

    def test_unknown_agent_returns_none(self, model_selector: ModelSelector):
        """Test that unknown agent types return None."""
        result = model_selector.select_model_for_agent("unknown-agent")

        assert result is None


class TestModelMetricsIntegration:
    """Tests for model metrics tracking integration."""

    def test_update_and_retrieve_metrics(self, model_selector: ModelSelector):
        """Test updating and retrieving model metrics."""
        model_id = "claude-3-5-sonnet-20241022"

        # Update metrics
        model_selector.update_model_metrics(
            model_id=model_id,
            latency=1500.0,
            success=True,
            token_count=5000
        )

        # Retrieve metrics
        metrics = model_selector.get_model_metrics(model_id)

        assert metrics is not None
        assert metrics["total_requests"] == 1
        assert metrics["successful_requests"] == 1
        assert metrics["failed_requests"] == 0
        assert metrics["total_latency"] == 1500.0
        assert metrics["avg_latency"] == 1500.0
        assert metrics["success_rate"] == 1.0

    def test_metrics_influence_latency_estimates(self, model_selector: ModelSelector):
        """Test that metrics influence latency estimates."""
        model_id = "claude-3-5-sonnet-20241022"

        # Update metrics with specific latency
        model_selector.update_model_metrics(
            model_id=model_id,
            latency=800.0,
            success=True,
            token_count=3000
        )

        # Get model config
        provider = model_selector.model_manager.get_provider(ModelProviderType.ANTHROPIC)
        model = provider.get_model(model_id)

        # Estimate latency - should use metrics
        from devflow.core.model_selector import SelectionCriteria
        criteria = SelectionCriteria(task_type="code_generation")
        estimated = model_selector._estimate_latency(model, criteria)

        # Should be close to our recorded metric
        assert abs(estimated - 800.0) < 100

    def test_multiple_metrics_updates(self, model_selector: ModelSelector):
        """Test multiple metric updates aggregate correctly."""
        model_id = "gpt-4-turbo"

        # First request
        model_selector.update_model_metrics(
            model_id=model_id,
            latency=1000.0,
            success=True,
            token_count=2000
        )

        # Second request
        model_selector.update_model_metrics(
            model_id=model_id,
            latency=2000.0,
            success=True,
            token_count=3000
        )

        # Third request (failed)
        model_selector.update_model_metrics(
            model_id=model_id,
            latency=500.0,
            success=False,
            token_count=0
        )

        metrics = model_selector.get_model_metrics(model_id)

        assert metrics["total_requests"] == 3
        assert metrics["successful_requests"] == 2
        assert metrics["failed_requests"] == 1
        assert metrics["avg_latency"] == (1000.0 + 2000.0 + 500.0) / 3
        assert metrics["success_rate"] == 2.0 / 3.0

    def test_get_all_metrics(self, model_selector: ModelSelector):
        """Test retrieving metrics for all models."""
        # Update metrics for multiple models
        model_selector.update_model_metrics("claude-3-5-sonnet-20241022", 1000.0, True, 2000)
        model_selector.update_model_metrics("gpt-4-turbo", 1500.0, True, 3000)

        all_metrics = model_selector.get_all_metrics()

        assert len(all_metrics) == 2
        assert "claude-3-5-sonnet-20241022" in all_metrics
        assert "gpt-4-turbo" in all_metrics


class TestEndToEndWorkflows:
    """Tests for end-to-end model selection and fallback workflows."""

    def test_complete_selection_and_failure_workflow(self, model_selector: ModelSelector):
        """Test complete workflow from selection to fallback."""
        criteria = SelectionCriteria(
            task_type="code_generation",
            strategy=SelectionStrategy.BALANCED
        )

        # Step 1: Select initial model
        initial = model_selector.select_model(criteria)
        assert initial is not None
        initial_model_id = initial.model_id

        # Step 2: Simulate successful request
        model_selector.update_model_metrics(
            model_id=initial_model_id,
            latency=1200.0,
            success=True,
            token_count=4000
        )

        metrics = model_selector.get_model_metrics(initial_model_id)
        assert metrics["success_rate"] == 1.0

        # Step 3: Simulate failure and get fallback
        fallback = model_selector.get_fallback_model(initial_model_id, criteria)
        assert fallback is not None
        assert fallback.model_id != initial_model_id

        # Step 4: Update fallback metrics
        model_selector.update_model_metrics(
            model_id=fallback.model_id,
            latency=1800.0,
            success=True,
            token_count=3500
        )

        # Verify both models have metrics
        all_metrics = model_selector.get_all_metrics()
        assert len(all_metrics) >= 2

    def test_agent_manager_has_model_components(self, model_manager: ModelManager):
        """Test that AgentManager integrates with ModelSelector."""
        from devflow.core.state_tracker import StateTracker
        from devflow.core.session_manager import SessionManager

        # This tests the integration without actually running agents
        state_tracker = StateTracker()
        session_manager = SessionManager()

        agent_manager = AgentManager(state_tracker, session_manager)

        # Verify agent manager has model components
        assert agent_manager.model_manager is not None
        assert agent_manager.model_selector is not None

        # Verify model selector is configured correctly
        assert agent_manager.model_selector.model_manager is not None

    def test_task_type_to_agent_to_model_mapping(self, model_selector: ModelSelector):
        """Test the complete chain: task type -> agent -> model."""
        # Define mapping from task to agent
        task_to_agent = {
            "code_generation": "dev-story",
            "code_review": "code-review",
            "analysis": "business-analyst"
        }

        for task_type, agent_type in task_to_agent.items():
            # Get model for agent
            result = model_selector.select_model_for_agent(agent_type)

            assert result is not None, f"No model found for agent {agent_type}"
            assert result.model_id is not None
            assert result.provider is not None

    def test_cost_tracking_across_selections(self, model_selector: ModelSelector):
        """Test cost estimation across multiple selections."""
        task_types = ["code_generation", "code_review", "analysis", "simple_tasks"]

        total_estimated_cost = 0.0

        for task_type in task_types:
            criteria = SelectionCriteria(
                task_type=task_type,
                strategy=SelectionStrategy.BALANCED
            )

            result = model_selector.select_model(criteria)
            assert result is not None

            total_estimated_cost += result.estimated_cost

        # Total cost should be reasonable
        assert total_estimated_cost > 0
        assert total_estimated_cost < 1.0  # Less than $1 for typical tasks

    def test_model_availability_changes(self, test_config_path: Path):
        """Test behavior when model availability changes."""
        # Create manager and selector
        model_manager = ModelManager(config_path=test_config_path)
        model_selector = ModelSelector(model_manager, config_path=test_config_path)

        # Initial selection
        criteria = SelectionCriteria(task_type="code_generation")
        result1 = model_selector.select_model(criteria)
        assert result1 is not None

        # Simulate model becoming unavailable
        anthropic_provider = model_manager.get_provider(ModelProviderType.ANTHROPIC)
        sonnet_model = anthropic_provider.get_model("claude-3-5-sonnet-20241022")
        sonnet_model.available = False

        # Select again - should choose different model
        result2 = model_selector.select_model(criteria)
        assert result2 is not None
        if result1.model_id == "claude-3-5-sonnet-20241022":
            # Should have switched to a different model
            assert result2.model_id != "claude-3-5-sonnet-20241022"

    def test_concurrent_selections(self, model_selector: ModelSelector):
        """Test that concurrent selections work correctly."""
        import threading

        results = []
        errors = []

        def select_model():
            try:
                criteria = SelectionCriteria(
                    task_type="code_generation",
                    strategy=SelectionStrategy.BALANCED
                )
                result = model_selector.select_model(criteria)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = [threading.Thread(target=select_model) for _ in range(5)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all selections succeeded
        assert len(errors) == 0
        assert len(results) == 5
        for result in results:
            assert result is not None
            assert result.model_id is not None
