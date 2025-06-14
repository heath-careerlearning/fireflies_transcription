import os
from dotenv import load_dotenv

load_dotenv()
 
FIREFLIES_API_KEY = os.getenv('FIREFLIES_API_KEY')
if not FIREFLIES_API_KEY:
    raise ValueError("FIREFLIES_API_KEY not found in environment variables")

class Config:
    DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', '/data/videos')
    TRANSCRIPT_DIR = os.getenv('TRANSCRIPT_DIR', '/data/transcripts')
    TRACKING_DIR = os.getenv('TRACKING_DIR', '/data/tracking')
    WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base') 