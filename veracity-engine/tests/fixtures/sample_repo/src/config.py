"""
Configuration module for sample repo fixture.
"""
from dataclasses import dataclass
from typing import Optional


DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3


@dataclass
class AppConfig:
    """Application configuration."""

    timeout: int = DEFAULT_TIMEOUT
    retries: int = DEFAULT_RETRIES
    debug: bool = False
    log_level: str = "INFO"

    def validate(self) -> bool:
        """
        Validate configuration values.

        Returns:
            True if configuration is valid
        """
        if self.timeout < 0:
            return False
        if self.retries < 0:
            return False
        return True


def load_config(path: Optional[str] = None) -> AppConfig:
    """
    Load configuration from file or defaults.

    Args:
        path: Optional path to config file

    Returns:
        AppConfig instance
    """
    return AppConfig()
