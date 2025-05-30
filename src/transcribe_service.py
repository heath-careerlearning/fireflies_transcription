import os
import logging
from pathlib import Path
import sys
import time
from typing import Optional

# Add parent directory to path to import transcribe
sys.path.append(str(Path(__file__).parent.parent))
from transcribe import transcribe_audio

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants - will be overridden by environment variables if set
DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', '/data/videos')
TRANSCRIPT_DIR = os.getenv('TRANSCRIPT_DIR', '/data/transcripts')
TRACKING_DIR = os.getenv('TRACKING_DIR', '/data/tracking')
MODEL_SIZE = os.getenv('WHISPER_MODEL', 'base')
DOWNLOADED_FILE = os.path.join(TRACKING_DIR, 'downloaded.txt')

def get_downloaded_files():
    """Get list of already downloaded files."""
    if not os.path.exists(DOWNLOADED_FILE):
        return []
    with open(DOWNLOADED_FILE, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def process_video(filename):
    """Process a video file using the existing transcribe module."""
    video_path = os.path.join(DOWNLOAD_DIR, filename)
    transcript_path = os.path.join(TRANSCRIPT_DIR, f"{os.path.splitext(filename)[0]}.txt")
    
    # Skip if transcript already exists
    if os.path.exists(transcript_path):
        logger.info(f"Transcript for {filename} already exists, skipping transcription")
        return True
        
    try:
        logger.info(f"Starting transcription of {filename}")
        logger.info(f"Using model size: {MODEL_SIZE}")
        
        # Use the existing transcribe function
        transcription = transcribe_audio(video_path, MODEL_SIZE)
        
        # Save the transcript
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(transcription)
            
        logger.info(f"Successfully transcribed {filename}")
        return True
    except Exception as e:
        logger.error(f"Error transcribing {filename}: {str(e)}")
        return False

def main():
    """Main function to run the transcription service."""
    # Create directories if they don't exist
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
    
    while True:
        # Get list of downloaded files
        downloaded_files = get_downloaded_files()
        logger.info(f"Found {len(downloaded_files)} downloaded files to process")
        
        if not downloaded_files:
            logger.info("No downloaded files found to transcribe, waiting...")
            time.sleep(60)  # Wait a minute before checking again
            continue
        
        # Process videos
        successful = 0
        failed = 0
        for filename in downloaded_files:
            video_path = os.path.join(DOWNLOAD_DIR, filename)
            if not os.path.exists(video_path):
                logger.warning(f"Video file {filename} not found, skipping")
                continue
                
            if process_video(filename):
                successful += 1
            else:
                failed += 1
        
        logger.info(f"Transcription batch complete. Successful: {successful}, Failed: {failed}")
        time.sleep(60)  # Wait a minute before checking for new files

if __name__ == "__main__":
    main()
