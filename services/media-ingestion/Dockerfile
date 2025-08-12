FROM python:3.10-slim

WORKDIR /app

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    gcc \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy shared libraries first
COPY libs /tmp/libs

# Copy requirements first for better caching
COPY services/media-ingestion/requirements.txt .
RUN pip install -r requirements.txt

# Install shared libraries
RUN pip install -e /tmp/libs/common-py
RUN pip install -e /tmp/libs/contracts

# Copy application code
COPY services/media-ingestion/ .

# Run the application
CMD ["python", "main.py"]
