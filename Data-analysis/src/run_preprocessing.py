"""
Phase 3 experiment entry point: turn a Phase 2 diarized transcript JSON into
a ProcessedTranscript (speaker turns + structural context flags), as input
for later didactic-behaviour classification. No classification happens here.

Usage:
    python run_preprocessing.py --diarized ../../Data-local/processed/diarization/testaudio4_fragment_medium_diarized.json
    python run_preprocessing.py --diarized <json> --max-gap-within-turn 1.0 --large-context-gap 4.0
"""
import argparse
import sys
from pathlib import Path

from config import PreprocessingConfig, PREPROCESSING_OUTPUT_DIR
from models.schema import WorkshopTranscript
from models.processed import ProcessedTranscript
from preprocessing.turns import build_speaker_turns
from preprocessing.context import attach_context
from preprocessing.turn_stats import duration_by_speaker, turn_span_by_speaker, count_speaker_switches


def main():
    parser = argparse.ArgumentParser(description="Phase 3: group diarized segments into speaker turns + context")
    parser.add_argument("--diarized", required=True, help="Path to a Phase 2 diarized transcript JSON")
    parser.add_argument("--out", default=None, help="Output JSON path (default: Data-local/processed/preprocessing/)")
    parser.add_argument("--max-gap-within-turn", type=float, default=None, help="Override PreprocessingConfig default")
    parser.add_argument("--large-context-gap", type=float, default=None, help="Override PreprocessingConfig default")
    args = parser.parse_args()

    src_path = Path(args.diarized)
    if not src_path.exists():
        sys.exit(f"Not found: {src_path}")
    transcript = WorkshopTranscript.model_validate_json(src_path.read_text(encoding="utf-8"))

    cfg = PreprocessingConfig()
    if args.max_gap_within_turn is not None:
        cfg.max_gap_within_turn_seconds = args.max_gap_within_turn
    if args.large_context_gap is not None:
        cfg.large_context_gap_seconds = args.large_context_gap

    turns = build_speaker_turns(transcript.segments, max_gap_within_turn_seconds=cfg.max_gap_within_turn_seconds)
    turns = attach_context(turns, large_context_gap_seconds=cfg.large_context_gap_seconds)

    processed = ProcessedTranscript(
        source_transcript_path=str(src_path),
        audio_file=transcript.audio_file,
        language=transcript.language,
        duration=transcript.duration,
        model_size=transcript.model_size,
        original_segment_count=len(transcript.segments),
        turns=turns,
        preprocessing_config={
            "max_gap_within_turn_seconds": cfg.max_gap_within_turn_seconds,
            "large_context_gap_seconds": cfg.large_context_gap_seconds,
        },
    )

    PREPROCESSING_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else PREPROCESSING_OUTPUT_DIR / f"{src_path.stem}_turns.json"
    out_path.write_text(processed.model_dump_json(indent=2), encoding="utf-8")

    n_overlap = sum(1 for t in turns if t.overlap)
    n_uncertain = sum(1 for t in turns if t.uncertain_assignment)
    n_no_ctx_before = sum(1 for t in turns if not t.context_available_before)
    n_no_ctx_after = sum(1 for t in turns if not t.context_available_after)
    n_unc_ctx_before = sum(1 for t in turns if t.context_uncertain_before)
    n_unc_ctx_after = sum(1 for t in turns if t.context_uncertain_after)

    print(f"segments -> turns        : {len(transcript.segments)} -> {len(turns)}")
    print(f"speaking time by speaker : {duration_by_speaker(turns)}  (sum of source-segment durations)")
    print(f"turn_span by speaker     : {turn_span_by_speaker(turns)}  (turn.end-turn.start, incl. gaps within a turn)")
    print(f"speaker switches         : {count_speaker_switches(turns)}")
    print(f"overlap turns            : {n_overlap}")
    print(f"uncertain turns          : {n_uncertain}")
    print(f"no context before/after  : {n_no_ctx_before} / {n_no_ctx_after}")
    print(f"uncertain context b/a    : {n_unc_ctx_before} / {n_unc_ctx_after}")
    print(f"written to {out_path}")


if __name__ == "__main__":
    main()
