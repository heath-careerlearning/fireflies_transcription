import os
import re
import asyncio
from typing import Dict, Optional
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from dotenv import load_dotenv

class FirefliesTranscriber:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('FIREFLIES_API_KEY')
        if not self.api_key:
            raise ValueError("FIREFLIES_API_KEY not found in environment variables")
        
        # Initialize GraphQL client
        transport = AIOHTTPTransport(
            url='https://api.fireflies.ai/graphql',
            headers={'Authorization': f'Bearer {self.api_key}'}
        )
        self.client = Client(transport=transport, fetch_schema_from_transport=True)

    def _extract_file_id(self, url: str) -> str:
        """Extract file ID from Google Drive URL."""
        patterns = [
            r'/file/d/([a-zA-Z0-9_-]+)',
            r'[?&]id=([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError("Invalid Google Drive URL format")

    def _get_direct_url(self, url: str) -> str:
        """Convert Google Drive URL to direct download URL."""
        file_id = self._extract_file_id(url)
        # Use the direct download format that works with large files
        return f"https://drive.google.com/u/0/uc?id={file_id}&export=download"

    async def upload_audio(self, file_url: str, title: str) -> Dict:
        """Upload an audio file for transcription."""
        mutation = gql("""
            mutation UploadAudio($input: AudioUploadInput!) {
                uploadAudio(input: $input) {
                    success
                    title
                    message
                }
            }
        """)
        
        variables = {
            "input": {
                "url": file_url,
                "title": title
            }
        }
        
        result = await self.client.execute_async(mutation, variable_values=variables)
        return result['uploadAudio']

    async def get_transcript(self, title: str) -> Dict:
        """Get transcript for a meeting by title."""
        query = gql("""
            query GetTranscript($title: String!) {
                transcripts(filter: { title: $title }) {
                    text
                }
            }
        """)
        
        variables = {"title": title}
        result = await self.client.execute_async(query, variable_values=variables)
        return result['transcripts'][0] if result['transcripts'] else None

    async def process_file(self, file_url: str, title: Optional[str] = None) -> Dict:
        """Process a single file: upload and get transcript."""
        # Convert Google Drive URL to direct download URL
        direct_url = self._get_direct_url(file_url)
        print(f"Using direct download URL: {direct_url}")  # Debug print
        
        if not title:
            # Extract filename from URL
            title = os.path.basename(file_url.split('?')[0])
        
        # Upload the file
        upload_result = await self.upload_audio(direct_url, title)
        if not upload_result['success']:
            raise Exception(f"Upload failed: {upload_result['message']}")
        
        # Wait a bit for processing to start
        await asyncio.sleep(5)
        
        # Try to get the transcript
        max_attempts = 30  # 5 minutes total with 10-second intervals
        for attempt in range(max_attempts):
            transcript = await self.get_transcript(title)
            if transcript:
                return transcript
            await asyncio.sleep(10)
        
        raise TimeoutError("Transcription timed out")

    async def process_files(self, file_urls: list[str]) -> list[Dict]:
        """Process multiple files."""
        results = []
        for url in file_urls:
            result = await self.process_file(url)
            results.append(result)
        return results 