FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy shared libraries first
COPY libs /tmp/libs

# Copy requirements first for better caching
COPY services/vision-embedding/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install shared libraries
RUN pip install -e /tmp/libs/common-py
RUN pip install -e /tmp/libs/contracts

# Copy application code
COPY services/vision-embedding/ .

# Run the application
CMD ["python", "main.py"]