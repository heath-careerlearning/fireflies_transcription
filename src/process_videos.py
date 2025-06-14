import os
import asyncio
import aiohttp
import logging
from pathlib import Path
import sys
import argparse
import traceback
import time
from typing import Optional, Set, Dict
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants - will be overridden by environment variables if set
DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', '/data/videos')
TRACKING_DIR = os.getenv('TRACKING_DIR', '/data/tracking')
DOWNLOADED_FILE = os.path.join(TRACKING_DIR, 'downloaded.txt')
DOWNLOAD_LIST_FILE = os.path.join(TRACKING_DIR, 'download_list.txt')
FILE_SIZES_FILE = os.path.join(TRACKING_DIR, 'file_sizes.json')

# Download configuration
DOWNLOAD_TIMEOUT = 14400  # 4 hours
CHUNK_TIMEOUT = 1800  # 30 minutes per chunk
MAX_RETRIES = 5
RETRY_DELAY = 300  # 5 minutes between retries
MAX_CONCURRENT_DOWNLOADS = 2  # Reduced to 2 concurrent downloads
CHUNK_SIZE = 1024 * 1024  # 1MB chunks
RATE_LIMIT_DELAY = 60  # 1 minute delay between initial requests
MAX_CONCURRENT_REQUESTS = 1  # Rate limit the initial HEAD requests

# Speed monitoring
SPEED_CHECK_INTERVAL = 60  # Check speed every minute
MIN_SPEED_BYTES_PER_SECOND = 1024  # 1KB/s minimum speed

async def check_network_connectivity():
    """Check if network connectivity is working"""
    try:
        # Check DNS resolution
        logger.info("Checking DNS resolution...")
        result = await asyncio.create_subprocess_exec(
            'nslookup', 'wccdownload.on24.com',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()
        if result.returncode == 0:
            logger.info("DNS resolution working")
        else:
            logger.error(f"DNS resolution failed: {stderr.decode()}")
            return False

        # Check network connectivity with ping to on24
        logger.info("Checking network connectivity to on24...")
        result = await asyncio.create_subprocess_exec(
            'ping', '-c', '4', 'wccdownload.on24.com',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()
        if result.returncode == 0:
            logger.info("Network connectivity working")
            logger.info(f"Ping results: {stdout.decode()}")
        else:
            logger.error(f"Network connectivity failed: {stderr.decode()}")
            return False

        return True
    except Exception as e:
        logger.error(f"Network check failed: {str(e)}")
        return False

def get_downloaded_files() -> Set[str]:
    """Get set of already downloaded files."""
    if not os.path.exists(DOWNLOADED_FILE):
        return set()
    with open(DOWNLOADED_FILE, 'r') as f:
        return {line.strip() for line in f if line.strip()}

def get_expected_sizes() -> Dict[str, int]:
    """Get expected file sizes from the JSON file."""
    if not os.path.exists(FILE_SIZES_FILE):
        return {}
    with open(FILE_SIZES_FILE, 'r') as f:
        return json.load(f)

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

def is_file_complete(filename: str, expected_size: int) -> bool:
    """Check if a file is completely downloaded."""
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if not os.path.exists(file_path):
        return False
    return os.path.getsize(file_path) == expected_size

async def get_expected_file_size(url: str, session: aiohttp.ClientSession) -> Optional[int]:
    """Get the expected file size from a HEAD request."""
    try:
        async with session.head(url) as response:
            if response.status == 200:
                size = int(response.headers.get('Content-Length', 0))
                if size > 0:
                    return size
                logger.warning(f"Could not determine file size for {url}")
            else:
                logger.warning(f"HEAD request failed for {url}: HTTP {response.status}")
    except Exception as e:
        logger.error(f"Error getting file size for {url}: {str(e)}")
    return None

async def download_video(session, url, filename, retry_count: int = 0) -> bool:
    """Download a video file with retry logic."""
    output_path = os.path.join(DOWNLOAD_DIR, filename)
    start_time = time.time()
    last_speed_check = start_time
    last_bytes_downloaded = 0
    
    try:
        logger.info(f"Attempting to download {filename} from {url} (attempt {retry_count + 1}/{MAX_RETRIES})")
        
        # Add delay between downloads to avoid rate limiting
        if retry_count == 0:  # Only on first attempt
            logger.info(f"Waiting {RATE_LIMIT_DELAY} seconds before starting download...")
            await asyncio.sleep(RATE_LIMIT_DELAY)
        
        # Check network connectivity before attempting download
        if not await check_network_connectivity():
            logger.error("Network connectivity check failed, will retry")
            if retry_count < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
                return await download_video(session, url, filename, retry_count + 1)
            return False

        # Get expected file size
        expected_size = await get_expected_file_size(url, session)
        if expected_size:
            logger.info(f"Expected file size for {filename}: {expected_size} bytes")
            
            # Check if file exists and is incomplete
            if os.path.exists(output_path):
                actual_size = os.path.getsize(output_path)
                if actual_size > 0 and actual_size < expected_size:
                    logger.warning(f"Found incomplete file: {filename} (size: {actual_size}, expected: {expected_size})")
                    # Remove from downloaded.txt if it exists
                    if filename in get_downloaded_files():
                        with open(DOWNLOADED_FILE, 'r') as f:
                            lines = f.readlines()
                        with open(DOWNLOADED_FILE, 'w') as f:
                            for line in lines:
                                if line.strip() != filename:
                                    f.write(line)
                    # Delete incomplete file
                    os.remove(output_path)
        
        timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)
        async with session.get(url, timeout=timeout) as response:
            # Log response headers for rate limit detection
            logger.info(f"Response headers for {filename}: {dict(response.headers)}")
            
            if response.status == 200:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                last_progress_time = time.time()
                last_progress = 0
                
                with open(output_path, 'wb') as f:
                    while True:
                        try:
                            chunk = await asyncio.wait_for(
                                response.content.read(CHUNK_SIZE),
                                timeout=CHUNK_TIMEOUT
                            )
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Speed monitoring
                            current_time = time.time()
                            if current_time - last_speed_check >= SPEED_CHECK_INTERVAL:
                                bytes_since_last_check = downloaded - last_bytes_downloaded
                                speed = bytes_since_last_check / (current_time - last_speed_check)
                                logger.info(f"Download speed for {filename}: {speed/1024:.2f} KB/s")
                                
                                if speed < MIN_SPEED_BYTES_PER_SECOND:
                                    logger.warning(f"Download speed too slow for {filename}: {speed/1024:.2f} KB/s")
                                    raise asyncio.TimeoutError("Download speed too slow")
                                
                                last_speed_check = current_time
                                last_bytes_downloaded = downloaded
                            
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                current_time = time.time()
                                
                                # Only log if integer percent increased
                                if int(progress) > int(last_progress):
                                    last_progress = progress
                                    last_progress_time = current_time
                                    logger.info(f"Download progress for {filename}: {int(progress)}% (elapsed: {int(current_time - start_time)}s)")
                        except asyncio.TimeoutError:
                            logger.error(f"Chunk download timeout for {filename}")
                            raise

                # Verify download size if we had an expected size
                if expected_size and downloaded != expected_size:
                    logger.error(f"Download incomplete for {filename}: got {downloaded} bytes, expected {expected_size}")
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    if retry_count < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        return await download_video(session, url, filename, retry_count + 1)
                    return False
                
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
    
    # First, get all file sizes with rate limiting
    file_sizes = {}
    timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout for HEAD requests
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS)
    
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        for url in video_urls:
            filename = get_filename(url)
            size = await get_expected_file_size(url, session)
            if size:
                file_sizes[filename] = size
                logger.info(f"Got size for {filename}: {size} bytes")
            await asyncio.sleep(RATE_LIMIT_DELAY)  # Rate limit the HEAD requests
    
    # Now download files with higher concurrency
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

async def main():
    """Main entry point."""
    args = parse_args()
    await download_videos(args.limit)

def parse_args():
    parser = argparse.ArgumentParser(description='Download videos.')
    parser.add_argument('--limit', type=int, help='Limit the number of videos to process')
    return parser.parse_args()

if __name__ == '__main__':
    asyncio.run(main()) 