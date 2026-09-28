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

docent_role is likewise left None: no voice recognition ever ran on a
hand-written transcript. `speaker_mapping` (e.g. {"MAIN_SPEAKER": "DOCENT"})
is a human-authored label for a synthetic scenario, not a recognition
result — it is kept on FragmentTurns as separate, informational metadata
and deliberately NOT copied into docent_role, so the two kinds of "this is
the teacher" information (asserted vs. recognized) never get conflated.
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
