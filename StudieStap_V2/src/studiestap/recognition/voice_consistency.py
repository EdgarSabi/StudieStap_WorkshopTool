"""Stemconsistentie: past de stem in een segment bij het sprekerlabel dat pyannote gaf?

Optionele diagnostiek. Deze module VERANDERT niets: geen sprekerlabels, geen intervallen,
geen tekst. Ze geeft per segment alleen een waarneming terug; `quality/checks.py` maakt
daar een onzekerheidssignaal van.

Berekening (per opname, geen referentieopname nodig):
  1. Per ruwe spreker: een stemprofiel = gemiddelde embedding van de langste stukken
     zonder andere sprekers (dezelfde stukken als bij docentherkenning).
  2. Per segment met een dominante spreker: embed het stuk van het segment waarin alleen
     die spreker actief is.
  3. Vergelijk dat stuk (cosinus) met het profiel van het eigen label en van de andere
     labels. Stukken die het segment zelf overlappen tellen NIET mee in de profielen,
     zodat een segment zijn eigen profiel niet kan bepalen.

Geen vaste drempel. Een afwijking wordt alleen gemeld als het stuk
  (a) dichter bij een ander label ligt dan bij het eigen label, EN
  (b) minder op het eigen profiel lijkt dan elk eigen referentiestuk zelf (laagste
      score van de eigen stukken tegen het profiel van de overige eigen stukken).
Anders is de uitkomst CONSISTENT of INCONCLUSIVE. Te weinig bewijs -> INCONCLUSIVE.
"""
from __future__ import annotations

from typing import Callable, Optional

from ..models import SegmentSpeakers, SegmentVoiceCheck, SpeakerInterval
from .teacher import MAX_CLIPS_PER_SPEAKER, cosine_similarity, exclusive_parts

EmbedClip = Callable[[float, float], Optional[list[float]]]
# PRAKTISCHE, NIET-GEVALIDEERDE KEUZE: met minder eigen referentiestukken is er geen bruikbaar "eigen bereik"
# (leave-one-out) te bepalen; dan is de uitkomst INCONCLUSIVE. Niet getoetst op gelabelde opnames.
MIN_OWN_CLIPS = 3


def _mean(vectors: list[list[float]]) -> list[float]:
    return [sum(col) / len(vectors) for col in zip(*vectors)]


def _overlaps(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return min(a[1], b[1]) > max(a[0], b[0])


def _speaker_clips(intervals: list[SpeakerInterval], embed_clip: EmbedClip, min_clip: float):
    """Per spreker: [(start, eind, embedding)] van de langste stukken zonder andere sprekers."""
    out: dict[str, list[tuple[float, float, list[float]]]] = {}
    for speaker in sorted({i.speaker for i in intervals}):
        parts = [p for iv in intervals if iv.speaker == speaker
                 for p in exclusive_parts(iv, intervals) if p[1] - p[0] >= min_clip]
        parts.sort(key=lambda p: p[1] - p[0], reverse=True)
        clips = []
        for s, e in parts[:MAX_CLIPS_PER_SPEAKER]:
            emb = embed_clip(s, e)
            if emb is not None:
                clips.append((s, e, emb))
        out[speaker] = clips
    return out


def _segment_clip(sp: SegmentSpeakers, intervals: list[SpeakerInterval], min_clip: float):
    """Langste stuk van het segment waarin alleen de dominante spreker actief is, of None."""
    parts = [p for x in sp.intersections if x.speaker == sp.dominant_speaker
             for p in exclusive_parts(SpeakerInterval(x.speaker, x.start, x.end), intervals)]
    parts = [p for p in parts if p[1] - p[0] >= min_clip]
    return max(parts, key=lambda p: p[1] - p[0]) if parts else None


def _inconclusive(sp: SegmentSpeakers, reason: str, **extra) -> SegmentVoiceCheck:
    return SegmentVoiceCheck(sp.segment_id, sp.dominant_speaker, "INCONCLUSIVE", reason, **extra)


def check_voice_consistency(
    segment_speakers: list[SegmentSpeakers],
    intervals: list[SpeakerInterval],
    embed_clip: EmbedClip,
    min_clip_seconds: float,
) -> list[SegmentVoiceCheck]:
    """Een `SegmentVoiceCheck` per segment, in dezelfde volgorde als `segment_speakers`."""
    clips = _speaker_clips(intervals, embed_clip, min_clip_seconds)
    results = []
    for sp in segment_speakers:
        if sp.dominant_speaker is None:
            results.append(_inconclusive(sp, "Geen dominante spreker (geen of gelijkspel)."))
            continue
        span = _segment_clip(sp, intervals, min_clip_seconds)
        if span is None:
            results.append(_inconclusive(sp, f"Geen stuk van minstens {min_clip_seconds} s met alleen deze spreker."))
            continue
        emb = embed_clip(*span)
        if emb is None:
            results.append(_inconclusive(sp, "Stuk kon niet worden geembed.", clip=span))
            continue

        # Profielen zonder stukken die dit segment overlappen.
        profiles = {s: [e for (a, b, e) in cs if not _overlaps((a, b), span)] for s, cs in clips.items()}
        own = profiles.get(sp.dominant_speaker, [])
        others = {s: v for s, v in profiles.items() if s != sp.dominant_speaker and v}
        if len(own) < MIN_OWN_CLIPS or not others:
            results.append(_inconclusive(sp, "Te weinig eigen of andere referentiestukken voor een vergelijking.",
                                         clip=span))
            continue

        own_sim = cosine_similarity(emb, _mean(own))
        other_speaker, other_sim = max(((s, cosine_similarity(emb, _mean(v))) for s, v in others.items()),
                                       key=lambda t: t[1])
        # Laagste score van de eigen stukken, elk tegen het profiel van de overige eigen stukken.
        typical_low = min(cosine_similarity(own[i], _mean(own[:i] + own[i + 1:])) for i in range(len(own)))

        in_range = own_sim >= typical_low
        if other_sim > own_sim and not in_range:
            verdict, reason = "CLOSER_TO_OTHER_SPEAKER", "Stuk lijkt meer op een ander label en valt buiten het eigen bereik."
        elif own_sim >= other_sim and in_range:
            verdict, reason = "CONSISTENT", "Stuk past bij het eigen label."
        else:
            verdict, reason = "INCONCLUSIVE", "Scores spreken elkaar tegen of liggen te dicht bij elkaar."
        results.append(SegmentVoiceCheck(sp.segment_id, sp.dominant_speaker, verdict, reason,
                                         round(own_sim, 4), other_speaker, round(other_sim, 4),
                                         round(typical_low, 4), span))
    return results
