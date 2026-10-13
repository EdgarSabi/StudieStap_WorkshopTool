"""Spraak naar tekst met faster-whisper.

Deze module doet precies een ding: audio (16 kHz WAV) -> `Transcript`.
Sprekers, woordtijden en kwaliteit horen hier niet; die zitten in andere modules.

`model_factory` bestaat zodat tests een nep-model kunnen meegeven. Normaal laat
je hem leeg en wordt het echte faster-whisper-model geladen.
"""
from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Optional

from ..models import Segment, StudieStapError, Transcript
from ..settings import TranscriptionSettings


def _load_real_model(s: TranscriptionSettings):
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise StudieStapError(
            "faster-whisper is niet geinstalleerd.",
            hint="Installeer de modelpakketten: pip install -e \".[models]\"",
        ) from e
    try:
        return WhisperModel(s.model_size, device=s.device, compute_type=s.compute_type)
    except Exception as e:  # modeldownload/cache/compute-type: voor de gebruiker te technisch
        raise StudieStapError(
            f"Whisper-model '{s.model_size}' kon niet worden geladen ({type(e).__name__}).",
            hint="Staat het model in de lokale cache of is er internet? Controleer ook device/compute_type in config.yaml.",
        ) from e


def transcribe(
    wav_path: str | Path,
    settings: TranscriptionSettings,
    model_factory: Optional[Callable[[TranscriptionSettings], object]] = None,
) -> Transcript:
    model = (model_factory or _load_real_model)(settings)
    started = time.time()
    try:
        raw_segments, info = model.transcribe(
            str(wav_path),
            language=settings.language,
            beam_size=settings.beam_size,
            condition_on_previous_text=settings.condition_on_previous_text,
            vad_filter=settings.vad_filter,
            word_timestamps=settings.word_timestamps,
        )
        segments = [
            Segment(
                id=i,
                start=float(s.start),
                end=float(s.end),
                text=(s.text or "").strip(),
                avg_logprob=getattr(s, "avg_logprob", None),
                no_speech_prob=getattr(s, "no_speech_prob", None),
                compression_ratio=getattr(s, "compression_ratio", None),
            )
            for i, s in enumerate(raw_segments)  # generator: hier wordt echt getranscribeerd
        ]
    except StudieStapError:
        raise
    except Exception as e:
        raise StudieStapError(
            f"Transcriberen is mislukt ({type(e).__name__}: {e}).",
            hint="Probeer een kortere opname of controleer geheugen en device in config.yaml.",
        ) from e

    return Transcript(
        language=settings.language,
        duration_seconds=float(getattr(info, "duration", 0.0)),
        model=f"faster-whisper/{settings.model_size}",
        settings=asdict(settings),
        runtime_seconds=round(time.time() - started, 2),
        segments=segments,
    )
