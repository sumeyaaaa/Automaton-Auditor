# Automaton Auditor - Dockerfile
# Multi-stage build for production-ready containerization

FROM python:3.11-slim as base

# Install system dependencies required for git, PDF processing, and AST tools
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./
COPY uv.lock* ./

# Install dependencies using uv
# Use --frozen only if uv.lock exists, otherwise generate it
RUN if [ -f uv.lock ]; then \
        uv sync --frozen --no-dev; \
    else \
        uv sync --no-dev; \
    fi

# Copy application code
COPY . .

# Install the package in editable mode
RUN uv pip install -e .

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create audit directories
RUN mkdir -p audit/report_bypeer_received \
    audit/report_onpeer_generated \
    audit/report_onself_generated \
    audit/langsmith_logs

# Default entrypoint - can be overridden
ENTRYPOINT ["python", "-m", "src.graph"]

# Default command shows usage
CMD ["--help"]

