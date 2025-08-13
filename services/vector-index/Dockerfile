FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY services/vector-index/requirements.txt .
RUN pip install -r requirements.txt

# Copy shared libraries
COPY libs/common-py /app/libs/common-py
COPY libs/contracts /app/libs/contracts
COPY libs/config.py /app/libs/config.py

# Install shared libraries in development mode
RUN pip install -e /app/libs/common-py
RUN pip install -e /app/libs/contracts

# Copy application code
COPY services/vector-index/ .

# Expose port
EXPOSE 8081
