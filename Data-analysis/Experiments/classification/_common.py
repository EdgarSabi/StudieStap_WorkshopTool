"""
Shared paths for the classification experiment (Fase 5A).

Standalone experiment: does NOT modify Data-analysis/src. Where it reuses
production code (models.processed.ProcessedTranscript), it only imports and
reads it — same pattern as the other Experiments/ scripts.
"""
import sys
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXPERIMENT_DIR.parents[2]  # .../StudieStap_WorkshopTool
SRC_DIR = PROJECT_ROOT / "Data-analysis" / "src"

# Read-only reuse of the production pipeline's models (models.processed.ProcessedTranscript
# etc.) — nothing here writes into Data-analysis/src or calls anything that would.
sys.path.insert(0, str(SRC_DIR))

RAW_DIR = PROJECT_ROOT / "Data-local" / "raw" / "classification"
OUTPUT_DIR = PROJECT_ROOT / "Data-local" / "processed" / "classification"
