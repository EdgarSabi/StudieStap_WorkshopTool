import sys
from pathlib import Path

# Make config/models/docent_recognition importable as top-level modules
# regardless of which directory `python -m unittest` is invoked from —
# same pattern Experiments/classification/tests/__init__.py uses.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # Data-analysis/src
