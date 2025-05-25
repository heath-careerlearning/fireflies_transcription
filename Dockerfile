FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only the necessary files
COPY requirements.txt .
COPY transcribe.py .
COPY src/process_videos.py .
COPY docs/download_list.txt docs/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create data directories
RUN mkdir -p /data/videos /data/transcripts

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DOWNLOAD_DIR=/data/videos
ENV TRANSCRIPT_DIR=/data/transcripts
ENV WHISPER_MODEL=base

# Run the application
CMD ["python", "process_videos.py"] 