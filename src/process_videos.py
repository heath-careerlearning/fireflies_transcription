import os
import asyncio
import aiohttp
import logging
from pathlib import Path
import sys
import argparse
import glob
import traceback
import socket
import subprocess
from typing import Optional, Set
from concurrent.futures import ThreadPoolExecutor

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
DOWNLOAD_LIST_FILE = os.path.join(TRACKING_DIR, 'download_list.txt')

# Download configuration
DOWNLOAD_TIMEOUT = 300  # 5 minutes
CHUNK_TIMEOUT = 30  # 30 seconds per chunk
MAX_RETRIES = 3
RETRY_DELAY = 60  # 1 minute
MAX_CONCURRENT_DOWNLOADS = 5  # Limit concurrent downloads

def check_network_connectivity():
    """Check basic network connectivity and DNS resolution."""
    try:
        # Check DNS resolution
        socket.gethostbyname('google.com')
        logger.info("DNS resolution working")
        
        # Try to ping Google
        try:
            subprocess.run(['ping', '-c', '1', 'google.com'], 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE, 
                         timeout=5)
            logger.info("Network connectivity working")
        except subprocess.TimeoutExpired:
            logger.warning("Ping timed out - possible network latency issues")
        except FileNotFoundError:
            logger.warning("Ping command not available")
            
        return True
    except socket.gaierror as e:
        logger.error(f"DNS resolution failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Network check failed: {str(e)}")
        return False

def get_downloaded_files() -> Set[str]:
    """Get set of already downloaded files."""
    if not os.path.exists(DOWNLOADED_FILE):
        return set()
    with open(DOWNLOADED_FILE, 'r') as f:
        return {line.strip() for line in f if line.strip()}

def is_url(path):
    """Check if the path is a URL."""
    return path.startswith(('http://', 'https://'))

def get_filename(path):
    """Extract filename from URL or path."""
    if is_url(path):
        return path.split('/')[-1]
    return os.path.basename(path)

def mark_as_downloaded(filename):
    """Mark a file as downloaded."""
    with open(DOWNLOADED_FILE, 'a') as f:
        f.write(f"{filename}\n")

async def download_video(session, url, filename, retry_count: int = 0) -> bool:
    """Download a video file with retry logic."""
    output_path = os.path.join(DOWNLOAD_DIR, filename)
    
    try:
        logger.info(f"Attempting to download {filename} from {url} (attempt {retry_count + 1}/{MAX_RETRIES})")
        
        # Check network connectivity before attempting download
        if not check_network_connectivity():
            logger.error("Network connectivity check failed, will retry")
            if retry_count < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
                return await download_video(session, url, filename, retry_count + 1)
            return False
        
        timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)
        async with session.get(url, timeout=timeout) as response:
            if response.status == 200:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(output_path, 'wb') as f:
                    while True:
                        try:
                            chunk = await asyncio.wait_for(
                                response.content.read(8192),
                                timeout=CHUNK_TIMEOUT
                            )
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                logger.info(f"Download progress for {filename}: {progress:.1f}%")
                        except asyncio.TimeoutError:
                            logger.error(f"Chunk download timeout for {filename}")
                            raise
                
                logger.info(f"Successfully downloaded {filename}")
                mark_as_downloaded(filename)
                return True
            else:
                error_msg = f"Failed to download {filename}: HTTP {response.status}"
                if response.status == 404:
                    error_msg += " - File not found"
                elif response.status == 403:
                    error_msg += " - Access forbidden"
                elif response.status == 401:
                    error_msg += " - Authentication required"
                logger.error(error_msg)
                return False
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error(f"Network error downloading {filename}: {str(e)}")
        logger.error(f"Full error details: {traceback.format_exc()}")
        if retry_count < MAX_RETRIES - 1:
            logger.info(f"Retrying download of {filename} in {RETRY_DELAY} seconds...")
            await asyncio.sleep(RETRY_DELAY)
            return await download_video(session, url, filename, retry_count + 1)
        logger.error(f"Max retries reached for {filename}")
        return False
    except IOError as e:
        logger.error(f"File system error downloading {filename}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading {filename}: {str(e)}")
        logger.error(f"Full error details: {traceback.format_exc()}")
        return False

async def download_videos(limit: Optional[int] = None) -> None:
    """Download videos from the list that haven't been downloaded yet."""
    # Create directories if they don't exist
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Get already downloaded files
    downloaded_files = get_downloaded_files()
    logger.info(f"Found {len(downloaded_files)} already downloaded files")
    
    # Read the download list
    with open(DOWNLOAD_LIST_FILE, 'r') as f:
        video_urls = [line.strip() for line in f if line.strip()]
    
    # Filter for URLs only and exclude already downloaded files
    video_urls = [url for url in video_urls if is_url(url)]
    video_urls = [url for url in video_urls if get_filename(url) not in downloaded_files]
    
    if not video_urls:
        logger.info("No new videos to download")
        return
    
    # Apply limit if specified
    if limit is not None:
        video_urls = video_urls[:limit]
        logger.info(f"Downloading {len(video_urls)} videos (limited)")
    else:
        logger.info(f"Downloading {len(video_urls)} videos")
    
    # Download videos with concurrency limit
    timeout = aiohttp.ClientTimeout(total=None)  # No timeout for the session
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_DOWNLOADS)
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        tasks = []
        for url in video_urls:
            filename = get_filename(url)
            task = asyncio.create_task(download_video(session, url, filename))
            tasks.append(task)
        
        # Wait for all downloads to complete
        await asyncio.gather(*tasks)

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
        logger.error(f"Full error details: {traceback.format_exc()}")
        return False

def transcribe_videos(limit: Optional[int] = None) -> None:
    """Transcribe videos that have been downloaded (listed in downloaded.txt)."""
    # Create directories if they don't exist
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
    
    # Get list of downloaded files
    downloaded_files = get_downloaded_files()
    logger.info(f"Found {len(downloaded_files)} downloaded files to process")
    
    if not downloaded_files:
        logger.warning("No downloaded files found to transcribe")
        return
    
    # Apply limit if specified
    if limit is not None:
        downloaded_files = list(downloaded_files)[:limit]
        logger.info(f"Transcribing {len(downloaded_files)} videos (limited)")
    
    # Process videos
    successful = 0
    failed = 0
    for filename in downloaded_files:
        video_path = os.path.join(DOWNLOAD_DIR, filename)
        if not os.path.exists(video_path):
            logger.warning(f"Video file {filename} not found in {DOWNLOAD_DIR}, skipping")
            continue
            
        logger.info(f"Starting transcription of {filename}")
        if process_video(filename):
            successful += 1
        else:
            failed += 1
    
    logger.info(f"Transcription complete. Successful: {successful}, Failed: {failed}")

async def main():
    """Main function to run downloads and transcription in parallel."""
    args = parse_args()
    
    logger.info("Starting video processing")
    logger.info(f"Download directory: {DOWNLOAD_DIR}")
    logger.info(f"Transcript directory: {TRANSCRIPT_DIR}")
    logger.info(f"Tracking directory: {TRACKING_DIR}")
    
    # Create tasks for download and transcription
    tasks = []
    
    if not args.transcribe_only:
        logger.info("Starting download phase")
        download_task = asyncio.create_task(download_videos(args.limit))
        tasks.append(download_task)
    
    if not args.download_only:
        logger.info("Starting transcription phase")
        # Run transcription in a thread pool since it's CPU-bound
        with ThreadPoolExecutor() as executor:
            transcription_task = asyncio.get_event_loop().run_in_executor(
                executor, transcribe_videos, args.limit
            )
            tasks.append(transcription_task)
    
    # Wait for all tasks to complete
    await asyncio.gather(*tasks)
    logger.info("Video processing completed")

def parse_args():
    parser = argparse.ArgumentParser(description='Download and transcribe videos.')
    parser.add_argument('--limit', type=int, help='Limit the number of videos to process')
    parser.add_argument('--download-only', action='store_true', help='Only download videos')
    parser.add_argument('--transcribe-only', action='store_true', help='Only transcribe videos')
    return parser.parse_args()

if __name__ == "__main__":
    asyncio.run(main()) 