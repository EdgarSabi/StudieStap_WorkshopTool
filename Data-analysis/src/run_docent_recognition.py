"""
Phase 4 entry point: attach a `docent_role` (DOCENT/OTHER/ONZEKER) to each
speaker turn of a Phase 3 ProcessedTranscript, by comparing each turn's own
audio to a teacher reference recording (pyannote WeSpeaker embeddings).

This is a research / inspection script, same status as run_diarization.py
and run_preprocessing.py — not a didactic classifier. `docent_role` is kept
strictly separate from `speaker` (the diarization identity/talk-time
heuristic): MAIN_SPEAKER does NOT automatically become DOCENT here — see
models/processed.py's SpeakerTurn docstring and docent_recognition/assign.py
for the full decision rule.

Both the fragment audio and the reference audio are explicit, configurable
paths — nothing here is hardcoded to the three test fragments or to
testdocent.mp3, so this works with any workshop recording and any teacher's
own reference clip.

Usage:
    python run_docent_recognition.py \\
        --processed ../../Data-local/processed/preprocessing/<fragment>_turns.json \\
        --reference ../../Data-local/raw/<docent_reference>.mp3

    # override which fragment audio to slice (defaults to the audio_file
    # already recorded in the ProcessedTranscript):
    python run_docent_recognition.py --processed <turns.json> --reference <ref.mp3> \\
        --audio <path/to/fragment.mp3> --threshold 0.4 --min-duration 1.5
"""
import argparse
import json
import sys
import time
from pathlib import Path

from config import DocentRecognitionConfig, DOCENT_RECOGNITION_OUTPUT_DIR, DIARIZATION_OUTPUT_DIR
from models.processed import ProcessedTranscript
from diarization.pyannote_backend import _load_wav_waveform
from docent_recognition import DocentReferenceRecognizer, assign_docent_roles, summarize_docent_roles
from run_diarization import _to_wav


def main():
    parser = argparse.ArgumentParser(description="Phase 4: attach docent_role to a ProcessedTranscript's turns")
    parser.add_argument("--processed", required=True, help="Path to a Phase 3 ProcessedTranscript JSON")
    parser.add_argument("--reference", required=True, help="Path to the teacher's reference audio (mp3/wav)")
    parser.add_argument("--audio", default=None, help="Override fragment audio path (default: audio_file in the ProcessedTranscript)")
    parser.add_argument("--threshold", type=float, default=None, help="Override DocentRecognitionConfig.similarity_threshold (experimental)")
    parser.add_argument("--min-duration", type=float, default=None, help="Override DocentRecognitionConfig.min_clip_duration_seconds")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--out", default=None, help="Output JSON path (default: Data-local/processed/docent_recognition/)")
    parser.add_argument("--force", action="store_true", help="Redo wav conversion and overwrite output")
    args = parser.parse_args()

    processed_path = Path(args.processed)
    if not processed_path.exists():
        sys.exit(f"ProcessedTranscript JSON not found: {processed_path}")
    processed = ProcessedTranscript.model_validate_json(processed_path.read_text(encoding="utf-8"))

    reference_path = Path(args.reference)
    if not reference_path.exists():
        sys.exit(f"Reference audio not found: {reference_path}")

    audio_path = Path(args.audio) if args.audio else Path(processed.audio_file)
    if not audio_path.exists():
        sys.exit(
            f"Fragment audio not found: {audio_path}\n"
            f"(from {'--audio' if args.audio else 'ProcessedTranscript.audio_file'}). "
            f"Pass --audio explicitly if the transcript's recorded path has moved."
        )

    config = DocentRecognitionConfig(reference_audio=str(reference_path), device=args.device)
    if args.threshold is not None:
        config.similarity_threshold = args.threshold
    if args.min_duration is not None:
        config.min_clip_duration_seconds = args.min_duration

    DOCENT_RECOGNITION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else DOCENT_RECOGNITION_OUTPUT_DIR / f"{processed_path.stem}_docent_roles.json"
    if out_path.exists() and not args.force:
        sys.exit(f"{out_path} already exists. Use --force to overwrite.")

    # Reuse the diarization step's wav cache dir for the fragment audio (same
    # audio, likely already converted there); the reference gets its own
    # cache dir since it isn't tied to any one fragment.
    fragment_wav = _to_wav(audio_path, DIARIZATION_OUTPUT_DIR, args.force)
    reference_wav = _to_wav(reference_path, DOCENT_RECOGNITION_OUTPUT_DIR, args.force)

    print(f"Loading docent recognition model '{config.embedding_model}' on {config.device} ...")
    t0 = time.time()
    recognizer = DocentReferenceRecognizer(reference_wav, config.embedding_model, device=config.device)
    model_load_seconds = round(time.time() - t0, 2)
    if recognizer.reference_warning:
        print(f"  (warning while embedding reference clip: {recognizer.reference_warning})")

    print(f"Comparing {len(processed.turns)} turns in {processed_path.name} against {reference_path.name} ...")
    fragment_waveform, fragment_sr = _load_wav_waveform(fragment_wav)

    t0 = time.time()
    new_turns = assign_docent_roles(processed.turns, fragment_waveform, fragment_sr, recognizer, config)
    assignment_seconds = round(time.time() - t0, 2)

    stats = summarize_docent_roles(new_turns)

    docent_recognition_meta = {
        "embedding_model": config.embedding_model,
        "reference_audio": str(reference_path),
        "similarity_threshold": config.similarity_threshold,
        "threshold_status": "experimentele instelling, niet gevalideerd als bewezen betrouwbaar criterium "
                             "(zie Experiments/speaker_recognition/comparison/results.md)",
        "min_clip_duration_seconds": config.min_clip_duration_seconds,
        "device": config.device,
        "model_load_seconds": model_load_seconds,
        "assignment_seconds": assignment_seconds,
        "source_processed_transcript": str(processed_path),
        "fragment_audio": str(audio_path),
        "summary": stats,
    }

    enriched = processed.model_copy(update={"turns": new_turns, "docent_recognition": docent_recognition_meta})
    out_path.write_text(enriched.model_dump_json(indent=2), encoding="utf-8")

    print("\n--- docent recognition summary ---")
    print(f"per role          : {stats['per_role']}")
    print(f"threshold (exp.)  : {config.similarity_threshold}")
    print(f"min clip duration : {config.min_clip_duration_seconds}s")
    print(f"model load        : {model_load_seconds}s   assignment: {assignment_seconds}s")
    print(f"\nwritten to {out_path}")


if __name__ == "__main__":
    main()
