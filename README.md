# MLX Whisper Transcriber for macOS

A standalone macOS GUI application for OpenAI's Whisper model, optimized for Apple Silicon using [MLX](https://github.com/ml-explore/mlx).

![App Icon](icon_master.png)

## Quick Start

### 1. Install Homebrew
If you don't have Homebrew installed, open **Terminal** and run:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install FFmpeg
This application requires FFmpeg for audio processing. Run this command in Terminal:
```bash
brew install ffmpeg
```

### 3. Download & Install
1. Go to the [Releases page](https://github.com/necoha/mlx-whisper-mac/releases).
2. Download the latest `MLXWhisperTranscriber.dmg`.
3. Open the DMG file and drag the app to your **Applications** folder.

### 4. Run the App
Open `MLXWhisperTranscriber` from your Applications folder.
*   **Note**: The first time you transcribe, the app will download the necessary model files. This may take a few minutes depending on your internet connection.

---

## Features

*   **Apple Silicon Optimized**: Runs locally on your Mac's GPU/NPU using MLX.
*   **Offline Capable**: Supports loading models from local folders (great for corporate environments).
*   **User Friendly**: Simple GUI with drag-and-drop support.
*   **Language Support**: Auto-detection or manual selection (English, Japanese, etc.).
*   **Progress Tracking**: Real-time logs and progress bar.

## Models

### Automatic Download
By default, the application automatically downloads the selected model from Hugging Face when you first use it. The models are cached locally for future use.

### Manual Download (Offline Mode)
If you are in an environment with restricted internet access (e.g., corporate firewall) or want to manage models manually:

1.  Visit the [Hugging Face repository](https://huggingface.co/mlx-community) for the desired model (e.g., `mlx-community/whisper-large-v3`).
2.  Download all files in the repository (or clone it) to a local folder.
    *   Ensure `config.json`, `model.safetensors` (or `weights.npz`), and `tokenizer.json` are included.
3.  In the app, click the **"Load Local..."** button (green button).
4.  Select the folder where you downloaded the model files.

## For Developers

### Run from Source

1.  **Install uv** (Fast Python package manager):
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Clone and Setup**:
    ```bash
    git clone https://github.com/necoha/mlx-whisper-mac.git
    cd mlx-whisper-mac
    
    # Create virtual environment and install dependencies
    uv venv
    source .venv/bin/activate
    uv pip install -r requirements.txt
    ```

3.  **Run the App**:
    ```bash
    python gui.py
    ```

### Build Standalone App

To package the application into a standard macOS `.app` bundle:

1.  Follow the "Run from Source" steps to set up your environment.
2.  Run the build script:
    ```bash
    python build.py
    ```
3.  The application/DMG will be created in the `dist/` folder.

## Troubleshooting

*   **"FFmpeg not found"**: Make sure you installed it with `brew install ffmpeg`. The app looks in `/opt/homebrew/bin`.
*   **"App is damaged"**: If you see this error, it usually means the app wasn't signed or notarized correctly, or was modified. Try downloading the latest official release.

## Author

**necoha** - [GitHub](https://github.com/necoha)

## License

MIT

