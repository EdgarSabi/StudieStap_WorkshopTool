"""Woorduitlijning met WhisperX op reeds getranscribeerde Whisper-segmenten.

WhisperX doet hier GEEN nieuwe transcriptie: we geven de bestaande segmenten
(tekst + begin/eind) mee en het wav2vec2-alignmentmodel zoekt per woord de tijd.

Status (altijd vastgelegd):
  succeeded    alle woorden hebben een begin- en eindtijd
  partial      sommige woorden of segmenten niet
  unavailable  whisperx/model/taal niet beschikbaar -> we gaan door op segmentniveau
  failed       alignment crashte of gaf een onbruikbaar resultaat

`aligner` is voor tests: een functie (segmenten, wav_path) -> lijst dicts met "words".
"""
from __future__ import annotations

import importlib.util
import time
from pathlib import Path
from typing import Callable, Optional

from ..models import (AlignedSegment, StepStatus, Transcript, Word, WordAlignment)
from ..settings import AlignmentSettings


def whisperx_installed() -> bool:
    return importlib.util.find_spec("whisperx") is not None


class _Unavailable(Exception):
    pass


def _whisperx_aligner(language: str, device: str):
    """Laad het alignmentmodel en geef (aligner_functie, modelnaam) terug."""
    if not whisperx_installed():
        raise _Unavailable("whisperx is niet geinstalleerd (pip install -e \".[align]\").")
    import whisperx
    try:
        from whisperx.alignment import DEFAULT_ALIGN_MODELS_HF, DEFAULT_ALIGN_MODELS_TORCH
        if language not in DEFAULT_ALIGN_MODELS_HF and language not in DEFAULT_ALIGN_MODELS_TORCH:
            raise _Unavailable(f"WhisperX heeft geen alignmentmodel voor taal '{language}'.")
        model_name = DEFAULT_ALIGN_MODELS_HF.get(language) or DEFAULT_ALIGN_MODELS_TORCH.get(language)
    except ImportError:
        model_name = None  # andere whisperx-versie: we laten load_align_model beslissen
    try:
        model, metadata = whisperx.load_align_model(language_code=language, device=device)
    except Exception as e:
        raise _Unavailable(f"Alignmentmodel kon niet worden geladen ({type(e).__name__}).") from e

    def align(segments: list[dict], wav_path: str) -> list[dict]:
        audio = whisperx.load_audio(str(wav_path))
        out = whisperx.align(segments, model, metadata, audio, device, return_char_alignments=False)
        return out["segments"]

    return align, model_name


def _timed(w: Word) -> bool:
    return w.start is not None and w.end is not None


def align_words(
    transcript: Transcript,
    wav_path: str | Path,
    settings: AlignmentSettings,
    aligner: Optional[Callable[[list[dict], str], list[dict]]] = None,
) -> WordAlignment:
    started = time.time()
    language = transcript.language
    model_name = None
    base = dict(language=language)

    if not transcript.segments:
        return WordAlignment(StepStatus.SUCCEEDED, "Geen segmenten om uit te lijnen.", **base)

    try:
        if aligner is None:
            aligner, model_name = _whisperx_aligner(language, settings.device)
    except _Unavailable as e:
        return WordAlignment(StepStatus.UNAVAILABLE,
                             f"{e} Doorgaan op segmentniveau, zonder woordnauwkeurige claims.", **base)

    payload = [{"start": s.start, "end": s.end, "text": s.text} for s in transcript.segments]
    try:
        aligned = aligner(payload, str(wav_path))
    except Exception as e:
        return WordAlignment(StepStatus.FAILED,
                             f"Woorduitlijning mislukt ({type(e).__name__}: {e}). Doorgaan op segmentniveau.",
                             model=model_name, runtime_seconds=round(time.time() - started, 2), **base)

    # WhisperX kan een segment in zinnen splitsen: het aantal uitvoersegmenten hoeft dus niet gelijk te zijn.
    # Elk uitvoersegment gaat terug naar het invoersegment waarmee het de meeste tijd overlapt.
    words_by_id: dict[int, list[Word]] = {s.id: [] for s in transcript.segments}
    for al in aligned:
        a0, a1 = al.get("start"), al.get("end")
        if a0 is None or a1 is None:
            return WordAlignment(StepStatus.FAILED, "Aligner gaf een segment zonder tijden terug; niet te koppelen. "
                                 "Doorgaan op segmentniveau.", model=model_name,
                                 runtime_seconds=round(time.time() - started, 2), **base)
        best = max(transcript.segments, key=lambda s: min(a1, s.end) - max(a0, s.start))
        if min(a1, best.end) - max(a0, best.start) <= 0:
            return WordAlignment(StepStatus.FAILED, "Een uitgelijnd segment valt buiten alle invoersegmenten; niet te koppelen. "
                                 "Doorgaan op segmentniveau.", model=model_name,
                                 runtime_seconds=round(time.time() - started, 2), **base)
        words_by_id[best.id] += [Word(text=w.get("word", ""), start=w.get("start"), end=w.get("end"),
                                      score=w.get("score")) for w in al.get("words", [])]

    result_segments: list[AlignedSegment] = []
    for seg in transcript.segments:
        words = words_by_id[seg.id]
        timed = sum(_timed(w) for w in words)
        if not seg.text.strip():
            status = StepStatus.SUCCEEDED
        elif not words or timed == 0:
            status = StepStatus.FAILED
        elif timed < len(words):
            status = StepStatus.PARTIAL
        else:
            status = StepStatus.SUCCEEDED
        result_segments.append(AlignedSegment(segment_id=seg.id, words=words, status=status))

    statuses = {s.status for s in result_segments}
    if statuses <= {StepStatus.SUCCEEDED}:
        overall, msg = StepStatus.SUCCEEDED, "Alle woorden hebben een tijd."
    elif statuses == {StepStatus.FAILED}:
        overall, msg = StepStatus.FAILED, "Geen enkel segment kon woordtijden krijgen."
    else:
        overall = StepStatus.PARTIAL
        n_bad = sum(s.status != StepStatus.SUCCEEDED for s in result_segments)
        msg = f"{n_bad} van {len(result_segments)} segmenten niet (volledig) uitgelijnd."

    return WordAlignment(overall, msg, model=model_name, runtime_seconds=round(time.time() - started, 2),
                         segments=result_segments, **base)
