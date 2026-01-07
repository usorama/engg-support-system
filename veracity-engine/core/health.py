"""
Health Check Server for Veracity Engine (STORY-004).

Provides HTTP endpoints for:
- /health: Basic liveness check
- /ready: Readiness check with dependency verification
- /metrics: Prometheus-format metrics export

Runs as a background thread to avoid blocking main application.
"""
import json
import socket
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional, Callable

from core.metrics import get_registry
from core.structured_logging import get_logger

logger = get_logger(__name__)

# Version info (can be updated by main application)
VERSION = "0.1.0"


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health check endpoints."""

    # Dependency check functions (set by application)
    neo4j_check: Optional[Callable[[], bool]] = None
    ollama_check: Optional[Callable[[], bool]] = None

    def log_message(self, format: str, *args) -> None:
        """Override to use structured logging instead of stderr."""
        logger.debug("health_request", path=args[0] if args else "unknown")

    def do_GET(self):
        """Handle GET requests for health endpoints."""
        if self.path == "/health":
            self._handle_health()
        elif self.path == "/ready":
            self._handle_ready()
        elif self.path == "/metrics":
            self._handle_metrics()
        else:
            self._send_response(404, {"error": "Not found"})

    def _handle_health(self):
        """Handle /health endpoint - basic liveness check."""
        response = {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": VERSION,
        }
        self._send_response(200, response)

    def _handle_ready(self):
        """Handle /ready endpoint - check dependencies."""
        checks: Dict[str, str] = {}
        all_ready = True

        # Check Neo4j
        if self.neo4j_check:
            try:
                if self.neo4j_check():
                    checks["neo4j"] = "ok"
                else:
                    checks["neo4j"] = "error: check returned false"
                    all_ready = False
            except Exception as e:
                checks["neo4j"] = f"error: {str(e)}"
                all_ready = False
        else:
            checks["neo4j"] = "skip: no check configured"

        # Check Ollama
        if self.ollama_check:
            try:
                if self.ollama_check():
                    checks["ollama"] = "ok"
                else:
                    checks["ollama"] = "error: check returned false"
                    all_ready = False
            except Exception as e:
                checks["ollama"] = f"error: {str(e)}"
                all_ready = False
        else:
            checks["ollama"] = "skip: no check configured"

        response = {
            "status": "ready" if all_ready else "not_ready",
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        status_code = 200 if all_ready else 503
        self._send_response(status_code, response)

    def _handle_metrics(self):
        """Handle /metrics endpoint - Prometheus format."""
        registry = get_registry()
        metrics_output = registry.to_prometheus()

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.end_headers()
        self.wfile.write(metrics_output.encode("utf-8"))

    def _send_response(self, status_code: int, data: Dict[str, Any]):
        """Send a JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))


class HealthServer:
    """
    Background health check server.

    Usage:
        server = HealthServer(port=8080)
        server.set_neo4j_check(lambda: driver.verify_connectivity())
        server.start()
        # ... application runs ...
        server.stop()
    """

    def __init__(self, port: int = 8080, host: str = "0.0.0.0"):
        self.port = port
        self.host = host
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def set_neo4j_check(self, check_fn: Callable[[], bool]) -> None:
        """Set the Neo4j health check function."""
        HealthCheckHandler.neo4j_check = check_fn

    def set_ollama_check(self, check_fn: Callable[[], bool]) -> None:
        """Set the Ollama health check function."""
        HealthCheckHandler.ollama_check = check_fn

    def start(self) -> bool:
        """
        Start the health check server in a background thread.

        Returns:
            True if started successfully, False otherwise.
        """
        if self._running:
            logger.warning("health_server_already_running")
            return False

        try:
            self._server = HTTPServer((self.host, self.port), HealthCheckHandler)
            self._thread = threading.Thread(target=self._serve, daemon=True)
            self._thread.start()
            self._running = True
            logger.info("health_server_started", host=self.host, port=self.port)
            return True
        except OSError as e:
            logger.error("health_server_start_failed", error=str(e))
            return False

    def _serve(self):
        """Background thread to serve requests."""
        if self._server:
            self._server.serve_forever()

    def stop(self):
        """Stop the health check server."""
        if self._server:
            self._server.shutdown()
            self._running = False
            logger.info("health_server_stopped")

    @property
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._running

    def get_health_url(self) -> str:
        """Get the URL for the health endpoint."""
        return f"http://{self.host}:{self.port}/health"

    def get_ready_url(self) -> str:
        """Get the URL for the ready endpoint."""
        return f"http://{self.host}:{self.port}/ready"

    def get_metrics_url(self) -> str:
        """Get the URL for the metrics endpoint."""
        return f"http://{self.host}:{self.port}/metrics"


# Global health server instance
_health_server: Optional[HealthServer] = None


def get_health_server(port: int = 8080) -> HealthServer:
    """Get or create the global health server instance."""
    global _health_server
    if _health_server is None:
        _health_server = HealthServer(port=port)
    return _health_server


def check_neo4j_connection(uri: str, user: str, password: str) -> bool:
    """
    Check if Neo4j is reachable and accepting connections.

    Args:
        uri: Neo4j connection URI (e.g., bolt://localhost:7687)
        user: Neo4j username
        password: Neo4j password

    Returns:
        True if connection successful, False otherwise.
    """
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        driver.close()
        return True
    except Exception as e:
        logger.debug("neo4j_check_failed", error=str(e))
        return False


def check_ollama_running() -> bool:
    """
    Check if Ollama is running and responding.

    Returns:
        True if Ollama is running, False otherwise.
    """
    try:
        import ollama
        ollama.list()
        return True
    except Exception as e:
        logger.debug("ollama_check_failed", error=str(e))
        return False
