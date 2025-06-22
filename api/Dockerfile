# Dockerfile for FastAPI Recipe Recommendation API
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 3009

# Start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3009"]
