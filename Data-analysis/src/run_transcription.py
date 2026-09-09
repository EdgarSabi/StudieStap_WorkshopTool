"""
Phase 1 test entry point: audio file -> structured transcript JSON.

This is NOT the final pipeline CLI (that's Phase 12 / section 15 of the
spec) — just a small script to validate transcription on its own.

Usage:
    python run_transcription.py breinschade.mp3
    python run_transcription.py breinschade.mp3 --model small --force
"""
import argparse
import sys

from config import TranscriptionConfig, RAW_DATA_DIR, PROCESSED_DATA_DIR
from transcription.engine import TranscriptionEngine
from transcription.cache import cached_result_exists, output_path_for


def main():
    parser = argparse.ArgumentParser(description="Phase 1: audio -> transcript JSON")
    parser.add_argument("audio_filename", help="Filename inside Data-local/raw/")
    parser.add_argument("--model", default="base", help="Whisper model size")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--force", action="store_true", help="Re-transcribe even if a cached output exists")
    args = parser.parse_args()

    audio_path = RAW_DATA_DIR / args.audio_filename
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not args.force and cached_result_exists(audio_path, PROCESSED_DATA_DIR):
        print(f"Cached transcript already exists at "
              f"{output_path_for(audio_path, PROCESSED_DATA_DIR)}. Use --force to redo.")
        sys.exit(0)

    config = TranscriptionConfig(
        model_size=args.model,
        device=args.device,
        compute_type=args.compute_type,
    )

    print(f"Loading model '{config.model_size}' on {config.device} ({config.compute_type})...")
    engine = TranscriptionEngine(config)

    print(f"Transcribing {audio_path}...")
    result = engine.transcribe(audio_path)

    out_path = output_path_for(audio_path, PROCESSED_DATA_DIR)
    out_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    print(f"Done in {result.transcription_time_seconds}s. "
          f"{len(result.segments)} segments written to {out_path}")


if __name__ == "__main__":
    main()