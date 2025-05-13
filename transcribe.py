import whisper
import argparse
from pathlib import Path

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

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio files using OpenAI's Whisper")
    parser.add_argument("audio_path", help="Path to the audio file")
    parser.add_argument("--model", default="base", choices=["tiny", "base", "small", "medium", "large"],
                      help="Whisper model to use (default: base)")
    
    args = parser.parse_args()
    
    try:
        transcription = transcribe_audio(args.audio_path, args.model)
        
        # Save to same directory as input with .txt extension
        input_path = Path(args.audio_path)
        output_path = input_path.with_suffix('.txt')
        
        # Save the transcription
        output_path.write_text(transcription, encoding="utf-8")
        print(f"Transcription saved to: {output_path}")
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 