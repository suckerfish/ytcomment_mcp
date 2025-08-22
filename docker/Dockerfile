FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY . .

# Install dependencies
RUN uv pip install --system -e .

# Keep container running
CMD ["tail", "-f", "/dev/null"]