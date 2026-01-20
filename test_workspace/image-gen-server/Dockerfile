# Dockerfile for HTTP Image Generation Service
FROM python:3.10-slim

WORKDIR /app

# Copy dependency list and install packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install uv

# Copy the rest of the application code
COPY . .

# Expose the port
EXPOSE 8080

# Start the HTTP server
CMD ["uv", "run", "uvicorn", "http_server:app", "--host", "0.0.0.0", "--port", "8080"]
