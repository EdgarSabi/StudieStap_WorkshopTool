"""Veilige audio-invoer.

Doel: een willekeurig lokaal MP3/WAV-bestand controleren en omzetten naar een
16 kHz mono WAV-werkkopie voor de modellen. Het originele bestand wordt alleen
GELEZEN: nooit gewijzigd, verplaatst of overschreven.

Waarom altijd omzetten? Pyannote en WhisperX willen 16 kHz mono; met een eigen
conversie via ffmpeg weten we zeker welk formaat de modellen krijgen.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import wave
from pathlib import Path

from ..models import AudioInfo, StudieStapError

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a"}
WORKING_WAV_NAME = "audio_16k_mono.wav"


def validate_audio_path(path: str | Path) -> Path:
    """Controleer dat het bestand bestaat, niet leeg is en een ondersteund formaat heeft."""
    p = Path(path)
    if not p.exists():
        raise StudieStapError(f"Audiobestand niet gevonden: {p}",
                              hint="Controleer het pad. Zet het pad tussen aanhalingstekens als het spaties bevat.")
    if not p.is_file():
        raise StudieStapError(f"Dit is geen bestand: {p}", hint="Geef het pad naar een MP3- of WAV-bestand.")
    if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise StudieStapError(
            f"Niet-ondersteund audioformaat '{p.suffix}'.",
            hint=f"Ondersteund: {', '.join(sorted(SUPPORTED_EXTENSIONS))}.",
        )
    if p.stat().st_size == 0:
        raise StudieStapError(f"Het audiobestand is leeg: {p}")
    return p


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _find_ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise StudieStapError(
            "ffmpeg is niet gevonden.",
            hint="Installeer ffmpeg (bijv. 'winget install Gyan.FFmpeg') en start de terminal opnieuw.",
        )
    return exe


def wav_duration_seconds(wav_path: Path) -> float:
    with wave.open(str(wav_path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def prepare_audio(source: str | Path, work_dir: Path) -> AudioInfo:
    """Valideer `source` en schrijf een 16 kHz mono 16-bit WAV naar work_dir."""
    src = validate_audio_path(source)
    ffmpeg = _find_ffmpeg()
    work_dir.mkdir(parents=True, exist_ok=True)
    wav_path = work_dir / WORKING_WAV_NAME

    cmd = [ffmpeg, "-y", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000",
           "-sample_fmt", "s16", str(wav_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not wav_path.exists():
        raise StudieStapError(
            f"ffmpeg kon dit bestand niet lezen: {src.name}",
            hint="Het bestand is mogelijk beschadigd of geen echte audio. Probeer het opnieuw te exporteren.",
        )
    duration = wav_duration_seconds(wav_path)
    if duration <= 0:
        raise StudieStapError(f"Het audiobestand bevat geen geluid (duur 0 s): {src.name}")

    return AudioInfo(
        source_path=str(src.resolve()),
        sha256=sha256_of_file(src),
        size_bytes=src.stat().st_size,
        duration_seconds=round(duration, 3),
        source_format=src.suffix.lower().lstrip("."),
        working_wav=str(wav_path),
    )


def load_wav_waveform(wav_path: str | Path):
    """Lees een 16-bit PCM WAV als torch-tensor (kanalen, samples) + samplerate.

    We decoderen zelf en geven pyannote een waveform in plaats van een pad, zodat
    pyannote geen torchcodec/FFmpeg-DLL's nodig heeft (dat gaf problemen op Windows).
    """
    import numpy as np
    import torch

    with wave.open(str(wav_path), "rb") as w:
        if w.getsampwidth() != 2 or w.getcomptype() != "NONE":
            raise StudieStapError("Interne werkkopie heeft niet het verwachte 16-bit PCM-formaat.")
        channels, rate, raw = w.getnchannels(), w.getframerate(), w.readframes(w.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    samples = samples.reshape(-1, channels).T if channels > 1 else samples[np.newaxis, :]
    return torch.from_numpy(np.ascontiguousarray(samples)), rate
