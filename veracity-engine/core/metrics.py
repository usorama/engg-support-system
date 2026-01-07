"""
Metrics Collection for Veracity Engine (STORY-004).

Provides simple Prometheus-compatible metrics:
- Counter: Monotonically increasing value
- Gauge: Value that can go up and down
- Histogram: Distribution of values with buckets

Thread-safe implementation for concurrent access.
"""
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from contextlib import contextmanager


@dataclass
class Counter:
    """A counter metric that only goes up."""
    name: str
    help: str
    labels: Dict[str, str] = field(default_factory=dict)
    _value: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def value(self) -> float:
        """Get the current counter value."""
        with self._lock:
            return self._value

    def inc(self, amount: float = 1.0) -> None:
        """Increment the counter by the given amount (default 1)."""
        if amount < 0:
            raise ValueError("Counter can only be incremented, not decremented")
        with self._lock:
            self._value += amount

    def to_prometheus(self) -> str:
        """Export counter in Prometheus format."""
        labels_str = self._format_labels()
        return f"{self.name}{labels_str} {self._value}"

    def _format_labels(self) -> str:
        if not self.labels:
            return ""
        label_pairs = [f'{k}="{v}"' for k, v in sorted(self.labels.items())]
        return "{" + ",".join(label_pairs) + "}"


@dataclass
class Gauge:
    """A gauge metric that can go up and down."""
    name: str
    help: str
    labels: Dict[str, str] = field(default_factory=dict)
    _value: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def value(self) -> float:
        """Get the current gauge value."""
        with self._lock:
            return self._value

    def set(self, value: float) -> None:
        """Set the gauge to the given value."""
        with self._lock:
            self._value = value

    def inc(self, amount: float = 1.0) -> None:
        """Increment the gauge by the given amount."""
        with self._lock:
            self._value += amount

    def dec(self, amount: float = 1.0) -> None:
        """Decrement the gauge by the given amount."""
        with self._lock:
            self._value -= amount

    def to_prometheus(self) -> str:
        """Export gauge in Prometheus format."""
        labels_str = self._format_labels()
        return f"{self.name}{labels_str} {self._value}"

    def _format_labels(self) -> str:
        if not self.labels:
            return ""
        label_pairs = [f'{k}="{v}"' for k, v in sorted(self.labels.items())]
        return "{" + ",".join(label_pairs) + "}"


@dataclass
class Histogram:
    """A histogram metric for recording value distributions."""
    name: str
    help: str
    buckets: List[float] = field(default_factory=lambda: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0])
    labels: Dict[str, str] = field(default_factory=dict)
    _bucket_counts: Dict[float, int] = field(default_factory=dict)
    _sum: float = 0.0
    _count: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self):
        # Initialize bucket counts
        self._bucket_counts = {b: 0 for b in self.buckets}
        self._bucket_counts[float("inf")] = 0

    @property
    def sum(self) -> float:
        """Get the sum of all observed values."""
        with self._lock:
            return self._sum

    @property
    def count(self) -> int:
        """Get the count of observations."""
        with self._lock:
            return self._count

    def observe(self, value: float) -> None:
        """Observe a value and update histogram buckets."""
        with self._lock:
            self._sum += value
            self._count += 1
            for bucket in sorted(self._bucket_counts.keys()):
                if value <= bucket:
                    self._bucket_counts[bucket] += 1

    @contextmanager
    def time(self):
        """
        Context manager to measure duration.

        Usage:
            with histogram.time():
                do_something()
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self.observe(duration)

    def to_prometheus(self) -> str:
        """Export histogram in Prometheus format."""
        lines = []
        labels_str = self._format_labels()

        # Output bucket counts
        cumulative = 0
        for bucket in sorted(self.buckets):
            cumulative += self._bucket_counts.get(bucket, 0)
            le = f'+Inf' if bucket == float("inf") else str(bucket)
            if labels_str:
                bucket_labels = labels_str[:-1] + f',le="{le}"' + "}"
            else:
                bucket_labels = f'{{le="{le}"}}'
            lines.append(f"{self.name}_bucket{bucket_labels} {cumulative}")

        # Add +Inf bucket
        cumulative += self._bucket_counts.get(float("inf"), 0)
        if labels_str:
            inf_labels = labels_str[:-1] + ',le="+Inf"}'
        else:
            inf_labels = '{le="+Inf"}'
        lines.append(f"{self.name}_bucket{inf_labels} {cumulative}")

        # Sum and count
        lines.append(f"{self.name}_sum{labels_str} {self._sum}")
        lines.append(f"{self.name}_count{labels_str} {self._count}")

        return "\n".join(lines)

    def _format_labels(self) -> str:
        if not self.labels:
            return ""
        label_pairs = [f'{k}="{v}"' for k, v in sorted(self.labels.items())]
        return "{" + ",".join(label_pairs) + "}"


class MetricsRegistry:
    """
    Registry for all metrics in the application.

    Provides a central place to create and access metrics.
    """

    def __init__(self):
        self._metrics: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def counter(self, name: str, help: str, labels: Optional[Dict[str, str]] = None) -> Counter:
        """Create or get a counter metric."""
        key = f"counter:{name}"
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = Counter(name=name, help=help, labels=labels or {})
            return self._metrics[key]

    def gauge(self, name: str, help: str, labels: Optional[Dict[str, str]] = None) -> Gauge:
        """Create or get a gauge metric."""
        key = f"gauge:{name}"
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = Gauge(name=name, help=help, labels=labels or {})
            return self._metrics[key]

    def histogram(
        self, name: str, help: str,
        buckets: Optional[List[float]] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> Histogram:
        """Create or get a histogram metric."""
        key = f"histogram:{name}"
        with self._lock:
            if key not in self._metrics:
                kwargs = {"name": name, "help": help, "labels": labels or {}}
                if buckets:
                    kwargs["buckets"] = buckets
                self._metrics[key] = Histogram(**kwargs)
            return self._metrics[key]

    def to_prometheus(self) -> str:
        """Export all metrics in Prometheus format."""
        lines = []
        with self._lock:
            for key, metric in sorted(self._metrics.items()):
                # Add HELP and TYPE comments
                lines.append(f"# HELP {metric.name} {metric.help}")
                if isinstance(metric, Counter):
                    lines.append(f"# TYPE {metric.name} counter")
                elif isinstance(metric, Gauge):
                    lines.append(f"# TYPE {metric.name} gauge")
                elif isinstance(metric, Histogram):
                    lines.append(f"# TYPE {metric.name} histogram")
                lines.append(metric.to_prometheus())
                lines.append("")

        return "\n".join(lines)


# Global metrics registry singleton
_registry: Optional[MetricsRegistry] = None


def get_registry() -> MetricsRegistry:
    """Get the global metrics registry."""
    global _registry
    if _registry is None:
        _registry = MetricsRegistry()
    return _registry


# Convenience functions for common metrics
def get_build_duration_histogram() -> Histogram:
    """Get the build duration histogram."""
    return get_registry().histogram(
        "veracity_build_duration_seconds",
        "Time taken to build knowledge graph",
        buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
    )


def get_query_duration_histogram() -> Histogram:
    """Get the query duration histogram."""
    return get_registry().histogram(
        "veracity_query_duration_seconds",
        "Time taken to execute query",
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )


def get_files_processed_counter() -> Counter:
    """Get the files processed counter."""
    return get_registry().counter(
        "veracity_build_files_processed_total",
        "Total number of files processed during builds"
    )


def get_query_counter() -> Counter:
    """Get the query count counter."""
    return get_registry().counter(
        "veracity_query_count_total",
        "Total number of queries executed"
    )


def get_error_counter() -> Counter:
    """Get the error counter."""
    return get_registry().counter(
        "veracity_errors_total",
        "Total number of errors encountered"
    )
