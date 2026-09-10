"""
Central configuration for the workshop-coach pipeline.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "Data-local" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "Data-local" / "processed"
TEST_FILES_DIR = Path(__file__).resolve().parent / "test-files"
BENCHMARK_OUTPUT_DIR = PROCESSED_DATA_DIR / "benchmark"
DIARIZATION_OUTPUT_DIR = PROCESSED_DATA_DIR / "diarization"

# Load a repo-root .env (gitignored) if present, so HF_TOKEN etc. don't have
# to be exported by hand. Never overrides variables already set in the shell.
try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env", override=False)
except ImportError:
    pass


def get_hf_token() -> Optional[str]:
    """HuggingFace token for gated models (pyannote). Checked lazily, never logged."""
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")

# Informational only — faster-whisper accepts any valid model name/size,
# this list is just what the benchmark CLI's --help advertises.
SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large-v3", "large-v3-turbo"]


@dataclass
class TranscriptionConfig:
    language: str = "nl"
    model_size: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    use_batching: bool = False   # off by default for benchmarking, see engine.py note
    batch_size: int = 8

    # --- decoding parameters (faster-whisper WhisperModel.transcribe) ---
    beam_size: int = 5                              # library default
    condition_on_previous_text: bool = True          # library default; set False to test long-audio drift
    repetition_penalty: float = 1.0                  # library default = disabled
    no_repeat_ngram_size: int = 0                     # library default = disabled
    word_timestamps: bool = False
    hallucination_silence_threshold: Optional[float] = None  # only has effect if word_timestamps=True

    vad_filter: bool = True                           # NOT library default (False) — see explanation below
    vad_parameters: Optional[dict] = None              # e.g. {"min_silence_duration_ms": 500}

    # Whisper's own internal "is this segment bad" thresholds (library defaults,
    # left untouched so we don't silently change decoding behaviour).
    log_prob_threshold: Optional[float] = -1.0
    no_speech_threshold: Optional[float] = 0.6
    compression_ratio_threshold: Optional[float] = 2.4

    # --- OUR post-hoc flagging thresholds (heuristic — NOT whisper internals) ---
    flag_avg_logprob_below: float = -1.0
    flag_no_speech_prob_above: float = 0.6
    flag_compression_ratio_above: float = 2.4
    flag_repetition_word_ratio: float = 0.6     # one word makes up >= 60% of a segment
    flag_repetition_min_words: int = 6


@dataclass
class DiarizationConfig:
    """
    Phase 2 (speaker diarization). Separate from TranscriptionConfig on purpose:
    diarization is its own layer and its backend is NOT a settled choice yet.
    """
    backend: str = "pyannote"                       # key into diarization.get_backend()
    hf_model: str = "pyannote/speaker-diarization-3.1"  # gated — needs HF_TOKEN + accepted licence
    device: str = "cpu"                              # "cpu" or "cuda"

    # Optional priors. Leave both None to let the model decide the speaker count;
    # set them when a fragment is known to have e.g. exactly 2-4 speakers.
    min_speakers: Optional[int] = None
    max_speakers: Optional[int] = None

    # --- MAIN_SPEAKER vs OTHER_SPEAKER_n labelling (heuristic, not a research claim) ---
    # The raw diarization speaker with the most total speaking time becomes
    # MAIN_SPEAKER; everyone else becomes OTHER_SPEAKER_1, _2, ... by talk time.
    main_speaker_min_share: float = 0.0   # if the top speaker's share is below this, label MAIN as uncertain

    # --- transcript-segment -> speaker assignment (pure geometry on time spans) ---
    overlap_min_ratio: float = 0.15       # 2nd speaker covers >= 15% of a segment -> mark overlap
    uncertain_coverage_below: float = 0.60  # winning speaker covers < 60% of the segment -> uncertain
    uncertain_margin_below: float = 0.15    # (winner - runner_up) / segment_duration < 15% -> uncertain