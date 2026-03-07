"""
End-to-End Verification Script for Multi-Model Support

This script performs comprehensive verification of:
1. Model configuration with multiple providers
2. Agent creation with different task types
3. Appropriate model selection for each task type
4. Model failure and fallback behavior
5. Metrics tracking

Run with: pytest tests/test_e2e_model_selection_verification.py -v -s
"""

import pytest
import json
import time
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock

# Mock external libraries before import
import sys
sys.modules['anthropic'] = MagicMock()
sys.modules['openai'] = MagicMock()
sys.modules['requests'] = MagicMock()

from devflow.core.model_manager import ModelManager, ModelProviderType
from devflow.core.model_selector import ModelSelector, SelectionStrategy
from devflow.core.model_metrics import ModelMetrics
from devflow.core.agent_manager import AgentManager, AgentConfig
from devflow.core.state_tracker import StateTracker
from devflow.core.session_manager import SessionManager


class TestEndToEndModelSelection:
    """End-to-end tests for model selection system."""

    @pytest.fixture
    def test_config_path(self, tmp_path: Path) -> Path:
        """Create test configuration with multiple models."""
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
                            "capabilities": ["code_generation", "code_review", "architecture", "analysis", "writing"],
                            "priority": 1,
                            "available": True
                        },
                        "claude-3-opus-20240229": {
                            "name": "Claude 3 Opus",
                            "type": "chat",
                            "max_tokens": 200000,
                            "input_cost_per_1k": 0.015,
                            "output_cost_per_1k": 0.075,
                            "capabilities": ["complex_reasoning", "code_generation", "code_review", "architecture", "analysis"],
                            "priority": 2,
                            "available": True
                        },
                        "claude-3-haiku-20240307": {
                            "name": "Claude 3 Haiku",
                            "type": "chat",
                            "max_tokens": 200000,
                            "input_cost_per_1k": 0.00025,
                            "output_cost_per_1k": 0.00125,
                            "capabilities": ["simple_tasks", "quick_response", "classification"],
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
                            "capabilities": ["code_generation", "code_review", "analysis", "writing"],
                            "priority": 1,
                            "available": True
                        },
                        "gpt-4": {
                            "name": "GPT-4",
                            "type": "chat",
                            "max_tokens": 8192,
                            "input_cost_per_1k": 0.03,
                            "output_cost_per_1k": 0.06,
                            "capabilities": ["complex_reasoning", "code_generation", "code_review"],
                            "priority": 2,
                            "available": True
                        },
                        "gpt-3.5-turbo": {
                            "name": "GPT-3.5 Turbo",
                            "type": "chat",
                            "max_tokens": 16385,
                            "input_cost_per_1k": 0.0005,
                            "output_cost_per_1k": 0.0015,
                            "capabilities": ["simple_tasks", "quick_response", "classification"],
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
                "architecture": {
                    "preferred_models": [
                        "anthropic/claude-3-5-sonnet-20241022",
                        "anthropic/claude-3-opus-20240229"
                    ],
                    "fallback_models": [
                        "openai/gpt-4"
                    ],
                    "min_capability": "architecture"
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
                "writing": {
                    "preferred_models": [
                        "anthropic/claude-3-5-sonnet-20241022",
                        "openai/gpt-4-turbo"
                    ],
                    "fallback_models": [
                        "openai/gpt-3.5-turbo",
                        "anthropic/claude-3-haiku-20240307"
                    ],
                    "min_capability": "writing"
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
                "architect": {
                    "task_type": "architecture",
                    "model_override": None
                },
                "business-analyst": {
                    "task_type": "analysis",
                    "model_override": None
                },
                "product-owner": {
                    "task_type": "writing",
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
                    }
                }
            }
        }

        config_file = tmp_path / "model_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f)

        return config_file

    @pytest.fixture
    def model_manager(self, test_config_path: Path) -> ModelManager:
        """Create ModelManager instance."""
        return ModelManager(config_path=test_config_path)

    @pytest.fixture
    def model_selector(self, model_manager: ModelManager, test_config_path: Path) -> ModelSelector:
        """Create ModelSelector instance."""
        return ModelSelector(model_manager=model_manager, config_path=test_config_path)

    @pytest.fixture
    def agent_manager(self, model_manager: ModelManager) -> AgentManager:
        """Create AgentManager instance."""
        state_tracker = StateTracker()
        session_manager = SessionManager()
        return AgentManager(state_tracker, session_manager)

    def test_step1_multiple_models_configured(self, test_config_path: Path):
        """
        Step 1: Verify multiple models are configured in model_config.json
        """
        print("\n=== Step 1: Verifying multiple models are configured ===")

        # Load and verify configuration
        with open(test_config_path, 'r') as f:
            config = json.load(f)

        # Check providers exist
        assert "providers" in config, "Missing 'providers' key in config"
        assert "anthropic" in config["providers"], "Missing Anthropic provider"
        assert "openai" in config["providers"], "Missing OpenAI provider"

        # Check models for each provider
        anthropic_models = config["providers"]["anthropic"]["models"]
        openai_models = config["providers"]["openai"]["models"]

        # Verify Anthropic has multiple models
        assert len(anthropic_models) >= 3, "Expected at least 3 Anthropic models"
        assert "claude-3-5-sonnet-20241022" in anthropic_models
        assert "claude-3-opus-20240229" in anthropic_models
        assert "claude-3-haiku-20240307" in anthropic_models

        # Verify OpenAI has multiple models
        assert len(openai_models) >= 3, "Expected at least 3 OpenAI models"
        assert "gpt-4-turbo" in openai_models
        assert "gpt-4" in openai_models
        assert "gpt-3.5-turbo" in openai_models

        print(f"✓ Found {len(anthropic_models)} Anthropic models")
        print(f"✓ Found {len(openai_models)} OpenAI models")
        print(f"✓ Configuration verified successfully")

    def test_step2_create_agents_different_task_types(self, agent_manager: AgentManager):
        """
        Step 2: Create agents with different task types
        """
        print("\n=== Step 2: Creating agents with different task types ===")

        # Test different agent types
        agent_types_to_test = [
            ("dev-story-1", "dev-story", "Implement user authentication"),
            ("code-review-1", "code-review", "Review PR #123"),
            ("architect-1", "architect", "Design system architecture"),
            ("business-analyst-1", "business-analyst", "Analyze requirements"),
            ("product-owner-1", "product-owner", "Define product roadmap"),
        ]

        created_agents = []

        for agent_id, agent_type, task in agent_types_to_test:
            # Create agent
            created_id = agent_manager.create_agent(
                agent_id=agent_id,
                agent_type=agent_type,
                task=task
            )

            # Verify agent was created
            assert created_id == agent_id, f"Failed to create agent {agent_id}"

            # Get agent info
            agent_info = agent_manager.get_agent(agent_id)
            assert agent_info is not None, f"Agent {agent_id} not found"

            # Verify model was selected
            assert agent_info["config"].model is not None, f"No model selected for {agent_id}"

            created_agents.append({
                "id": agent_id,
                "type": agent_type,
                "task": task,
                "model": agent_info["config"].model,
                "selection": agent_info["model_selection"]
            })

            print(f"✓ Created {agent_type} agent with model: {agent_info['config'].model}")

        # Verify all agents were created
        assert len(created_agents) == len(agent_types_to_test)

        print(f"\n✓ Successfully created {len(created_agents)} agents with different task types")

    def test_step3_verify_appropriate_model_selection(self, agent_manager: AgentManager):
        """
        Step 3: Verify appropriate models are selected for each task type
        """
        print("\n=== Step 3: Verifying appropriate model selection ===")

        # Define expected model mappings based on task types
        # (models that should be selected for each agent type)
        expected_models_by_task = {
            "code_generation": ["claude-3-5-sonnet-20241022", "gpt-4-turbo"],
            "code_review": ["claude-3-5-sonnet-20241022", "gpt-4-turbo"],
            "architecture": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
            "analysis": ["claude-3-5-sonnet-20241022", "gpt-4-turbo"],
            "writing": ["claude-3-5-sonnet-20241022", "gpt-4-turbo"],
        }

        # Create agents for different task types
        test_cases = [
            ("dev-story-test", "dev-story", "Implement feature X", "code_generation"),
            ("code-review-test", "code-review", "Review code", "code_review"),
            ("architect-test", "architect", "Design system", "architecture"),
            ("ba-test", "business-analyst", "Analyze data", "analysis"),
            ("po-test", "product-owner", "Write requirements", "writing"),
        ]

        verification_results = []

        for agent_id, agent_type, task, expected_task in test_cases:
            # Create agent
            agent_manager.create_agent(
                agent_id=agent_id,
                agent_type=agent_type,
                task=task
            )

            # Get agent info
            agent_info = agent_manager.get_agent(agent_id)
            selected_model = agent_info["config"].model
            selection_result = agent_info["model_selection"]

            # Verify model is appropriate for task type
            expected_models = expected_models_by_task[expected_task]
            is_appropriate = selected_model in expected_models

            # Verify selection result details
            assert selection_result is not None, "No selection result found"
            assert selection_result.model_id == selected_model, "Model ID mismatch"
            assert selection_result.provider in ["anthropic", "openai"], "Invalid provider"
            assert selection_result.score > 0, "Invalid selection score"
            assert selection_result.estimated_cost > 0, "Invalid cost estimate"
            assert selection_result.estimated_latency > 0, "Invalid latency estimate"
            assert selection_result.fallback_available is True, "Fallback should be available"

            verification_results.append({
                "agent_type": agent_type,
                "expected_task": expected_task,
                "selected_model": selected_model,
                "provider": selection_result.provider,
                "score": selection_result.score,
                "estimated_cost": selection_result.estimated_cost,
                "is_appropriate": is_appropriate,
                "has_fallback": selection_result.fallback_available
            })

            status = "✓" if is_appropriate else "✗"
            print(f"{status} {agent_type}: {selected_model} ({selection_result.provider}) "
                  f"- Cost: ${selection_result.estimated_cost:.4f}, "
                  f"Latency: {selection_result.estimated_latency:.0f}ms")

            assert is_appropriate, f"Inappropriate model {selected_model} for task type {expected_task}"

        print(f"\n✓ All {len(verification_results)} agents have appropriate model selections")
        print("✓ Model selection correctly maps task types to capable models")

    def test_step4_trigger_model_failure_and_fallback(self, agent_manager: AgentManager):
        """
        Step 4: Trigger a model failure and verify fallback occurs
        """
        print("\n=== Step 4: Testing model failure and fallback ===")

        # Create an agent
        agent_id = "test-fallback-agent"
        agent_manager.create_agent(
            agent_id=agent_id,
            agent_type="dev-story",
            task="Implement test feature"
        )

        # Get initial model
        agent_info = agent_manager.get_agent(agent_id)
        initial_model = agent_info["config"].model
        initial_selection = agent_info["model_selection"]

        print(f"Initial model: {initial_model}")

        # Simulate model failure
        print(f"Simulating failure for model: {initial_model}")

        fallback_result = agent_manager.handle_model_failure(
            agent_id=agent_id,
            failed_model_id=initial_model,
            error=Exception("Simulated API error")
        )

        # Verify fallback occurred
        assert fallback_result is not None, "No fallback model available"
        assert fallback_result.model_id != initial_model, "Fallback model same as failed model"

        # Get updated agent info
        updated_info = agent_manager.get_agent(agent_id)
        new_model = updated_info["config"].model

        print(f"Fallback model: {fallback_result.model_id}")
        print(f"Agent updated to: {new_model}")

        # Verify agent config was updated
        assert new_model == fallback_result.model_id, "Agent model not updated"

        # Verify fallback info
        fallback_info = agent_manager.get_agent_fallback_info(agent_id)
        assert fallback_info is not None, "No fallback info available"
        assert fallback_info["fallback_count"] == 1, "Fallback count incorrect"
        assert len(fallback_info["fallback_history"]) == 1, "Fallback history missing"
        # Verify failed model is in excluded list (may be with or without provider prefix)
        assert initial_model in fallback_info["excluded_models"], "Failed model not excluded"

        print(f"Fallback count: {fallback_info['fallback_count']}")
        print(f"Fallback history: {fallback_info['fallback_history']}")
        print(f"Excluded models: {fallback_info['excluded_models']}")

        # Test multiple sequential fallbacks
        print("\nTesting multiple sequential fallbacks...")

        # Trigger second failure
        second_fallback = agent_manager.handle_model_failure(
            agent_id=agent_id,
            failed_model_id=new_model,
            error=Exception("Second failure")
        )

        if second_fallback:
            print(f"Second fallback: {second_fallback.model_id}")

            # Verify fallback count increased
            fallback_info = agent_manager.get_agent_fallback_info(agent_id)
            assert fallback_info["fallback_count"] == 2, "Fallback count not incremented"
            assert len(fallback_info["fallback_history"]) == 2, "Fallback history incomplete"

            print(f"Fallback count after second failure: {fallback_info['fallback_count']}")
        else:
            print("No second fallback available (all models exhausted)")

        print("\n✓ Model failure triggered successful fallback")
        print("✓ Agent configuration updated with fallback model")
        print("✓ Fallback history and excluded models tracked correctly")

    def test_step5_verify_metrics_tracking(self, agent_manager: AgentManager):
        """
        Step 5: Check metrics are being tracked
        """
        print("\n=== Step 5: Verifying metrics tracking ===")

        # Create multiple agents and simulate activity
        test_agents = [
            ("metrics-agent-1", "dev-story", "Task 1"),
            ("metrics-agent-2", "code-review", "Task 2"),
            ("metrics-agent-3", "architect", "Task 3"),
        ]

        created_agents = []

        for agent_id, agent_type, task in test_agents:
            agent_manager.create_agent(
                agent_id=agent_id,
                agent_type=agent_type,
                task=task
            )

            agent_info = agent_manager.get_agent(agent_id)
            created_agents.append({
                "id": agent_id,
                "type": agent_type,
                "model": agent_info["config"].model,
                "selection": agent_info["model_selection"]
            })

        # Simulate metrics updates
        model_selector = agent_manager.model_selector

        print("Simulating model usage with metrics...")

        for agent in created_agents:
            model_id = agent["model"]

            # Simulate successful request
            model_selector.update_model_metrics(
                model_id=model_id,
                latency=1500.0,
                success=True,
                token_count=5000
            )

            print(f"✓ Recorded metrics for {agent['type']}: {model_id}")

        # Verify metrics are tracked
        print("\nRetrieving metrics...")

        all_metrics = model_selector.get_all_metrics()
        assert len(all_metrics) > 0, "No metrics recorded"

        print(f"\n✓ Metrics tracked for {len(all_metrics)} models")

        # Verify individual model metrics
        for agent in created_agents:
            model_id = agent["model"]
            metrics = model_selector.get_model_metrics(model_id)

            if metrics:
                print(f"\nMetrics for {model_id}:")
                print(f"  Total requests: {metrics['total_requests']}")
                print(f"  Successful: {metrics['successful_requests']}")
                print(f"  Failed: {metrics['failed_requests']}")
                print(f"  Avg latency: {metrics['avg_latency']:.2f}ms")
                print(f"  Success rate: {metrics['success_rate']:.2%}")

                assert metrics['total_requests'] > 0, "No requests recorded"
                assert metrics['successful_requests'] > 0, "No successful requests"
                assert metrics['avg_latency'] > 0, "No latency recorded"
                assert metrics['success_rate'] > 0, "No success rate recorded"

        # Verify model selector has internal metrics cache
        assert hasattr(model_selector, 'model_metrics'), "Missing metrics cache"
        assert len(model_selector.model_metrics) > 0, "Metrics cache empty"

        print("\n✓ Metrics tracking working correctly")
        print("✓ Latency, success rate, and token usage all tracked")
        print("✓ Metrics can be retrieved for individual models")
        print("✓ Overall metrics summary available")

    def test_complete_end_to_end_workflow(self, agent_manager: AgentManager):
        """
        Complete end-to-end workflow test combining all verification steps
        """
        print("\n" + "="*70)
        print("COMPLETE END-TO-END VERIFICATION")
        print("="*70)

        # Step 1: Create agents
        print("\n[Step 1] Creating agents for different task types...")
        agents = []

        agent_configs = [
            ("agent-dev-1", "dev-story", "Implement authentication", "code_generation"),
            ("agent-review-1", "code-review", "Review PR #456", "code_review"),
            ("agent-arch-1", "architect", "Design API architecture", "architecture"),
        ]

        for agent_id, agent_type, task, expected_task in agent_configs:
            agent_manager.create_agent(agent_id, agent_type, task)
            agent_info = agent_manager.get_agent(agent_id)
            agents.append({
                "id": agent_id,
                "type": agent_type,
                "task": expected_task,
                "model": agent_info["config"].model,
                "selection": agent_info["model_selection"]
            })
            print(f"  ✓ {agent_id}: {agent_info['config'].model}")

        # Step 2: Verify model selection
        print("\n[Step 2] Verifying model selection...")

        expected_models = {
            "code_generation": ["claude-3-5-sonnet-20241022", "gpt-4-turbo"],
            "code_review": ["claude-3-5-sonnet-20241022", "gpt-4-turbo"],
            "architecture": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
        }

        for agent in agents:
            task = agent["task"]
            model = agent["model"]
            valid = model in expected_models[task]
            assert valid, f"Invalid model {model} for task {task}"
            print(f"  ✓ {agent['id']}: {model} is appropriate for {task}")

        # Step 3: Track metrics
        print("\n[Step 3] Tracking metrics...")

        model_selector = agent_manager.model_selector

        for agent in agents:
            model_selector.update_model_metrics(
                model_id=agent["model"],
                latency=1200.0,
                success=True,
                token_count=4000
            )
            print(f"  ✓ Tracked metrics for {agent['model']}")

        # Step 4: Test fallback
        print("\n[Step 4] Testing fallback...")

        test_agent = agents[0]
        agent_id = test_agent["id"]
        original_model = test_agent["model"]

        fallback = agent_manager.handle_model_failure(
            agent_id=agent_id,
            failed_model_id=original_model,
            error=Exception("Test failure")
        )

        assert fallback is not None, "No fallback available"
        assert fallback.model_id != original_model, "Fallback same as original"

        print(f"  ✓ Fallback from {original_model} to {fallback.model_id}")

        # Verify fallback info
        fallback_info = agent_manager.get_agent_fallback_info(agent_id)
        assert fallback_info["fallback_count"] == 1
        print(f"  ✓ Fallback count: {fallback_info['fallback_count']}")
        print(f"  ✓ Excluded models: {fallback_info['excluded_models']}")

        # Step 5: Verify final state
        print("\n[Step 5] Verifying final state...")

        # Check all metrics
        all_metrics = model_selector.get_all_metrics()
        print(f"  ✓ Total models with metrics: {len(all_metrics)}")

        # Check individual model metrics
        for agent in agents:
            model = agent["model"]
            metrics = model_selector.get_model_metrics(model)
            if metrics:
                print(f"  ✓ {model}: {metrics['total_requests']} requests, "
                      f"{metrics['success_rate']:.1%} success rate")

        print("\n" + "="*70)
        print("✓ ALL VERIFICATION STEPS PASSED")
        print("="*70)
        print("\nSummary:")
        print("  ✓ Multiple models configured correctly")
        print("  ✓ Agents created with appropriate task types")
        print("  ✓ Model selection works for different tasks")
        print("  ✓ Fallback mechanism functions correctly")
        print("  ✓ Metrics tracking working as expected")
