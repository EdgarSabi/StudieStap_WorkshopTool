"""
Central configuration for the workshop-coach pipeline.

Phase 1 only needs a small subset of this; the rest of the fields will
grow as later phases are implemented, so this file doesn't need to be
restructured each time.
"""
from dataclasses import dataclass
from pathlib import Path

# project-root/Data-analysis/src/config.py -> project-root/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "Data-local" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "Data-local" / "processed"


@dataclass
class TranscriptionConfig:
    language: str = "nl"
    model_size: str = "base"       # tiny / base / small / medium / large-v3
    device: str = "cpu"            # "cpu" or "cuda"
    compute_type: str = "int8"     # int8 / int8_float16 / float16 / float32
    batch_size: int = 8            # only used if use_batching=True
    use_batching: bool = True