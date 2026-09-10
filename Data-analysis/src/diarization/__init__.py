"""
Phase 2: speaker diarization as a separate layer on top of transcription.

Design notes:
- `base.DiarizationBackend` is the swap point. Nothing outside `pyannote_backend`
  imports pyannote, so a different backend can be dropped in later.
- `labeling` turns raw backend speaker ids into MAIN_SPEAKER / OTHER_SPEAKER_n.
- `assign` couples speaker turns onto existing timestamped transcript segments.
  It is pure time-span geometry: no ML, unit-testable on its own.
"""
from .base import DiarizationBackend, DiarizationResult, SpeakerTurn


def get_backend(config) -> DiarizationBackend:
    """Factory: resolve config.backend -> a backend instance. Imports the concrete
    backend lazily so its heavy / optional deps aren't required just to import
    this package."""
    if config.backend == "pyannote":
        from .pyannote_backend import PyannoteBackend

        return PyannoteBackend(config)
    raise ValueError(f"Unknown diarization backend: {config.backend!r}")


__all__ = [
    "DiarizationBackend",
    "DiarizationResult",
    "SpeakerTurn",
    "get_backend",
]
