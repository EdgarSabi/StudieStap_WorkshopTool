"""Sprekerkoppeling: ruwe sprekerintervallen leggen over segmenten en woorden.

Dit is pure tijdrekenkunde (geen model). De kernregel, geleerd van de branch
`feature/lossless-speaker-intersections`:

    Een segment kan meerdere sprekers bevatten. We bewaren ALLE overlappen
    (`intersections`). De "dominante spreker" is alleen een samenvatting.

Woordniveau (alleen als er woordtijden zijn):
    SINGLE      precies een spreker overlapt het woord
    AMBIGUOUS   twee of meer sprekers overlappen het woord -> we kiezen NIET
    NO_SPEAKER  geen enkele spreker overlapt het woord
    NO_TIMING   het woord heeft geen tijd -> niets te koppelen, niets verzonnen
"""
from __future__ import annotations

from typing import Optional

from ..models import (Intersection, Segment, SegmentSpeakers, SpeakerInterval, StepStatus,
                      WordAlignment, WordSpeaker)


def _merge(spans: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Voeg overlappende (begin, eind)-paren samen, zodat niets dubbel geteld wordt."""
    merged: list[list[float]] = []
    for s, e in sorted(spans):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def _total(spans: list[tuple[float, float]]) -> float:
    return sum(e - s for s, e in spans)


def segment_intersections(seg_start: float, seg_end: float,
                          intervals: list[SpeakerInterval]) -> list[Intersection]:
    out = []
    for iv in intervals:
        start, end = max(seg_start, iv.start), min(seg_end, iv.end)
        if end > start:
            out.append(Intersection(speaker=iv.speaker, start=start, end=end, duration=end - start))
    out.sort(key=lambda x: (x.start, x.end, x.speaker))
    return out


def _simultaneous_seconds(per_speaker_spans: dict[str, list[tuple[float, float]]]) -> float:
    """Totale tijd waarin minstens twee verschillende sprekers tegelijk actief zijn."""
    events: list[tuple[float, int]] = []
    for spans in per_speaker_spans.values():
        for s, e in spans:
            events += [(s, +1), (e, -1)]
    events.sort()
    active, last, total = 0, 0.0, 0.0
    for t, delta in events:
        if active >= 2:
            total += t - last
        active += delta
        last = t
    return total


def _couple_word(index: int, text: str, start: Optional[float], end: Optional[float],
                 intervals: list[SpeakerInterval]) -> WordSpeaker:
    if start is None or end is None:
        return WordSpeaker(index, text, start, end, status="NO_TIMING")
    if end > start:
        speakers = {iv.speaker for iv in intervals if min(end, iv.end) > max(start, iv.start)}
    else:  # woord van nul lengte: tel een spreker mee als het tijdstip binnen diens interval valt
        speakers = {iv.speaker for iv in intervals if iv.start <= start <= iv.end}
    candidates = sorted(speakers)
    if not candidates:
        return WordSpeaker(index, text, start, end, status="NO_SPEAKER")
    if len(candidates) == 1:
        return WordSpeaker(index, text, start, end, status="SINGLE", speaker=candidates[0],
                           candidates=candidates)
    return WordSpeaker(index, text, start, end, status="AMBIGUOUS", speaker=None, candidates=candidates)


def couple_speakers(
    segments: list[Segment],
    intervals: list[SpeakerInterval],
    alignment: Optional[WordAlignment] = None,
    min_single_speaker_coverage: float = 0.60,
) -> list[SegmentSpeakers]:
    """Een `SegmentSpeakers` per segment, in dezelfde volgorde. Verandert de invoer niet."""
    aligned_by_id = {}
    if alignment is not None and alignment.status in (StepStatus.SUCCEEDED, StepStatus.PARTIAL):
        aligned_by_id = {a.segment_id: a for a in alignment.segments}

    result: list[SegmentSpeakers] = []
    for seg in segments:
        duration = max(0.0, seg.end - seg.start)
        inters = segment_intersections(seg.start, seg.end, intervals)

        per_speaker_spans: dict[str, list[tuple[float, float]]] = {}
        for x in inters:
            per_speaker_spans.setdefault(x.speaker, []).append((x.start, x.end))
        per_speaker_spans = {k: _merge(v) for k, v in sorted(per_speaker_spans.items())}
        seconds = {k: round(_total(v), 4) for k, v in per_speaker_spans.items()}
        covered = _total(_merge([sp for v in per_speaker_spans.values() for sp in v]))

        if not seconds:
            attribution = "NONE"
        elif len(seconds) >= 2:
            attribution = "MIXED"
        else:
            coverage = (next(iter(seconds.values())) / duration) if duration > 0 else 0.0
            attribution = "SINGLE" if coverage >= min_single_speaker_coverage else "PARTIAL"

        dominant, share = None, None
        if seconds and duration > 0:
            ranked = sorted(seconds.items(), key=lambda kv: kv[1], reverse=True)
            tie = len(ranked) > 1 and abs(ranked[0][1] - ranked[1][1]) < 1e-9
            if not tie:  # bij een gelijkspel kiezen we niet
                dominant, share = ranked[0][0], round(ranked[0][1] / duration, 4)

        words: list[WordSpeaker] = []
        aligned = aligned_by_id.get(seg.id)
        if aligned is not None:
            words = [_couple_word(i, w.text, w.start, w.end, intervals) for i, w in enumerate(aligned.words)]

        result.append(SegmentSpeakers(
            segment_id=seg.id,
            intersections=inters,
            seconds_per_speaker=seconds,
            simultaneous_seconds=round(_simultaneous_seconds(per_speaker_spans), 4),
            uncovered_seconds=round(max(0.0, duration - covered), 4),
            attribution=attribution,
            dominant_speaker=dominant,
            dominant_share=share,
            words=words,
        ))
    return result
