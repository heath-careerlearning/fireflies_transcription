import os
import json
import logging
from pathlib import Path
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
BASE_DIR = Path(__file__).parent.parent
DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', str(BASE_DIR / 'data' / 'videos'))
TRACKING_DIR = os.getenv('TRACKING_DIR', str(BASE_DIR / 'data' / 'tracking'))
FILE_SIZES_FILE = os.path.join(TRACKING_DIR, 'file_sizes.json')
DOWNLOADED_FILE = os.path.join(TRACKING_DIR, 'downloaded.txt')

def get_expected_sizes() -> dict:
    """Get expected file sizes from the JSON file."""
    if not os.path.exists(FILE_SIZES_FILE):
        logger.error(f"File sizes JSON not found at {FILE_SIZES_FILE}")
        return {}
    
    try:
        with open(FILE_SIZES_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error reading JSON file: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error reading file sizes: {str(e)}")
        return {}

def get_downloaded_files() -> list:
    """Get list of files from downloaded.txt."""
    if not os.path.exists(DOWNLOADED_FILE):
        logger.error(f"Downloaded files list not found at {DOWNLOADED_FILE}")
        return []
    
    try:
        with open(DOWNLOADED_FILE, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error(f"Error reading downloaded files list: {str(e)}")
        return []

def check_file_sizes():
    """Check actual file sizes against expected sizes for downloaded files."""
    expected_sizes = get_expected_sizes()
    downloaded_files = get_downloaded_files()
    
    if not expected_sizes:
        logger.error("No expected sizes found, cannot proceed with check")
        return
    
    if not downloaded_files:
        logger.error("No downloaded files found in list, cannot proceed with check")
        return

    logger.info(f"Found {len(downloaded_files)} files in downloaded list")
    
    # Check each downloaded file
    for filename in downloaded_files:
        if filename not in expected_sizes:
            logger.warning(f"No expected size found for {filename}")
            continue
            
        expected_size = expected_sizes[filename]
        file_path = os.path.join(DOWNLOAD_DIR, filename)
        
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {filename}")
            continue
            
        actual_size = os.path.getsize(file_path)
        if actual_size != expected_size:
            logger.warning(
                f"Size mismatch for {filename}:\n"
                f"  Expected: {expected_size:,} bytes\n"
                f"  Actual:   {actual_size:,} bytes\n"
                f"  Diff:     {actual_size - expected_size:,} bytes"
            )
        else:
            logger.info(f"Size match for {filename}: {actual_size:,} bytes")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Check file sizes against expected sizes.')
    parser.add_argument('--download-dir', help='Override the download directory path')
    args = parser.parse_args()

    if args.download_dir:
        global DOWNLOAD_DIR
        DOWNLOAD_DIR = args.download_dir
        logger.info(f"Using custom download directory: {DOWNLOAD_DIR}")

    logger.info(f"Checking files in: {DOWNLOAD_DIR}")
    check_file_sizes()

if __name__ == '__main__':
    main() 