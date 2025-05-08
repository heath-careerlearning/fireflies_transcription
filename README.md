# Fireflies Transcription Service

A Python service that automates the transcription of audio files using Fireflies.ai API.

## Features

- Submit publicly accessible audio files to Fireflies.ai for transcription
- Download transcripts as JSON without timestamps or speaker names
- Batch processing support

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
```
Then fill in your Fireflies.ai API key in `.env`

## Usage

```python
from fireflies_transcriber import FirefliesTranscriber

transcriber = FirefliesTranscriber()
transcriber.process_file("https://your-public-file-url.mp3")
```

## Project Structure

```
.
├── README.md
├── requirements.txt
├── .env.example
├── src/
│   ├── __init__.py
│   ├── fireflies_transcriber.py
│   └── config.py
└── tests/
    └── __init__.py
```

## Requirements

- Python 3.8+
- Fireflies.ai API key
- Publicly accessible audio file URLs 