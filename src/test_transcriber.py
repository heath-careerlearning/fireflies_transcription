import asyncio
from fireflies_transcriber import FirefliesTranscriber

async def test_transcriber():
    transcriber = FirefliesTranscriber()
    url = "https://drive.google.com/file/d/1WZl1t-y9RrBOXGn5PaMpRUShqCfRbwUp/view?usp=sharing"
    
    try:
        print("Starting transcription process...")
        result = await transcriber.process_file(url)
        print("\nTranscription completed!")
        print(f"Transcript text: {result['text']}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_transcriber()) 