# Use Python 3.10 slim image
FROM python:3.10-slim

# Build context is root, so we need to copy from test_workspace/image-gen-server/
WORKDIR /app

# Copy image-gen-server directory
COPY test_workspace/image-gen-server/ .

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt-lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port
EXPOSE 8080

# Run the HTTP server
CMD ["python", "-m", "uvicorn", "http_server:app", "--host", "0.0.0.0", "--port", "8080"]
