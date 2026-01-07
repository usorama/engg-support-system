# Monitoring & Observability

This document describes the observability infrastructure for Veracity Engine.

## Overview

Veracity Engine provides three pillars of observability:
1. **Structured Logging** - JSON-formatted logs with correlation IDs
2. **Health Checks** - HTTP endpoints for liveness and readiness
3. **Metrics** - Prometheus-compatible metrics for monitoring

## Structured Logging

### Configuration

```python
from core.logging import configure_logging, get_logger

# Configure JSON output (default)
configure_logging(level="INFO", json_output=True)

# Or configure console output for development
configure_logging(level="DEBUG", json_output=False)
```

### Usage

```python
from core.logging import get_logger

logger = get_logger(__name__)

# Basic logging
logger.info("operation_started", project="my-project")
logger.warning("threshold_exceeded", value=95, limit=90)
logger.error("operation_failed", error="Connection refused")
```

### JSON Log Format

```json
{
  "timestamp": "2025-12-30T12:34:56.789Z",
  "level": "info",
  "logger": "core.build_graph",
  "event": "build_started",
  "correlation_id": "abc-123-def",
  "project": "my-project",
  "files_to_process": 42
}
```

### Log Fields

| Field | Description | Required |
|-------|-------------|----------|
| `timestamp` | ISO 8601 UTC timestamp | Yes |
| `level` | Log level (debug, info, warning, error) | Yes |
| `logger` | Logger name (module path) | Yes |
| `event` | Event/message name | Yes |
| `correlation_id` | Request trace ID | When set |
| `*` | Additional context fields | Optional |

## Correlation IDs

Correlation IDs enable request tracing across components.

### Setting Correlation ID

```python
from core.logging import set_correlation_id, correlation_id_scope, get_logger

logger = get_logger(__name__)

# Manual setting
cid = set_correlation_id()  # Auto-generates UUID
logger.info("started")  # Will include correlation_id

# Context manager (recommended)
with correlation_id_scope() as cid:
    logger.info("step1")
    logger.info("step2")
    # Both logs have same correlation_id
# Correlation ID cleared after context
```

### Passing Correlation ID

When calling external services or spawning workers, pass the correlation ID:

```python
from core.logging import get_correlation_id

cid = get_correlation_id()
# Pass cid to subprocess or external API
```

## Health Check Endpoints

The health server provides HTTP endpoints for monitoring.

### Starting the Health Server

```python
from core.health import get_health_server

server = get_health_server(port=8080)
server.set_neo4j_check(lambda: driver.verify_connectivity())
server.set_ollama_check(lambda: check_ollama_running())
server.start()
```

### Endpoints

#### GET /health

Basic liveness check. Returns 200 if process is running.

```json
{
  "status": "ok",
  "timestamp": "2025-12-30T12:34:56.789Z",
  "version": "0.1.0"
}
```

#### GET /ready

Readiness check with dependency verification. Returns 200 if ready, 503 if not.

```json
{
  "status": "ready",
  "checks": {
    "neo4j": "ok",
    "ollama": "ok"
  },
  "timestamp": "2025-12-30T12:34:56.789Z"
}
```

Or if not ready:

```json
{
  "status": "not_ready",
  "checks": {
    "neo4j": "error: connection refused",
    "ollama": "ok"
  },
  "timestamp": "2025-12-30T12:34:56.789Z"
}
```

#### GET /metrics

Prometheus-format metrics export.

```
# HELP veracity_build_duration_seconds Time taken to build knowledge graph
# TYPE veracity_build_duration_seconds histogram
veracity_build_duration_seconds_bucket{le="1.0"} 5
veracity_build_duration_seconds_sum 3.75
veracity_build_duration_seconds_count 5

# HELP veracity_query_count_total Total number of queries executed
# TYPE veracity_query_count_total counter
veracity_query_count_total 42
```

## Metrics

### Available Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `veracity_build_duration_seconds` | Histogram | Time to build knowledge graph |
| `veracity_query_duration_seconds` | Histogram | Time to execute query |
| `veracity_build_files_processed_total` | Counter | Files processed during builds |
| `veracity_query_count_total` | Counter | Total queries executed |
| `veracity_errors_total` | Counter | Total errors encountered |

### Using Metrics

```python
from core.metrics import (
    get_build_duration_histogram,
    get_query_counter,
    get_error_counter,
)

# Record build duration
hist = get_build_duration_histogram()
with hist.time():
    build_graph()

# Increment query counter
get_query_counter().inc()

# Track errors
try:
    do_operation()
except Exception:
    get_error_counter().inc()
    raise
```

### Custom Metrics

```python
from core.metrics import get_registry

registry = get_registry()

# Create custom counter
my_counter = registry.counter(
    "my_custom_metric_total",
    "Description of my metric"
)
my_counter.inc()

# Create custom histogram
my_histogram = registry.histogram(
    "my_custom_duration_seconds",
    "Duration of my operation",
    buckets=[0.1, 0.5, 1.0, 5.0]
)
my_histogram.observe(0.75)
```

## VPS Monitoring Setup

### Log Files

Logs are written to stdout by default. Redirect to files for VPS:

```bash
# Run with log file
python3 core/build_graph.py 2>&1 | tee -a /var/log/veracity/build.log
```

### Log Rotation

Create `/etc/logrotate.d/veracity`:

```
/var/log/veracity/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 veracity veracity
}
```

### Health Check Monitoring

Use a simple cron job to monitor health:

```bash
# /etc/cron.d/veracity-health
*/5 * * * * root curl -sf http://localhost:8080/ready || echo "Veracity not ready" | mail -s "Alert" admin@example.com
```

### Docker Compose Integration

```yaml
services:
  veracity:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Troubleshooting

### Finding Logs for a Request

Use correlation ID to trace:

```bash
# Find all logs for a specific request
grep "abc-123-def" /var/log/veracity/*.log
```

### Checking Metrics

```bash
curl http://localhost:8080/metrics | grep veracity_
```

### Common Issues

| Symptom | Possible Cause | Solution |
|---------|---------------|----------|
| No logs appearing | Log level too high | Set `VERACITY_LOGGING__LEVEL=DEBUG` |
| `/ready` returns 503 | Dependency down | Check Neo4j/Ollama connectivity |
| High error count | Application issues | Check error logs with correlation ID |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VERACITY_LOGGING__LEVEL` | Log level | INFO |
| `HEALTH_CHECK_PORT` | Health server port | 8080 |

## Best Practices

1. **Always use correlation IDs** for request tracing
2. **Log structured data** not formatted strings
3. **Include context** in log entries (project, operation, etc.)
4. **Monitor `/ready`** not just `/health` for dependencies
5. **Set up alerts** for error rate increases
