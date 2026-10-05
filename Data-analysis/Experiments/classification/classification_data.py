"""
Data + loading for the classification step: turn-shaped data models, the two
input-format loaders, and context-window selection.

Split from classification.py (prompt building + the mock classifier + the
CLI) purely because together they'd be one very long file to scroll through —
conceptually, these two files together ARE "the classification step".
classification.py imports everything it needs from here.

Standalone experiment: does NOT modify Data-analysis/src. Where it reuses
production code (models.ProcessedTranscript), it only imports and reads it.
"""
import json
import sys
from pathlib import Path
from typing import Iterator, Optional

from pydantic import BaseModel, Field, field_validator

EXPERIMENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXPERIMENT_DIR.parents[2]  # .../StudieStap_WorkshopTool
SRC_DIR = PROJECT_ROOT / "Data-analysis" / "src"

# Read-only reuse of the production pipeline's models (models.ProcessedTranscript)
# — nothing here writes into Data-analysis/src or calls anything that would.
sys.path.insert(0, str(SRC_DIR))
from models import ProcessedTranscript  # noqa: E402

RAW_DIR = PROJECT_ROOT / "Data-local" / "raw" / "classification"
OUTPUT_DIR = PROJECT_ROOT / "Data-local" / "processed" / "classification"


# ============================================================
# Turn-shaped data: one ClassificationTurn = one thing someone said.
# ============================================================
# Deliberately a SEPARATE, smaller model than models.SpeakerTurn — that
# production model requires real ASR provenance (source_segments: a list of
# full TranscriptSegment objects), which a hand-written test transcript
# simply doesn't have. Both load_manual_fixture() and load_pipeline_processed()
# below produce this SAME shape, so the rest of the pipeline (context
# selection, classification) never needs to know which source a turn came
# from.
#
# Three fields — uncertain_assignment, overlap, docent_role — use
# Optional[bool]/Optional[str] with None meaning "unknown / not available",
# which is NOT the same as "False" (known to be clean) or "OTHER". This
# matters: a hand-written transcript has no automatic-recognition signal at
# all, so those fields stay None; a real ProcessedTranscript that went
# through the production pipeline has the ACTUAL True/False/DOCENT/OTHER
# value, carried over as-is. Never guess one from the other.

class ClassificationTurn(BaseModel):
    turn_id: int
    speaker: Optional[str] = None
    text: str

    # Optional on purpose: a hand-written test transcript has no timestamps.
    # Nothing downstream depends on these being present — turn ORDER in the
    # list is what defines "previous"/"next", not time.
    start: Optional[float] = None
    end: Optional[float] = None

    uncertain_assignment: Optional[bool] = None
    overlap: Optional[bool] = None

    # Phase 4 (docent recognition) fields — None when not evaluated (manual
    # transcripts, or a ProcessedTranscript that never went through
    # docent_recognition.py). Never inferred from `speaker`.
    docent_role: Optional[str] = None
    docent_role_similarity: Optional[float] = None   # raw cosine similarity — NOT a calibrated probability
    docent_role_note: Optional[str] = None            # why ONZEKER, or an embedding warning

    source: str  # "manual" | "pipeline_processed" — traceability only, no semantics attached


class FragmentTurns(BaseModel):
    """What both loaders return — the one shape the rest of the pipeline
    (context selection, classification) consumes, regardless of input format."""
    fragment_id: str
    source: str                  # "manual" | "pipeline_processed"
    source_path: str             # traceability back to the input file
    speaker_mapping: Optional[dict] = None   # e.g. {"MAIN_SPEAKER": "DOCENT"} — informational only
    turns: list[ClassificationTurn] = Field(default_factory=list)


# ============================================================
# Loading a fragment from disk — two input formats, one output shape.
# ============================================================

def load_manual_fixture(path: Path) -> FragmentTurns:
    """Hand-written test transcript, e.g.
    Data-local/raw/classification/test_classification_01.json:
        {
          "fragment_id": "...",
          "speaker_mapping": {"MAIN_SPEAKER": "DOCENT", "OTHER_SPEAKER": "LEERLING"},
          "turns": [{"turn_id": 1, "speaker": "MAIN_SPEAKER", "text": "..."}, ...]
        }
    No timestamps, no uncertainty/overlap/docent_role signal — none of that
    exists for a hand-written transcript, so those fields stay None
    ("unknown"), never defaulted to False/"OTHER" ("known"). `speaker_mapping`
    is a human-authored label for a synthetic scenario, not a recognition
    result — kept as separate, informational metadata on FragmentTurns and
    deliberately NOT copied into docent_role.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    turns = [
        ClassificationTurn(
            turn_id=t["turn_id"],
            speaker=t.get("speaker"),
            text=t["text"],
            start=t.get("start"),   # usually absent -> None
            end=t.get("end"),
            uncertain_assignment=None,
            overlap=None,
            source="manual",
        )
        for t in data["turns"]
    ]

    return FragmentTurns(
        fragment_id=data["fragment_id"],
        source="manual",
        source_path=str(path),
        speaker_mapping=data.get("speaker_mapping"),
        turns=turns,
    )


def load_pipeline_processed(path: Path) -> FragmentTurns:
    """An existing pipeline ProcessedTranscript JSON (Phase 3 output from
    preprocessing.py, e.g. Data-local/processed/preprocessing/<fragment>_turns.json
    — optionally also enriched by docent_recognition.py). Reuses
    models.ProcessedTranscript to parse it, unchanged. Unlike the manual
    loader, real uncertainty/overlap/docent_role information EXISTS here and
    is carried over as the actual value — never dropped, never reset to None."""
    processed = ProcessedTranscript.model_validate_json(Path(path).read_text(encoding="utf-8"))

    turns = [
        ClassificationTurn(
            turn_id=t.turn_id,
            speaker=t.speaker,
            text=t.text,
            start=t.start,
            end=t.end,
            uncertain_assignment=t.uncertain_assignment,
            overlap=t.overlap,
            docent_role=t.docent_role,
            docent_role_similarity=t.docent_role_similarity,
            docent_role_note=t.docent_role_note,
            source="pipeline_processed",
        )
        for t in processed.turns
    ]

    return FragmentTurns(
        fragment_id=Path(path).stem,
        source="pipeline_processed",
        source_path=str(path),
        speaker_mapping=None,
        turns=turns,
    )


def load_fragment(path: Path) -> FragmentTurns:
    """Single entry point: auto-detects which of the two formats a JSON file
    is, so the rest of the pipeline only ever deals with one FragmentTurns
    shape. Detection is a simple top-level-key check: a ProcessedTranscript
    always has "source_transcript_path"; the manual format always has
    "speaker_mapping"/"turns". Anything else raises rather than guessing."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))

    if "source_transcript_path" in data:
        return load_pipeline_processed(path)
    if "speaker_mapping" in data or "turns" in data:
        return load_manual_fixture(path)

    raise ValueError(
        f"{path}: unrecognized format — expected either a ProcessedTranscript JSON "
        f"(has 'source_transcript_path') or a manual fixture (has 'speaker_mapping'/'turns')."
    )


# ============================================================
# Context windows: which turns does a classifier get to see at once?
# ============================================================
# Purely INDEX-based (position in the turn list), not time-based — turns
# from a hand-written transcript have no timestamps, and turn ORDER is what
# defines "previous"/"next" either way.
#
# Modes:
#   A  only the current turn
#   B  previous turn + current turn
#   C  two previous turns + current + next turn
#
# iter_context_windows() yields exactly ONE window per turn in the list
# (that turn as center) — so the same turn is never counted as more than one
# classification event, even though it may also appear as *context* in a
# neighbouring turn's window.

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
    # need different handling downstream:
    #   unknown_reliability: True if ANY turn's uncertain_assignment/overlap is None
    #                        (e.g. a manual-transcript turn is in the window)
    #   flagged_uncertain:   True if ANY turn's uncertain_assignment/overlap is True
    #                        (a real pipeline turn the diarization itself flagged)
    unknown_reliability: bool
    flagged_uncertain: bool

    # Same idea, for docent_role (Phase 4): True if ANY turn in the window has
    # docent_role None (not evaluated) or "ONZEKER" — i.e. the window
    # contains at least one turn whose docent/other status isn't a settled
    # DOCENT/OTHER call.
    docent_role_unresolved: bool


def select_context(turns: list[ClassificationTurn], center_index: int, mode: str) -> ContextWindow:
    if mode not in MODES:
        raise ValueError(f"Unknown context mode {mode!r}; expected one of {sorted(MODES)}")
    if not (0 <= center_index < len(turns)):
        raise IndexError(f"center_index {center_index} out of range for {len(turns)} turns")

    before, after = MODES[mode]
    start = max(0, center_index - before)
    end = min(len(turns), center_index + after + 1)
    window_turns = turns[start:end]

    return ContextWindow(
        mode=mode,
        center_turn_id=turns[center_index].turn_id,
        context_turn_ids=[t.turn_id for t in window_turns],
        turns=window_turns,
        unknown_reliability=any(t.uncertain_assignment is None or t.overlap is None for t in window_turns),
        flagged_uncertain=any(t.uncertain_assignment is True or t.overlap is True for t in window_turns),
        docent_role_unresolved=any(t.docent_role is None or t.docent_role == "ONZEKER" for t in window_turns),
    )


def iter_context_windows(turns: list[ClassificationTurn], mode: str) -> Iterator[ContextWindow]:
    """One window per turn, that turn always as center — never more than once."""
    for i in range(len(turns)):
        yield select_context(turns, i, mode)


# ============================================================
# Classification result: what a classifier's answer looks like once it's
# been checked and saved.
# ============================================================
# Deliberately minimal: no didactic scoring, no indicator definitions, no
# confidence/severity fields yet — `detected`/`evidence` are placeholders a
# real classifier will fill in later.
#
# status:
#   "OK"      the classifier produced a usable detected/evidence pair.
#   "UNKNOWN" not enough information to judge — detected/evidence may be None.
#
# The two @field_validator functions below are Pydantic's way of running
# extra checks WHEN a ClassificationResult is created, beyond "is each field
# the right type". Think of them as small guard clauses that raise an error
# instead of silently accepting bad data:
#   - _status_known: rejects any status string other than "OK"/"UNKNOWN" —
#     catches a typo like "Ok" immediately instead of it silently reaching
#     the output JSON.
#   - _center_in_context: rejects a result whose center_turn_id isn't
#     actually inside its own context_turn_ids list — that combination
#     should never happen, so if it does, something upstream is broken and
#     we want to know immediately rather than write out nonsense.

VALID_STATUSES = {"OK", "UNKNOWN"}


class ClassificationResult(BaseModel):
    fragment_id: str
    center_turn_id: int
    context_turn_ids: list[int]
    indicator_id: str

    detected: Optional[bool] = None
    evidence: Optional[str] = None
    status: str = "OK"

    model_name: str
    model_version: str
    prompt_version: str

    @field_validator("status")
    @classmethod
    def _status_known(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}, got {v!r}")
        return v

    @field_validator("context_turn_ids")
    @classmethod
    def _center_in_context(cls, v: list[int], info) -> list[int]:
        center = info.data.get("center_turn_id")
        if center is not None and center not in v:
            raise ValueError(f"center_turn_id {center} must be included in context_turn_ids {v}")
        return v
