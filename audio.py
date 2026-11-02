import sounddevice as sd
import numpy as np
import threading
import queue
import subprocess
import re


def find_monitor_source():
    """Find the PulseAudio monitor source for system audio capture."""
    try:
        result = subprocess.run(
            ["pactl", "list", "sources", "short"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split("\n"):
            if ".monitor" in line.lower():
                parts = line.split("\t")
                if len(parts) >= 2:
                    return parts[1]
    except Exception:
        pass

    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if "monitor" in d["name"].lower() and d["max_input_channels"] > 0:
            return i
    return None


def find_device_index(pulse_name):
    """Map a PulseAudio source name to a sounddevice index."""
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if pulse_name in d["name"] and d["max_input_channels"] > 0:
            return i
    for i, d in enumerate(devices):
        if "monitor" in d["name"].lower() and d["max_input_channels"] > 0:
            return i
    return None


class AudioCapture:
    def __init__(self, sample_rate=16000, chunk_seconds=3):
        self.sample_rate = sample_rate
        self.chunk_seconds = chunk_seconds
        self.chunk_samples = sample_rate * chunk_seconds
        self._buffer = np.zeros(0, dtype=np.float32)
        self._lock = threading.Lock()
        self._stream = None
        self._running = False
        self.audio_queue = queue.Queue(maxsize=100)

    def _callback(self, indata, frames, time_info, status):
        mono = indata[:, 0] if indata.ndim > 1 else indata.flatten()
        mono = mono.astype(np.float32)
        with self._lock:
            self._buffer = np.concatenate([self._buffer, mono])
            while len(self._buffer) >= self.chunk_samples:
                chunk = self._buffer[: self.chunk_samples].copy()
                self._buffer = self._buffer[self.chunk_samples :]
                try:
                    self.audio_queue.put_nowait(chunk)
                except queue.Full:
                    try:
                        self.audio_queue.get_nowait()
                        self.audio_queue.put_nowait(chunk)
                    except queue.Empty:
                        pass

    def start(self):
        pulse_name = find_monitor_source()
        device_idx = None
        if isinstance(pulse_name, str):
            device_idx = find_device_index(pulse_name)
        elif isinstance(pulse_name, int):
            device_idx = pulse_name

        self._running = True
        self._stream = sd.InputStream(
            device=device_idx,
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=int(self.sample_rate * 0.5),
            callback=self._callback,
        )
        self._stream.start()

    def stop(self):
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def get_chunk(self, timeout=5.0):
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
