import os
import whisper
from typing import Dict, Optional
from pathlib import Path

class WhisperTranscriber:
    def __init__(self, model_size: str = "base"):
        """
        Initialize the Whisper transcriber.
        
        Args:
            model_size: Size of the model to use. Options are:
                - "tiny" (fastest, least accurate)
                - "base" (good balance)
                - "small" (better accuracy)
                - "medium" (even better)
                - "large" (best accuracy, slowest)
        """
        print(f"Loading Whisper {model_size} model...")
        self.model = whisper.load_model(model_size)
        print("Model loaded successfully!")

    def transcribe_file(self, file_path: str, language: Optional[str] = None) -> Dict:
        """
        Transcribe a local audio/video file.
        
        Args:
            file_path: Path to the audio/video file
            language: Optional language code (e.g., 'en' for English)
                     If None, Whisper will auto-detect the language
        
        Returns:
            Dict containing:
            - text: The full transcript
            - segments: List of segments with timestamps
            - language: Detected language
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        print(f"Transcribing file: {file_path}")
        result = self.model.transcribe(
            file_path,
            language=language,
            verbose=True  # Shows progress
        )
        
        return result

    def save_transcript(self, result: Dict, output_path: Optional[str] = None) -> str:
        """
        Save the transcript to a text file.
        
        Args:
            result: The transcription result from transcribe_file
            output_path: Optional path to save the transcript
                        If None, saves in the same directory as the input file
        
        Returns:
            Path to the saved transcript file
        """
        if output_path is None:
            # Create output path based on input file
            input_path = result.get('input_path', 'transcript')
            output_path = str(Path(input_path).with_suffix('.txt'))
        
        # Save just the text without timestamps
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result['text'])
            
        print(f"Transcript saved to: {output_path}")
        return output_path

def main():
    # Example usage
    transcriber = WhisperTranscriber(model_size="base")
    
    # Get file path from command line
    import sys
    if len(sys.argv) != 2:
        print("Usage: python whisper_transcriber.py <path_to_audio_file>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    
    try:
        # Transcribe the file
        result = transcriber.transcribe_file(file_path)
        
        # Save the transcript
        output_path = transcriber.save_transcript(result)
        
        print("\nTranscription completed!")
        print(f"Detected language: {result['language']}")
        print(f"Transcript saved to: {output_path}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 