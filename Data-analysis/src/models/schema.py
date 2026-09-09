"""
Shared data schemas. Extended with faster-whisper's per-segment quality
metadata and our own heuristic flags, for research comparison.
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


class WorkshopTranscript(BaseModel):
    audio_file: str
    language: str
    duration: float
    segments: list[TranscriptSegment]
    model_size: str
    transcription_time_seconds: float
    transcription_config: dict = Field(default_factory=dict)  # snapshot, for comparing benchmark runs