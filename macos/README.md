# Whisper Transcriber (macOS)

A local speech-to-text desktop app for macOS. Transcribe audio/video files, or
record and transcribe a meeting — everything runs on your Mac, nothing is
uploaded.

This macOS build uses **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)
(CTranslate2)** with the **public `Systran/faster-whisper-*` models**. Those
models need no Hugging Face login, which fixes the
`401 Client Error / Repository Not Found` you get with the old MLX
(`mlx-community/whisper-large-v3`) models.

---

## Highlights

- **File transcription**: drag & drop or browse; batch processing supported.
- **Timestamped output**: writes a `.txt` (with time ranges) and a `.srt`
  subtitle file next to each input.
- **Meeting recording**: records your microphone; also captures system audio if
  a virtual loopback device (BlackHole) is installed.
- **No FFmpeg install needed**: audio decoding is handled by the bundled PyAV.
- **Offline/corporate friendly**: local models, system trust store, cache manager.
- **CPU inference (int8)** — runs on both Apple Silicon and Intel Macs.

---

## Getting the app (no Python required)

You do **not** need to build it yourself. A prebuilt installer is produced by
GitHub Actions:

1. Go to the repository's **Actions → Build macOS installer**.
2. Download the `WhisperTranscriber-macOS` artifact (a `.dmg`), or grab it from
   the **Releases** page if a `mac-v*` tag was published.
3. Open the `.dmg`, drag **WhisperTranscriber** into **Applications**, done.

> First launch: right-click the app → **Open** (Gatekeeper shows an "unidentified
> developer" prompt because the app is not notarized). See `USER_GUIDE.md`.

---

## Run from source

> Requires Python 3.9 – 3.12.

```bash
cd macos

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python gui.py
```

On the first transcription the selected model is downloaded from Hugging Face
(a few hundred MB up to ~3 GB) and cached for later use.

### Command line

```bash
python transcribe.py "/path/to/audio.mp3" --model large-v3-turbo --language en
```

- `--model`: `tiny` / `base` / `small` / `medium` / `large-v3` / `large-v3-turbo`,
  a Hugging Face repo id, or a local model folder path.
- `--language`: language code (e.g. `en`, `ja`, `zh`); omit for auto-detection.

Output is written next to the input as `<name>.txt` (timestamped) and
`<name>.srt` (subtitles).

---

## Build the installer yourself (on a Mac)

```bash
cd macos
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python build.py
```

Produces:

- `dist/WhisperTranscriber.app` — the application bundle.
- `dist/WhisperTranscriber-1.0.27.dmg` — a drag-to-Applications installer.

> PyInstaller cannot cross-compile: this must run on macOS. If you don't have a
> Mac, use the GitHub Actions workflow above instead.

---

## Recording meetings on macOS

macOS has no built-in way to record system audio. The app always records your
**microphone**. To also capture the **other participants**, install the free
[**BlackHole**](https://github.com/ExistentialAudio/BlackHole) driver and route
meeting audio through it (via an Aggregate / Multi-Output device). The app
auto-detects a BlackHole/Soundflower device and mixes it in.

Recordings and transcripts are saved to
`~/WhisperMeetings/meeting_YYYYMMDD_HHMMSS.{wav,txt,srt}`.

---

## Output formats

- **`.txt`** — one line per segment with a time range, e.g.
  `[00:18:05.900 --> 00:18:08.900] meeting content`.
- **`.srt`** — standard SubRip subtitles, usable directly as captions.

---

## Offline / restricted networks

1. On a machine with internet, open a model page, e.g.
   <https://huggingface.co/Systran/faster-whisper-large-v3/tree/main>
2. Download `config.json`, `model.bin`, `tokenizer.json`, `vocabulary.txt` into
   a folder.
3. In the app, click the green **Load Local...** and select that folder.

The app bundles `truststore`, so it uses the system certificate store and works
behind corporate proxies / SSL inspection.

---

## License

MIT
