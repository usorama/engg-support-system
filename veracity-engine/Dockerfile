# Veracity Engine Dockerfile
# Runs the MCP server and git watcher daemon for Dev Context Tracking
#
# Build: docker build -t veracity-engine:latest .
# Run:   docker run -d --name veracity-engine veracity-engine:latest

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY core/ ./core/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create directories for git repos (will be mounted)
RUN mkdir -p /repos

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Default ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: Run HTTP server (provides health check + API endpoints)
CMD ["python", "-m", "core.http_server", "--host", "0.0.0.0", "--port", "8000"]
