# Use official Python image
FROM python:3.11-slim

# Install system dependencies for Flet
RUN apt-get update && apt-get install -y \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose the app port
EXPOSE 8080

# Command to run the app in web mode for deployment
CMD ["flet", "run", "--web", "--port", "8080", "main.py"]
