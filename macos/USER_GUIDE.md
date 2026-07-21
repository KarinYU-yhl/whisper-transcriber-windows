# Whisper Transcriber (macOS) · User Guide

A local speech-to-text tool that turns audio/video files — or a recorded
meeting — into timestamped text. Everything runs on your own Mac; **no data is
uploaded**.

---

## Quick start (TL;DR)

> **Open the `.dmg` → drag `WhisperTranscriber` into `Applications` → launch it.**
> On the very first launch macOS blocks it (*"Apple could not verify…"*) because
> the app is not notarized. Allow it once via **System Settings → Privacy &
> Security → Open Anyway**, or run
> `xattr -dr com.apple.quarantine /Applications/WhisperTranscriber.app` in
> Terminal. The first transcription downloads the speech model. Full
> instructions below.

---

## 1. Install (no Python required)

1. Double-click `WhisperTranscriber-1.0.27.dmg`.
2. In the window that appears, **drag the `WhisperTranscriber` icon onto the
   `Applications` folder**.
3. Open **Applications** and launch **WhisperTranscriber**.

### First-launch Gatekeeper warning

Because the app is not signed/notarized by Apple, macOS blocks it on first
launch with a message like *"Apple could not verify 'WhisperTranscriber' is free
of malware..."* (only a **Done** button). This is normal for unsigned apps.

On modern macOS (Sequoia 15+) the old "right-click → Open" trick no longer works.
Use one of these instead:

**Option 1 — System Settings (no Terminal):**

1. Click **Done** on the warning.
2. Open **System Settings → Privacy & Security**.
3. Scroll down to the **Security** section — you'll see
   *"WhisperTranscriber" was blocked…* — click **Open Anyway**.
4. Confirm with Touch ID / your password.
5. When the dialog appears again, click **Open**. You only need to do this once.

**Option 2 — Terminal (most reliable):**

Open **Terminal** and run this (removes the download "quarantine" flag):

```bash
xattr -dr com.apple.quarantine /Applications/WhisperTranscriber.app
```

Then double-click the app normally.

No FFmpeg or other software is required.

---

## 2. First use downloads a model (needs internet once)

The first time you transcribe, the app downloads a speech-recognition model
(downloaded once, then cached locally for offline use):

| Model | Size | Notes |
|---|---|---|
| tiny / base | 75 MB / 150 MB | Fastest, lower accuracy, good for trying it out |
| small / medium | 500 MB / 1.5 GB | Middle ground |
| **large-v3-turbo** | ~1.6 GB | **Recommended**: fast and accurate |
| large-v3 | ~3 GB | Most accurate, slower |

> These are the public `Systran/faster-whisper-*` models — no Hugging Face login
> is required, so you will **not** see the old `401 / Repository Not Found`
> error. If your corporate network blocks the download, see "Offline use" below.

---

## 3. Transcribe an existing audio/video file

1. Open the app.
2. Click **Browse** to pick a file, or **drag & drop** files onto the window
   (multiple files = batch processing).
3. Choose a **Model** (recommended: `large-v3-turbo`).
4. Choose the **Language** (`English`, `Japanese`, `Chinese`, ...) or `Auto`.
5. Click **Start Transcription**.
6. When done, results are saved next to the original file with the same name:
   - `filename.txt` — timestamped text
   - `filename.srt` — subtitle file (usable as video captions)

---

## 4. Record and transcribe a meeting

1. Open the app and pick your **Model** and **Language** first.
2. Click **● Record Meeting** to start; the button turns red and shows the
   elapsed time and an audio level meter.
3. When the meeting ends, click **■ Stop & Transcribe**. The app saves the
   recording and transcribes it automatically.

**Microphone permission:** the first time, macOS asks to allow microphone
access — click **OK**. (If you miss it: **System Settings → Privacy & Security →
Microphone** and enable WhisperTranscriber.)

**Capturing the other participants (system audio):** unlike Windows, macOS
cannot record app/system audio on its own. The app records **your microphone**
by default. To also record the **other participants**:

1. Install the free [**BlackHole**](https://github.com/ExistentialAudio/BlackHole)
   audio driver.
2. Create an **Aggregate/Multi-Output device** so meeting audio also goes to
   BlackHole (see BlackHole's guide).
3. The app auto-detects BlackHole and mixes it in.

Files are saved to `~/WhisperMeetings/`:
- `meeting_DATE_TIME.wav` (recording)
- `meeting_DATE_TIME.txt` / `.srt` (text / subtitles)

---

## 5. About the output files

- **`.txt`** — timestamped text, so you can tell when each sentence was said,
  e.g. `[00:18:05.900 --> 00:18:08.900] meeting content`.
- **`.srt`** — standard subtitle format; import it into video software or use it
  as captions.

---

## 6. FAQ

**Q: I got `401 Client Error / Repository Not Found` in the old app.**
A: That was caused by the old MLX model (`mlx-community/whisper-large-v3`), which
now requires login. This build uses the public `Systran/faster-whisper-*` models
instead, so the error is gone.

**Q: The text turns into a string of numbers or repeats itself.**
A: This happens during long silent stretches and has been mitigated. If it still
occurs, use the `large-v3` or `large-v3-turbo` model.

**Q: Transcription is slow.**
A: On macOS the app runs on the CPU, so long audio takes a while. `large-v3-turbo`
is a good speed/accuracy balance.

**Q: Chinese/Japanese recognition is inaccurate.**
A: Set the correct **Language** and use `large-v3-turbo` or `large-v3`.

**Q: Is my audio uploaded anywhere?**
A: No. All processing happens locally; only the initial model download uses the
internet.

---

## 7. Offline / restricted network use

1. On a computer with internet, open the model page, e.g.
   <https://huggingface.co/Systran/faster-whisper-large-v3/tree/main>
2. Download all files (`config.json`, `model.bin`, `tokenizer.json`,
   `vocabulary.txt`) into a folder.
3. In the app, click the green **Load Local...** and select that folder to work
   fully offline.

---

## 8. Managing downloaded models

Click **Manage Cache** to view and delete downloaded models and free up disk
space.

---

For questions, contact the person who provided this tool.
