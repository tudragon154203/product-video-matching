# Official Playwright base image (Python 3.10 + Playwright v1.48.0 + Ubuntu 24.04 Noble)
FROM mcr.microsoft.com/playwright/python:v1.48.0-noble

WORKDIR /app

# Copy requirements first for better caching
COPY services/video-crawler/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared libraries
COPY libs/common-py /app/libs/common-py
COPY libs/contracts /app/libs/contracts
COPY libs/config.py /app/libs/config.py

# Install shared libraries in development mode
RUN pip install -e /app/libs/common-py
RUN pip install -e /app/libs/contracts