FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy shared libraries first
COPY libs /tmp/libs

# Copy requirements first for better caching
COPY services/results-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install shared libraries
RUN pip install -e /tmp/libs/common-py
RUN pip install -e /tmp/libs/contracts

# Copy application code
COPY services/results-api/ .

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]