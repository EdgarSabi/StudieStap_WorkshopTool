"""
Backend-neutral diarization interface and result types.

Any diarization backend (pyannote today, maybe something else later) implements
`DiarizationBackend.diarize()` and returns a `DiarizationResult`. Downstream code
(labeling, segment assignment, the experiment runner) only touches these types,
never a backend-specific object.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SpeakerTurn:
    """One contiguous stretch attributed to a single speaker, in seconds.

    `speaker` is the backend's own raw label (e.g. "SPEAKER_00") — mapping to
    MAIN_SPEAKER / OTHER_SPEAKER_n happens later, in `labeling`.
    """
    start: float
    end: float
    speaker: str
    confidence: Optional[float] = None

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass
class DiarizationResult:
    turns: list[SpeakerTurn]
    backend: str
    model: str
    settings: dict = field(default_factory=dict)
    runtime_seconds: float = 0.0

    @property
    def raw_speakers(self) -> list[str]:
        return sorted({t.speaker for t in self.turns})

    def talk_time(self) -> dict[str, float]:
        """Total speaking seconds per raw speaker label."""
        totals: dict[str, float] = {}
        for t in self.turns:
            totals[t.speaker] = totals.get(t.speaker, 0.0) + t.duration
        return totals


class DiarizationBackend(ABC):
    """Implementations load their model once (in __init__) and reuse it."""

    name: str = "base"

    @abstractmethod
    def diarize(
        self,
        audio_path: Path,
        *,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
    ) -> DiarizationResult:
        ...
