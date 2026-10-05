"""
STAP 3 — Preprocessing: merge ASR text segments into speaker turns, and
record how much context is available/trustworthy around each turn.

Phase 2 diarized transcript JSON -> ProcessedTranscript (speaker turns +
context info), as input for docent recognition and, later, classification.

Draaien:
    python preprocessing.py --diarized <Phase 2 JSON> [--max-gap-within-turn 1.5] [--large-context-gap 3.0]
"""
import argparse
import sys
from pathlib import Path
from typing import Optional

from config import PreprocessingConfig, PREPROCESSING_OUTPUT_DIR
from models import WorkshopTranscript, TranscriptSegment, ProcessedTranscript, SpeakerTurn


# ============================================================
# Merge consecutive ASR segments (already speaker-labelled by diarization)
# into logical speaker turns.
# ============================================================
# Merge rule (conservative on purpose — thresholds are heuristic experimental
# defaults in config.PreprocessingConfig, meant to be retuned later):
#
#   A segment is ISOLATED — always its own singleton turn, never merged with
#   a neighbour in either direction — if ANY of:
#     - speaker is None (unassigned)
#     - uncertain_assignment is True
#     - overlap is True
#   Folding a possibly-misattributed or crosstalk segment into a neighbouring
#   turn would let that uncertainty contaminate a turn that reads as
#   confidently assigned text — e.g. a single "Meneer." segment that may
#   actually belong to the other speaker must not get absorbed into a long
#   MAIN_SPEAKER turn.
#
#   Two CLEAN segments (both overlap=False and uncertain_assignment=False)
#   merge into one turn if, walking in time order:
#     (a) they have the same speaker (not None), AND
#     (b) the gap since the previous segment's end <= max_gap_within_turn_seconds
#
# So a merged (n_segments_merged > 1) turn is, by construction, always
# overlap=False and uncertain_assignment=False. Isolated segments are NOT
# dropped — each becomes its own turn, fully inspectable via
# SpeakerTurn.source_segments, so their content and flags stay directly
# visible rather than merged away.

def build_speaker_turns(
    segments: list[TranscriptSegment], *, max_gap_within_turn_seconds: float
) -> list[SpeakerTurn]:
    if not segments:
        return []

    turns: list[SpeakerTurn] = []

    def close(indices: list[int]) -> None:
        subset = [segments[j] for j in indices]
        confidences = [s.speaker_confidence for s in subset if s.speaker_confidence is not None]
        turns.append(SpeakerTurn(
            turn_id=len(turns),
            speaker=subset[0].speaker,
            start=subset[0].start,
            end=subset[-1].end,
            text=" ".join(s.text for s in subset).strip(),
            source_indices=list(indices),
            source_segments=subset,
            n_segments_merged=len(subset),
            overlap=any(s.overlap for s in subset),
            uncertain_assignment=any(s.uncertain_assignment for s in subset),
            speaker_confidence_min=min(confidences) if confidences else None,
            speaker_confidence_mean=(sum(confidences) / len(confidences)) if confidences else None,
        ))

    current: list[int] = []  # indices of an in-progress CLEAN, mergeable turn

    for i, seg in enumerate(segments):
        is_isolated = seg.speaker is None or seg.uncertain_assignment or seg.overlap
        if is_isolated:
            if current:
                close(current)
                current = []
            close([i])
            continue

        if current:
            prev_seg = segments[current[-1]]
            same_speaker = seg.speaker == prev_seg.speaker
            gap = seg.start - prev_seg.end
            if same_speaker and gap <= max_gap_within_turn_seconds:
                current.append(i)
                continue
            close(current)
        current = [i]

    if current:
        close(current)

    # invariant: every original segment ends up in exactly one turn
    assert sum(t.n_segments_merged for t in turns) == len(segments)
    return turns


# ============================================================
# Attach structural context-availability / context-uncertainty info to each
# speaker turn, based on its neighbours within the same turn list.
# ============================================================
# Two independent axes, deliberately not conflated:
#   - context_available_{before,after}: is there a neighbouring turn at all.
#     False at the edge of a fragment ("no context") — NOT automatically
#     treated as uncertain.
#   - context_uncertain_{before,after}: IF a neighbour exists, is it itself
#     shaky (uncertain_assignment / overlap) or far away (gap larger than
#     large_context_gap_seconds, a heuristic experimental default).

def attach_context(turns: list[SpeakerTurn], *, large_context_gap_seconds: float) -> list[SpeakerTurn]:
    n = len(turns)
    out: list[SpeakerTurn] = []

    for i, turn in enumerate(turns):
        prev_turn = turns[i - 1] if i > 0 else None
        next_turn = turns[i + 1] if i < n - 1 else None

        gap_before = round(turn.start - prev_turn.end, 3) if prev_turn else None
        gap_after = round(next_turn.start - turn.end, 3) if next_turn else None

        context_uncertain_before = bool(prev_turn) and (
            prev_turn.uncertain_assignment
            or prev_turn.overlap
            or (gap_before is not None and gap_before > large_context_gap_seconds)
        )
        context_uncertain_after = bool(next_turn) and (
            next_turn.uncertain_assignment
            or next_turn.overlap
            or (gap_after is not None and gap_after > large_context_gap_seconds)
        )

        overlap_in_context = (
            turn.overlap
            or (prev_turn.overlap if prev_turn else False)
            or (next_turn.overlap if next_turn else False)
        )

        out.append(turn.model_copy(update={
            "prev_turn_id": prev_turn.turn_id if prev_turn else None,
            "next_turn_id": next_turn.turn_id if next_turn else None,
            "gap_before_seconds": gap_before,
            "gap_after_seconds": gap_after,
            "context_available_before": prev_turn is not None,
            "context_available_after": next_turn is not None,
            "context_uncertain_before": context_uncertain_before,
            "context_uncertain_after": context_uncertain_after,
            "overlap_in_context": overlap_in_context,
        }))

    return out


# ============================================================
# Small descriptive-stat helpers over speaker turns, for the CLI printout.
# ============================================================

def duration_by_speaker(turns: list[SpeakerTurn]) -> dict[str, float]:
    """Actual speaking time per label: the sum of each ORIGINAL source
    segment's own (end - start), NOT turn.end - turn.start. A merged turn's
    outer span can include small gaps between its source segments (silence,
    not speech) — see turn_span_by_speaker() for that instead."""
    out: dict[str, float] = {}
    for t in turns:
        key = t.speaker or "UNASSIGNED"
        speaking_seconds = sum(s.end - s.start for s in t.source_segments)
        out[key] = out.get(key, 0.0) + speaking_seconds
    return {k: round(v, 2) for k, v in out.items()}


def turn_span_by_speaker(turns: list[SpeakerTurn]) -> dict[str, float]:
    """Sum of (turn.end - turn.start) per label — the outer time span each
    turn occupies, INCLUDING any small gaps between its merged segments.
    This is NOT actual speaking time (use duration_by_speaker() for that)."""
    out: dict[str, float] = {}
    for t in turns:
        key = t.speaker or "UNASSIGNED"
        out[key] = out.get(key, 0.0) + (t.end - t.start)
    return {k: round(v, 2) for k, v in out.items()}


def count_speaker_switches(turns: list[SpeakerTurn]) -> int:
    """Number of consecutive turn pairs with a different speaker label."""
    return sum(1 for a, b in zip(turns, turns[1:]) if a.speaker != b.speaker)


def speaker_sequence(turns: list[SpeakerTurn]) -> list[Optional[str]]:
    return [t.speaker for t in turns]


# ============================================================
# CLI: Phase 2 diarized transcript JSON -> ProcessedTranscript JSON
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Stap 3: group diarized segments into speaker turns + context")
    parser.add_argument("--diarized", required=True, help="Path to a Phase 2 diarized transcript JSON")
    parser.add_argument("--out", default=None, help="Output JSON path (default: Data-local/processed/preprocessing/)")
    parser.add_argument("--max-gap-within-turn", type=float, default=None, help="Override PreprocessingConfig default")
    parser.add_argument("--large-context-gap", type=float, default=None, help="Override PreprocessingConfig default")
    args = parser.parse_args()

    src_path = Path(args.diarized)
    if not src_path.exists():
        sys.exit(f"Not found: {src_path}")
    transcript = WorkshopTranscript.model_validate_json(src_path.read_text(encoding="utf-8"))

    cfg = PreprocessingConfig()
    if args.max_gap_within_turn is not None:
        cfg.max_gap_within_turn_seconds = args.max_gap_within_turn
    if args.large_context_gap is not None:
        cfg.large_context_gap_seconds = args.large_context_gap

    turns = build_speaker_turns(transcript.segments, max_gap_within_turn_seconds=cfg.max_gap_within_turn_seconds)
    turns = attach_context(turns, large_context_gap_seconds=cfg.large_context_gap_seconds)

    processed = ProcessedTranscript(
        source_transcript_path=str(src_path),
        audio_file=transcript.audio_file,
        language=transcript.language,
        duration=transcript.duration,
        model_size=transcript.model_size,
        original_segment_count=len(transcript.segments),
        turns=turns,
        preprocessing_config={
            "max_gap_within_turn_seconds": cfg.max_gap_within_turn_seconds,
            "large_context_gap_seconds": cfg.large_context_gap_seconds,
        },
    )

    PREPROCESSING_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else PREPROCESSING_OUTPUT_DIR / f"{src_path.stem}_turns.json"
    out_path.write_text(processed.model_dump_json(indent=2), encoding="utf-8")

    n_overlap = sum(1 for t in turns if t.overlap)
    n_uncertain = sum(1 for t in turns if t.uncertain_assignment)
    n_no_ctx_before = sum(1 for t in turns if not t.context_available_before)
    n_no_ctx_after = sum(1 for t in turns if not t.context_available_after)
    n_unc_ctx_before = sum(1 for t in turns if t.context_uncertain_before)
    n_unc_ctx_after = sum(1 for t in turns if t.context_uncertain_after)

    print(f"segments -> turns        : {len(transcript.segments)} -> {len(turns)}")
    print(f"speaking time by speaker : {duration_by_speaker(turns)}  (sum of source-segment durations)")
    print(f"turn_span by speaker     : {turn_span_by_speaker(turns)}  (turn.end-turn.start, incl. gaps within a turn)")
    print(f"speaker switches         : {count_speaker_switches(turns)}")
    print(f"overlap turns            : {n_overlap}")
    print(f"uncertain turns          : {n_uncertain}")
    print(f"no context before/after  : {n_no_ctx_before} / {n_no_ctx_after}")
    print(f"uncertain context b/a    : {n_unc_ctx_before} / {n_unc_ctx_after}")
    print(f"written to {out_path}")


if __name__ == "__main__":
    main()
