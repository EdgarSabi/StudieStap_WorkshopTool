import sys
from pathlib import Path

# Make classification_data/classification importable as top-level modules,
# regardless of which directory `python -m unittest` is invoked from.
# classification_data.py puts Data-analysis/src on sys.path itself (as soon
# as it's imported), so no separate step is needed for that.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
