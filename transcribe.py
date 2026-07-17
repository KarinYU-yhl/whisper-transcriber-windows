import argparse
import os
import mlx_whisper

def transcribe_audio(audio_path):
    if not os.path.exists(audio_path):
        print(f"Error: File '{audio_path}' not found.")
        return

    print(f"Transcribing '{audio_path}' using mlx-whisper (large-v3)...")
    
    # Transcribe using mlx-community/whisper-large-v3
    # mlx-whisper automatically uses Apple Silicon GPU
    result = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo="mlx-community/whisper-large-v3"
    )
    
    text = result["text"]
    
    # Generate output filename (same name as input, but with .txt extension)
    base_name = os.path.splitext(audio_path)[0]
    output_path = f"{base_name}.txt"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
        
    print(f"Transcription saved to '{output_path}'")

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio using mlx-whisper (v3) on Apple Silicon.")
    parser.add_argument("audio_file", help="Path to the audio file to transcribe.")
    
    args = parser.parse_args()
    
    transcribe_audio(args.audio_file)

if __name__ == "__main__":
    main()
