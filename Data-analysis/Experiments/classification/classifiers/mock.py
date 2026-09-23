"""
STAP 4 — mock classifier: ONLY fixed, non-content-derived test results.

Deliberately does not look at the prompt or indicator_id at all — it exists
to verify the technical pipeline (context selection -> prompt -> classifier
-> schema validation -> reproducibility record) works end-to-end, not to
produce plausible-looking classifications. Cycles through a small fixed set
of canned results so tests can exercise the OK/True, OK/False and UNKNOWN
paths without any real classification logic.
"""
from typing import Optional

from .base import Classifier, RawModelOutput

DEFAULT_CANNED_RESULTS: list[RawModelOutput] = [
    RawModelOutput(detected=True, evidence="mock: fixed positive result", status="OK"),
    RawModelOutput(detected=False, evidence="mock: fixed negative result", status="OK"),
    RawModelOutput(detected=None, evidence="mock: fixed insufficient-information result", status="UNKNOWN"),
]


class MockClassifier(Classifier):
    name = "mock"
    version = "0.1"

    def __init__(self, canned_results: Optional[list[RawModelOutput]] = None):
        self._canned = canned_results or DEFAULT_CANNED_RESULTS
        if not self._canned:
            raise ValueError("canned_results must not be empty")
        self._call_count = 0

    def classify(self, prompt: str, *, indicator_id: str) -> RawModelOutput:
        result = self._canned[self._call_count % len(self._canned)]
        self._call_count += 1
        return result
