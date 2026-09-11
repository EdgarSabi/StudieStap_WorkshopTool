"""
Phase 3: preprocessing / context-structuring output.

Deliberately a SEPARATE model set from models/schema.py. Phase 1/2 output
(WorkshopTranscript, TranscriptSegment) is read-only input to this layer and
is never modified — this module defines the "processed representation":
ASR segments grouped into speaker turns, with full traceability back to the
original segments and explicit context-availability / context-uncertainty
flags. No didactic classification fields live here.
"""
from typing import Optional
from pydantic import BaseModel, Field

from models.schema import TranscriptSegment


class SpeakerTurn(BaseModel):
    turn_id: int
    speaker: Optional[str] = None      # MAIN_SPEAKER / OTHER_SPEAKER_n / None (unassigned)
    start: float
    end: float
    text: str

    # --- traceability: the ORIGINAL segments, embedded verbatim (full TranscriptSegment,
    # including speaker_raw, avg_logprob/no_speech_prob/compression_ratio, quality_flags,
    # etc.) — nothing dropped, nothing summarized away. `source_indices` gives the exact
    # position of each in the source WorkshopTranscript.segments list. ---
    source_indices: list[int] = Field(default_factory=list)
    source_segments: list[TranscriptSegment] = Field(default_factory=list)
    n_segments_merged: int = 0

    # --- aggregated quality signals over source_segments (never hidden) ---
    # Merging is conservative (see preprocessing/turns.py): a segment with
    # overlap=True or uncertain_assignment=True is ALWAYS its own singleton
    # turn, never merged into a neighbour. So for a turn with
    # n_segments_merged > 1, both flags below are guaranteed False — only for
    # a singleton turn (n_segments_merged == 1) can either be True, reflecting
    # that one source segment directly.
    overlap: bool = False
    uncertain_assignment: bool = False
    speaker_confidence_min: Optional[float] = None
    speaker_confidence_mean: Optional[float] = None

    # --- structural context relative to neighbouring turns (no semantics, no classification) ---
    prev_turn_id: Optional[int] = None
    next_turn_id: Optional[int] = None
    gap_before_seconds: Optional[float] = None
    gap_after_seconds: Optional[float] = None

    # Two independent axes, deliberately not conflated:
    #  - context_available_*: is there a neighbouring turn at all (False if this
    #    turn is at the edge of the fragment — "no context", not "bad context")
    #  - context_uncertain_*: IF a neighbour exists, is it itself shaky
    #    (uncertain_assignment / overlap) or far away (large silence gap)
    context_available_before: bool = False
    context_available_after: bool = False
    context_uncertain_before: bool = False
    context_uncertain_after: bool = False

    overlap_in_context: bool = False   # this turn or either available neighbour overlaps

    # NOTE for later classifiers: judging a turn (e.g. as gerichte feedback)
    # requires checking BOTH that the turn itself is clean
    # (overlap is False and uncertain_assignment is False) AND that the
    # relevant context is available and not uncertain
    # (context_available_before/after and not context_uncertain_before/after).
    # A clean turn with shaky context, or an uncertain turn with clean
    # context, are both cases where a classifier should hold back.


class ProcessedTranscript(BaseModel):
    source_transcript_path: str        # traceability to the Phase 1/2 JSON this was built from
    audio_file: str
    language: str
    duration: float
    model_size: str                    # ASR model of the source transcript (e.g. "medium")
    original_segment_count: int
    turns: list[SpeakerTurn]
    preprocessing_config: dict = Field(default_factory=dict)  # snapshot of thresholds used
