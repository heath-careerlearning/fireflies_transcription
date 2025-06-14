import os
import json
import asyncio
import aiohttp
import logging
from pathlib import Path
from typing import Dict, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants - adjust paths based on environment
BASE_DIR = Path(__file__).parent.parent
TRACKING_DIR = os.getenv('TRACKING_DIR', str(BASE_DIR / 'data' / 'tracking'))
DOWNLOAD_LIST_FILE = os.path.join(TRACKING_DIR, 'download_list.txt')
FILE_SIZES_FILE = os.path.join(TRACKING_DIR, 'file_sizes.json')

async def get_file_size(url: str, session: aiohttp.ClientSession) -> Optional[int]:
    """Get file size from HEAD request."""
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

def get_filename(url: str) -> str:
    """Extract filename from URL."""
    return url.split('/')[-1]

async def main():
    """Generate file sizes JSON file."""
    # Create tracking directory if it doesn't exist
    os.makedirs(TRACKING_DIR, exist_ok=True)
    
    # Read download list
    with open(DOWNLOAD_LIST_FILE, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    logger.info(f"Found {len(urls)} URLs to process")
    
    # Get file sizes
    file_sizes: Dict[str, int] = {}
    timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout for HEAD requests
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for url in urls:
            filename = get_filename(url)
            size = await get_file_size(url, session)
            if size:
                file_sizes[filename] = size
                logger.info(f"Got size for {filename}: {size} bytes")
            else:
                logger.warning(f"Could not get size for {filename}")
    
    # Save to JSON file
    with open(FILE_SIZES_FILE, 'w') as f:
        json.dump(file_sizes, f, indent=2)
    
    logger.info(f"Saved {len(file_sizes)} file sizes to {FILE_SIZES_FILE}")

if __name__ == '__main__':
    asyncio.run(main()) 