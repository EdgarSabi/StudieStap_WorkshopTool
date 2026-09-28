"""
Gemakskoppeling: draait de volledige route in één keer —
transcriptie -> diarisatie -> preprocessing -> docentherkenning.

Roept gewoon de vier bestaande scripts na elkaar aan (run_transcription.py,
run_diarization.py, run_preprocessing.py, run_docent_recognition.py) met de
bestandsnamen die ze zelf al als conventie gebruiken. Bevat zelf GEEN nieuwe
logica — puur orkestratie, zodat je niet elke stap los hoeft te typen.

Gebruik:
    .venv\\Scripts\\python.exe run_docent_pipeline.py testaudio6_fragment.mp3

    # met een andere docentreferentie of ander model:
    .venv\\Scripts\\python.exe run_docent_pipeline.py testaudio6_fragment.mp3 --reference test-files/andere_docent.mp3 --model medium

    # audio uit Data-local/raw i.p.v. test-files:
    .venv\\Scripts\\python.exe run_docent_pipeline.py opname.mp3 --dir raw
"""
import argparse
import subprocess
import sys
from pathlib import Path

from config import PROCESSED_DATA_DIR, DIARIZATION_OUTPUT_DIR, PREPROCESSING_OUTPUT_DIR, DOCENT_RECOGNITION_OUTPUT_DIR

SCRIPT_DIR = Path(__file__).resolve().parent


def run_step(step_number: int, description: str, args: list[str]) -> None:
    print(f"\n=== Stap {step_number}/4: {description} ===", flush=True)
    result = subprocess.run([sys.executable, *args], cwd=SCRIPT_DIR)
    if result.returncode != 0:
        sys.exit(
            f"\nStap {step_number} ({description}) is gestopt (zie foutmelding hierboven). "
            f"Als het klaagt dat output al bestaat, voeg --force toe aan dit script."
        )


def main():
    parser = argparse.ArgumentParser(description="Draait transcriptie t/m docentherkenning in één keer.")
    parser.add_argument("audio_filename", help="Bestandsnaam van de audio, bv. testaudio6_fragment.mp3")
    parser.add_argument("--dir", choices=["raw", "test"], default="test",
                         help="'test' = Data-analysis/src/test-files, 'raw' = Data-local/raw (default: test)")
    parser.add_argument("--reference", default="test-files/testdocent.mp3",
                         help="Pad naar de docentreferentie-audio (default: test-files/testdocent.mp3)")
    parser.add_argument("--model", default="medium", help="Whisper-modelgrootte (default: medium)")
    parser.add_argument("--threshold", type=float, default=None, help="Override de similarity-drempel voor docentrol")
    parser.add_argument("--force", action="store_true", help="Bestaande output overschrijven bij elke stap")
    args = parser.parse_args()

    stem = Path(args.audio_filename).stem
    force = ["--force"] if args.force else []

    # Stap 1: transcriptie
    run_step(1, "transcriptie", [
        "run_transcription.py", args.audio_filename, "--dir", args.dir, "--model", args.model, *force,
    ])
    transcript_path = PROCESSED_DATA_DIR / f"{stem}.json"

    # Stap 2: diarisatie
    run_step(2, "diarisatie", [
        "run_diarization.py", "--transcript", str(transcript_path), *force,
    ])
    diarized_path = DIARIZATION_OUTPUT_DIR / f"{stem}_diarized.json"

    # Stap 3: preprocessing (segmenten -> spreekbeurten + context)
    run_step(3, "preprocessing", [
        "run_preprocessing.py", "--diarized", str(diarized_path), *force,
    ])
    processed_path = PREPROCESSING_OUTPUT_DIR / f"{diarized_path.stem}_turns.json"

    # Stap 4: docentherkenning (vergelijkt elke spreekbeurt met de referentiestem)
    threshold_args = ["--threshold", str(args.threshold)] if args.threshold is not None else []
    run_step(4, "docentherkenning", [
        "run_docent_recognition.py", "--processed", str(processed_path), "--reference", args.reference,
        *threshold_args, *force,
    ])
    out_path = DOCENT_RECOGNITION_OUTPUT_DIR / f"{processed_path.stem}_docent_roles.json"

    print(f"\nKlaar. Eindresultaat (spreekbeurten + docentrol):\n  {out_path}")


if __name__ == "__main__":
    main()
