import asyncio
import sys
import re
from fireflies_transcriber import FirefliesTranscriber

def extract_file_id(url: str) -> str:
    """Extract file ID from Google Drive URL."""
    # Match patterns like:
    # https://drive.google.com/file/d/FILE_ID/view
    # https://drive.google.com/open?id=FILE_ID
    patterns = [
        r'/file/d/([a-zA-Z0-9_-]+)',
        r'[?&]id=([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    raise ValueError("Invalid Google Drive URL format")

async def main():
    if len(sys.argv) != 2:
        print("Usage: python example.py <google_drive_url>")
        sys.exit(1)
        
    # Initialize the transcriber
    transcriber = FirefliesTranscriber()
    
    # Get Google Drive URL from command line
    drive_url = sys.argv[1]
    try:
        file_id = extract_file_id(drive_url)
        file_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        # Process the file
        result = await transcriber.process_file(file_url)
        print(f"Upload successful: {result['message']}")
        
        # TODO: After transcription is complete, get the transcript
        # transcript = await transcriber.get_transcript(result['id'])
        # print(f"Transcript: {transcript['text']}")
        
    except ValueError as e:
        print(f"Error: {str(e)}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 