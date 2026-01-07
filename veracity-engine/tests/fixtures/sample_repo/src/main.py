"""
Main application module for sample repo fixture.

This module provides the entry point for the sample application.
"""
from typing import List, Optional

from .utils import helper_function, calculate_sum
from .config import AppConfig


VERSION = "1.0.0"


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the application.

    Args:
        args: Command line arguments (optional)

    Returns:
        Exit code (0 for success)
    """
    config = AppConfig()
    result = process_data(config)
    return 0 if result else 1


def process_data(config: AppConfig) -> bool:
    """
    Process data according to configuration.

    Args:
        config: Application configuration

    Returns:
        True if processing succeeded
    """
    data = [1, 2, 3, 4, 5]
    total = calculate_sum(data)
    return total > 0


class Application:
    """Main application class."""

    def __init__(self, name: str):
        """
        Initialize the application.

        Args:
            name: Application name
        """
        self.name = name
        self.config = AppConfig()

    def run(self) -> None:
        """Run the application."""
        main()

    def get_status(self) -> str:
        """Get application status."""
        return f"{self.name} v{VERSION} - running"
