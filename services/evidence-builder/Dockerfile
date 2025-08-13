FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libgl1 \                 
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \           
    libgomp1  \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY services/evidence-builder/requirements.txt .
RUN pip install -r requirements.txt
