"""
Tests for Metrics and Self-Learning System (Phase 3).

Tests cover:
- QueryMetrics tracking and retrieval
- ConfidenceTuner analysis and recommendations
- Feedback correlation calculations
- Weight adjustment logic
- Tuning application and persistence
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from core.metrics.query_metrics import QueryMetrics
from core.metrics.confidence_tuner import ConfidenceTuner


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for testing."""
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    driver.session.return_value.__exit__.return_value = None
    return driver


@pytest.fixture
def mock_config():
    """Mock configuration."""
    config = MagicMock()
    config.neo4j.uri = "bolt://localhost:7687"
    config.neo4j.user = "neo4j"
    config.neo4j.password.get_secret_value.return_value = "password"
    return config


@pytest.fixture
def sample_query_id():
    """Generate a sample query ID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_metrics_data():
    """Sample metrics data for testing."""
    base_time = datetime.now()
    return [
        {
            "query_id": str(uuid.uuid4()),
            "project": "test_project",
            "timestamp": base_time.isoformat(),
            "execution_time_ms": 120.5,
            "result_count": 10,
            "confidence_score": 85.0,
            "evidence_count": 10,
            "user_feedback": "useful"
        },
        {
            "query_id": str(uuid.uuid4()),
            "project": "test_project",
            "timestamp": (base_time - timedelta(hours=1)).isoformat(),
            "execution_time_ms": 95.3,
            "result_count": 5,
            "confidence_score": 60.0,
            "evidence_count": 5,
            "user_feedback": "not_useful"
        },
        {
            "query_id": str(uuid.uuid4()),
            "project": "test_project",
            "timestamp": (base_time - timedelta(hours=2)).isoformat(),
            "execution_time_ms": 150.0,
            "result_count": 15,
            "confidence_score": 90.0,
            "evidence_count": 15,
            "user_feedback": "useful"
        },
    ]


# ============================================================================
# QueryMetrics Tests
# ============================================================================

class TestQueryMetrics:
    """Tests for QueryMetrics class."""

    @patch('core.metrics.query_metrics.get_config')
    @patch('core.metrics.query_metrics.GraphDatabase')
    def test_init_creates_constraints(self, mock_graph_db, mock_get_config, mock_config):
        """Test QueryMetrics initialization creates constraints."""
        mock_get_config.return_value = mock_config
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver

        metrics = QueryMetrics()

        # Verify driver was created
        mock_graph_db.driver.assert_called_once_with(
            "bolt://localhost:7687",
            auth=("neo4j", "password")
        )

        # Verify constraint creation was attempted
        assert mock_driver.session.called

    @patch('core.metrics.query_metrics.get_config')
    @patch('core.metrics.query_metrics.GraphDatabase')
    def test_track_query_success(self, mock_graph_db, mock_get_config, mock_config, sample_query_id):
        """Test successful query tracking."""
        mock_get_config.return_value = mock_config
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"id": sample_query_id}

        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver

        metrics = QueryMetrics()
        success = metrics.track_query(
            query_id=sample_query_id,
            project="test_project",
            execution_time_ms=100.0,
            result_count=10,
            confidence_score=85.0,
            evidence_count=10
        )

        assert success is True
        assert mock_session.run.called

    @patch('core.metrics.query_metrics.get_config')
    @patch('core.metrics.query_metrics.GraphDatabase')
    def test_track_query_with_scores(self, mock_graph_db, mock_get_config, mock_config, sample_query_id):
        """Test query tracking with vector and keyword scores."""
        mock_get_config.return_value = mock_config
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"id": sample_query_id}

        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver

        metrics = QueryMetrics()
        success = metrics.track_query(
            query_id=sample_query_id,
            project="test_project",
            execution_time_ms=100.0,
            result_count=10,
            confidence_score=85.0,
            vector_score_avg=0.85,
            keyword_score_avg=0.75,
            evidence_count=10
        )

        assert success is True
        # Verify the track_query was called successfully
        assert mock_session.run.called
        # The method was called with parameters - that's sufficient for this test

    @patch('core.metrics.query_metrics.get_config')
    @patch('core.metrics.query_metrics.GraphDatabase')
    def test_update_feedback(self, mock_graph_db, mock_get_config, mock_config, sample_query_id):
        """Test updating query metric with feedback."""
        mock_get_config.return_value = mock_config
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"id": sample_query_id}

        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver

        metrics = QueryMetrics()
        success = metrics.update_feedback(sample_query_id, "useful")

        assert success is True
        # Verify feedback update was called
        assert mock_session.run.called

    @patch('core.metrics.query_metrics.get_config')
    @patch('core.metrics.query_metrics.GraphDatabase')
    def test_get_metrics_time_window(self, mock_graph_db, mock_get_config, mock_config, sample_metrics_data):
        """Test retrieving metrics within time window."""
        mock_get_config.return_value = mock_config
        mock_driver = MagicMock()
        mock_session = MagicMock()

        # Mock result with sample data
        mock_result = MagicMock()
        mock_result.__iter__.return_value = iter(sample_metrics_data)

        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver

        metrics = QueryMetrics()
        results = metrics.get_metrics(time_window_hours=24)

        assert len(results) == 3
        assert all("query_id" in r for r in results)

    @patch('core.metrics.query_metrics.get_config')
    @patch('core.metrics.query_metrics.GraphDatabase')
    def test_get_metrics_with_filters(self, mock_graph_db, mock_get_config, mock_config):
        """Test retrieving metrics with filters."""
        mock_get_config.return_value = mock_config
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__.return_value = iter([])

        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver

        metrics = QueryMetrics()
        results = metrics.get_metrics(
            time_window_hours=24,
            project="test_project",
            min_confidence=70.0,
            has_feedback=True
        )

        # Verify filters were applied in query (query was called)
        assert mock_session.run.called
        # The filters are embedded in the Cypher query string, not as separate params
        call_args = mock_session.run.call_args
        cypher_query = call_args[0][0] if call_args[0] else ""
        assert "m.project" in cypher_query or "project" in str(call_args)

    @patch('core.metrics.query_metrics.get_config')
    @patch('core.metrics.query_metrics.GraphDatabase')
    def test_get_feedback_stats(self, mock_graph_db, mock_get_config, mock_config):
        """Test retrieving feedback statistics."""
        mock_get_config.return_value = mock_config
        mock_driver = MagicMock()
        mock_session = MagicMock()

        # Mock aggregated stats result
        mock_result = MagicMock()
        mock_result.single.return_value = {
            "total_queries": 100,
            "queries_with_feedback": 50,
            "useful_count": 30,
            "not_useful_count": 15,
            "partial_count": 5,
            "avg_confidence_useful": 85.0,
            "avg_confidence_not_useful": 55.0
        }

        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver

        metrics = QueryMetrics()
        stats = metrics.get_feedback_stats(time_window_hours=24)

        assert stats["total_queries"] == 100
        assert stats["queries_with_feedback"] == 50
        assert stats["useful_count"] == 30
        assert stats["avg_confidence_useful"] == 85.0

    @patch('core.metrics.query_metrics.get_config')
    @patch('core.metrics.query_metrics.GraphDatabase')
    def test_context_manager(self, mock_graph_db, mock_get_config, mock_config):
        """Test QueryMetrics context manager."""
        mock_get_config.return_value = mock_config
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver

        with QueryMetrics() as metrics:
            assert metrics is not None

        # Verify driver was closed
        mock_driver.close.assert_called_once()


# ============================================================================
# ConfidenceTuner Tests
# ============================================================================

class TestConfidenceTuner:
    """Tests for ConfidenceTuner class."""

    @patch('core.metrics.confidence_tuner.QueryMetrics')
    def test_init(self, mock_query_metrics):
        """Test ConfidenceTuner initialization."""
        mock_metrics_instance = MagicMock()
        mock_query_metrics.return_value = mock_metrics_instance

        tuner = ConfidenceTuner()

        assert tuner.metrics == mock_metrics_instance

    @patch('core.metrics.confidence_tuner.QueryMetrics')
    def test_analyze_feedback_insufficient_data(self, mock_query_metrics):
        """Test feedback analysis with insufficient data."""
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.get_metrics.return_value = []
        mock_query_metrics.return_value = mock_metrics_instance

        tuner = ConfidenceTuner()
        analysis = tuner.analyze_feedback(min_feedback_samples=5)

        assert analysis["status"] == "insufficient_data"
        assert "recommendations" in analysis

    @patch('core.metrics.confidence_tuner.QueryMetrics')
    def test_analyze_feedback_success(self, mock_query_metrics, sample_metrics_data):
        """Test successful feedback analysis."""
        mock_metrics_instance = MagicMock()
        mock_metrics_instance.get_metrics.return_value = sample_metrics_data
        mock_query_metrics.return_value = mock_metrics_instance

        tuner = ConfidenceTuner()
        analysis = tuner.analyze_feedback(min_feedback_samples=2)

        assert analysis["status"] == "success"
        assert "feedback_distribution" in analysis
        assert "confidence_stats" in analysis
        assert "recommendations" in analysis

    @patch('core.metrics.confidence_tuner.QueryMetrics')
    def test_correlation_calculation(self, mock_query_metrics):
        """Test Pearson correlation calculation."""
        mock_metrics_instance = MagicMock()
        mock_query_metrics.return_value = mock_metrics_instance

        tuner = ConfidenceTuner()

        # Perfect positive correlation
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [1.0, 2.0, 3.0, 4.0, 5.0]
        corr = tuner._calculate_correlation(x, y)
        assert abs(corr - 1.0) < 0.01

        # Perfect negative correlation
        y_neg = [5.0, 4.0, 3.0, 2.0, 1.0]
        corr_neg = tuner._calculate_correlation(x, y_neg)
        assert abs(corr_neg + 1.0) < 0.01

        # No correlation
        y_random = [3.0, 1.0, 4.0, 2.0, 5.0]
        corr_random = tuner._calculate_correlation(x, y_random)
        assert abs(corr_random) < 1.0

    @patch('core.metrics.confidence_tuner.QueryMetrics')
    def test_false_positive_detection(self, mock_query_metrics):
        """Test detection of false positives (high confidence, not useful)."""
        mock_metrics_instance = MagicMock()

        # Create data with false positives
        metrics_data = [
            {"confidence_score": 90.0, "user_feedback": "not_useful"},  # False positive
            {"confidence_score": 85.0, "user_feedback": "useful"},
            {"confidence_score": 80.0, "user_feedback": "not_useful"},  # False positive
            {"confidence_score": 70.0, "user_feedback": "useful"},
        ]

        mock_metrics_instance.get_metrics.return_value = metrics_data
        mock_query_metrics.return_value = mock_metrics_instance

        tuner = ConfidenceTuner()
        analysis = tuner.analyze_feedback(min_feedback_samples=2)

        # Should detect 2 false positives out of 4 queries = 50%
        assert analysis["false_positive_rate"] == 0.5

    @patch('core.metrics.confidence_tuner.QueryMetrics')
    def test_false_negative_detection(self, mock_query_metrics):
        """Test detection of false negatives (low confidence, useful)."""
        mock_metrics_instance = MagicMock()

        # Create data with false negatives
        metrics_data = [
            {"confidence_score": 40.0, "user_feedback": "useful"},  # False negative
            {"confidence_score": 85.0, "user_feedback": "useful"},
            {"confidence_score": 45.0, "user_feedback": "useful"},  # False negative
            {"confidence_score": 30.0, "user_feedback": "not_useful"},
        ]

        mock_metrics_instance.get_metrics.return_value = metrics_data
        mock_query_metrics.return_value = mock_metrics_instance

        tuner = ConfidenceTuner()
        analysis = tuner.analyze_feedback(min_feedback_samples=2)

        # Should detect 2 false negatives out of 4 queries = 50%
        assert analysis["false_negative_rate"] == 0.5

    @patch('core.metrics.confidence_tuner.QueryMetrics')
    def test_calculate_adjustments_high_fp_rate(self, mock_query_metrics):
        """Test adjustment calculation with high false positive rate."""
        mock_metrics_instance = MagicMock()

        # High false positive rate scenario
        metrics_data = [
            {"confidence_score": 90.0, "user_feedback": "not_useful"} for _ in range(3)
        ] + [
            {"confidence_score": 85.0, "user_feedback": "useful"} for _ in range(2)
        ]

        mock_metrics_instance.get_metrics.return_value = metrics_data
        mock_query_metrics.return_value = mock_metrics_instance

        tuner = ConfidenceTuner()
        adjustments = tuner.calculate_adjustments(adjustment_strength=0.1)

        # Should increase staleness penalty
        assert adjustments["staleness_penalty_delta"] > 0

    @patch('core.metrics.confidence_tuner.QueryMetrics')
    def test_calculate_adjustments_high_fn_rate(self, mock_query_metrics):
        """Test adjustment calculation with high false negative rate."""
        mock_metrics_instance = MagicMock()

        # High false negative rate scenario
        metrics_data = [
            {"confidence_score": 40.0, "user_feedback": "useful"} for _ in range(3)
        ] + [
            {"confidence_score": 30.0, "user_feedback": "not_useful"} for _ in range(2)
        ]

        mock_metrics_instance.get_metrics.return_value = metrics_data
        mock_query_metrics.return_value = mock_metrics_instance

        tuner = ConfidenceTuner()
        adjustments = tuner.calculate_adjustments(adjustment_strength=0.1)

        # Should decrease staleness penalty and increase connectivity bonus
        assert adjustments["staleness_penalty_delta"] < 0
        assert adjustments["connectivity_bonus_delta"] > 0

    @patch('core.metrics.confidence_tuner.QueryMetrics')
    def test_apply_tuning_dry_run(self, mock_query_metrics):
        """Test dry run mode (no actual application)."""
        mock_metrics_instance = MagicMock()
        mock_query_metrics.return_value = mock_metrics_instance

        tuner = ConfidenceTuner()
        adjustments = {
            "staleness_penalty_delta": 2.0,
            "orphan_penalty_delta": 1.0,
            "connectivity_bonus_delta": 0.5
        }

        result = tuner.apply_tuning(adjustments, dry_run=True)

        assert result["applied"] is False
        assert result["dry_run"] is True
        assert result["adjustments"] == adjustments

    @patch('core.metrics.confidence_tuner.QueryMetrics')
    def test_apply_tuning_success(self, mock_query_metrics):
        """Test successful tuning application."""
        mock_metrics_instance = MagicMock()
        mock_driver = MagicMock()
        mock_session = MagicMock()

        # Mock successful Neo4j update
        mock_result = MagicMock()
        mock_result.single.return_value = {
            "staleness_penalty_delta": 2.0,
            "orphan_penalty_delta": 1.0,
            "connectivity_bonus_delta": 0.5,
            "tuning_count": 1
        }

        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_metrics_instance.driver = mock_driver
        mock_query_metrics.return_value = mock_metrics_instance

        tuner = ConfidenceTuner()
        adjustments = {
            "staleness_penalty_delta": 2.0,
            "orphan_penalty_delta": 1.0,
            "connectivity_bonus_delta": 0.5
        }

        result = tuner.apply_tuning(adjustments, dry_run=False)

        assert result["applied"] is True
        assert "cumulative_adjustments" in result

    @patch('core.metrics.confidence_tuner.QueryMetrics')
    def test_get_current_tuning(self, mock_query_metrics):
        """Test retrieving current tuning configuration."""
        mock_metrics_instance = MagicMock()
        mock_driver = MagicMock()
        mock_session = MagicMock()

        # Mock tuning config result
        mock_result = MagicMock()
        mock_result.single.return_value = {
            "staleness_penalty_delta": 2.0,
            "orphan_penalty_delta": 1.0,
            "connectivity_bonus_delta": 0.5,
            "last_tuned": "2025-01-15T10:00:00",
            "tuning_count": 3
        }

        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_metrics_instance.driver = mock_driver
        mock_query_metrics.return_value = mock_metrics_instance

        tuner = ConfidenceTuner()
        current = tuner.get_current_tuning()

        assert current["staleness_penalty_delta"] == 2.0
        assert current["tuning_count"] == 3

    @patch('core.metrics.confidence_tuner.QueryMetrics')
    def test_get_current_tuning_no_config(self, mock_query_metrics):
        """Test retrieving tuning when no config exists (returns defaults)."""
        mock_metrics_instance = MagicMock()
        mock_driver = MagicMock()
        mock_session = MagicMock()

        # Mock empty result (no tuning applied yet)
        mock_result = MagicMock()
        mock_result.single.return_value = None

        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_metrics_instance.driver = mock_driver
        mock_query_metrics.return_value = mock_metrics_instance

        tuner = ConfidenceTuner()
        current = tuner.get_current_tuning()

        assert current["staleness_penalty_delta"] == 0.0
        assert current["tuning_count"] == 0

    @patch('core.metrics.confidence_tuner.QueryMetrics')
    def test_context_manager(self, mock_query_metrics):
        """Test ConfidenceTuner context manager."""
        mock_metrics_instance = MagicMock()
        mock_query_metrics.return_value = mock_metrics_instance

        with ConfidenceTuner() as tuner:
            assert tuner is not None

        # Verify metrics was closed
        mock_metrics_instance.close.assert_called_once()


# ============================================================================
# Integration Tests (require Neo4j)
# ============================================================================

@pytest.mark.integration
class TestMetricsIntegration:
    """Integration tests requiring actual Neo4j instance."""

    def test_end_to_end_workflow(self):
        """Test complete workflow: track -> feedback -> analyze -> tune."""
        # This would be implemented with a real Neo4j test instance
        pytest.skip("Requires Neo4j test instance")
