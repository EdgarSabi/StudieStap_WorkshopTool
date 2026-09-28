"""
STAP 3 — configurable context windows.

Purely INDEX-based (position in the turn list), not time-based — turns from
a hand-written transcript have no timestamps, and turn ORDER is what defines
"previous"/"next" either way (see schemas/turn.py). This is why
preprocessing/context.py's attach_context() (which reasons about time gaps
between turn.start/turn.end) isn't reused here: it would need real
timestamps to compute gap_before/gap_after, and STAP 3 doesn't need gaps —
only "N turns back / M turns forward in the list".

Modes:
  A  only the current turn
  B  previous turn + current turn
  C  two previous turns + current + next turn

iter_context_windows() yields exactly ONE window per turn in the list (that
turn as center) — so the same turn is never counted as more than one
classification event, even though it may also appear as *context* in a
neighbouring turn's window.
"""
from typing import Iterator

from schemas.turn import ClassificationTurn
from pydantic import BaseModel

MODES = {
    "A": (0, 0),   # (turns_before, turns_after)
    "B": (1, 0),
    "C": (2, 1),
}


class ContextWindow(BaseModel):
    mode: str
    center_turn_id: int
    context_turn_ids: list[int]          # ordered, always includes center_turn_id
    turns: list[ClassificationTurn]      # same order as context_turn_ids

    # Reliability of the window's own turns — kept as two SEPARATE booleans,
    # not merged into one, because "we don't know" and "we know it's shaky"
    # require different downstream handling (see schemas/turn.py):
    #   unknown_reliability: True if ANY turn's uncertain_assignment/overlap is None
    #                        (e.g. a manual-transcript turn is in the window)
    #   flagged_uncertain:   True if ANY turn's uncertain_assignment/overlap is True
    #                        (a real pipeline turn the diarization itself flagged)
    unknown_reliability: bool
    flagged_uncertain: bool

    # Same idea, for docent_role (Phase 4): True if ANY turn in the window has
    # docent_role None (not evaluated) or "ONZEKER" — i.e. the window
    # contains at least one turn whose docent/other status isn't a settled
    # DOCENT/OTHER call. A classifier should treat that as missing evidence,
    # not silently ignore it.
    docent_role_unresolved: bool


def _reliability_flags(turns: list[ClassificationTurn]) -> tuple[bool, bool]:
    unknown = any(t.uncertain_assignment is None or t.overlap is None for t in turns)
    flagged = any(t.uncertain_assignment is True or t.overlap is True for t in turns)
    return unknown, flagged


def _docent_role_unresolved(turns: list[ClassificationTurn]) -> bool:
    return any(t.docent_role is None or t.docent_role == "ONZEKER" for t in turns)


def select_context(turns: list[ClassificationTurn], center_index: int, mode: str) -> ContextWindow:
    if mode not in MODES:
        raise ValueError(f"Unknown context mode {mode!r}; expected one of {sorted(MODES)}")
    if not (0 <= center_index < len(turns)):
        raise IndexError(f"center_index {center_index} out of range for {len(turns)} turns")

    before, after = MODES[mode]
    start = max(0, center_index - before)
    end = min(len(turns), center_index + after + 1)
    window_turns = turns[start:end]

    unknown, flagged = _reliability_flags(window_turns)

    return ContextWindow(
        mode=mode,
        center_turn_id=turns[center_index].turn_id,
        context_turn_ids=[t.turn_id for t in window_turns],
        turns=window_turns,
        unknown_reliability=unknown,
        flagged_uncertain=flagged,
        docent_role_unresolved=_docent_role_unresolved(window_turns),
    )


def iter_context_windows(turns: list[ClassificationTurn], mode: str) -> Iterator[ContextWindow]:
    """One window per turn, that turn always as center — never more than once."""
    for i in range(len(turns)):
        yield select_context(turns, i, mode)
