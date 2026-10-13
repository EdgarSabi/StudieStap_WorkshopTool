"""Gedeelde hulpmiddelen voor de tests. Alle testgegevens zijn synthetisch."""
import math
import shutil
import struct
import wave
from pathlib import Path

import pytest

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg niet op PATH")


def make_wav(path: Path, seconds: float = 1.0, rate: int = 48000, channels: int = 2) -> Path:
    """Schrijf een synthetische sinustoon als WAV (geen echte spraak, geen privacy-risico)."""
    n = int(seconds * rate)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            v = int(12000 * math.sin(2 * math.pi * 440 * i / rate))
            frames += struct.pack("<h", v) * channels
        w.writeframes(bytes(frames))
    return path


@pytest.fixture
def wav_file(tmp_path):
    return make_wav(tmp_path / "toon.wav")
