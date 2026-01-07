"""
Structured Logging for Veracity Engine (STORY-004).

Provides JSON-formatted structured logging with:
- Correlation ID tracking for request tracing
- Context binding for additional metadata
- Log level configuration from config
- Timestamp in ISO 8601 format
"""
import logging
import sys
import uuid
import contextvars
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog

# Context variable for correlation ID (thread-safe)
_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)

# Global flag to track if logging is configured
_logging_configured = False


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID for request tracing."""
    return _correlation_id.get()


def set_correlation_id(cid: Optional[str] = None) -> str:
    """
    Set the correlation ID for the current context.

    Args:
        cid: Correlation ID to set. If None, generates a new UUID.

    Returns:
        The correlation ID that was set.
    """
    if cid is None:
        cid = str(uuid.uuid4())
    _correlation_id.set(cid)
    return cid


def clear_correlation_id() -> None:
    """Clear the correlation ID from the current context."""
    _correlation_id.set(None)


class CorrelationIdContextManager:
    """Context manager for setting correlation ID in a scope."""

    def __init__(self, cid: Optional[str] = None):
        self.cid = cid
        self.token: Optional[contextvars.Token] = None

    def __enter__(self) -> str:
        if self.cid is None:
            self.cid = str(uuid.uuid4())
        self.token = _correlation_id.set(self.cid)
        return self.cid

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token is not None:
            _correlation_id.reset(self.token)
        return False


def correlation_id_scope(cid: Optional[str] = None) -> CorrelationIdContextManager:
    """
    Create a context manager for correlation ID scope.

    Usage:
        with correlation_id_scope() as cid:
            logger.info("operation", correlation_id=cid)
    """
    return CorrelationIdContextManager(cid)


def add_correlation_id(
    logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Structlog processor to add correlation ID to log entries."""
    cid = get_correlation_id()
    if cid is not None and "correlation_id" not in event_dict:
        event_dict["correlation_id"] = cid
    return event_dict


def add_timestamp(
    logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Structlog processor to add ISO 8601 timestamp."""
    event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event_dict


def configure_logging(
    level: str = "INFO",
    json_output: bool = True,
    stream: Any = None
) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: If True, output JSON; if False, output colored console format
        stream: Output stream (default: sys.stdout)
    """
    global _logging_configured

    if stream is None:
        stream = sys.stdout

    # Convert string level to logging level
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        stream=stream,
        force=True,
    )

    # Choose processors based on output format
    if json_output:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            add_timestamp,
            add_correlation_id,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _logging_configured = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger for the given name.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Configured structlog logger
    """
    global _logging_configured

    # Auto-configure if not already done
    if not _logging_configured:
        configure_logging()

    return structlog.get_logger(name)


# Convenience function for binding context
def bind_context(**kwargs) -> None:
    """
    Bind context variables that will be included in all subsequent logs.

    Usage:
        bind_context(project="my-project", operation="build")
        logger.info("started")  # Will include project and operation
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()


# For backward compatibility - expose at module level
def info(message: str, **kwargs) -> None:
    """Log an info message (convenience function)."""
    get_logger("veracity").info(message, **kwargs)


def warning(message: str, **kwargs) -> None:
    """Log a warning message (convenience function)."""
    get_logger("veracity").warning(message, **kwargs)


def error(message: str, **kwargs) -> None:
    """Log an error message (convenience function)."""
    get_logger("veracity").error(message, **kwargs)


def debug(message: str, **kwargs) -> None:
    """Log a debug message (convenience function)."""
    get_logger("veracity").debug(message, **kwargs)
