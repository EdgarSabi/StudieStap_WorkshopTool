# EXPERIMENT ONLY
# Does not modify Data-analysis/src/transcription/engine.py or models/schema.py.
"""
STAP 2 — word_timestamps=True experiment.

TranscriptionConfig.word_timestamps already exists as a flag and is already
passed to faster-whisper's WhisperModel.transcribe() (see
Data-analysis/src/transcription/engine.py), but the per-word output
(faster_whisper.transcribe.Segment.words -> list[Word(start,end,word,
probability)]) is never read or stored anywhere: TranscriptSegment has no
`words` field, so it's silently discarded today.

This script does NOT touch engine.py or schema.py. It calls WhisperModel
directly (same pattern as the Afgeronde_experimenten/diarization/community1
and diarization/whisperx experiments — a thin, separate script reusing config,
not the pipeline's own
conversion code), with the EXACT same transcribe kwargs the baseline pipeline
used for these fragments (see transcription_config in
Data-local/processed/<fragment>.json), except word_timestamps=True. That way
word_timestamps is the only variable, and any segmentation/text difference
from the baseline is attributable to that flag (or ordinary run-to-run
nondeterminism) rather than a config change.

Also runs a few cheap reliability checks on the returned word timestamps
(monotonicity, zero-duration words, words outside their segment's bounds,
low per-word probability) — see "word_timestamp_checks" in the output.

Input:  Data-analysis/src/test-files/<fragment>.mp3
Output: Data-local/processed/word_level_speaker_attribution/<fragment>_words.json

Usage (existing project venv, no new installs):
    Data-analysis\\src\\.venv\\Scripts\\python.exe extract_word_timestamps.py
    Data-analysis\\src\\.venv\\Scripts\\python.exe extract_word_timestamps.py --fragment testaudio1_fragment --force
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _common as common  # noqa: E402

from faster_whisper import WhisperModel  # noqa: E402

EXPERIMENT_NAME = "word_timestamps"


def _check_word_timestamps(segments: list[dict]) -> dict:
    """Cheap, mechanical reliability checks — not a correctness judgement
    about *which* speaker said a word, just: do the timestamps make sense."""
    n_words = 0
    n_zero_or_negative_duration = 0
    n_nonmonotonic_within_segment = 0  # a word starting before the previous word ended by more than a hair
    n_outside_segment_bounds = 0       # word start/end falls outside [segment.start, segment.end] by > 0.02s
    n_low_probability = 0              # faster-whisper's own per-word confidence < 0.5
    durations = []
    probabilities = []

    for seg in segments:
        words = seg["words"]
        prev_end = None
        for w in words:
            n_words += 1
            dur = w["end"] - w["start"]
            durations.append(dur)
            probabilities.append(w["probability"])
            if dur <= 0:
                n_zero_or_negative_duration += 1
            if prev_end is not None and w["start"] < prev_end - 0.01:
                n_nonmonotonic_within_segment += 1
            if w["start"] < seg["start"] - 0.02 or w["end"] > seg["end"] + 0.02:
                n_outside_segment_bounds += 1
            if w["probability"] < 0.5:
                n_low_probability += 1
            prev_end = w["end"]

    return {
        "n_words_total": n_words,
        "n_zero_or_negative_duration": n_zero_or_negative_duration,
        "n_nonmonotonic_within_segment": n_nonmonotonic_within_segment,
        "n_outside_segment_bounds": n_outside_segment_bounds,
        "n_low_probability_lt_0.5": n_low_probability,
        "mean_word_duration_s": round(sum(durations) / len(durations), 4) if durations else None,
        "min_word_duration_s": round(min(durations), 4) if durations else None,
        "mean_word_probability": round(sum(probabilities) / len(probabilities), 4) if probabilities else None,
        "min_word_probability": round(min(probabilities), 4) if probabilities else None,
    }


def run_one(fragment: str, model: WhisperModel, transcribe_kwargs: dict, force: bool) -> dict:
    audio_path = common.audio_path(fragment)
    if not audio_path.exists():
        sys.exit(f"Audio not found: {audio_path}")

    out_path = common.OUTPUT_DIR / f"{fragment}_words.json"
    if out_path.exists() and not force:
        sys.exit(f"{out_path} already exists. Pass --force to overwrite.")

    print(f"[{fragment}] transcribing with word_timestamps=True ...")
    t0 = time.time()
    segments_iter, info = model.transcribe(str(audio_path), **transcribe_kwargs)

    segments = []
    for seg in segments_iter:
        words = [
            {
                "word": w.word,
                "start": round(w.start, 4),
                "end": round(w.end, 4),
                "probability": round(w.probability, 4),
            }
            for w in (seg.words or [])
        ]
        segments.append({
            "start": round(seg.start, 4),
            "end": round(seg.end, 4),
            "text": seg.text.strip(),
            "avg_logprob": seg.avg_logprob,
            "no_speech_prob": seg.no_speech_prob,
            "compression_ratio": seg.compression_ratio,
            "words": words,
        })
    elapsed = round(time.time() - t0, 2)

    checks = _check_word_timestamps(segments)

    output = {
        "experiment": EXPERIMENT_NAME,
        "audio_file": str(audio_path),
        "model_size": common.ASR_MODEL_SIZE,
        "transcription_config": transcribe_kwargs,
        "duration": info.duration,
        "transcription_time_seconds": elapsed,
        "segments": segments,
        "word_timestamp_checks": checks,
    }

    common.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  segments: {len(segments)}   words: {checks['n_words_total']}   time: {elapsed}s")
    print(f"  mean word duration: {checks['mean_word_duration_s']}s   "
          f"mean word probability: {checks['mean_word_probability']}")
    print(f"  reliability flags -> zero/negative dur: {checks['n_zero_or_negative_duration']}, "
          f"nonmonotonic: {checks['n_nonmonotonic_within_segment']}, "
          f"outside segment bounds: {checks['n_outside_segment_bounds']}, "
          f"low prob(<0.5): {checks['n_low_probability_lt_0.5']}")
    print(f"  written to {out_path}\n")
    return output


def main():
    parser = argparse.ArgumentParser(description="STAP 2: faster-whisper word_timestamps=True experiment")
    parser.add_argument(
        "--fragment", action="append", dest="fragments",
        help="Fragment name (no extension), repeatable. Default: all 3 eval fragments.",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    fragments = args.fragments or common.EVAL_FRAGMENTS

    cfg = common.base_transcription_config()
    print(f"Loading whisper model '{cfg.model_size}' on {cfg.device} ({cfg.compute_type}) ...")
    model = WhisperModel(cfg.model_size, device=cfg.device, compute_type=cfg.compute_type)

    # Identical to the baseline pipeline's own transcribe_kwargs (see
    # transcription/engine.py), except word_timestamps=True.
    transcribe_kwargs = dict(
        language=cfg.language,
        beam_size=cfg.beam_size,
        condition_on_previous_text=cfg.condition_on_previous_text,
        repetition_penalty=cfg.repetition_penalty,
        no_repeat_ngram_size=cfg.no_repeat_ngram_size,
        word_timestamps=True,
        hallucination_silence_threshold=cfg.hallucination_silence_threshold,
        vad_filter=cfg.vad_filter,
        vad_parameters=cfg.vad_parameters,
        log_prob_threshold=cfg.log_prob_threshold,
        no_speech_threshold=cfg.no_speech_threshold,
        compression_ratio_threshold=cfg.compression_ratio_threshold,
    )

    for fragment in fragments:
        run_one(fragment, model, transcribe_kwargs, args.force)


if __name__ == "__main__":
    main()
