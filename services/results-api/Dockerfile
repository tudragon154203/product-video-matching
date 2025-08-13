FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY services/results-api/requirements.txt .
RUN pip install -r requirements.txt

# Expose port
EXPOSE 8080
