"""
pyannote.audio implementation of DiarizationBackend.

This is the ONLY module that imports pyannote. It is also the only one that
knows about HuggingFace tokens and gated models. Keep backend-specific quirks
in here.

`diarize()` is given a 16 kHz mono WAV (run_diarization.py converts to that
with the ffmpeg CLI) and decodes it with the stdlib `wave` module, handing
pyannote a waveform tensor. That deliberately avoids pyannote 4.x's default
torchcodec audio loader, which on Windows needs FFmpeg *shared* DLLs.

Setup (one-time, done by a human — gated model + credentials):
  1. pip install pyannote.audio
  2. On huggingface.co accept the user conditions for BOTH
       pyannote/speaker-diarization-3.1
       pyannote/segmentation-3.0
  3. Create a read token and put it in <repo-root>/.env as:  HF_TOKEN=hf_xxx
"""
import time
import wave
from pathlib import Path
from typing import Optional

from config import DiarizationConfig, get_hf_token
from .base import DiarizationBackend, DiarizationResult, SpeakerTurn


def _load_wav_waveform(wav_path: Path):
    """Read a 16-bit PCM WAV into a (channels, samples) float32 torch tensor.

    We decode the audio ourselves and hand pyannote a waveform, instead of a
    file path, so pyannote never calls torchcodec. torchcodec on Windows needs
    FFmpeg *shared* DLLs; a static ffmpeg.exe (what's on this machine) is not
    enough. run_diarization.py already produced this 16 kHz mono WAV with the
    ffmpeg CLI, so no decoding library is needed here.
    """
    import numpy as np
    import torch

    with wave.open(str(wav_path), "rb") as w:
        if w.getcomptype() != "NONE":
            raise RuntimeError(f"{wav_path.name} is compressed WAV; expected 16-bit PCM.")
        if w.getsampwidth() != 2:
            raise RuntimeError(
                f"{wav_path.name} has {w.getsampwidth() * 8}-bit samples; "
                f"run_diarization.py should produce 16-bit PCM."
            )
        n_channels = w.getnchannels()
        sample_rate = w.getframerate()
        raw = w.readframes(w.getnframes())

    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).T          # (channels, samples)
    else:
        samples = samples[np.newaxis, :]                       # (1, samples)
    return torch.from_numpy(np.ascontiguousarray(samples)), sample_rate


class PyannoteBackend(DiarizationBackend):
    name = "pyannote"

    def __init__(self, config: DiarizationConfig):
        self.config = config

        try:
            import torch
            from pyannote.audio import Pipeline
        except ImportError as e:
            raise ImportError(
                "pyannote.audio is not installed. Run:  pip install pyannote.audio"
            ) from e

        token = get_hf_token()
        if not token:
            raise RuntimeError(
                "No HuggingFace token found. Put HF_TOKEN=... in <repo-root>/.env "
                "(see this file's docstring for the full setup)."
            )

        try:
            # pyannote.audio >= 3.3 renamed use_auth_token -> token; keep both working.
            try:
                self._pipeline = Pipeline.from_pretrained(config.hf_model, token=token)
            except TypeError:
                self._pipeline = Pipeline.from_pretrained(config.hf_model, use_auth_token=token)
        except Exception as e:
            raise RuntimeError(
                f"Could not load '{config.hf_model}'. If this is a 401/403 or mentions "
                f"access/gated: accept the user conditions for BOTH "
                f"pyannote/speaker-diarization-3.1 AND pyannote/segmentation-3.0 on "
                f"huggingface.co with the account this token belongs to. "
                f"Original error: {e}"
            ) from e

        if self._pipeline is None:
            # from_pretrained returns None (not raises) on an auth/licence problem
            raise RuntimeError(
                f"Pipeline.from_pretrained('{config.hf_model}') returned None — this "
                f"means the token is invalid or the model licence has not been accepted."
            )

        self._pipeline.to(torch.device(config.device))

    def diarize(
        self,
        audio_path: Path,
        *,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
    ) -> DiarizationResult:
        kwargs = {}
        if min_speakers is not None:
            kwargs["min_speakers"] = min_speakers
        if max_speakers is not None:
            kwargs["max_speakers"] = max_speakers

        waveform, sample_rate = _load_wav_waveform(Path(audio_path))

        start = time.time()
        output = self._pipeline({"waveform": waveform, "sample_rate": sample_rate}, **kwargs)
        runtime = time.time() - start

        # pyannote 4.x returns a DiarizeOutput (with .speaker_diarization);
        # pyannote 3.x returns the Annotation directly.
        annotation = getattr(output, "speaker_diarization", output)

        turns = [
            SpeakerTurn(start=float(segment.start), end=float(segment.end), speaker=str(label))
            for segment, _track, label in annotation.itertracks(yield_label=True)
        ]
        turns.sort(key=lambda t: (t.start, t.end))

        return DiarizationResult(
            turns=turns,
            backend=self.name,
            model=self.config.hf_model,
            settings={
                "device": self.config.device,
                "min_speakers": min_speakers,
                "max_speakers": max_speakers,
            },
            runtime_seconds=round(runtime, 2),
        )
