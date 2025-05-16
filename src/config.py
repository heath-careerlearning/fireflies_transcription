import os
from dotenv import load_dotenv

load_dotenv()
 
FIREFLIES_API_KEY = os.getenv('FIREFLIES_API_KEY')
if not FIREFLIES_API_KEY:
    raise ValueError("FIREFLIES_API_KEY not found in environment variables") 