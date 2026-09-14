# EXPERIMENT ONLY
# Does not replace the existing diarization pipeline.
"""
Experiment A: pyannote/speaker-diarization-community-1 instead of the
baseline pyannote/speaker-diarization-3.1.

This does NOT touch the production pipeline. It reuses the baseline's own
modules as-is (PyannoteBackend, labeling, assign) and only swaps the
`hf_model` in a fresh DiarizationConfig — that class already takes the model
id as a parameter, so no baseline code needed to change to test a different
pyannote pipeline.

Reused, unmodified from Data-analysis/src:
  - diarization.get_backend / PyannoteBackend   (loads whichever hf_model
    the config says — community-1 here, 3.1 in the real pipeline)
  - diarization.labeling.build_label_map        (raw speaker -> MAIN/OTHER_n)
  - diarization.assign.assign_speakers/summarize (segment <-> turn geometry)
  - run_diarization._to_wav                     (mp3 -> 16kHz mono wav for pyannote)
  - models.schema.WorkshopTranscript             (to read the baseline transcript JSON)

Input:  Data-local/processed/<fragment>.json          (Phase 1 baseline transcript)
        Data-analysis/src/test-files/<fragment>.mp3   (same audio as baseline)
Output: Data-local/processed/diarization_experiments/community1/<fragment>_community1.json

Usage (from anywhere, run with the EXISTING project venv — no new installs needed):
    python community1_test.py
    python community1_test.py --fragment testaudio1_fragment --fragment testaudio5_fragment
"""
import argparse
import json
import sys
import time
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(SRC_DIR))

from config import DiarizationConfig, PROCESSED_DATA_DIR, TEST_FILES_DIR  # noqa: E402
from models.schema import WorkshopTranscript  # noqa: E402
from diarization import get_backend  # noqa: E402
from diarization.labeling import build_label_map  # noqa: E402
from diarization.assign import assign_speakers, summarize  # noqa: E402
from run_diarization import _to_wav  # noqa: E402

EXPERIMENT_NAME = "pyannote_community_1"
BASELINE_MODEL = "speaker-diarization-3.1"
COMMUNITY1_MODEL = "pyannote/speaker-diarization-community-1"

OUTPUT_DIR = PROCESSED_DATA_DIR / "diarization_experiments" / "community1"
# Reuse the same 16kHz mono wav's the baseline diarization run already produced
# (or produce them the same way, via the baseline's own _to_wav helper).
WAV_CACHE_DIR = PROCESSED_DATA_DIR / "diarization"

DEFAULT_FRAGMENTS = ["testaudio1_fragment", "testaudio2_fragment"]


def run_one(fragment: str, backend, device: str, force: bool) -> dict:
    transcript_path = PROCESSED_DATA_DIR / f"{fragment}.json"
    if not transcript_path.exists():
        sys.exit(f"Baseline transcript not found: {transcript_path} (run run_transcription.py first)")
    transcript = WorkshopTranscript.model_validate_json(transcript_path.read_text(encoding="utf-8"))

    audio_path = TEST_FILES_DIR / f"{fragment}.mp3"
    if not audio_path.exists():
        sys.exit(f"Audio not found: {audio_path}")

    wav_path = _to_wav(audio_path, WAV_CACHE_DIR, force=False)

    print(f"[{fragment}] diarizing with {COMMUNITY1_MODEL} ...")
    result = backend.diarize(wav_path)

    label_info = build_label_map(result)
    new_segments = assign_speakers(transcript.segments, result.turns, label_info["map"])
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
        "assignment": stats,
    }

    output = {
        "experiment": EXPERIMENT_NAME,
        "baseline_model": BASELINE_MODEL,
        "diarization_model": COMMUNITY1_MODEL,
        "source_transcript": str(transcript_path),
        "audio_file": str(audio_path),
        "language": transcript.language,
        "duration": transcript.duration,
        "asr_model_size": transcript.model_size,
        "segments": [seg.model_dump() for seg in new_segments],
        "diarization": diarization_meta,
        "runtime_seconds": result.runtime_seconds,
    }

    out_path = OUTPUT_DIR / f"{fragment}_community1.json"
    if out_path.exists() and not force:
        sys.exit(f"{out_path} already exists. Pass --force to overwrite.")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  raw speakers    : {result.raw_speakers}  ({len(result.turns)} turns)")
    for row in label_info["inventory"]:
        print(f"    {row['label']:<16} <- {row['raw']:<12} {row['talk_seconds']:>7.1f}s  ({row['share']*100:4.1f}%)")
    print(f"  segments        : {stats['segments']}  per_label={stats['per_label']}")
    print(f"  overlap/uncertain/unassigned : {stats['overlap_segments']}/{stats['uncertain_segments']}/{stats['unassigned_segments']}")
    print(f"  diarization time: {result.runtime_seconds}s")
    print(f"  written to {out_path}\n")

    return output


def main():
    parser = argparse.ArgumentParser(description="Experiment A: pyannote speaker-diarization-community-1")
    parser.add_argument(
        "--fragment", action="append", dest="fragments",
        help="Fragment name (no extension), repeatable. Default: testaudio1_fragment, testaudio2_fragment",
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--force", action="store_true", help="Overwrite existing experiment output")
    args = parser.parse_args()

    fragments = args.fragments or DEFAULT_FRAGMENTS

    config = DiarizationConfig(hf_model=COMMUNITY1_MODEL, device=args.device)
    print(f"Loading pyannote pipeline '{config.hf_model}' on {config.device} ...")
    t0 = time.time()
    backend = get_backend(config)
    print(f"Model loaded in {time.time() - t0:.1f}s\n")

    for fragment in fragments:
        run_one(fragment, backend, args.device, args.force)


if __name__ == "__main__":
    main()
