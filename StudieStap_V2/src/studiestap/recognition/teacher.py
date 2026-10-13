"""Docentherkenning: lijkt de stem van deze spreker op de referentieopname van de docent?

Twee dingen worden bewust APART gehouden:
  * identiteit  - MATCH / NO_MATCH / UNKNOWN / NO_REFERENCE   (stemvergelijking)
  * rol         - "docent" of "onbekend"                        (afgeleid)

Een spreker-ID als SPEAKER_00 is dus nooit automatisch "docent" (en niemand
wordt automatisch "leerling" genoemd). Zonder referentieopname krijgt iedereen
NO_REFERENCE. De gelijkenis is een ruwe cosinuswaarde, GEEN kans, en de
drempel (0.35) is een experimentele instelling uit eerder werk.

De kernlogica (`recognize_teacher`) krijgt functies mee om stukjes audio te
embedden, zodat ze zonder echt model te testen is.
"""
from __future__ import annotations

import math
from statistics import median
from typing import Callable, Optional

from ..models import SpeakerInterval, SpeakerRole, StudieStapError
from ..settings import TeacherSettings, get_hf_token

MAX_CLIPS_PER_SPEAKER = 10  # de langste stukken; houdt de rekentijd beperkt


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return 0.0 if na == 0 or nb == 0 else dot / (na * nb)


def exclusive_parts(target: SpeakerInterval, all_intervals: list[SpeakerInterval]) -> list[tuple[float, float]]:
    """Het deel van `target` waarin GEEN andere spreker actief is (om geen mengstem te embedden)."""
    parts = [(target.start, target.end)]
    for other in all_intervals:
        if other.speaker == target.speaker:
            continue
        nxt = []
        for s, e in parts:
            if other.end <= s or other.start >= e:
                nxt.append((s, e))
                continue
            if other.start > s:
                nxt.append((s, other.start))
            if other.end < e:
                nxt.append((other.end, e))
        parts = nxt
    return parts


def no_reference_roles(intervals: list[SpeakerInterval]) -> list[SpeakerRole]:
    return [SpeakerRole(speaker=s, identity_status="NO_REFERENCE", role="onbekend",
                        note="Geen referentieopname van de docent opgegeven.")
            for s in sorted({i.speaker for i in intervals})]


def recognize_teacher(
    intervals: list[SpeakerInterval],
    reference_embedding: list[float],
    embed_clip: Callable[[float, float], Optional[list[float]]],
    settings: TeacherSettings,
) -> list[SpeakerRole]:
    roles = []
    for speaker in sorted({i.speaker for i in intervals}):
        clips = []
        for iv in (i for i in intervals if i.speaker == speaker):
            clips += [p for p in exclusive_parts(iv, intervals) if p[1] - p[0] >= settings.min_clip_seconds]
        clips.sort(key=lambda p: p[1] - p[0], reverse=True)

        sims = []
        for s, e in clips[:MAX_CLIPS_PER_SPEAKER]:
            emb = embed_clip(s, e)
            if emb is not None:  # niet te embedden = onbekend, geen bewijs voor iets
                sims.append(cosine_similarity(reference_embedding, emb))

        if not sims:
            roles.append(SpeakerRole(speaker, "UNKNOWN", "onbekend", None, 0,
                                     f"Geen bruikbaar stuk van minstens {settings.min_clip_seconds} s "
                                     "zonder andere sprekers."))
            continue
        sim = round(median(sims), 4)
        if sim >= settings.similarity_threshold:
            roles.append(SpeakerRole(speaker, "MATCH", "docent", sim, len(sims),
                                     "Stem lijkt op de referentie (experimentele drempel, geen bewezen zekerheid)."))
        else:
            roles.append(SpeakerRole(speaker, "NO_MATCH", "onbekend", sim, len(sims),
                                     "Stem lijkt niet op de referentiedocent; rol (leerling, andere docent...) onbekend."))
    return roles


# ----------------------------------------------------------------- echt model (WeSpeaker)

def _load_wespeaker(settings: TeacherSettings):
    """Laad WeSpeaker. Geef `embed(waveform, rate) -> lijst of None` terug (None = niet te embedden)."""
    try:
        import numpy as np
        import torch
        from pyannote.audio import Inference, Model
    except ImportError as e:
        raise StudieStapError("pyannote.audio is niet geinstalleerd.",
                              hint="Installeer de modelpakketten: pip install -e \".[models]\"") from e

    try:
        model = Model.from_pretrained(settings.embedding_model, token=get_hf_token())
        inference = Inference(model, window="whole", device=torch.device(settings.device))
    except Exception as e:
        raise StudieStapError(
            f"Embeddingmodel '{settings.embedding_model}' kon niet worden geladen ({type(e).__name__}).",
            hint="Lokale cache + huggingface.offline: true, of HF_TOKEN in .env met geaccepteerde voorwaarden.") from e

    def embed(waveform, rate) -> Optional[list[float]]:
        if waveform.numel() == 0:
            return None
        try:
            return np.asarray(inference({"waveform": waveform, "sample_rate": rate})).reshape(-1).tolist()
        except Exception:
            return None

    return embed


def _clip_embedder(wav_path: str, embed) -> Callable[[float, float], Optional[list[float]]]:
    from ..audio.loader import load_wav_waveform

    wave, rate = load_wav_waveform(wav_path)
    return lambda start, end: embed(wave[:, int(start * rate):int(end * rate)], rate)


def build_clip_embedder(wav_path: str, settings: TeacherSettings) -> Callable[[float, float], Optional[list[float]]]:
    """Geef `embed_clip(start, end)` voor een stuk van de opname (ook gebruikt door voice_consistency)."""
    return _clip_embedder(wav_path, _load_wespeaker(settings))


def build_wespeaker_embedder(wav_path: str, reference_wav: str, settings: TeacherSettings):
    """Geef (reference_embedding, embed_clip) terug op basis van pyannote/WeSpeaker."""
    from ..audio.loader import load_wav_waveform

    embed = _load_wespeaker(settings)
    ref_wave, ref_rate = load_wav_waveform(reference_wav)
    reference = embed(ref_wave, ref_rate)
    if reference is None:
        raise StudieStapError("De referentieopname van de docent kon niet worden gebruikt.",
                              hint="Gebruik een opname met duidelijke spraak van alleen de docent.")
    return reference, _clip_embedder(wav_path, embed)
