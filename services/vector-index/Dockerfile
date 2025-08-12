FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy shared libraries first
COPY libs /tmp/libs

# Copy requirements first for better caching
COPY services/vector-index/requirements.txt .
RUN pip install -r requirements.txt

# Install shared libraries
RUN pip install -e /tmp/libs/common-py
RUN pip install -e /tmp/libs/contracts

# Expose port
EXPOSE 8081
