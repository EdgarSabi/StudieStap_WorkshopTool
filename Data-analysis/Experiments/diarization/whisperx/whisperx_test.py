# EXPERIMENT ONLY
# Does not replace the existing diarization pipeline.
"""
Experiment B: WhisperX (word-level forced alignment) + pyannote diarization,
to test whether WORD-level speaker assignment solves the problem the baseline
has: one faster-whisper SEGMENT (e.g. "Dit ben jij. Dit ben ik.") can contain
speech from two different people, but the baseline's assign_speakers() can
only give the whole segment one speaker label.

This is a FULLY SEPARATE experiment, run in its own venv (.venv-whisperx,
Python 3.12) with its own dependency set (requirements-whisperx.txt) — see
that file's header for why. It does NOT import faster-whisper, WhisperModel,
or anything from Data-analysis/src/transcription — WhisperX bundles its own
faster-whisper-based ASR internally.

Reused from Data-analysis/src (both are pure-python, no pydantic/faster-whisper
dependency, so they import cleanly in this separate venv):
  - config.TEST_FILES_DIR / PROCESSED_DATA_DIR / get_hf_token()
  - diarization.base.SpeakerTurn / DiarizationResult
  - diarization.labeling.build_label_map   (raw speaker -> MAIN/OTHER_n, same
    heuristic as the baseline, applied here to whisperx's diarization turns
    so the two experiments' speaker labels read the same way)

Deliberately NOT reused: diarization.assign.assign_speakers — that module
assigns one speaker per *segment* by time-overlap geometry, which is exactly
the limitation this experiment tests an alternative to. WhisperX's own
whisperx.diarize.assign_word_speakers() does the equivalent job at WORD level
instead, which is the whole point of Experiment B.

Pipeline per fragment: load audio -> whisperx ASR (medium) -> forced alignment
(wav2vec2, word timestamps) -> pyannote diarization -> assign_word_speakers()
(per-word AND per-segment speaker) -> two output JSONs.

Input:  Data-analysis/src/test-files/<fragment>.mp3   (same audio as baseline)
Output: Data-local/processed/diarization_experiments/whisperx/
          <fragment>_whisperx_raw.json         (near-raw whisperx output)
          <fragment>_whisperx_normalized.json  (project-style segments + readable turns)

Usage (from THIS folder, with the isolated venv):
    .venv-whisperx\\Scripts\\python.exe whisperx_test.py
    .venv-whisperx\\Scripts\\python.exe whisperx_test.py --fragment testaudio5_fragment --force
"""
import argparse
import json
import sys
import time
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(SRC_DIR))

from config import PROCESSED_DATA_DIR, TEST_FILES_DIR, get_hf_token  # noqa: E402
from diarization.base import SpeakerTurn, DiarizationResult  # noqa: E402
from diarization.labeling import build_label_map  # noqa: E402

import whisperx  # noqa: E402
from whisperx.diarize import DiarizationPipeline, assign_word_speakers  # noqa: E402

EXPERIMENT_NAME = "whisperx_pyannote"
# Pinned to the SAME diarization model as the baseline (not community-1) on
# purpose: this experiment isolates the effect of word-level forced alignment
# on speaker assignment. Comparing diarization MODELS is Experiment A's job.
DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"
ALIGN_MODEL_NL = "jonatasgrosman/wav2vec2-large-xlsr-53-dutch"  # whisperx's default for language_code="nl"

OUTPUT_DIR = PROCESSED_DATA_DIR / "diarization_experiments" / "whisperx"
DEFAULT_FRAGMENTS = ["testaudio1_fragment", "testaudio2_fragment"]


def _reconstruct_turns(segments: list[dict]) -> list[dict]:
    """Merge consecutive words with the same (friendly) speaker label into
    readable turns, e.g. [{"speaker": "MAIN_SPEAKER", "text": "Dit ben jij."},
    {"speaker": "OTHER_SPEAKER_1", "text": "Dit ben ik."}] — regardless of
    which whisper SEGMENT boundary the words originally fell in."""
    turns = []
    current_speaker = None
    current_words: list[str] = []

    def flush():
        if current_words:
            turns.append({"speaker": current_speaker, "text": " ".join(current_words)})

    for seg in segments:
        for w in seg.get("words", []):
            speaker = w.get("speaker")
            if speaker != current_speaker:
                flush()
                current_speaker = speaker
                current_words = []
            current_words.append(w.get("word", "").strip())
    flush()
    return turns


def run_one(fragment: str, whisper_model, align_model, align_metadata, diarize_model, args) -> None:
    audio_path = TEST_FILES_DIR / f"{fragment}.mp3"
    if not audio_path.exists():
        sys.exit(f"Audio not found: {audio_path}")

    out_raw = OUTPUT_DIR / f"{fragment}_whisperx_raw.json"
    out_norm = OUTPUT_DIR / f"{fragment}_whisperx_normalized.json"
    if (out_raw.exists() or out_norm.exists()) and not args.force:
        sys.exit(f"{out_raw.name}/{out_norm.name} already exist in {OUTPUT_DIR}. Pass --force to overwrite.")

    print(f"[{fragment}] loading audio ...")
    audio = whisperx.load_audio(str(audio_path))

    timings = {}

    print(f"[{fragment}] ASR (whisper {args.model}) ...")
    t0 = time.time()
    asr_result = whisper_model.transcribe(audio, batch_size=args.batch_size, language=args.language)
    timings["asr_seconds"] = round(time.time() - t0, 2)

    print(f"[{fragment}] forced alignment ({ALIGN_MODEL_NL}) ...")
    t0 = time.time()
    aligned_result = whisperx.align(
        asr_result["segments"], align_model, align_metadata, audio, args.device,
        return_char_alignments=False,
    )
    timings["alignment_seconds"] = round(time.time() - t0, 2)

    print(f"[{fragment}] diarization ({DIARIZATION_MODEL}) ...")
    t0 = time.time()
    diarize_df = diarize_model(audio)
    timings["diarization_seconds"] = round(time.time() - t0, 2)

    result = assign_word_speakers(diarize_df, aligned_result)
    timings["total_seconds"] = round(sum(timings.values()), 2)

    # --- friendly MAIN_SPEAKER / OTHER_SPEAKER_n labels, same heuristic as baseline ---
    turns = [
        SpeakerTurn(start=float(row["start"]), end=float(row["end"]), speaker=str(row["speaker"]))
        for _, row in diarize_df.iterrows()
    ]
    diar_result = DiarizationResult(turns=turns, backend="pyannote", model=DIARIZATION_MODEL)
    label_info = build_label_map(diar_result)
    label_map = label_info["map"]

    for seg in result["segments"]:
        if seg.get("speaker") is not None:
            seg["speaker_raw"] = seg["speaker"]
            seg["speaker"] = label_map.get(seg["speaker"], seg["speaker"])
        for w in seg.get("words", []):
            if w.get("speaker") is not None:
                w["speaker_raw"] = w["speaker"]
                w["speaker"] = label_map.get(w["speaker"], w["speaker"])

    # --- raw-ish output: full whisperx result + diarization turns, minimally touched ---
    raw_output = {
        "experiment": EXPERIMENT_NAME,
        "audio_file": str(audio_path),
        "asr_model": args.model,
        "alignment_model": ALIGN_MODEL_NL,
        "diarization_model": DIARIZATION_MODEL,
        "language": args.language,
        "device": args.device,
        "timings": timings,
        "diarization_turns": [
            {"start": t.start, "end": t.end, "speaker_raw": t.speaker,
             "speaker": label_map.get(t.speaker, t.speaker)}
            for t in turns
        ],
        "segments": result["segments"],          # includes per-word "words": [{word,start,end,score,speaker,speaker_raw}]
        "word_segments": result.get("word_segments"),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_raw.write_text(json.dumps(raw_output, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- normalized output: project-style segment fields + readable reconstructed turns ---
    n_mixed = 0
    normalized_segments = []
    for seg in result["segments"]:
        words = seg.get("words", [])
        word_speakers = {w.get("speaker") for w in words if w.get("speaker") is not None}
        is_mixed = len(word_speakers) > 1
        if is_mixed:
            n_mixed += 1
        normalized_segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip(),
            "speaker": seg.get("speaker"),            # dominant speaker for the whole segment (like baseline)
            "speaker_raw": seg.get("speaker_raw"),
            "mixed_speakers": is_mixed,                # True = this ASR segment's words split across >1 speaker
            "words": [
                {
                    "word": w.get("word"),
                    "start": w.get("start"),
                    "end": w.get("end"),
                    "score": w.get("score"),
                    "speaker": w.get("speaker"),
                    "speaker_raw": w.get("speaker_raw"),
                }
                for w in words
            ],
        })

    readable_turns = _reconstruct_turns(result["segments"])

    normalized_output = {
        "experiment": EXPERIMENT_NAME,
        "baseline_model": "speaker-diarization-3.1",
        "asr_model": args.model,
        "alignment_model": ALIGN_MODEL_NL,
        "diarization_model": DIARIZATION_MODEL,
        "audio_file": str(audio_path),
        "language": args.language,
        "runtime_seconds": timings["total_seconds"],
        "timings": timings,
        "speaker_inventory": label_info["inventory"],
        "segments": normalized_segments,
        "mixed_speaker_segments": n_mixed,
        "mixed_speaker_segments_total": len(normalized_segments),
        "readable_turns": readable_turns,   # e.g. [{"speaker": "MAIN_SPEAKER", "text": "Dit ben jij."}, ...]
    }
    out_norm.write_text(json.dumps(normalized_output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  timings         : {timings}")
    print(f"  raw speakers    : {diar_result.raw_speakers}  ({len(turns)} turns)")
    for row in label_info["inventory"]:
        print(f"    {row['label']:<16} <- {row['raw']:<12} {row['talk_seconds']:>7.1f}s  ({row['share']*100:4.1f}%)")
    print(f"  segments        : {len(normalized_segments)}  mixed_speaker_segments={n_mixed}")
    print(f"  readable turns  :")
    for t in readable_turns[:8]:
        print(f"    {t['speaker']}: {t['text']}")
    if len(readable_turns) > 8:
        print(f"    ... ({len(readable_turns) - 8} more)")
    print(f"  written to {out_raw.name} and {out_norm.name}\n")


def main():
    parser = argparse.ArgumentParser(description="Experiment B: WhisperX + pyannote (word-level speaker assignment)")
    parser.add_argument(
        "--fragment", action="append", dest="fragments",
        help="Fragment name (no extension), repeatable. Default: testaudio1_fragment, testaudio2_fragment",
    )
    parser.add_argument("--model", default="medium", help="Whisper model size (matches baseline: medium)")
    parser.add_argument("--language", default="nl")
    parser.add_argument("--device", default="cpu", help="cpu or cuda")
    parser.add_argument("--compute-type", default="float32", help="float32 for cpu, float16 for cuda")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    fragments = args.fragments or DEFAULT_FRAGMENTS

    token = get_hf_token()
    if not token:
        sys.exit(
            "No HuggingFace token found (checked HF_TOKEN / HUGGINGFACE_TOKEN via "
            "<repo-root>/.env, same as the baseline). Needed for pyannote diarization."
        )

    print(f"Loading whisper model '{args.model}' on {args.device} ({args.compute_type}) ...")
    whisper_model = whisperx.load_model(args.model, args.device, compute_type=args.compute_type, language=args.language)

    print(f"Loading alignment model for '{args.language}' ...")
    align_model, align_metadata = whisperx.load_align_model(language_code=args.language, device=args.device)

    print(f"Loading diarization pipeline '{DIARIZATION_MODEL}' ...")
    diarize_model = DiarizationPipeline(model_name=DIARIZATION_MODEL, token=token, device=args.device)
    print()

    for fragment in fragments:
        run_one(fragment, whisper_model, align_model, align_metadata, diarize_model, args)


if __name__ == "__main__":
    main()
