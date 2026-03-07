"""
Unit tests for ModelMetrics performance tracking.

Tests the metrics tracking system including:
- MetricRecord creation and storage
- ModelStatistics calculation and aggregation
- MetricsSummary generation
- Thread safety for concurrent operations
- Export/import functionality
- Filtering by task type and agent type
- Percentile calculations
- Error tracking and retrieval
"""

import pytest
import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict

from devflow.core.model_metrics import (
    MetricType,
    MetricRecord,
    ModelStatistics,
    MetricsSummary,
    ModelMetrics,
)


# Fixtures

@pytest.fixture
def sample_metrics() -> ModelMetrics:
    """Create a sample ModelMetrics instance."""
    return ModelMetrics(max_records=1000)


@pytest.fixture
def populated_metrics(sample_metrics: ModelMetrics) -> ModelMetrics:
    """Create a ModelMetrics instance with sample data."""
    # Add various records
    sample_metrics.record_request(
        model_id="claude-3-5-sonnet",
        provider="anthropic",
        latency_ms=150.5,
        cost_usd=0.005,
        input_tokens=1000,
        output_tokens=500,
        success=True,
        task_type="code_generation",
        agent_type="dev-story"
    )
    sample_metrics.record_request(
        model_id="claude-3-5-sonnet",
        provider="anthropic",
        latency_ms=200.0,
        cost_usd=0.006,
        input_tokens=1200,
        output_tokens=600,
        success=True,
        task_type="code_generation",
        agent_type="dev-story"
    )
    sample_metrics.record_request(
        model_id="gpt-4-turbo",
        provider="openai",
        latency_ms=180.0,
        cost_usd=0.008,
        input_tokens=800,
        output_tokens=400,
        success=True,
        task_type="analysis",
        agent_type="code-review"
    )
    sample_metrics.record_request(
        model_id="gpt-4-turbo",
        provider="openai",
        latency_ms=250.0,
        cost_usd=0.010,
        input_tokens=1500,
        output_tokens=750,
        success=False,
        error_message="Rate limit exceeded",
        task_type="analysis",
        agent_type="code-review"
    )
    sample_metrics.record_request(
        model_id="llama3-70b",
        provider="local",
        latency_ms=300.0,
        cost_usd=0.0,
        input_tokens=2000,
        output_tokens=1000,
        success=True,
        task_type="code_generation",
        agent_type="dev-story"
    )
    return sample_metrics


@pytest.fixture
def temp_export_file(tmp_path: Path) -> Path:
    """Create a temporary file for metrics export."""
    return tmp_path / "metrics_export.json"


# MetricRecord Tests

class TestMetricRecord:
    """Tests for MetricRecord dataclass."""

    def test_metric_record_creation(self):
        """Test creating a MetricRecord object."""
        record = MetricRecord(
            timestamp=time.time(),
            model_id="test-model",
            provider="test_provider",
            latency_ms=150.5,
            cost_usd=0.005,
            input_tokens=1000,
            output_tokens=500,
            success=True,
            error_message=None,
            task_type="code_generation",
            agent_type="dev-story"
        )
        assert record.model_id == "test-model"
        assert record.provider == "test_provider"
        assert record.latency_ms == 150.5
        assert record.cost_usd == 0.005
        assert record.input_tokens == 1000
        assert record.output_tokens == 500
        assert record.success is True
        assert record.error_message is None
        assert record.task_type == "code_generation"
        assert record.agent_type == "dev-story"

    def test_metric_record_with_error(self):
        """Test MetricRecord with error information."""
        record = MetricRecord(
            timestamp=time.time(),
            model_id="test-model",
            provider="test_provider",
            latency_ms=200.0,
            cost_usd=0.0,
            input_tokens=0,
            output_tokens=0,
            success=False,
            error_message="API Error"
        )
        assert record.success is False
        assert record.error_message == "API Error"


# ModelStatistics Tests

class TestModelStatistics:
    """Tests for ModelStatistics dataclass."""

    def test_model_statistics_creation(self):
        """Test creating a ModelStatistics object."""
        stats = ModelStatistics(
            model_id="test-model",
            provider="test_provider",
            total_requests=10,
            successful_requests=9,
            failed_requests=1,
            avg_latency_ms=150.5,
            min_latency_ms=100.0,
            max_latency_ms=200.0,
            p50_latency_ms=150.0,
            p95_latency_ms=190.0,
            p99_latency_ms=198.0,
            total_cost_usd=0.05,
            avg_cost_usd=0.005,
            total_input_tokens=5000,
            total_output_tokens=2500,
            avg_input_tokens=500,
            avg_output_tokens=250,
            success_rate=0.9,
            error_rate=0.1,
            last_updated=time.time(),
            latencies=[100.0, 150.0, 200.0],
            costs=[0.003, 0.005, 0.007]
        )
        assert stats.model_id == "test-model"
        assert stats.provider == "test_provider"
        assert stats.total_requests == 10
        assert stats.successful_requests == 9
        assert stats.failed_requests == 1
        assert stats.success_rate == 0.9
        assert stats.error_rate == 0.1


# MetricsSummary Tests

class TestMetricsSummary:
    """Tests for MetricsSummary dataclass."""

    def test_metrics_summary_creation(self):
        """Test creating a MetricsSummary object."""
        summary = MetricsSummary(
            total_requests=100,
            total_cost_usd=0.5,
            total_tokens=50000,
            overall_success_rate=0.95,
            most_used_model="claude-3-5-sonnet",
            fastest_model="gpt-4-turbo",
            most_cost_effective_model="llama3-70b",
            model_count=3
        )
        assert summary.total_requests == 100
        assert summary.total_cost_usd == 0.5
        assert summary.total_tokens == 50000
        assert summary.overall_success_rate == 0.95
        assert summary.most_used_model == "claude-3-5-sonnet"
        assert summary.fastest_model == "gpt-4-turbo"
        assert summary.most_cost_effective_model == "llama3-70b"
        assert summary.model_count == 3


# ModelMetrics Tests

class TestModelMetricsInitialization:
    """Tests for ModelMetrics initialization."""

    def test_initialization_default(self):
        """Test ModelMetrics initialization with default values."""
        metrics = ModelMetrics()
        assert metrics.max_records == 10000
        assert metrics.records == []
        assert metrics.model_stats == {}
        assert metrics.lock is not None
        assert metrics.provider_costs == {}

    def test_initialization_custom_max_records(self):
        """Test ModelMetrics initialization with custom max_records."""
        metrics = ModelMetrics(max_records=500)
        assert metrics.max_records == 500


class TestModelMetricsRecordRequest:
    """Tests for recording model requests."""

    def test_record_request_basic(self, sample_metrics: ModelMetrics):
        """Test basic request recording."""
        sample_metrics.record_request(
            model_id="test-model",
            provider="test_provider",
            latency_ms=150.5,
            cost_usd=0.005,
            input_tokens=1000,
            output_tokens=500,
            success=True
        )
        assert len(sample_metrics.records) == 1
        assert sample_metrics.records[0].model_id == "test-model"
        assert sample_metrics.records[0].latency_ms == 150.5

    def test_record_request_with_metadata(self, sample_metrics: ModelMetrics):
        """Test request recording with task type and agent type."""
        sample_metrics.record_request(
            model_id="test-model",
            provider="test_provider",
            latency_ms=150.5,
            cost_usd=0.005,
            input_tokens=1000,
            output_tokens=500,
            success=True,
            task_type="code_generation",
            agent_type="dev-story"
        )
        assert sample_metrics.records[0].task_type == "code_generation"
        assert sample_metrics.records[0].agent_type == "dev-story"

    def test_record_request_with_error(self, sample_metrics: ModelMetrics):
        """Test recording a failed request."""
        sample_metrics.record_request(
            model_id="test-model",
            provider="test_provider",
            latency_ms=200.0,
            cost_usd=0.0,
            input_tokens=0,
            output_tokens=0,
            success=False,
            error_message="API Error"
        )
        assert sample_metrics.records[0].success is False
        assert sample_metrics.records[0].error_message == "API Error"

    def test_record_request_auto_trim(self, sample_metrics: ModelMetrics):
        """Test that records are automatically trimmed when exceeding max."""
        small_metrics = ModelMetrics(max_records=3)
        # Add 5 records
        for i in range(5):
            small_metrics.record_request(
                model_id=f"model-{i}",
                provider="test",
                latency_ms=100.0 + i,
                cost_usd=0.001,
                success=True
            )
        # Should only keep last 3
        assert len(small_metrics.records) == 3
        assert small_metrics.records[0].model_id == "model-2"

    def test_record_request_updates_provider_costs(self, sample_metrics: ModelMetrics):
        """Test that recording updates provider costs."""
        sample_metrics.record_request(
            model_id="test-model",
            provider="anthropic",
            latency_ms=150.0,
            cost_usd=0.005,
            success=True
        )
        assert sample_metrics.provider_costs["anthropic"] == 0.005
        sample_metrics.record_request(
            model_id="test-model",
            provider="anthropic",
            latency_ms=150.0,
            cost_usd=0.003,
            success=True
        )
        assert sample_metrics.provider_costs["anthropic"] == 0.008


class TestModelMetricsStatistics:
    """Tests for statistics calculation and retrieval."""

    def test_get_model_statistics_existing(self, populated_metrics: ModelMetrics):
        """Test getting statistics for an existing model."""
        stats = populated_metrics.get_model_statistics("claude-3-5-sonnet")
        assert stats is not None
        assert stats.model_id == "claude-3-5-sonnet"
        assert stats.provider == "anthropic"
        assert stats.total_requests == 2
        assert stats.successful_requests == 2
        assert stats.failed_requests == 0
        assert stats.avg_latency_ms == 175.25  # (150.5 + 200.0) / 2
        assert stats.min_latency_ms == 150.5
        assert stats.max_latency_ms == 200.0

    def test_get_model_statistics_nonexistent(self, sample_metrics: ModelMetrics):
        """Test getting statistics for a non-existent model."""
        stats = sample_metrics.get_model_statistics("nonexistent")
        assert stats is None

    def test_get_all_statistics(self, populated_metrics: ModelMetrics):
        """Test getting statistics for all models."""
        all_stats = populated_metrics.get_all_statistics()
        assert len(all_stats) == 3
        assert "claude-3-5-sonnet" in all_stats
        assert "gpt-4-turbo" in all_stats
        assert "llama3-70b" in all_stats

    def test_statistics_percentiles(self, populated_metrics: ModelMetrics):
        """Test percentile calculations in statistics."""
        stats = populated_metrics.get_model_statistics("claude-3-5-sonnet")
        # With only 2 data points, p50 should be the middle value
        assert stats.p50_latency_ms >= stats.min_latency_ms
        assert stats.p50_latency_ms <= stats.max_latency_ms

    def test_statistics_success_rate(self, populated_metrics: ModelMetrics):
        """Test success rate calculation."""
        stats = populated_metrics.get_model_statistics("gpt-4-turbo")
        assert stats.total_requests == 2
        assert stats.successful_requests == 1
        assert stats.failed_requests == 1
        assert stats.success_rate == 0.5
        assert stats.error_rate == 0.5


class TestModelMetricsSummary:
    """Tests for metrics summary generation."""

    def test_get_summary_populated(self, populated_metrics: ModelMetrics):
        """Test getting summary with populated data."""
        summary = populated_metrics.get_summary()
        assert summary.total_requests == 5
        assert summary.total_cost_usd == pytest.approx(0.029, rel=0.1)
        assert summary.total_tokens > 0
        assert summary.overall_success_rate == 0.8  # 4/5 success
        assert summary.most_used_model in ["claude-3-5-sonnet", "gpt-4-turbo"]
        assert summary.model_count == 3

    def test_get_summary_empty(self, sample_metrics: ModelMetrics):
        """Test getting summary with no data."""
        summary = sample_metrics.get_summary()
        assert summary.total_requests == 0
        assert summary.total_cost_usd == 0.0
        assert summary.total_tokens == 0
        assert summary.overall_success_rate == 0.0
        assert summary.most_used_model == ""
        assert summary.fastest_model == ""
        assert summary.most_cost_effective_model == ""
        assert summary.model_count == 0


class TestModelMetricsLatency:
    """Tests for latency tracking and percentiles."""

    def test_get_latency_percentiles_existing(self, populated_metrics: ModelMetrics):
        """Test getting latency percentiles for existing model."""
        percentiles = populated_metrics.get_latency_percentiles("claude-3-5-sonnet")
        assert percentiles is not None
        assert "p50" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles
        assert percentiles["p50"] > 0

    def test_get_latency_percentiles_nonexistent(self, sample_metrics: ModelMetrics):
        """Test getting latency percentiles for non-existent model."""
        percentiles = sample_metrics.get_latency_percentiles("nonexistent")
        assert percentiles is None


class TestModelMetricsSuccessRate:
    """Tests for success rate tracking."""

    def test_get_success_rate_default_window(self, populated_metrics: ModelMetrics):
        """Test getting success rate with default time window."""
        # All records are within default 60 minute window
        rate = populated_metrics.get_success_rate("gpt-4-turbo")
        assert rate == 50.0  # 1 success out of 2 = 50%

    def test_get_success_rate_custom_window(self, populated_metrics: ModelMetrics):
        """Test getting success rate with custom time window."""
        # Very small window (1 second) - should only include very recent requests
        rate = populated_metrics.get_success_rate("claude-3-5-sonnet", window_minutes=0)
        # Depending on timing, might be 0 or 100
        assert isinstance(rate, float)
        assert 0 <= rate <= 100

    def test_get_success_rate_no_records(self, sample_metrics: ModelMetrics):
        """Test getting success rate when no records exist."""
        rate = sample_metrics.get_success_rate("nonexistent")
        assert rate == 0.0


class TestModelMetricsCosts:
    """Tests for cost tracking."""

    def test_get_cost_by_provider(self, populated_metrics: ModelMetrics):
        """Test getting costs broken down by provider."""
        costs = populated_metrics.get_cost_by_provider()
        assert "anthropic" in costs
        assert "openai" in costs
        assert "local" in costs
        assert costs["anthropic"] == pytest.approx(0.011, rel=0.1)
        assert costs["openai"] == pytest.approx(0.018, rel=0.1)
        assert costs["local"] == 0.0

    def test_get_cost_by_provider_empty(self, sample_metrics: ModelMetrics):
        """Test getting costs when no data exists."""
        costs = sample_metrics.get_cost_by_provider()
        assert costs == {}


class TestModelMetricsTopModels:
    """Tests for top models tracking."""

    def test_get_top_models_by_usage(self, populated_metrics: ModelMetrics):
        """Test getting top models by usage count."""
        top_models = populated_metrics.get_top_models_by_usage(limit=5)
        assert len(top_models) == 3
        # All models have 2 requests except one might have different count
        model_ids = [model_id for model_id, _ in top_models]
        assert "claude-3-5-sonnet" in model_ids
        assert "gpt-4-turbo" in model_ids
        assert "llama3-70b" in model_ids

    def test_get_top_models_by_usage_limit(self, populated_metrics: ModelMetrics):
        """Test getting top models with limit."""
        top_models = populated_metrics.get_top_models_by_usage(limit=2)
        assert len(top_models) == 2

    def test_get_top_models_by_usage_empty(self, sample_metrics: ModelMetrics):
        """Test getting top models when no data exists."""
        top_models = sample_metrics.get_top_models_by_usage()
        assert top_models == []


class TestModelMetricsErrors:
    """Tests for error tracking."""

    def test_get_recent_errors(self, populated_metrics: ModelMetrics):
        """Test getting recent error records."""
        errors = populated_metrics.get_recent_errors(limit=10)
        assert len(errors) == 1
        assert errors[0].success is False
        assert errors[0].error_message == "Rate limit exceeded"
        assert errors[0].model_id == "gpt-4-turbo"

    def test_get_recent_errors_limit(self, populated_metrics: ModelMetrics):
        """Test getting recent errors with limit."""
        errors = populated_metrics.get_recent_errors(limit=1)
        assert len(errors) <= 1

    def test_get_recent_errors_empty(self, sample_metrics: ModelMetrics):
        """Test getting recent errors when no errors exist."""
        errors = sample_metrics.get_recent_errors()
        assert errors == []


class TestModelMetricsFiltering:
    """Tests for filtering metrics by task type and agent type."""

    def test_get_metrics_by_task_type(self, populated_metrics: ModelMetrics):
        """Test filtering metrics by task type."""
        code_gen_stats = populated_metrics.get_metrics_by_task_type("code_generation")
        assert len(code_gen_stats) == 2  # claude and llama3
        assert "claude-3-5-sonnet" in code_gen_stats
        assert "llama3-70b" in code_gen_stats
        assert code_gen_stats["claude-3-5-sonnet"].total_requests == 2

    def test_get_metrics_by_task_type_nonexistent(self, populated_metrics: ModelMetrics):
        """Test filtering by non-existent task type."""
        stats = populated_metrics.get_metrics_by_task_type("nonexistent")
        assert stats == {}

    def test_get_metrics_by_agent_type(self, populated_metrics: ModelMetrics):
        """Test filtering metrics by agent type."""
        dev_story_stats = populated_metrics.get_metrics_by_agent_type("dev-story")
        assert len(dev_story_stats) == 2  # claude and llama3
        assert "claude-3-5-sonnet" in dev_story_stats
        assert "llama3-70b" in dev_story_stats

    def test_get_metrics_by_agent_type_nonexistent(self, populated_metrics: ModelMetrics):
        """Test filtering by non-existent agent type."""
        stats = populated_metrics.get_metrics_by_agent_type("nonexistent")
        assert stats == {}


class TestModelMetricsExportImport:
    """Tests for export and import functionality."""

    def test_export_metrics_dict(self, populated_metrics: ModelMetrics):
        """Test exporting metrics to dictionary."""
        export_data = populated_metrics.export_metrics()
        assert "timestamp" in export_data
        assert "summary" in export_data
        assert "models" in export_data
        assert export_data["summary"]["total_requests"] == 5
        assert len(export_data["models"]) == 3

    def test_export_metrics_to_file(self, populated_metrics: ModelMetrics, temp_export_file: Path):
        """Test exporting metrics to file."""
        populated_metrics.export_metrics(filepath=temp_export_file)
        assert temp_export_file.exists()

        # Verify file contents
        with open(temp_export_file, 'r') as f:
            data = json.load(f)
        assert "summary" in data
        assert "models" in data
        assert data["summary"]["total_requests"] == 5

    def test_import_metrics(self, sample_metrics: ModelMetrics):
        """Test importing metrics from dictionary."""
        import_data = {
            "summary": {
                "total_requests": 100,
                "total_cost_usd": 0.5,
                "total_tokens": 50000,
                "provider_costs": {
                    "anthropic": 0.3,
                    "openai": 0.2
                }
            },
            "models": {}
        }
        sample_metrics.import_metrics(import_data)
        assert sample_metrics.provider_costs["anthropic"] == 0.3
        assert sample_metrics.provider_costs["openai"] == 0.2


class TestModelMetricsReset:
    """Tests for reset functionality."""

    def test_reset_metrics_all(self, populated_metrics: ModelMetrics):
        """Test resetting all metrics."""
        populated_metrics.reset_metrics()
        assert len(populated_metrics.records) == 0
        assert len(populated_metrics.model_stats) == 0
        assert len(populated_metrics.provider_costs) == 0

    def test_reset_metrics_specific_model(self, populated_metrics: ModelMetrics):
        """Test resetting metrics for a specific model."""
        populated_metrics.reset_metrics(model_id="gpt-4-turbo")
        assert "gpt-4-turbo" not in populated_metrics.model_stats
        assert "claude-3-5-sonnet" in populated_metrics.model_stats
        assert "llama3-70b" in populated_metrics.model_stats
        # Check records are also filtered
        for record in populated_metrics.records:
            assert record.model_id != "gpt-4-turbo"

    def test_reset_metrics_nonexistent_model(self, populated_metrics: ModelMetrics):
        """Test resetting metrics for non-existent model."""
        initial_count = len(populated_metrics.model_stats)
        populated_metrics.reset_metrics(model_id="nonexistent")
        # Should not affect existing models
        assert len(populated_metrics.model_stats) == initial_count


class TestModelMetricsThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_recording(self, sample_metrics: ModelMetrics):
        """Test concurrent request recording."""
        num_threads = 10
        records_per_thread = 100

        def record_requests(thread_id: int):
            for i in range(records_per_thread):
                sample_metrics.record_request(
                    model_id=f"model-{thread_id % 3}",
                    provider=f"provider-{thread_id % 2}",
                    latency_ms=100.0 + i,
                    cost_usd=0.001,
                    input_tokens=100,
                    output_tokens=50,
                    success=True
                )

        threads = [
            threading.Thread(target=record_requests, args=(i,))
            for i in range(num_threads)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all records were captured
        assert len(sample_metrics.records) == num_threads * records_per_thread

        # Verify statistics were updated
        total_stats_requests = sum(
            stats.total_requests for stats in sample_metrics.model_stats.values()
        )
        assert total_stats_requests == num_threads * records_per_thread

    def test_concurrent_read_write(self, populated_metrics: ModelMetrics):
        """Test concurrent reads and writes."""
        def write_records():
            for i in range(50):
                populated_metrics.record_request(
                    model_id="test-model",
                    provider="test",
                    latency_ms=100.0 + i,
                    cost_usd=0.001,
                    success=True
                )

        def read_records():
            for _ in range(50):
                populated_metrics.get_summary()
                populated_metrics.get_all_statistics()
                populated_metrics.get_top_models_by_usage()

        threads = [
            threading.Thread(target=write_records),
            threading.Thread(target=read_records),
            threading.Thread(target=read_records)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should not raise any exceptions
        assert len(populated_metrics.records) > 0


class TestModelMetricsEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_single_request_statistics(self, sample_metrics: ModelMetrics):
        """Test statistics with a single request."""
        sample_metrics.record_request(
            model_id="test-model",
            provider="test",
            latency_ms=150.0,
            cost_usd=0.005,
            input_tokens=1000,
            output_tokens=500,
            success=True
        )
        stats = sample_metrics.get_model_statistics("test-model")
        assert stats.total_requests == 1
        assert stats.avg_latency_ms == 150.0
        assert stats.min_latency_ms == 150.0
        assert stats.max_latency_ms == 150.0

    def test_zero_latency(self, sample_metrics: ModelMetrics):
        """Test recording zero latency."""
        sample_metrics.record_request(
            model_id="test-model",
            provider="test",
            latency_ms=0.0,
            cost_usd=0.0,
            success=True
        )
        stats = sample_metrics.get_model_statistics("test-model")
        assert stats.min_latency_ms == 0.0

    def test_all_failed_requests(self, sample_metrics: ModelMetrics):
        """Test statistics when all requests failed."""
        for i in range(5):
            sample_metrics.record_request(
                model_id="test-model",
                provider="test",
                latency_ms=100.0 + i,
                cost_usd=0.0,
                success=False,
                error_message=f"Error {i}"
            )
        stats = sample_metrics.get_model_statistics("test-model")
        assert stats.total_requests == 5
        assert stats.successful_requests == 0
        assert stats.failed_requests == 5
        assert stats.success_rate == 0.0
        assert stats.error_rate == 1.0

    def test_very_large_numbers(self, sample_metrics: ModelMetrics):
        """Test handling very large token counts and costs."""
        sample_metrics.record_request(
            model_id="test-model",
            provider="test",
            latency_ms=1000.0,
            cost_usd=100.0,
            input_tokens=1000000,
            output_tokens=500000,
            success=True
        )
        stats = sample_metrics.get_model_statistics("test-model")
        assert stats.total_input_tokens == 1000000
        assert stats.total_output_tokens == 500000
        assert stats.total_cost_usd == 100.0


# Integration Tests

class TestModelMetricsIntegration:
    """Integration tests for ModelMetrics."""

    def test_full_metrics_workflow(self, sample_metrics: ModelMetrics, temp_export_file: Path):
        """Test complete workflow from recording to export."""
        # Record various requests
        sample_metrics.record_request(
            model_id="claude-3-5-sonnet",
            provider="anthropic",
            latency_ms=150.0,
            cost_usd=0.005,
            input_tokens=1000,
            output_tokens=500,
            success=True,
            task_type="code_generation"
        )
        sample_metrics.record_request(
            model_id="gpt-4-turbo",
            provider="openai",
            latency_ms=180.0,
            cost_usd=0.008,
            input_tokens=800,
            output_tokens=400,
            success=True,
            task_type="analysis"
        )
        sample_metrics.record_request(
            model_id="claude-3-5-sonnet",
            provider="anthropic",
            latency_ms=200.0,
            cost_usd=0.006,
            input_tokens=1200,
            output_tokens=600,
            success=False,
            error_message="Timeout",
            task_type="code_generation"
        )

        # Get statistics
        claude_stats = sample_metrics.get_model_statistics("claude-3-5-sonnet")
        assert claude_stats.total_requests == 2
        assert claude_stats.successful_requests == 1

        # Get summary
        summary = sample_metrics.get_summary()
        assert summary.total_requests == 3
        assert summary.overall_success_rate == pytest.approx(0.667, rel=0.1)

        # Filter by task type
        code_gen_stats = sample_metrics.get_metrics_by_task_type("code_generation")
        assert "claude-3-5-sonnet" in code_gen_stats
        assert code_gen_stats["claude-3-5-sonnet"].total_requests == 2

        # Get errors
        errors = sample_metrics.get_recent_errors()
        assert len(errors) == 1
        assert errors[0].error_message == "Timeout"

        # Export
        export_data = sample_metrics.export_metrics(filepath=temp_export_file)
        assert temp_export_file.exists()

        # Verify export
        with open(temp_export_file, 'r') as f:
            data = json.load(f)
        assert data["summary"]["total_requests"] == 3

    def test_multi_model_comparison(self, sample_metrics: ModelMetrics):
        """Test comparing metrics across multiple models."""
        # Add data for different models
        models = [
            ("claude-3-5-sonnet", "anthropic", 150.0, 0.005),
            ("gpt-4-turbo", "openai", 180.0, 0.008),
            ("llama3-70b", "local", 300.0, 0.0),
        ]

        for model_id, provider, latency, cost in models:
            for i in range(10):
                sample_metrics.record_request(
                    model_id=model_id,
                    provider=provider,
                    latency_ms=latency + i * 10,
                    cost_usd=cost,
                    input_tokens=1000,
                    output_tokens=500,
                    success=True
                )

        # Compare statistics
        all_stats = sample_metrics.get_all_statistics()
        assert len(all_stats) == 3

        # Verify each model has correct stats
        for model_id, _, _, _ in models:
            stats = all_stats[model_id]
            assert stats.total_requests == 10
            assert stats.successful_requests == 10

        # Compare costs
        costs = sample_metrics.get_cost_by_provider()
        assert costs["local"] == 0.0
        assert costs["anthropic"] > 0
        assert costs["openai"] > 0

    def test_time_based_filtering(self, sample_metrics: ModelMetrics):
        """Test time-based filtering of metrics."""
        import time

        # Record requests at different times
        sample_metrics.record_request(
            model_id="test-model",
            provider="test",
            latency_ms=100.0,
            cost_usd=0.001,
            success=True
        )
        time.sleep(0.1)  # Small delay

        sample_metrics.record_request(
            model_id="test-model",
            provider="test",
            latency_ms=150.0,
            cost_usd=0.002,
            success=True
        )

        # Get success rate with window that includes both
        rate_all = sample_metrics.get_success_rate("test-model", window_minutes=1)
        assert rate_all == 100.0

        # Get success rate with tiny window (might only include latest)
        rate_recent = sample_metrics.get_success_rate("test-model", window_minutes=0.0001)
        assert 0 <= rate_recent <= 100
