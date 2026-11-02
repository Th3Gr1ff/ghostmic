import threading
import time
from collections import deque


class Transcriber:
    def __init__(self, model_size="medium", device="cuda", compute_type=None):
        self.model_size = model_size
        self.device = device
        if compute_type is None:
            self.compute_type = "float16" if device == "cuda" else "int8"
        else:
            self.compute_type = compute_type
        self.model = None
        self._transcript_lines = deque(maxlen=500)
        self._lock = threading.Lock()
        self._full_text = ""

    def load_model(self):
        from faster_whisper import WhisperModel
        try:
            self.model = WhisperModel(
                self.model_size, device=self.device, compute_type=self.compute_type
            )
        except Exception:
            self.model = WhisperModel(
                self.model_size, device="cpu", compute_type="int8"
            )
            self.device = "cpu"
            self.compute_type = "int8"

    def transcribe_chunk(self, audio_np):
        if self.model is None:
            return ""

        segments, info = self.model.transcribe(
            audio_np,
            beam_size=5,
            language=None,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200,
            ),
        )

        text_parts = []
        for seg in segments:
            text = seg.text.strip()
            if text:
                text_parts.append(text)

        combined = " ".join(text_parts)
        if combined:
            with self._lock:
                self._transcript_lines.append(combined)
                self._full_text += " " + combined

        return combined

    def get_transcript(self, last_n=None):
        with self._lock:
            if last_n:
                lines = list(self._transcript_lines)[-last_n:]
                return " ".join(lines)
            return self._full_text.strip()

    def get_recent(self, n=10):
        with self._lock:
            lines = list(self._transcript_lines)[-n:]
            return "\n".join(lines)
