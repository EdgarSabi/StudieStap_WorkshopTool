"""
Minimal cache check: skip re-transcription if an output JSON for this
audio file already exists, unless the caller forces a redo.

Deliberately simple for Phase 1 — no content hashing or invalidation
logic yet, just an existence check on the expected output path.
"""
from pathlib import Path


def output_path_for(audio_path: Path, processed_dir: Path) -> Path:
    return processed_dir / f"{audio_path.stem}.json"


def cached_result_exists(audio_path: Path, processed_dir: Path) -> bool:
    return output_path_for(audio_path, processed_dir).exists()