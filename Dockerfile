FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY server.py .
COPY search.py .
COPY info.py .
COPY manual_auth.py .

# Config directory for credentials (to be bind mounted)
RUN mkdir -p /app/config
VOLUME /app/config

# Environment variable for credentials path
ENV CREDENTIALS_PATH=/app/config/credentials.json

# Entrypoint script
COPY main.py .
ENTRYPOINT ["python", "main.py"]

# No CMD: entrypoint always starts HTTP/SSE server
