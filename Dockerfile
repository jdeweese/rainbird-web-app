FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY server.py simple_cli.py index.html ./

# Create config directory (mount target for persistent settings)
RUN mkdir -p /app/config
ENV CONFIG_PATH=/app/config/config.json

# Expose port
EXPOSE 8000

# Run server
CMD ["python", "server.py"]
