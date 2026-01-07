# API Documentation

## Overview

This document describes the API for the sample application.

## Endpoints

### Main Entry

```python
def main(args: Optional[List[str]] = None) -> int
```

Main entry point for the application.

### Process Data

```python
def process_data(config: AppConfig) -> bool
```

Process data according to configuration.

## Configuration

The application uses `AppConfig` for configuration:

- `timeout`: Request timeout in seconds (default: 30)
- `retries`: Number of retry attempts (default: 3)
- `debug`: Enable debug mode (default: False)

## Usage

```python
from src.main import main, Application

# Simple usage
exit_code = main()

# With application class
app = Application("my-app")
app.run()
```
