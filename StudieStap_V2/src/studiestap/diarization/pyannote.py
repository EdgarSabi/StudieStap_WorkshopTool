"""Sprekerdiarizatie met pyannote: WIE spreekt WANNEER.

Uitvoer is `Diarization`: de ruwe intervallen, onbewerkt. Als twee sprekers
tegelijk actief zijn, staan er twee overlappende intervallen in. Er worden hier
geen rollen, vriendelijke namen of "hoofdspreker" verzonnen.

Later een andere backend gebruiken? Schrijf een klasse met dezelfde methode
`diarize(wav_path) -> Diarization` en zet hem in `BACKENDS` onderaan.
"""
from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Optional

from ..models import Diarization, SpeakerInterval, StudieStapError
from ..settings import DiarizationSettings, get_hf_token


class PyannoteDiarizer:
    name = "pyannote"

    def __init__(self, settings: DiarizationSettings, pipeline=None):
        """`pipeline` is voor tests (nep-pipeline). Normaal wordt het echte model geladen."""
        self.settings = settings
        self._pipeline = pipeline if pipeline is not None else self._load_pipeline()

    def _load_pipeline(self):
        try:
            import torch
            from pyannote.audio import Pipeline
        except ImportError as e:
            raise StudieStapError(
                "pyannote.audio is niet geinstalleerd.",
                hint="Installeer de modelpakketten: pip install -e \".[models]\"",
            ) from e
        token = get_hf_token()  # mag None zijn als het model lokaal gecachet is
        try:
            try:
                pipeline = Pipeline.from_pretrained(self.settings.model, token=token)
            except TypeError:  # oudere pyannote-versies heten dit argument anders
                pipeline = Pipeline.from_pretrained(self.settings.model, use_auth_token=token)
        except Exception as e:
            raise StudieStapError(
                f"Diarizatiemodel '{self.settings.model}' kon niet worden geladen ({type(e).__name__}).",
                hint="Staat het model in de lokale cache (zet dan huggingface.offline: true), "
                     "of is HF_TOKEN gezet in .env en zijn de modelvoorwaarden geaccepteerd?",
            ) from e
        if pipeline is None:  # pyannote geeft soms None i.p.v. een fout bij ontbrekende toegang
            raise StudieStapError(
                f"Diarizatiemodel '{self.settings.model}' gaf geen pipeline terug.",
                hint="Meestal: ongeldig token of de gebruikersvoorwaarden van het model zijn niet geaccepteerd.",
            )
        pipeline.to(torch.device(self.settings.device))
        return pipeline

    def diarize(self, wav_path: str | Path) -> Diarization:
        from ..audio.loader import load_wav_waveform

        waveform, rate = load_wav_waveform(wav_path)
        kwargs = {}
        if self.settings.min_speakers is not None:
            kwargs["min_speakers"] = self.settings.min_speakers
        if self.settings.max_speakers is not None:
            kwargs["max_speakers"] = self.settings.max_speakers

        started = time.time()
        try:
            output = self._pipeline({"waveform": waveform, "sample_rate": rate}, **kwargs)
        except Exception as e:
            raise StudieStapError(f"Diarizatie is mislukt ({type(e).__name__}: {e}).") from e
        return self._to_result(output, time.time() - started)

    def _to_result(self, output, runtime: float) -> Diarization:
        # pyannote 4 geeft een object met .speaker_diarization (mag overlap bevatten);
        # pyannote 3 geeft direct de Annotation.
        annotation = getattr(output, "speaker_diarization", output)
        intervals = [
            SpeakerInterval(speaker=str(label), start=float(seg.start), end=float(seg.end))
            for seg, _track, label in annotation.itertracks(yield_label=True)
        ]
        intervals.sort(key=lambda i: (i.start, i.end, i.speaker))
        return Diarization(
            backend=self.name,
            model=self.settings.model,
            settings=asdict(self.settings),
            runtime_seconds=round(runtime, 2),
            intervals=intervals,
        )


# Later een andere backend? Voeg hem hier toe (naam in config.yaml -> klasse).
BACKENDS: dict[str, Callable[..., object]] = {"pyannote": PyannoteDiarizer}


def get_diarizer(settings: DiarizationSettings):
    try:
        backend = BACKENDS[settings.backend]
    except KeyError:
        raise StudieStapError(f"Onbekende diarizatie-backend '{settings.backend}'.",
                              hint=f"Beschikbaar: {', '.join(BACKENDS)}.")
    return backend(settings)
