"""
Command-line transcription tool for macOS.

Uses faster-whisper (CTranslate2) with the public Systran/faster-whisper-*
models (no Hugging Face login required), instead of the old Apple MLX engine.
On macOS inference runs on the CPU (int8). Audio decoding is handled by PyAV
(bundled FFmpeg), so a system-wide FFmpeg install is not required.

Usage:
    python transcribe.py <audio_file> [--model large-v3] [--language ja]
"""
import argparse
import os
import sys
import time

# The xet download backend can fail behind corporate proxies
# ("Byte range not sequential"); the classic HTTP download is more robust.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import logging

import truststore

# Use the system trust store so corporate proxies / SSL inspection work.
truststore.inject_into_ssl()

# Silence the harmless "unauthenticated requests to the HF Hub" warning.
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)


def detect_device():
    """Return (device, compute_type) based on available hardware.

    Tries CUDA first, falls back to CPU. int8 keeps CPU usage practical,
    while float16 is the fast path on GPU.
    """
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def transcribe_audio(audio_path, model_name="large-v3", language=None):
    if not os.path.exists(audio_path):
        print(f"Error: File '{audio_path}' not found.", file=sys.stderr)
        return 1

    from faster_whisper import WhisperModel

    device, compute_type = detect_device()
    print(f"Loading model '{model_name}' on {device} ({compute_type})...")

    model = WhisperModel(model_name, device=device, compute_type=compute_type)

    print(f"Transcribing '{audio_path}'...")
    start = time.time()

    segments, info = model.transcribe(
        audio_path,
        language=language,  # None -> auto-detect
        beam_size=5,
        vad_filter=True,
        # Avoid hallucinated repetition (e.g. "7, 8, 9..." during silence).
        condition_on_previous_text=False,
        no_repeat_ngram_size=3,
        no_speech_threshold=0.6,
    )

    if language is None:
        print(f"Detected language: {info.language} (p={info.language_probability:.2f})")

    from output_formats import write_outputs

    # segments is a generator; iterating drives the actual decoding.
    segments_data = []
    for segment in segments:
        segments_data.append((float(segment.start), float(segment.end), segment.text))
        print(f"[{segment.start:6.1f}s -> {segment.end:6.1f}s] {segment.text.strip()}")

    duration = time.time() - start

    base_name = os.path.splitext(audio_path)[0]
    txt_path, srt_path = write_outputs(base_name, segments_data)

    print(f"\nSaved:\n  {txt_path}\n  {srt_path}\n(took {duration:.1f}s)")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio using faster-whisper on Windows (CPU/CUDA)."
    )
    parser.add_argument("audio_file", help="Path to the audio/video file to transcribe.")
    parser.add_argument(
        "--model",
        default="large-v3",
        help="Model size or HF repo or local folder (e.g. tiny, base, small, "
        "medium, large-v3, large-v3-turbo). Default: large-v3",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Language code (e.g. en, ja, zh). Omit for auto-detection.",
    )
    args = parser.parse_args()

    sys.exit(transcribe_audio(args.audio_file, args.model, args.language))


if __name__ == "__main__":
    main()
