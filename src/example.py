import asyncio
from fireflies_transcriber import FirefliesTranscriber

async def main():
    # Initialize the transcriber
    transcriber = FirefliesTranscriber()
    
    # Example file URL (replace with your actual public URL)
    file_url = "https://example.com/path/to/your/audio.mp3"
    
    try:
        # Process a single file
        result = await transcriber.process_file(file_url)
        print(f"Upload successful: {result['message']}")
        
        # TODO: After transcription is complete, get the transcript
        # transcript = await transcriber.get_transcript(result['id'])
        # print(f"Transcript: {transcript['text']}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 