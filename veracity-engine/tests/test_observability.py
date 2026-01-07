"""
Tests for Observability Infrastructure (STORY-004).

Tests cover:
1. Structured logging with JSON output
2. Correlation ID tracking
3. Metrics collection (Counter, Gauge, Histogram)
4. Health check endpoints
"""
import json
import time
import threading
import pytest
import requests
from io import StringIO
from unittest.mock import patch, MagicMock

from core.structured_logging import (
    get_logger,
    configure_logging,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
    correlation_id_scope,
    bind_context,
    clear_context,
)
from core.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    get_registry,
    get_build_duration_histogram,
    get_query_counter,
    get_error_counter,
)
from core.health import (
    HealthServer,
    HealthCheckHandler,
    check_ollama_running,
)


class TestStructuredLogging:
    """Tests for structured logging functionality."""

    def test_get_logger_returns_logger(self):
        """get_logger should return a structured logger."""
        logger = get_logger("test_module")
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")

    def test_logger_outputs_json(self):
        """Logger should output valid JSON when json_output=True."""
        output = StringIO()
        configure_logging(level="DEBUG", json_output=True, stream=output)

        logger = get_logger("test_json")
        logger.info("test_message", key1="value1", key2=42)

        output.seek(0)
        log_line = output.readline()

        # Should be parseable as JSON
        log_data = json.loads(log_line)
        assert log_data["event"] == "test_message"
        assert log_data["key1"] == "value1"
        assert log_data["key2"] == 42
        assert "timestamp" in log_data

    def test_log_has_timestamp(self):
        """Logs should include ISO 8601 timestamp."""
        output = StringIO()
        configure_logging(level="INFO", json_output=True, stream=output)

        logger = get_logger("test_timestamp")
        logger.info("timestamp_test")

        output.seek(0)
        log_data = json.loads(output.readline())

        assert "timestamp" in log_data
        # ISO 8601 format includes T and Z or +00:00
        assert "T" in log_data["timestamp"]

    def test_log_level_filtering(self):
        """Logs below configured level should be filtered."""
        output = StringIO()
        configure_logging(level="WARNING", json_output=True, stream=output)

        logger = get_logger("test_filter")
        logger.debug("debug_msg")
        logger.info("info_msg")
        logger.warning("warning_msg")

        output.seek(0)
        logs = output.read()

        # DEBUG and INFO should be filtered, only WARNING should appear
        assert "debug_msg" not in logs
        assert "info_msg" not in logs
        assert "warning_msg" in logs


class TestCorrelationId:
    """Tests for correlation ID tracking."""

    def setup_method(self):
        """Clear correlation ID before each test."""
        clear_correlation_id()

    def test_set_and_get_correlation_id(self):
        """Should be able to set and retrieve correlation ID."""
        cid = set_correlation_id("test-cid-123")
        assert cid == "test-cid-123"
        assert get_correlation_id() == "test-cid-123"

    def test_auto_generate_correlation_id(self):
        """Should auto-generate UUID if no ID provided."""
        cid = set_correlation_id()
        assert cid is not None
        assert len(cid) == 36  # UUID format

    def test_clear_correlation_id(self):
        """Should be able to clear correlation ID."""
        set_correlation_id("to-be-cleared")
        clear_correlation_id()
        assert get_correlation_id() is None

    def test_correlation_id_context_manager(self):
        """Context manager should set and clear correlation ID."""
        assert get_correlation_id() is None

        with correlation_id_scope("scoped-cid") as cid:
            assert cid == "scoped-cid"
            assert get_correlation_id() == "scoped-cid"

        # Should be cleared after context
        assert get_correlation_id() is None

    def test_correlation_id_in_logs(self):
        """Correlation ID should appear in log entries."""
        output = StringIO()
        configure_logging(level="INFO", json_output=True, stream=output)

        set_correlation_id("log-cid-456")
        logger = get_logger("test_cid_log")
        logger.info("with_correlation_id")

        output.seek(0)
        log_data = json.loads(output.readline())

        assert log_data.get("correlation_id") == "log-cid-456"

        clear_correlation_id()


class TestCounter:
    """Tests for Counter metric."""

    def test_counter_starts_at_zero(self):
        """Counter should start at zero."""
        counter = Counter("test_counter", "Test counter")
        assert counter.value == 0

    def test_counter_increment(self):
        """Counter should increment correctly."""
        counter = Counter("test_inc", "Test increment")
        counter.inc()
        assert counter.value == 1
        counter.inc(5)
        assert counter.value == 6

    def test_counter_rejects_negative(self):
        """Counter should reject negative increments."""
        counter = Counter("test_neg", "Test negative")
        with pytest.raises(ValueError):
            counter.inc(-1)

    def test_counter_prometheus_format(self):
        """Counter should export in Prometheus format."""
        counter = Counter("my_counter", "My counter")
        counter.inc(42)

        output = counter.to_prometheus()
        assert "my_counter 42" in output


class TestGauge:
    """Tests for Gauge metric."""

    def test_gauge_set(self):
        """Gauge should be settable."""
        gauge = Gauge("test_gauge", "Test gauge")
        gauge.set(10)
        assert gauge.value == 10

    def test_gauge_inc_dec(self):
        """Gauge should increment and decrement."""
        gauge = Gauge("test_gauge_ops", "Test gauge ops")
        gauge.inc(5)
        assert gauge.value == 5
        gauge.dec(2)
        assert gauge.value == 3

    def test_gauge_prometheus_format(self):
        """Gauge should export in Prometheus format."""
        gauge = Gauge("my_gauge", "My gauge")
        gauge.set(99)

        output = gauge.to_prometheus()
        assert "my_gauge 99" in output


class TestHistogram:
    """Tests for Histogram metric."""

    def test_histogram_observe(self):
        """Histogram should record observations."""
        histogram = Histogram("test_hist", "Test histogram")
        histogram.observe(0.1)
        histogram.observe(0.5)
        histogram.observe(1.0)

        assert histogram.count == 3
        assert abs(histogram.sum - 1.6) < 0.001

    def test_histogram_time_context_manager(self):
        """Histogram should time operations."""
        histogram = Histogram("test_timer", "Test timer")

        with histogram.time():
            time.sleep(0.05)  # 50ms

        assert histogram.count == 1
        assert histogram.sum >= 0.05

    def test_histogram_prometheus_format(self):
        """Histogram should export in Prometheus format."""
        histogram = Histogram(
            "my_hist", "My histogram",
            buckets=[0.1, 0.5, 1.0]
        )
        histogram.observe(0.3)

        output = histogram.to_prometheus()
        assert "my_hist_bucket" in output
        assert "my_hist_sum" in output
        assert "my_hist_count" in output


class TestMetricsRegistry:
    """Tests for MetricsRegistry."""

    def test_registry_creates_metrics(self):
        """Registry should create and return metrics."""
        registry = MetricsRegistry()

        counter = registry.counter("reg_counter", "Registry counter")
        gauge = registry.gauge("reg_gauge", "Registry gauge")
        histogram = registry.histogram("reg_hist", "Registry histogram")

        assert isinstance(counter, Counter)
        assert isinstance(gauge, Gauge)
        assert isinstance(histogram, Histogram)

    def test_registry_returns_same_metric(self):
        """Registry should return same metric for same name."""
        registry = MetricsRegistry()

        counter1 = registry.counter("same_counter", "Same")
        counter2 = registry.counter("same_counter", "Same")

        assert counter1 is counter2

    def test_registry_prometheus_export(self):
        """Registry should export all metrics in Prometheus format."""
        registry = MetricsRegistry()

        counter = registry.counter("export_counter", "Export counter")
        counter.inc(10)

        output = registry.to_prometheus()
        assert "# HELP export_counter" in output
        assert "# TYPE export_counter counter" in output
        assert "export_counter 10" in output


class TestGlobalMetrics:
    """Tests for global metric convenience functions."""

    def test_get_build_duration_histogram(self):
        """Should get build duration histogram."""
        hist = get_build_duration_histogram()
        assert isinstance(hist, Histogram)
        assert hist.name == "veracity_build_duration_seconds"

    def test_get_query_counter(self):
        """Should get query counter."""
        counter = get_query_counter()
        assert isinstance(counter, Counter)
        assert counter.name == "veracity_query_count_total"

    def test_get_error_counter(self):
        """Should get error counter."""
        counter = get_error_counter()
        assert isinstance(counter, Counter)
        assert counter.name == "veracity_errors_total"


class TestHealthServer:
    """Tests for HealthServer."""

    @pytest.fixture
    def health_server(self):
        """Create a health server on a random port."""
        import socket

        # Find available port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            port = s.getsockname()[1]

        server = HealthServer(port=port, host="127.0.0.1")
        yield server

        if server.is_running:
            server.stop()

    def test_health_server_starts_and_stops(self, health_server):
        """Health server should start and stop correctly."""
        assert not health_server.is_running

        started = health_server.start()
        assert started
        assert health_server.is_running

        health_server.stop()
        assert not health_server.is_running

    def test_health_endpoint_returns_ok(self, health_server):
        """Health endpoint should return OK."""
        health_server.start()
        time.sleep(0.1)  # Allow server to start

        response = requests.get(health_server.get_health_url(), timeout=1)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    def test_ready_endpoint_without_checks(self, health_server):
        """Ready endpoint should work without configured checks."""
        health_server.start()
        time.sleep(0.1)

        response = requests.get(health_server.get_ready_url(), timeout=1)

        # Without checks configured, should still return a response
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "checks" in data

    def test_metrics_endpoint(self, health_server):
        """Metrics endpoint should return Prometheus format."""
        # Add a metric first
        counter = get_registry().counter("health_test_counter", "Test counter")
        counter.inc(5)

        health_server.start()
        time.sleep(0.1)

        response = requests.get(health_server.get_metrics_url(), timeout=1)

        assert response.status_code == 200
        assert "text/plain" in response.headers["Content-Type"]
        assert "health_test_counter 5" in response.text


class TestOllamaCheck:
    """Tests for Ollama health check."""

    def test_check_ollama_returns_bool(self):
        """Check Ollama function should return a boolean."""
        # This test just verifies the function runs without error
        # and returns a boolean (may be True or False depending on
        # whether Ollama is actually running)
        result = check_ollama_running()
        assert isinstance(result, bool)

    def test_check_ollama_handles_import_error(self):
        """Check Ollama should handle gracefully when ollama not installed."""
        # The function has internal try/except, so it should return False
        # if there are any issues
        import sys
        original = sys.modules.get("ollama")

        try:
            # Temporarily remove ollama from modules
            if "ollama" in sys.modules:
                del sys.modules["ollama"]

            # This should return False due to import error or connection error
            # depending on if ollama module is available
            result = check_ollama_running()
            assert isinstance(result, bool)
        finally:
            # Restore
            if original:
                sys.modules["ollama"] = original


class TestLogContextBinding:
    """Tests for log context binding."""

    def test_bind_context(self):
        """bind_context should add fields to all logs."""
        output = StringIO()
        configure_logging(level="INFO", json_output=True, stream=output)

        bind_context(project="test-project", component="test")

        logger = get_logger("test_bind")
        logger.info("bound_log")

        output.seek(0)
        log_data = json.loads(output.readline())

        assert log_data.get("project") == "test-project"
        assert log_data.get("component") == "test"

        clear_context()
