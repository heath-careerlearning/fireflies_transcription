import os
import asyncio
import aiohttp
import logging
from pathlib import Path
import sys
import argparse

# Add parent directory to path to import transcribe
sys.path.append(str(Path(__file__).parent.parent))
from transcribe import transcribe_audio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants - will be overridden by environment variables if set
DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', 'temp/data/videos')
TRANSCRIPT_DIR = os.getenv('TRANSCRIPT_DIR', 'temp/data/transcripts')
MODEL_SIZE = os.getenv('WHISPER_MODEL', 'base')
DOWNLOADED_FILE = os.path.join(DOWNLOAD_DIR, 'downloaded.txt')

def is_url(path):
    """Check if the path is a URL."""
    return path.startswith(('http://', 'https://'))

def get_filename(path):
    """Extract filename from URL or path."""
    if is_url(path):
        return path.split('/')[-1]
    return os.path.basename(path)

def is_downloaded(filename):
    """Check if a file has been marked as downloaded."""
    if not os.path.exists(DOWNLOADED_FILE):
        return False
    with open(DOWNLOADED_FILE, 'r') as f:
        return filename in [line.strip() for line in f]

def mark_as_downloaded(filename):
    """Mark a file as downloaded."""
    with open(DOWNLOADED_FILE, 'a') as f:
        f.write(f"{filename}\n")

async def download_video(session, url, filename):
    """Download a video file."""
    output_path = os.path.join(DOWNLOAD_DIR, filename)
    
    # Skip if already downloaded
    if is_downloaded(filename):
        logger.info(f"File {filename} already exists, skipping download")
        return True
        
    try:
        async with session.get(url) as response:
            if response.status == 200:
                with open(output_path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                logger.info(f"Successfully downloaded {filename}")
                mark_as_downloaded(filename)
                return True
            else:
                logger.error(f"Failed to download {filename}: HTTP {response.status}")
                return False
    except Exception as e:
        logger.error(f"Error downloading {filename}: {str(e)}")
        return False

def process_video(filename):
    """Process a video file using the existing transcribe module."""
    video_path = os.path.join(DOWNLOAD_DIR, filename)
    transcript_path = os.path.join(TRANSCRIPT_DIR, f"{os.path.splitext(filename)[0]}.txt")
    
    # Skip if transcript already exists
    if os.path.exists(transcript_path):
        logger.info(f"Transcript for {filename} already exists, skipping transcription")
        return True
        
    try:
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

async def download_videos(limit=None):
    """Download videos from the list."""
    # Create directories if they don't exist
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Read the download list
    with open('docs/download_list.txt', 'r') as f:
        video_urls = [line.strip() for line in f if line.strip()]
    
    # Filter for URLs only
    video_urls = [url for url in video_urls if is_url(url)]
    
    # Apply limit if specified
    if limit is not None:
        video_urls = video_urls[:limit]
        logger.info(f"Downloading {len(video_urls)} videos (limited)")
    
    # Download videos
    async with aiohttp.ClientSession() as session:
        for url in video_urls:
            filename = get_filename(url)
            await download_video(session, url, filename)

def transcribe_videos(limit=None):
    """Transcribe videos that have been downloaded."""
    # Create directories if they don't exist
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
    
    # Read the download list
    with open('docs/download_list.txt', 'r') as f:
        video_paths = [line.strip() for line in f if line.strip()]
    
    # Apply limit if specified
    if limit is not None:
        video_paths = video_paths[:limit]
        logger.info(f"Transcribing {len(video_paths)} videos (limited)")
    
    # Process videos
    for path in video_paths:
        filename = get_filename(path)
        if is_url(path) and not is_downloaded(filename):
            logger.info(f"Skipping {filename} - not yet downloaded")
            continue
        process_video(filename)

def parse_args():
    parser = argparse.ArgumentParser(description='Download and transcribe videos.')
    parser.add_argument('--limit', type=int, help='Limit the number of videos to process')
    parser.add_argument('--download-only', action='store_true', help='Only download videos')
    parser.add_argument('--transcribe-only', action='store_true', help='Only transcribe videos')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    if not args.transcribe_only:
        asyncio.run(download_videos(args.limit))
    
    if not args.download_only:
        transcribe_videos(args.limit) 