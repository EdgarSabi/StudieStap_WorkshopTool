"""JSON-uitvoer, herkomst (provenance) en het verwijderen van runs.

Elke run krijgt een eigen map met losse JSON-bestanden:

    01_transcript.json        ruwe Whisper-uitvoer
    02_diarization_raw.json   ruwe sprekerintervallen (incl. overlap)
    03_word_alignment.json    woorduitlijning + status
    04_speaker_assignment.json  afgeleide sprekerkoppeling
    05_teacher_roles.json     docentherkenning (identiteit gescheiden van rol)
    06_quality.json           kwaliteitssignalen
    07_result.json            alles samengevoegd, met verwijzingen naar de delen
    run_manifest.json         configuratie, versies, stappen en hashes
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

from ..models import StudieStapError, to_dict

MANIFEST_NAME = "run_manifest.json"


def write_json(path: Path, obj: Any) -> str:
    """Schrijf JSON (atomisch: eerst tijdelijk bestand) en geef de sha256 van de inhoud terug."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(to_dict(obj), indent=2, ensure_ascii=False).encode("utf-8")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)  # bytes: Windows zou in tekstmodus \n in \r\n veranderen en de hash laten afwijken
    os.replace(tmp, path)
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def delete_run(run_dir: Path) -> None:
    """Verwijder een runmap. Veiligheid: alleen mappen met een run_manifest.json."""
    run_dir = Path(run_dir)
    if not (run_dir / MANIFEST_NAME).exists():
        raise StudieStapError(
            f"Dit lijkt geen StudieStap-runmap ({MANIFEST_NAME} ontbreekt): {run_dir}",
            hint="Uit voorzorg verwijderen we alleen mappen die door 'studiestap analyze/transcribe' zijn gemaakt.",
        )
    shutil.rmtree(run_dir)


def summary_for_database(result: dict) -> dict:
    """RESERVERING voor een toekomstige SQLite-export. Bouwt nog geen database.

    Bevat uitsluitend geaggregeerde, privacyveilige getallen: GEEN tekst, GEEN
    audiopad, GEEN embeddings en geen sprekerlabels per uitspraak.
    """
    segments = result.get("segments", [])
    return {
        "audio_sha256": result["audio"]["sha256"],
        "duration_seconds": result["audio"]["duration_seconds"],
        "n_segments": len(segments),
        "n_raw_speakers": len(result.get("raw_speakers", [])),
        "n_segments_review_required": sum(
            1 for s in segments if s["quality"]["status"] == "REVIEW_REQUIRED"),
        "n_segments_with_multiple_speakers": sum(
            1 for s in segments if s["speakers"] and s["speakers"]["attribution"] == "MIXED"),
        "word_alignment_status": result["steps"].get("word_alignment", {}).get("status"),
    }
