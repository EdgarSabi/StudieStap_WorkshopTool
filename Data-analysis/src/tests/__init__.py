import sys
from pathlib import Path

# Make config/models/diarization/docent_recognition importable as top-level
# modules regardless of which directory `python -m unittest` is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # Data-analysis/src
