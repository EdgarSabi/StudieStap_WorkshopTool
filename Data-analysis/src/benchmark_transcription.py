"""
Phase 1 benchmark: run the same audio through multiple Whisper model
sizes, save each result separately, and print a comparison summary.
Does NOT decide which model is "best" — that's a manual inspection step.

Usage:
    python benchmark_transcription.py --audio testaudio2.mp3 --dir test --models base small medium
"""
import argparse

from config import TranscriptionConfig, RAW_DATA_DIR, TEST_FILES_DIR, BENCHMARK_OUTPUT_DIR, SUPPORTED_MODELS
from transcription.engine import TranscriptionEngine


def main():
    parser = argparse.ArgumentParser(description="Benchmark: same audio through multiple whisper models")
    parser.add_argument("--audio", required=True, help="Filename inside the chosen --dir")
    parser.add_argument("--dir", choices=["raw", "test"], default="raw")
    parser.add_argument("--models", nargs="+", default=["base"], help=f"Any of: {SUPPORTED_MODELS}")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    args = parser.parse_args()

    input_dir = TEST_FILES_DIR if args.dir == "test" else RAW_DATA_DIR
    audio_path = input_dir / args.audio
    BENCHMARK_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for model_size in args.models:
        print(f"\n=== Model: {model_size} ===")
        config = TranscriptionConfig(model_size=model_size, device=args.device, compute_type=args.compute_type)
        engine = TranscriptionEngine(config)
        result = engine.transcribe(audio_path)

        out_path = BENCHMARK_OUTPUT_DIR / f"{audio_path.stem}_{model_size}.json"
        out_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

        flagged = sum(1 for s in result.segments if s.quality_flags)
        results.append((model_size, result.transcription_time_seconds, len(result.segments), flagged))
        print(f"  {len(result.segments)} segments, {flagged} flagged, {result.transcription_time_seconds}s -> {out_path}")

    print("\nMODEL       TIME       SEGMENTS   FLAGGED")
    for model_size, t, n_seg, n_flag in results:
        print(f"{model_size:<11} {t:<10} {n_seg:<10} {n_flag}")


if __name__ == "__main__":
    main()