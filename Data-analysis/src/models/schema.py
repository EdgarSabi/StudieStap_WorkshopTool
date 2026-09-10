"""
Shared data schemas. Extended with faster-whisper's per-segment quality
metadata and our own heuristic flags, for research comparison.

Phase 2 adds optional speaker/diarization fields. They are all optional with
defaults, so a Phase 1 transcript JSON (no diarization) still validates.
"""
from typing import Optional
from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    start: float
    end: float
    speaker: Optional[str] = None
    text: str

    # Raw quality signals from faster-whisper, preserved as-is.
    avg_logprob: Optional[float] = None
    no_speech_prob: Optional[float] = None
    compression_ratio: Optional[float] = None

    # Our own heuristic flags — see config.py flag_* thresholds.
    quality_flags: list[str] = Field(default_factory=list)

    # --- Phase 2: speaker diarization (filled in by the diarization layer) ---
    # `speaker` above holds the friendly label (MAIN_SPEAKER / OTHER_SPEAKER_1 / ...).
    speaker_raw: Optional[str] = None          # backend label before mapping, e.g. "SPEAKER_00"
    speaker_confidence: Optional[float] = None  # winning speaker's share of this segment's speech time
    overlap: bool = False                       # another speaker also covers a meaningful part of the segment
    uncertain_assignment: bool = False          # low coverage or near-tie -> treat the speaker label with caution


class SpeakerTurn(BaseModel):
    """One contiguous stretch attributed to a single speaker by the diarizer."""
    start: float
    end: float
    speaker: str                               # backend-raw label
    confidence: Optional[float] = None


class WorkshopTranscript(BaseModel):
    audio_file: str
    language: str
    duration: float
    segments: list[TranscriptSegment]
    model_size: str
    transcription_time_seconds: float
    transcription_config: dict = Field(default_factory=dict)  # snapshot, for comparing benchmark runs

    # --- Phase 2: present only after diarization has been coupled in ---
    # Free-form snapshot: backend, model, settings, runtime, raw->friendly label
    # map, per-speaker talk-time inventory, overlap/uncertain counts.
    diarization: Optional[dict] = None