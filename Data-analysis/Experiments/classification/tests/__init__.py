import sys
from pathlib import Path

# Make schemas/, loaders/, context/, classifiers/ importable as top-level
# modules, regardless of which directory `python -m unittest` is invoked
# from or which test module happens to be imported first.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _common  # noqa: E402,F401 — side effect: also puts Data-analysis/src on sys.path
# (needed by loaders/pipeline.py's `from models.processed import ProcessedTranscript`)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
