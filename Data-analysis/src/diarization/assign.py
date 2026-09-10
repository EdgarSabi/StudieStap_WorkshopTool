"""
Couple diarization speaker turns onto existing timestamped transcript segments.

Pure time-span geometry — no model, no I/O. Given a transcript segment's
[start, end] and the list of speaker turns, decide:
  - which speaker "owns" the segment (most overlapping time)
  - a confidence (owner's share of the segment's total attributed speech time)
  - whether another speaker also covers a meaningful slice  -> overlap
  - whether the assignment is shaky (low coverage or near-tie) -> uncertain

Important: a segment with NO overlapping speaker turn is marked
`uncertain_assignment=True` with `speaker=None`. That means "diarization did not
attribute this speech", NOT "no student spoke".
"""
from models.schema import TranscriptSegment
from .base import SpeakerTurn


def _overlap_seconds(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def assign_speakers(
    segments: list[TranscriptSegment],
    turns: list[SpeakerTurn],
    label_map: dict,
    *,
    overlap_min_ratio: float = 0.15,
    uncertain_coverage_below: float = 0.60,
    uncertain_margin_below: float = 0.15,
) -> list[TranscriptSegment]:
    """Return a NEW list of segments with speaker fields filled in. Input untouched."""
    out: list[TranscriptSegment] = []

    for seg in segments:
        duration = max(0.0, seg.end - seg.start)

        per_speaker: dict[str, float] = {}
        for t in turns:
            ov = _overlap_seconds(seg.start, seg.end, t.start, t.end)
            if ov > 0:
                per_speaker[t.speaker] = per_speaker.get(t.speaker, 0.0) + ov

        if not per_speaker or duration <= 0:
            out.append(seg.model_copy(update={
                "speaker": None,
                "speaker_raw": None,
                "speaker_confidence": None,
                "overlap": False,
                "uncertain_assignment": True,
            }))
            continue

        ranked = sorted(per_speaker.items(), key=lambda kv: kv[1], reverse=True)
        winner_raw, winner_ov = ranked[0]
        runner_ov = ranked[1][1] if len(ranked) > 1 else 0.0
        total_ov = sum(per_speaker.values())

        coverage = winner_ov / duration
        margin = (winner_ov - runner_ov) / duration
        confidence = winner_ov / total_ov if total_ov else 0.0

        out.append(seg.model_copy(update={
            "speaker": label_map.get(winner_raw, winner_raw),
            "speaker_raw": winner_raw,
            "speaker_confidence": round(confidence, 4),
            "overlap": (runner_ov / duration) >= overlap_min_ratio,
            "uncertain_assignment": (
                coverage < uncertain_coverage_below or margin < uncertain_margin_below
            ),
        }))

    return out


def summarize(segments: list[TranscriptSegment]) -> dict:
    """Counts for the experiment report / runner printout."""
    per_label: dict[str, int] = {}
    for s in segments:
        key = s.speaker or "UNASSIGNED"
        per_label[key] = per_label.get(key, 0) + 1
    return {
        "segments": len(segments),
        "per_label": per_label,
        "overlap_segments": sum(1 for s in segments if s.overlap),
        "uncertain_segments": sum(1 for s in segments if s.uncertain_assignment),
        "unassigned_segments": sum(1 for s in segments if s.speaker is None),
    }
