"""
Shared data schemas used across the whole pipeline, so timestamps and
speaker labels survive from transcription through to classification.

Phase 1 leaves `speaker` as None on every segment — it gets filled in
by Phase 2 (diarization). Nothing downstream should assume it's set yet.
"""
from typing import Optional
from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    start: float
    end: float
    speaker: Optional[str] = None
    text: str


class WorkshopTranscript(BaseModel):
    audio_file: str
    language: str
    duration: float
    segments: list[TranscriptSegment]
    model_size: str
    transcription_time_seconds: float