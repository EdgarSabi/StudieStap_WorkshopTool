"""
Lightweight turn representation for the classification experiment.

Deliberately a SEPARATE, smaller model than models.processed.SpeakerTurn —
that production model requires real ASR provenance (source_segments: list of
full TranscriptSegment objects), which a hand-written test transcript simply
doesn't have. Fabricating fake provenance to satisfy that schema would be
worse than having a smaller, honest one here. Both loaders/manual.py and
loaders/pipeline.py produce the SAME FragmentTurns/ClassificationTurn shape,
so the rest of the pipeline (context selection, classification) never needs
to know which source a turn came from.

Reliability fields (uncertain_assignment, overlap) are Optional[bool] with
None meaning "unknown / not available" — NOT "reliable". This matters:
  - loaders/pipeline.py fills them from the real, automated pipeline's
    actual True/False values (that information exists and is preserved).
  - loaders/manual.py has no such signal for a hand-written transcript, so
    it leaves them None. None must never be treated as "False" (=clean)
    downstream — see ContextWindow's reliability summary below, which keeps
    "unknown" and "known-clean" visibly distinct.

`docent_role` follows the same "None means unknown, never inferred" rule as
`speaker` above: it is populated ONLY when the source ProcessedTranscript
went through Phase 4 (run_docent_recognition.py), carried over exactly as
computed there (DOCENT/OTHER/ONZEKER, never re-derived from `speaker` here —
a MAIN_SPEAKER turn with no docent_role stays None, not "DOCENT"). A
hand-written manual transcript never has this evaluated, so it stays None
even though it may carry a `speaker_mapping` — that mapping is kept as
separate, informational metadata (see FragmentTurns) and is deliberately
NOT wired into `docent_role`, to avoid conflating a human-authored label
with a voice-recognition result.
"""
from typing import Optional
from pydantic import BaseModel, Field


class ClassificationTurn(BaseModel):
    turn_id: int
    speaker: Optional[str] = None
    text: str

    # Optional on purpose: a hand-written test transcript has no timestamps.
    # Nothing downstream (context selection, prompt building) depends on
    # these being present — turn order in the list is what defines "previous"
    # / "next", not time.
    start: Optional[float] = None
    end: Optional[float] = None

    # None = unknown (no signal available), NOT "False" (=known to be clean).
    # See module docstring.
    uncertain_assignment: Optional[bool] = None
    overlap: Optional[bool] = None

    # Phase 4 (docent recognition) fields — None when not evaluated (manual
    # transcripts, or a ProcessedTranscript that never went through
    # run_docent_recognition.py). Never inferred from `speaker`. See module
    # docstring for why "DOCENT"/"OTHER"/"ONZEKER"/None are kept distinct.
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
