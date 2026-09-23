"""
Shared helpers for the speaker-recognition (DOCENT vs OTHER) experiment.

This is a standalone, exploratory experiment — it does NOT import from, or
get imported by, the production pipeline in Data-analysis/src (transcription
+ diarization). It only *reads* files that pipeline already produced:

  - Data-local/processed/diarization/<fragment>_diarized.json   (chunks + text)
  - Data-local/processed/diarization/<fragment>_16k_mono.wav    (chunk audio)

Nothing in Data-analysis/src is modified, overwritten, or re-run by this
experiment.
"""
import csv
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from typing import NamedTuple, Optional

import numpy as np

EXPERIMENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXPERIMENT_DIR.parents[2]  # .../StudieStap_WorkshopTool
SRC_DIR = PROJECT_ROOT / "Data-analysis" / "src"
TEST_FILES_DIR = SRC_DIR / "test-files"
DIARIZATION_DIR = PROJECT_ROOT / "Data-local" / "processed" / "diarization"
OUTPUT_DIR = PROJECT_ROOT / "Data-local" / "processed" / "speaker_recognition"

# Teacher enrollment / reference clip — found in the existing test-files dir,
# contains only the teacher, made specifically for this experiment.
TEACHER_REF_AUDIO = TEST_FILES_DIR / "testdocent.mp3"

# Evaluation fragments. These are the *_fragment.mp3 files, not the full-length
# testaudio1/2/5.mp3 — the existing pipeline only ever ran ASR + diarization on
# the fragments (see Data-local/processed/diarization/*_diarized.json), so
# those are the only ones with ready-made chunk boundaries + text to reuse.
# Re-transcribing the full files was explicitly out of scope for this
# experiment ("verzin geen compleet nieuwe zware segmentatiepipeline").
EVAL_FRAGMENTS = ["testaudio1_fragment", "testaudio2_fragment", "testaudio5_fragment"]


class Chunk(NamedTuple):
    fragment: str
    index: int
    start: float
    end: float
    text: str
    pipeline_speaker: Optional[str]  # MAIN_SPEAKER / OTHER_SPEAKER_n / None — existing diarization's own label


def get_hf_token() -> Optional[str]:
    """Same lookup as Data-analysis/src/config.py, kept local so this
    experiment doesn't depend on importing the production package."""
    try:
        from dotenv import load_dotenv

        load_dotenv(PROJECT_ROOT / ".env", override=False)
    except ImportError:
        pass
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")


def load_chunks(fragment: str) -> list[Chunk]:
    """Reuse the existing diarized-transcript segments as evaluation chunks."""
    import json

    path = DIARIZATION_DIR / f"{fragment}_diarized.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — expected run_diarization.py to already have produced it."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        Chunk(fragment, i, s["start"], s["end"], s["text"], s.get("speaker"))
        for i, s in enumerate(data["segments"])
    ]


def fragment_wav_path(fragment: str) -> Path:
    path = DIARIZATION_DIR / f"{fragment}_16k_mono.wav"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — expected run_diarization.py to already have produced it."
        )
    return path


def _ffmpeg_to_wav(src: Path, dst: Path) -> Path:
    if dst.exists():
        return dst
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("ffmpeg not found on PATH — needed to convert the teacher reference clip to wav.")
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [ffmpeg, "-y", "-i", str(src), "-ac", "1", "-ar", "16000", str(dst)],
        check=True,
        capture_output=True,
    )
    return dst


def teacher_reference_wav() -> Path:
    """16 kHz mono wav of testdocent.mp3. Converted once and cached under this
    experiment's own output dir (Data-local/processed/speaker_recognition/) —
    kept separate from the production diarization output dir on purpose.
    testdocent.mp3 itself is never moved, renamed, or modified."""
    if not TEACHER_REF_AUDIO.exists():
        raise FileNotFoundError(f"Teacher reference clip not found: {TEACHER_REF_AUDIO}")
    return _ffmpeg_to_wav(TEACHER_REF_AUDIO, OUTPUT_DIR / "testdocent_16k_mono.wav")


def load_wav_mono(path: Path) -> tuple[np.ndarray, int]:
    """16-bit PCM WAV -> (float32 samples in [-1, 1], sample_rate)."""
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            raise RuntimeError(f"{path.name} is not 16-bit PCM.")
        n_channels = w.getnchannels()
        sample_rate = w.getframerate()
        raw = w.readframes(w.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)
    return samples, sample_rate


def slice_samples(samples: np.ndarray, sample_rate: int, start: float, end: float) -> np.ndarray:
    i0 = max(0, int(start * sample_rate))
    i1 = min(len(samples), int(end * sample_rate))
    return samples[i0:i1]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a).reshape(-1).astype(np.float64)
    b = np.asarray(b).reshape(-1).astype(np.float64)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def duration_bucket(seconds: float) -> str:
    if seconds < 0.5:
        return "<0.5s"
    if seconds < 1.0:
        return "0.5-1s"
    return ">1s"


# Any cosine-similarity threshold used in this experiment (or reused from it
# elsewhere, e.g. Experiments/word_level_speaker_attribution) is an
# EXPERIMENTAL setting chosen by inspecting the similarity distribution on a
# 49-chunk sample — see comparison/results.md's "Gekozen threshold" section
# for the full caveat. It is explicitly NOT a validated/proven-reliable
# classification criterion and should not be presented as one downstream.
THRESHOLD_STATUS_NOTE = (
    "experimentele instelling, gekozen op een steekproef van 49 chunks — "
    "geen gevalideerd/bewezen betrouwbaar classificatiecriterium"
)


def compute_agreement(diarization_label: Optional[str], recognition_label: Optional[str]) -> tuple[str, bool]:
    """Compare a diarization-pipeline label against a speaker-recognition
    label WITHOUT ever choosing a winner or merging them into one value —
    callers must keep both labels as separate fields; this only classifies
    how they relate, as (agreement, conflict).

    `diarization_label` is the existing pipeline's label (MAIN_SPEAKER /
    OTHER_SPEAKER_n / None). `recognition_label` is "DOCENT" / "OTHER" / None
    (None when recognition wasn't evaluated for this chunk, e.g. no
    threshold was supplied, or the chunk was too short/unembeddable).

    Returns:
      ("not_evaluated", False)               - no recognition_label to compare
      ("no_diarization_label", False)        - diarization gave no label (None/unassigned)
      ("consistent_docent", False)           - both agree: MAIN_SPEAKER <-> DOCENT
      ("consistent_other", False)            - both agree: OTHER_SPEAKER_n/other <-> OTHER
      ("conflict_diar_main_sim_low", True)   - diarization says MAIN_SPEAKER, recognition says OTHER
      ("conflict_diar_other_sim_high", True) - diarization says OTHER_SPEAKER_n, recognition says DOCENT
    """
    if recognition_label is None:
        return "not_evaluated", False
    if diarization_label is None:
        return "no_diarization_label", False

    diar_says_docent = diarization_label == "MAIN_SPEAKER"
    recognition_says_docent = recognition_label == "DOCENT"

    if diar_says_docent == recognition_says_docent:
        return ("consistent_docent" if diar_says_docent else "consistent_other"), False
    if diar_says_docent and not recognition_says_docent:
        return "conflict_diar_main_sim_low", True
    return "conflict_diar_other_sim_high", True


def print_distribution(label: str, values: list[float]) -> None:
    if not values:
        print(f"\n--- {label}: no scores to summarize ---")
        return
    arr = np.array(values)
    print(f"\n--- {label} similarity distribution (n={len(arr)}) ---")
    print(f"  min={arr.min():.3f}  max={arr.max():.3f}  mean={arr.mean():.3f}  std={arr.std():.3f}")
    for q in (10, 25, 50, 75, 90):
        print(f"  p{q:<3}: {np.percentile(arr, q):.3f}")


def write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        print(f"no rows to write for {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nwritten {len(rows)} rows -> {path}")
