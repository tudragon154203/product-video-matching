FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy shared libraries first
COPY libs /tmp/libs

# Copy requirements first for better caching
COPY services/catalog-collector/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install shared libraries
RUN pip install -e /tmp/libs/common-py
RUN pip install -e /tmp/libs/contracts

# Copy application code
COPY services/catalog-collector/ .

# Run the application
CMD ["python", "main.py"]