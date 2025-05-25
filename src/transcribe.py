import whisper
import argparse
from pathlib import Path
import concurrent.futures
from typing import List, Optional

def transcribe_audio(audio_path: str, model_name: str = "base") -> str:
    """
    Transcribe an audio file using OpenAI's Whisper model.
    
    Args:
        audio_path (str): Path to the audio file
        model_name (str): Name of the Whisper model to use (tiny, base, small, medium, large)
        
    Returns:
        str: Transcribed text
    """
    # Validate audio file exists
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    # Load the model
    print(f"Loading {model_name} model...")
    model = whisper.load_model(model_name)
    
    # Transcribe the audio
    print(f"Transcribing {audio_path}...")
    result = model.transcribe(str(audio_path))
    
    return result["text"]

def process_file(file_path: Path, model_name: str) -> None:
    """Process a single audio/video file and save its transcription."""
    try:
        transcription = transcribe_audio(str(file_path), model_name)
        output_path = file_path.with_suffix('.txt')
        output_path.write_text(transcription, encoding="utf-8")
        print(f"Transcription saved to: {output_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def get_media_files(directory: Path) -> List[Path]:
    """Get all media files from the directory."""
    media_extensions = {'.mp4', '.mp3', '.wav', '.m4a', '.avi', '.mov'}
    return [f for f in directory.iterdir() if f.is_file() and f.suffix.lower() in media_extensions]

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio/video files using OpenAI's Whisper")
    parser.add_argument("file", nargs="?", help="Path to a single audio/video file")
    parser.add_argument("--directory", help="Path to directory containing audio/video files")
    parser.add_argument("--model", default="base", choices=["tiny", "base", "small", "medium", "large"],
                      help="Whisper model to use (default: base)")
    
    args = parser.parse_args()
    
    if not args.file and not args.directory:
        parser.error("Either file path or --directory must be specified")
    
    try:
        if args.file:
            # Process single file
            file_path = Path(args.file)
            process_file(file_path, args.model)
        else:
            # Process directory
            directory = Path(args.directory)
            if not directory.exists() or not directory.is_dir():
                raise NotADirectoryError(f"Directory not found: {directory}")
            
            media_files = get_media_files(directory)
            if not media_files:
                print(f"No media files found in {directory}")
                return 0
            
            print(f"Found {len(media_files)} media files to process")
            for file_path in media_files:
                process_file(file_path, args.model)
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 