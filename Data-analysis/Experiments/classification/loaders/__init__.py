"""
Single entry point: load_fragment() auto-detects which of the two supported
formats a JSON file is, so the rest of the pipeline (run_classification.py,
context selection, classification) only ever deals with one FragmentTurns
shape — same pipeline for both, per the requirement that a hand-written
transcript and an existing ProcessedTranscript JSON must both work through
the classification pipeline unchanged.

Detection is a simple top-level-key check: ProcessedTranscript (Phase 3
output) always has "source_transcript_path"; the manual format always has
"speaker_mapping". Anything else raises rather than guessing.
"""
import json
import sys
from pathlib import Path

# loaders/pipeline.py needs Data-analysis/src on sys.path (for
# `from models.processed import ProcessedTranscript`) regardless of which
# module imports `loaders` first — set that up here, at the package's own
# entry point, rather than relying on some other caller having done it.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _common  # noqa: E402,F401 — side effect only: puts Data-analysis/src on sys.path

from schemas.turn import FragmentTurns  # noqa: E402
from .manual import load_manual_fixture  # noqa: E402
from .pipeline import load_pipeline_processed  # noqa: E402


def load_fragment(path: Path) -> FragmentTurns:
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


__all__ = ["load_fragment", "load_manual_fixture", "load_pipeline_processed"]
