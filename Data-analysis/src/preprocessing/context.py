"""
Attach structural context-availability / context-uncertainty info to each
speaker turn, based on its neighbours within the same turn list.

Two independent axes, deliberately not conflated:
  - context_available_{before,after}: is there a neighbouring turn at all.
    False at the edge of a fragment ("no context") — NOT automatically
    treated as uncertain.
  - context_uncertain_{before,after}: IF a neighbour exists, is it itself
    shaky (uncertain_assignment / overlap) or far away (gap larger than
    large_context_gap_seconds, a heuristic experimental default).

Pure function — returns a new list (via model_copy), does not mutate input.
"""
from models.processed import SpeakerTurn


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
