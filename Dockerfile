# Use official Python image
FROM python:3.11-slim

# Install system dependencies for Flet (UI and Audio)
RUN apt-get update && apt-get install -y \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libasound2 \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose the app port (Render uses PORT env var)
EXPOSE 8080

# Run main.py directly
CMD ["python", "main.py"]
