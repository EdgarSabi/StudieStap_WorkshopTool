"""
Phase 2 experiment entry point: take an existing Phase 1 transcript JSON,
run speaker diarization on its audio, couple speaker labels onto the
timestamped segments, and write an enriched transcript JSON.

This is a research / inspection script, NOT the final pipeline. It does not
do any didactic classification.

Usage:
    python run_diarization.py --transcript ../Data-local/processed/benchmark/testaudio4_medium.json
    python run_diarization.py --transcript <json> --audio testaudio4_fragment.mp3 --dir test --max-speakers 4
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from config import (
    DiarizationConfig,
    DIARIZATION_OUTPUT_DIR,
    RAW_DATA_DIR,
    TEST_FILES_DIR,
)
from models.schema import WorkshopTranscript
from diarization import get_backend
from diarization.labeling import build_label_map
from diarization.assign import assign_speakers, summarize

_WAV_SUFFIXES = {".wav"}


def _resolve_audio(transcript: WorkshopTranscript, audio_arg: str | None, dir_arg: str) -> Path:
    if audio_arg:
        base = TEST_FILES_DIR if dir_arg == "test" else RAW_DATA_DIR
        candidate = Path(audio_arg)
        return candidate if candidate.is_absolute() else base / audio_arg
    return Path(transcript.audio_file)


def _to_wav(audio_path: Path, out_dir: Path, force: bool) -> Path:
    """pyannote is happiest with 16 kHz mono wav; convert non-wav inputs with ffmpeg."""
    if audio_path.suffix.lower() in _WAV_SUFFIXES:
        return audio_path

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("ffmpeg not found on PATH — needed to convert audio to wav for diarization.")

    out_dir.mkdir(parents=True, exist_ok=True)
    wav_path = out_dir / f"{audio_path.stem}_16k_mono.wav"
    if wav_path.exists() and not force:
        print(f"Reusing existing {wav_path.name} (use --force to reconvert).")
        return wav_path

    print(f"Converting {audio_path.name} -> {wav_path.name} (16 kHz mono)...")
    subprocess.run(
        [ffmpeg, "-y", "-i", str(audio_path), "-ac", "1", "-ar", "16000", str(wav_path)],
        check=True,
        capture_output=True,
    )
    return wav_path


def main():
    parser = argparse.ArgumentParser(description="Phase 2: couple diarization onto a transcript JSON")
    parser.add_argument("--transcript", required=True, help="Path to a Phase 1 transcript JSON")
    parser.add_argument("--audio", default=None, help="Override audio file (filename inside --dir, or a path)")
    parser.add_argument("--dir", choices=["raw", "test"], default="test")
    parser.add_argument("--min-speakers", type=int, default=None)
    parser.add_argument("--max-speakers", type=int, default=None)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--out", default=None, help="Output JSON path (default: Data-local/processed/diarization/)")
    parser.add_argument("--force", action="store_true", help="Redo wav conversion and overwrite output")
    args = parser.parse_args()

    transcript_path = Path(args.transcript)
    if not transcript_path.exists():
        sys.exit(f"Transcript JSON not found: {transcript_path}")
    transcript = WorkshopTranscript.model_validate_json(transcript_path.read_text(encoding="utf-8"))

    audio_path = _resolve_audio(transcript, args.audio, args.dir)
    if not audio_path.exists():
        sys.exit(f"Audio file not found: {audio_path}")

    DIARIZATION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else DIARIZATION_OUTPUT_DIR / f"{transcript_path.stem}_diarized.json"
    if out_path.exists() and not args.force:
        sys.exit(f"{out_path} already exists. Use --force to overwrite.")

    wav_path = _to_wav(audio_path, DIARIZATION_OUTPUT_DIR, args.force)

    config = DiarizationConfig(
        device=args.device,
        min_speakers=args.min_speakers,
        max_speakers=args.max_speakers,
    )

    print(f"Loading diarization backend '{config.backend}' ({config.hf_model}) on {config.device}...")
    backend = get_backend(config)

    print(f"Diarizing {wav_path.name}...")
    result = backend.diarize(
        wav_path, min_speakers=config.min_speakers, max_speakers=config.max_speakers
    )

    label_info = build_label_map(result, main_speaker_min_share=config.main_speaker_min_share)
    new_segments = assign_speakers(
        transcript.segments,
        result.turns,
        label_info["map"],
        overlap_min_ratio=config.overlap_min_ratio,
        uncertain_coverage_below=config.uncertain_coverage_below,
        uncertain_margin_below=config.uncertain_margin_below,
    )
    stats = summarize(new_segments)

    diarization_meta = {
        "backend": result.backend,
        "model": result.model,
        "settings": result.settings,
        "runtime_seconds": result.runtime_seconds,
        "n_turns": len(result.turns),
        "raw_speakers": result.raw_speakers,
        "label_map": label_info["map"],
        "speaker_inventory": label_info["inventory"],
        "main_speaker_uncertain": label_info["main_speaker_uncertain"],
        "assignment_settings": {
            "overlap_min_ratio": config.overlap_min_ratio,
            "uncertain_coverage_below": config.uncertain_coverage_below,
            "uncertain_margin_below": config.uncertain_margin_below,
        },
        "assignment": stats,
        "source_transcript": transcript_path.name,
        "audio_file": str(audio_path),
    }

    enriched = transcript.model_copy(update={"segments": new_segments, "diarization": diarization_meta})
    out_path.write_text(enriched.model_dump_json(indent=2), encoding="utf-8")

    print("\n--- diarization summary ---")
    print(f"raw speakers      : {result.raw_speakers}  ({len(result.turns)} turns)")
    for row in label_info["inventory"]:
        print(f"  {row['label']:<16} <- {row['raw']:<12} {row['talk_seconds']:>7.1f}s  ({row['share']*100:4.1f}%)")
    print(f"segments          : {stats['segments']}")
    print(f"  per label       : {json.dumps(stats['per_label'])}")
    print(f"  overlap         : {stats['overlap_segments']}")
    print(f"  uncertain       : {stats['uncertain_segments']}")
    print(f"  unassigned      : {stats['unassigned_segments']}")
    print(f"diarization time  : {result.runtime_seconds}s")
    print(f"\nwritten to {out_path}")


if __name__ == "__main__":
    main()
