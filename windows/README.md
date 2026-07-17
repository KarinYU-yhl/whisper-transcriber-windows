# Whisper Transcriber (Windows)

A local speech-to-text desktop app for Windows. Transcribe audio/video files or
record and transcribe **Teams (or any app) meetings** — everything runs on your
machine, nothing is uploaded.

This is a Windows port of a macOS MLX Whisper app. The Apple-only MLX engine is
replaced by **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)
(CTranslate2)**, which runs on Windows **CPU** or **NVIDIA CUDA GPU** and selects
the device automatically.

---

## Highlights

- **File transcription**: drag & drop or browse; batch processing supported.
- **Meeting recording**: capture system audio (other participants) + your
  microphone (you), then auto-transcribe.
- **Timestamped output**: writes a `.txt` (with time ranges) and a `.srt`
  subtitle file next to each input.
- **No FFmpeg install needed**: audio decoding is handled by the bundled PyAV.
- **CPU or GPU**: uses NVIDIA CUDA when available, otherwise CPU (int8).
- **Offline/corporate friendly**: local models, system trust store, cache manager.

---

## Quick start (run from source)

> Works on Python 3.9 – 3.14 (`ctranslate2` ships a `cp314` wheel).

```powershell
cd windows

# Create and activate a virtual environment
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Launch the GUI
python gui.py
```

On the first transcription the selected model is downloaded from Hugging Face
(a few hundred MB up to ~3 GB) and cached for later use.

### Command line

```powershell
python transcribe.py "C:\path\to\audio.mp3" --model large-v3-turbo --language en
```

- `--model`: `tiny` / `base` / `small` / `medium` / `large-v3` / `large-v3-turbo`,
  or a Hugging Face repo id, or a local model folder path.
- `--language`: language code (e.g. `en`, `ja`, `zh`); omit for auto-detection.

Output is written next to the input as `<name>.txt` (timestamped) and
`<name>.srt` (subtitles).

---

## Record and transcribe a Teams meeting

The GUI has a **● Record Meeting** button:

1. Join your Teams meeting.
2. Pick a **Model** and **Language** in the app.
3. Click **● Record Meeting** — the button turns red and shows the elapsed time
   and a level meter.
4. When the meeting ends, click **■ Stop & Transcribe** — the app saves the
   recording and transcribes it automatically.

Two sources are captured and mixed automatically:

- **System audio (WASAPI loopback)**: what Teams plays through your speakers/
  headset, i.e. the **other participants**.
- **Your microphone**: your **own voice**.

Recordings and transcripts are saved to
`C:\Users\<you>\WhisperMeetings\meeting_YYYYMMDD_HHMMSS.{wav,txt,srt}`.

Tips:

- Keep the app running for the whole meeting; speakers or headphones both work.
- Long meetings use some RAM (16 kHz mono, ~230 MB/hour × 2 sources); 1–2 hour
  meetings are fine.

---

## Output formats

- **`.txt`** — one line per segment, prefixed with a time range, e.g.
  `[00:18:05.900 --> 00:18:08.900] meeting content`.
- **`.srt`** — standard SubRip subtitles, usable directly as captions.

---

## GPU acceleration (optional)

- With an **NVIDIA GPU + CUDA runtime**, the app uses the GPU automatically
  (`float16`) for a large speed-up. See the
  [faster-whisper GPU notes](https://github.com/SYSTRAN/faster-whisper#gpu)
  for cuBLAS/cuDNN setup.
- Without a GPU it falls back to CPU (`int8`). The current device is shown next
  to **Compute:** in the UI.

---

## Build a shareable package

```powershell
cd windows
.\.venv\Scripts\Activate.ps1
python build.py
```

The result is `dist\WhisperTranscriber\WhisperTranscriber.exe` (onedir, **no
Python required to run**).

### Make a zip to share with colleagues

```powershell
Copy-Item .\USER_GUIDE.md .\dist\WhisperTranscriber\USER_GUIDE.txt
Compress-Archive -Path .\dist\WhisperTranscriber -DestinationPath .\dist\WhisperTranscriber_v1.0.27.zip -Force
```

Send `WhisperTranscriber_v1.0.27.zip` (~90 MB) to a colleague:
**unzip → double-click `WhisperTranscriber.exe`** — no installation required
(the model downloads on first use).

An end-user guide is available in [`USER_GUIDE.md`](USER_GUIDE.md).

---

## Offline / restricted networks

1. On a machine with internet, open the model page, e.g.
   <https://huggingface.co/Systran/faster-whisper-large-v3/tree/main>
2. Download all files (`config.json`, `model.bin`, `tokenizer.json`,
   `vocabulary.txt`) into a folder.
3. In the app, click the green **Load Local...** and select that folder.

The app bundles `truststore`, so it uses the system certificate store and works
behind corporate proxies / SSL inspection.

---

## Troubleshooting

- **`ctranslate2` install fails**: make sure you are on 64-bit Python; if your
  Python is extremely new with no wheel yet, use 3.11/3.12.
- **First-run download is slow or fails**: a proxy/firewall may block Hugging
  Face — open the model page in a browser first, or use offline mode.
- **Output turns into repeated numbers**: this is Whisper hallucination during
  long silences (already mitigated); prefer `large-v3` / `large-v3-turbo`.

## License

MIT
