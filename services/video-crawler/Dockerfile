# Đi với TiktokAPI==6.2.2
FROM mcr.microsoft.com/playwright/python:v1.37.0-jammy

WORKDIR /app

# Copy requirements first for better caching
COPY services/video-crawler/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy shared libraries
COPY libs/common-py /app/libs/common-py
COPY libs/contracts /app/libs/contracts
COPY libs/config.py /app/libs/config.py

# Install shared libraries in development mode
RUN pip install -e /app/libs/common-py
RUN pip install -e /app/libs/contracts