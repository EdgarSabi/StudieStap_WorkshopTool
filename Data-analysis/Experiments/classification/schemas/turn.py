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

    source: str  # "manual" | "pipeline_processed" — traceability only, no semantics attached


class FragmentTurns(BaseModel):
    """What both loaders return — the one shape the rest of the pipeline
    (context selection, classification) consumes, regardless of input format."""
    fragment_id: str
    source: str                  # "manual" | "pipeline_processed"
    source_path: str             # traceability back to the input file
    speaker_mapping: Optional[dict] = None   # e.g. {"MAIN_SPEAKER": "DOCENT"} — informational only
    turns: list[ClassificationTurn] = Field(default_factory=list)
