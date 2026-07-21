# Whisper Transcriber

A local, offline speech-to-text desktop app for **Windows and macOS**.
Transcribe audio/video files or record and transcribe a meeting — everything
runs on your machine and nothing is uploaded.

Powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
(CTranslate2), using the public `Systran/faster-whisper-*` models. On Windows it
runs on **CPU** or **NVIDIA CUDA GPU** with automatic device selection; on macOS
it runs on the **CPU**.

## Features

- Transcribe audio/video files (drag & drop, batch supported)
- Record a meeting (system audio + your microphone) and auto-transcribe
- Timestamped `.txt` and `.srt` subtitle output
- No FFmpeg required (audio decoding via bundled PyAV)
- Offline / corporate-network friendly (local models, system trust store)

## Getting started

Pick your platform:

### Windows — [`windows/`](windows/)

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

### macOS — [`macos/`](macos/)

- **Run / build instructions:** [`macos/README.md`](macos/README.md)
- **End-user guide:** [`macos/USER_GUIDE.md`](macos/USER_GUIDE.md)
- **Prebuilt installer (.dmg):** built automatically by the
  [Build macOS installer](../../actions/workflows/build-macos.yml) GitHub Action
  (no Mac required to produce it). Download the artifact, or publish a release by
  pushing a `mac-v*` tag.

```bash
cd macos
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python gui.py
```

> The macOS build uses the public `Systran/faster-whisper-*` models, which fixes
> the `401 / Repository Not Found` error from the old MLX (`mlx-community/*`)
> models.

## License

MIT
