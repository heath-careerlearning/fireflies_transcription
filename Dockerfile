FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    iputils-ping \
    curl \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only the necessary files
COPY requirements.txt .
COPY src/process_videos.py .
COPY src/transcribe.py .
COPY src/config.py .

# Create data directories and copy tracking files
RUN mkdir -p /data/videos /data/transcripts /data/tracking
COPY data/tracking/download_list.txt /data/tracking/
COPY data/tracking/downloaded.txt /data/tracking/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DOWNLOAD_DIR=/data/videos
ENV TRANSCRIPT_DIR=/data/transcripts
ENV TRACKING_DIR=/data/tracking
ENV WHISPER_MODEL=base
ENV SERVICE_NAME=transcription

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import os; assert os.path.exists('/data/videos') and os.path.exists('/data/transcripts')"

# Run the application
CMD ["python", "process_videos.py"] 