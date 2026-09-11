"""
Merge consecutive ASR segments (already speaker-labelled by diarization) into
logical speaker turns.

Merge rule (conservative on purpose — see preprocessing_test_01.md "merge-regel
aangepast" for why; thresholds are heuristic experimental defaults in
config.PreprocessingConfig, meant to be retuned later):

  A segment is ISOLATED — always its own singleton turn, never merged with a
  neighbour in either direction — if ANY of:
    - speaker is None (unassigned)
    - uncertain_assignment is True
    - overlap is True
  Folding a possibly-misattributed or crosstalk segment into a neighbouring
  turn would let that uncertainty contaminate a turn that reads as confident
  ASSIGNMENT text — e.g. a single "Meneer." segment that may actually belong
  to the other speaker must not get absorbed into a long MAIN_SPEAKER turn.

  Two CLEAN segments (both overlap=False and uncertain_assignment=False) merge
  into one turn iff, walking in time order:
    (a) they have the same speaker (not None), AND
    (b) the gap since the previous segment's end <= max_gap_within_turn_seconds

So a normal (n_segments_merged > 1) turn is, by construction, always
overlap=False and uncertain_assignment=False — a later classifier can treat
"is this turn itself clean" (its own overlap/uncertain_assignment) and "is its
context clean" (the neighbours' context_uncertain_* flags, see context.py) as
two separate checks before judging it. Isolated segments are NOT dropped —
each becomes its own turn, fully inspectable via SpeakerTurn.source_segments,
so their content and flags stay directly visible rather than merged away.
"""
from models.schema import TranscriptSegment
from models.processed import SpeakerTurn


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
