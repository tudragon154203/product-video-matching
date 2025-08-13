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
        libgomp1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy shared libraries first
COPY libs /tmp/libs

# Copy requirements first for better caching
COPY services/vision-keypoint/requirements.txt .
RUN pip install -r requirements.txt

# Install shared libraries
RUN pip install -e /tmp/libs/common-py
RUN pip install -e /tmp/libs/contracts
