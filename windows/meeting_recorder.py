"""
Meeting recorder for Windows.

Captures the system output (WASAPI loopback = what other meeting participants
say, played through your speakers) AND your microphone (your own voice) at the
same time, then mixes them into a single 16 kHz mono track suitable for Whisper.

The two sources are recorded in separate threads (soundcard's ``record`` blocks
until enough frames are available, so a single loop cannot read both without
drop-outs). On stop, the two streams are aligned by length and summed.
"""
import threading
import time
import wave

import numpy as np
import soundcard as sc

SAMPLE_RATE = 16000  # Whisper expects 16 kHz mono
_CHUNK = 1600        # ~0.1s per read


class _SourceThread(threading.Thread):
    """Continuously records one audio source into a list of float32 chunks."""

    def __init__(self, microphone, name):
        super().__init__(daemon=True)
        self.microphone = microphone
        self.name = name
        self._stop = threading.Event()
        self.chunks = []
        self.error = None
        self.peak = 0.0  # most recent chunk peak, for a simple level meter

    def run(self):
        try:
            with self.microphone.recorder(samplerate=SAMPLE_RATE, channels=1) as rec:
                while not self._stop.is_set():
                    data = rec.record(numframes=_CHUNK)  # (n, 1) float32
                    mono = data[:, 0].astype(np.float32, copy=False)
                    self.chunks.append(mono)
                    if mono.size:
                        self.peak = float(np.abs(mono).max())
        except Exception as e:  # pragma: no cover - hardware dependent
            self.error = str(e)

    def stop(self):
        self._stop.set()

    def audio(self):
        if not self.chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(self.chunks)


class MeetingRecorder:
    """Records system loopback + (optionally) microphone and mixes them."""

    def __init__(self, include_mic=True):
        self.include_mic = include_mic
        self._loopback_thread = None
        self._mic_thread = None
        self._start_time = None

    def start(self):
        speaker = sc.default_speaker()
        loopback = sc.get_microphone(id=str(speaker.name), include_loopback=True)
        self._loopback_thread = _SourceThread(loopback, "loopback")
        self._loopback_thread.start()

        if self.include_mic:
            try:
                mic = sc.default_microphone()
                if mic is not None:
                    self._mic_thread = _SourceThread(mic, "mic")
                    self._mic_thread.start()
            except Exception:
                self._mic_thread = None

        self._start_time = time.time()

    @property
    def elapsed(self):
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    @property
    def level(self):
        """Combined recent peak level in [0, 1] for a UI meter."""
        lvl = 0.0
        if self._loopback_thread:
            lvl = max(lvl, self._loopback_thread.peak)
        if self._mic_thread:
            lvl = max(lvl, self._mic_thread.peak)
        return min(1.0, lvl)

    def stop(self):
        """Stop recording and return the mixed mono float32 audio (16 kHz)."""
        if self._loopback_thread:
            self._loopback_thread.stop()
        if self._mic_thread:
            self._mic_thread.stop()

        if self._loopback_thread:
            self._loopback_thread.join()
        if self._mic_thread:
            self._mic_thread.join()

        loopback_audio = (
            self._loopback_thread.audio() if self._loopback_thread else np.zeros(0, np.float32)
        )
        mic_audio = self._mic_thread.audio() if self._mic_thread else np.zeros(0, np.float32)

        if mic_audio.size and loopback_audio.size:
            n = min(loopback_audio.size, mic_audio.size)
            mixed = loopback_audio[:n] + mic_audio[:n]
        elif mic_audio.size:
            mixed = mic_audio
        else:
            mixed = loopback_audio

        # Prevent clipping distortion: scale down only if the sum overshoots.
        if mixed.size:
            peak = float(np.abs(mixed).max())
            if peak > 1.0:
                mixed = mixed / peak

        return mixed.astype(np.float32, copy=False)

    def errors(self):
        errs = []
        if self._loopback_thread and self._loopback_thread.error:
            errs.append(f"System audio: {self._loopback_thread.error}")
        if self._mic_thread and self._mic_thread.error:
            errs.append(f"Microphone: {self._mic_thread.error}")
        return errs


def save_wav(audio_float32, path, samplerate=SAMPLE_RATE):
    """Write a float32 [-1, 1] mono array to a 16-bit PCM WAV file."""
    clipped = np.clip(audio_float32, -1.0, 1.0)
    pcm16 = (clipped * 32767.0).astype(np.int16)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(samplerate)
        w.writeframes(pcm16.tobytes())
    return path
