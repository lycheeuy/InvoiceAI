FROM python:3.12-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt /app/

# Filter out development dependencies and install
RUN grep -v -E "pytest|httpx" requirements.txt > requirements.prod.txt && \
    pip install --no-cache-dir --timeout 300 --retries 5 --index-url https://mirrors.aliyun.com/pypi/simple/ -r requirements.prod.txt && \
    rm requirements.txt requirements.prod.txt

# Copy application code
COPY backend /app/backend

# Expose port
EXPOSE 8000

# Start Uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
