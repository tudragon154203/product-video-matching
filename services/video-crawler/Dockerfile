FROM python:3.10.8-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    ffmpeg \
    build-essential \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY services/video-crawler/requirements.txt .

# Install Python dependencies including Playwright
RUN pip install --no-cache-dir -r requirements.txt 

# Copy shared libraries
COPY libs/common-py /app/libs/common-py
COPY libs/contracts /app/libs/contracts
COPY libs/config.py /app/libs/config.py

# Install shared libraries in development mode
RUN pip install --no-cache-dir -e /app/libs/common-py && \
    pip install --no-cache-dir -e /app/libs/contracts

# (Optional) Environment hygiene
ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1