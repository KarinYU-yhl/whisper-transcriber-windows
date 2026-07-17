# Whisper Transcriber · User Guide

A local speech-to-text tool that turns audio/video files — or the audio of a
**Teams (or any app) meeting** — into timestamped text. Everything runs on your
own PC; **no data is uploaded**.

---

## Quick start (TL;DR)

> **Download the zip → unzip → double-click `WhisperTranscriber.exe`.**
> If a blue **"Windows protected your PC"** dialog appears on first launch, click
> **More info → Run anyway** (the app is not code-signed, so this warning is
> normal and safe). The first transcription downloads the speech model over the
> internet. Full instructions are below.

---

## 1. Install (no Python required)

1. Unzip `WhisperTranscriber.zip` anywhere, e.g. `D:\WhisperTranscriber`.
2. Open the folder and double-click **`WhisperTranscriber.exe`**.
3. (Optional) Right-click `WhisperTranscriber.exe` → **Send to → Desktop
   (create shortcut)** to launch it from your desktop later.

### First-launch SmartScreen warning

Because the app is not code-signed, Windows may show a blue
**"Windows protected your PC"** dialog (Publisher: Unknown). This is normal and
does not mean anything is wrong.

- **To run it:** click the **More info** link in the dialog, then click the
  **Run anyway** button that appears.
- **To avoid the warning entirely:** before unzipping, right-click the downloaded
  `WhisperTranscriber_v1.0.27.zip` → **Properties** → tick **Unblock** → **OK**,
  then unzip. (Or run in PowerShell:
  `Get-ChildItem "<folder>\WhisperTranscriber" -Recurse | Unblock-File`.)

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

> If your corporate network blocks the download, see "Offline use" at the end.

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

## 4. Record and transcribe a Teams meeting

1. Open the app and pick your **Model** and **Language** first.
2. Open and join your Teams meeting.
3. Click **● Record Meeting** to start; the button turns red and shows the
   elapsed time and an audio level meter.
4. When the meeting ends, click **■ Stop & Transcribe**. The app saves the
   recording and transcribes it automatically.

The recording automatically **mixes two audio sources**:

- **Other participants**: what Teams plays through your speakers/headset
  (system audio).
- **You**: your microphone.

Files are saved to `C:\Users\<your-name>\WhisperMeetings\`:
- `meeting_DATE_TIME.wav` (recording)
- `meeting_DATE_TIME.txt` / `.srt` (text / subtitles)

> Tips:
> - Keep the app running for the whole meeting.
> - Speakers or headphones both work — the other side is still captured.
> - Each line starts with a time range, e.g.
>   `[00:18:05.900 --> 00:18:08.900] meeting content`.

---

## 5. About the output files

- **`.txt`** — timestamped text, so you can tell when each sentence was said.
- **`.srt`** — standard subtitle format; import it into video software or use
  it as captions.

---

## 6. FAQ

**Q: The text turns into a string of numbers or repeats itself.**
A: This happens during long silent stretches and has been mitigated. If it still
occurs, use the `large-v3` or `large-v3-turbo` model — they resist this better.

**Q: Transcription is slow.**
A: Without an NVIDIA GPU the app uses the CPU, which is slower (be patient with
long audio). The **Compute:** label in the UI shows whether CPU or GPU is used.

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
