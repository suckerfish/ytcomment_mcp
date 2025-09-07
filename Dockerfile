FROM python:3.11-slim

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Install uv (pinned version for reproducibility)
RUN pip install --no-cache-dir uv==0.8.15

# Copy dependency files first (for better caching)
COPY pyproject.toml ./
COPY uv.lock* ./

# Install dependencies in a separate layer (cached unless dependencies change)
RUN uv pip install --system --no-cache .

# Copy application code (this layer changes most frequently)
COPY src/ ./src/

# Create non-root user for security
RUN adduser --disabled-password --gecos '' --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Health check with lightweight curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run the server with HTTP transport
CMD ["uv", "run", "python", "src/server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8080"]