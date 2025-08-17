FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc libgl1-mesa-glx libglib2.0-0 libsm6 libxrender1 && ldconfig && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY services/product-segmentor/requirements.txt .
RUN pip install -r requirements.txt

# Copy shared libraries
COPY libs/common-py /app/libs/common-py
COPY libs/contracts /app/libs/contracts
COPY libs/config.py /app/libs/config.py

# Install shared libraries in development mode
RUN pip install -e /app/libs/common-py
RUN pip install -e /app/libs/contracts

# Set environment variables
ENV PYTHONPATH=/app/app:/app/libs
ENV PYTHONUNBUFFERED=1
