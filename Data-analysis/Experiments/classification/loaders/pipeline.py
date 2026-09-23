"""
STAP 2 — loader for existing pipeline output.

Reuses models.processed.ProcessedTranscript UNCHANGED (Phase 3 output, e.g.
Data-local/processed/preprocessing/<fragment>_turns.json) — the production
schema is parsed as-is, nothing added or modified in Data-analysis/src.

Unlike the manual loader, real uncertainty/overlap information EXISTS here
(the automated diarization pipeline computed it) and is carried over as the
actual True/False value from SpeakerTurn — never dropped, never reset to
None. This is the concrete difference the classification pipeline relies on
to tell "known clean" apart from "unknown" (see schemas/turn.py).
"""
from pathlib import Path

from models.processed import ProcessedTranscript
from schemas.turn import ClassificationTurn, FragmentTurns


def load_pipeline_processed(path: Path) -> FragmentTurns:
    processed = ProcessedTranscript.model_validate_json(Path(path).read_text(encoding="utf-8"))

    turns = [
        ClassificationTurn(
            turn_id=t.turn_id,
            speaker=t.speaker,
            text=t.text,
            start=t.start,
            end=t.end,
            uncertain_assignment=t.uncertain_assignment,  # real, known value — preserved as-is
            overlap=t.overlap,                              # real, known value — preserved as-is
            source="pipeline_processed",
        )
        for t in processed.turns
    ]

    return FragmentTurns(
        fragment_id=Path(path).stem,
        source="pipeline_processed",
        source_path=str(path),
        speaker_mapping=None,
        turns=turns,
    )
