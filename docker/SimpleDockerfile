FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY . .

# Install dependencies
RUN uv pip install --system -e .

# Expose port
EXPOSE 8080

# Health check endpoint (optional - add to server.py if needed)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run the server with HTTP transport
CMD ["uv", "run", "python", "src/server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8080"]