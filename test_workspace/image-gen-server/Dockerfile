# Use Python 3.10 slim image
FROM python:3.10-slim

# Set working directory to the image-gen-server folder
WORKDIR /app/test_workspace/image-gen-server

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Debug: List files before copy
RUN echo "=== Debug: Files in current directory ===" && ls -la

# Copy the rest of the application
COPY . .

# Debug: List files after copy
RUN echo "=== Debug: Files after COPY ===" && ls -la

# Expose the port
EXPOSE 8080

# Run the HTTP server
CMD ["python", "-m", "uvicorn", "http_server:app", "--host", "0.0.0.0", "--port", "8080"]
