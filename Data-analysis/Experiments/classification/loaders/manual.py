"""
STAP 2 — loader for hand-written test transcripts.

Expected format (see Data-local/raw/classification/test_classification_01.json):
    {
      "fragment_id": "...",
      "speaker_mapping": {"MAIN_SPEAKER": "DOCENT", "OTHER_SPEAKER": "LEERLING"},
      "turns": [{"turn_id": 1, "speaker": "MAIN_SPEAKER", "text": "..."}, ...]
    }

No timestamps, no uncertainty/overlap signal — that information simply
doesn't exist for a hand-written transcript, so uncertain_assignment/overlap
are left None ("unknown"), never defaulted to False ("known clean"). See
schemas/turn.py's module docstring for why that distinction matters.
"""
import json
from pathlib import Path

from schemas.turn import ClassificationTurn, FragmentTurns


def load_manual_fixture(path: Path) -> FragmentTurns:
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    turns = [
        ClassificationTurn(
            turn_id=t["turn_id"],
            speaker=t.get("speaker"),
            text=t["text"],
            start=t.get("start"),   # usually absent -> None
            end=t.get("end"),
            uncertain_assignment=None,  # no such signal in a hand-written transcript
            overlap=None,
            source="manual",
        )
        for t in data["turns"]
    ]

    return FragmentTurns(
        fragment_id=data["fragment_id"],
        source="manual",
        source_path=str(path),
        speaker_mapping=data.get("speaker_mapping"),
        turns=turns,
    )
