# Whisper Transcriber (Windows)

A local, offline speech-to-text desktop app for Windows. Transcribe audio/video
files or **record and transcribe Teams (or any app) meetings** — everything runs
on your machine and nothing is uploaded.

Powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
(CTranslate2), running on **CPU** or **NVIDIA CUDA GPU** with automatic device
selection.

## Features

- Transcribe audio/video files (drag & drop, batch supported)
- Record a meeting (system audio + your microphone) and auto-transcribe
- Timestamped `.txt` and `.srt` subtitle output
- No FFmpeg required (audio decoding via bundled PyAV)
- Offline / corporate-network friendly (local models, system trust store)

## Getting started

All source code lives in the [`windows/`](windows/) folder.

- **Run / build instructions:** [`windows/README.md`](windows/README.md)
- **End-user guide:** [`windows/USER_GUIDE.md`](windows/USER_GUIDE.md)
- **Prebuilt package:** see the [Releases](../../releases) page — unzip and
  double-click `WhisperTranscriber.exe` (no installation required).

```powershell
cd windows
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python gui.py
```

## License

MIT
