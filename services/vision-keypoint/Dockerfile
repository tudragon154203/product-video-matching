FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update -o Acquire::Retries=5 && \
    apt-get install -y --no-install-recommends \
        gcc \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
        curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY services/vision-keypoint/requirements.txt .
RUN pip install -r requirements.txt

# Copy shared libraries
COPY libs/common-py /app/libs/common-py
COPY libs/contracts /app/libs/contracts
COPY libs/config.py /app/libs/config.py

# Install shared libraries in development mode
RUN pip install -e /app/libs/common-py
RUN pip install -e /app/libs/contracts

# Copy application code
COPY services/vision-keypoint/ .
