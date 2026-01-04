# Use Python 3.9 base image
FROM python:3.9-slim

# Install Perl (required for ldraw2stl conversion tool)
RUN apt-get update && apt-get install -y \
    perl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for sets and ensure permissions
RUN mkdir -p /app/sets && chmod 777 /app/sets

# Expose Flask port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "app.py"]
