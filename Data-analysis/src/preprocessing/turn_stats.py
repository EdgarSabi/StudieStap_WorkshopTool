"""
Small descriptive-stat helpers over speaker turns. Pure functions, no
classification — just make duration / speaker-switch patterns easy to
measure, per the Phase 3 requirement. A later classifier can scan
speaker_sequence() for patterns like MAIN_SPEAKER -> OTHER_SPEAKER_1 ->
MAIN_SPEAKER directly; nothing further is precomputed for that here.
"""
from typing import Optional
from models.processed import SpeakerTurn


def duration_by_speaker(turns: list[SpeakerTurn]) -> dict[str, float]:
    """Actual speaking time per label: the sum of each ORIGINAL source
    segment's own (end - start), NOT turn.end - turn.start. A merged turn's
    outer span can include small gaps between its source segments (silence,
    not speech), and source_segments always fully covers the original
    segments (see the traceability invariant in preprocessing/turns.py) — so
    this total is the same regardless of how segments happen to be merged
    into turns. For the outer span instead (which does include those gaps),
    see turn_span_by_speaker().
    """
    out: dict[str, float] = {}
    for t in turns:
        key = t.speaker or "UNASSIGNED"
        speaking_seconds = sum(s.end - s.start for s in t.source_segments)
        out[key] = out.get(key, 0.0) + speaking_seconds
    return {k: round(v, 2) for k, v in out.items()}


def turn_span_by_speaker(turns: list[SpeakerTurn]) -> dict[str, float]:
    """Sum of turn_span (turn.end - turn.start) per label — the outer time
    span each turn occupies, INCLUDING any small gaps between its merged
    segments. This is NOT actual speaking time (use duration_by_speaker() for
    that) — it depends on the merge rule, since merging changes how many gaps
    end up inside a turn's span versus between turns.
    """
    out: dict[str, float] = {}
    for t in turns:
        key = t.speaker or "UNASSIGNED"
        out[key] = out.get(key, 0.0) + turn_span(t)
    return {k: round(v, 2) for k, v in out.items()}


def turn_span(turn: SpeakerTurn) -> float:
    """turn.end - turn.start — the turn's outer time span. Includes any small
    gaps between its merged source segments, so it is NOT the same as actual
    speaking time (see duration_by_speaker())."""
    return turn.end - turn.start


def count_speaker_switches(turns: list[SpeakerTurn]) -> int:
    """Number of consecutive turn pairs with a different speaker label."""
    return sum(1 for a, b in zip(turns, turns[1:]) if a.speaker != b.speaker)


def speaker_sequence(turns: list[SpeakerTurn]) -> list[Optional[str]]:
    return [t.speaker for t in turns]
