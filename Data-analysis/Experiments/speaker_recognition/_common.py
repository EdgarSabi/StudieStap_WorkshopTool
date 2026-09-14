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
