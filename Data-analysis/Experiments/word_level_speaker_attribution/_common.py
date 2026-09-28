"""
Shared helpers for Fase 4 — word-level speaker attribution.

Standalone experiment: does NOT modify anything in Data-analysis/src. It
imports and reuses existing pipeline modules read-only (same pattern as the
other Experiments/ scripts, e.g. Afgeronde_experimenten/diarization/community1/community1_test.py),
and reuses the previous speaker_recognition experiment's helpers for the
WeSpeaker embedding/cosine-similarity plumbing rather than duplicating it.
"""
import importlib.util
import sys
from pathlib import Path
from typing import Optional

EXPERIMENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXPERIMENT_DIR.parents[2]  # .../StudieStap_WorkshopTool
SRC_DIR = PROJECT_ROOT / "Data-analysis" / "src"
SPEAKER_RECOGNITION_DIR = PROJECT_ROOT / "Data-analysis" / "Experiments" / "speaker_recognition"

# Make the production pipeline's own modules importable (read-only reuse —
# nothing here writes into Data-analysis/src or calls anything that would).
sys.path.insert(0, str(SRC_DIR))


def _load_speaker_recognition_common():
    """Import speaker_recognition/_common.py under a distinct module name.

    Both experiments happen to name their shared-helpers module `_common.py`;
    a plain `import _common` here would just re-return *this* module (already
    in sys.modules under that name) instead of the other experiment's file.
    Loading it explicitly by path avoids that collision while still reusing
    its code as-is (no copy-paste of cosine_similarity/wav-slicing helpers).
    """
    spec = importlib.util.spec_from_file_location(
        "speaker_recognition_common", SPEAKER_RECOGNITION_DIR / "_common.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sr_common = _load_speaker_recognition_common()  # speaker_recognition/_common.py, reused as-is

from config import (  # noqa: E402
    DiarizationConfig,
    PROCESSED_DATA_DIR,
    TEST_FILES_DIR,
    TranscriptionConfig,
    get_hf_token,
)
from models.schema import WorkshopTranscript  # noqa: E402

TEST_FILES_DIR = TEST_FILES_DIR  # re-export for convenience

# Same 3 fragments as the diarization/ and speaker_recognition/ experiments —
# the only ones with existing baseline transcripts + diarization output to
# compare against.
EVAL_FRAGMENTS = ["testaudio1_fragment", "testaudio2_fragment", "testaudio5_fragment"]

# Same whisper model size the baseline pipeline actually used for these
# fragments (see Data-local/processed/<fragment>.json -> "model_size").
ASR_MODEL_SIZE = "medium"

OUTPUT_DIR = PROCESSED_DATA_DIR / "word_level_speaker_attribution"

MANUAL_TRANSCRIPT_DIR = PROJECT_ROOT / "Data-local" / "raw"


def baseline_transcript_path(fragment: str) -> Path:
    return PROCESSED_DATA_DIR / f"{fragment}.json"


def load_baseline_transcript(fragment: str) -> WorkshopTranscript:
    path = baseline_transcript_path(fragment)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found — expected the existing Phase 1/2 pipeline output.")
    return WorkshopTranscript.model_validate_json(path.read_text(encoding="utf-8"))


def manual_transcript_text(fragment: str) -> Optional[str]:
    """fragment like 'testaudio1_fragment' -> Data-local/raw/testaudio1_manual.txt"""
    base = fragment.replace("_fragment", "")
    path = MANUAL_TRANSCRIPT_DIR / f"{base}_manual.txt"
    return path.read_text(encoding="utf-8") if path.exists() else None


def audio_path(fragment: str) -> Path:
    return TEST_FILES_DIR / f"{fragment}.mp3"


def diarization_wav_path(fragment: str) -> Path:
    """The 16 kHz mono wav the baseline diarization run already produced for
    this fragment (Data-local/processed/diarization/) — reused so we don't
    re-run ffmpeg conversion."""
    return PROCESSED_DATA_DIR / "diarization" / f"{fragment}_16k_mono.wav"


def base_transcription_config() -> TranscriptionConfig:
    """Same settings the baseline pipeline used for these fragments (see
    transcription_config in Data-local/processed/<fragment>.json), so the
    only variable in Step 2 is word_timestamps. model_size matches the
    project's provisional choice (medium)."""
    return TranscriptionConfig(model_size=ASR_MODEL_SIZE, device="cpu", compute_type="int8")


def base_diarization_config() -> DiarizationConfig:
    return DiarizationConfig(device="cpu")


__all__ = [
    "sr_common",
    "get_hf_token",
    "PROCESSED_DATA_DIR",
    "TEST_FILES_DIR",
    "EVAL_FRAGMENTS",
    "ASR_MODEL_SIZE",
    "OUTPUT_DIR",
    "baseline_transcript_path",
    "load_baseline_transcript",
    "manual_transcript_text",
    "audio_path",
    "diarization_wav_path",
    "base_transcription_config",
    "base_diarization_config",
]
