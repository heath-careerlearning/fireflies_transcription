import os
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

    async def get_transcript(self, meeting_id: str) -> Dict:
        """Get transcript for a meeting, excluding timestamps and speaker names."""
        query = gql("""
            query GetTranscript($id: ID!) {
                transcript(id: $id) {
                    text
                }
            }
        """)
        
        variables = {"id": meeting_id}
        result = await self.client.execute_async(query, variable_values=variables)
        return result['transcript']

    async def process_file(self, file_url: str, title: Optional[str] = None) -> Dict:
        """Process a single file: upload and get transcript."""
        if not title:
            title = os.path.basename(file_url)
        
        # Upload the file
        upload_result = await self.upload_audio(file_url, title)
        if not upload_result['success']:
            raise Exception(f"Upload failed: {upload_result['message']}")
        
        # TODO: Implement polling for transcription completion
        # For now, we'll need to manually check when the transcription is ready
        
        return upload_result

    async def process_files(self, file_urls: list[str]) -> list[Dict]:
        """Process multiple files."""
        results = []
        for url in file_urls:
            result = await self.process_file(url)
            results.append(result)
        return results 