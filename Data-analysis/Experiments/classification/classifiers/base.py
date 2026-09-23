"""
STAP 4 — minimal, swappable classifier interface.

Deliberately small: one abstract method. A real LLM classifier later
implements the same interface (name/version + classify()); nothing else in
the pipeline (context selection, prompt building, result validation) needs
to change to swap it in — that's the whole point of keeping this thin.

classify() takes an ALREADY-BUILT prompt string (see classifiers/prompt.py)
and returns a RawModelOutput, not a validated ClassificationResult —
validation against schemas/result.py happens in run_classification.py, kept
separate on purpose (STAP 4: "scheid modelaanroep / prompt / contextselectie
/ resultaatvalidatie").
"""
from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class RawModelOutput(BaseModel):
    """What a classifier returns, before validation into ClassificationResult.
    Deliberately loose — a real LLM classifier would parse its own raw
    text/JSON response into this shape; `raw` keeps whatever the
    implementation wants preserved for the reproducibility record."""
    detected: Optional[bool] = None
    evidence: Optional[str] = None
    status: str = "OK"
    raw: Optional[dict] = None


class Classifier(ABC):
    name: str
    version: str

    @abstractmethod
    def classify(self, prompt: str, *, indicator_id: str) -> RawModelOutput:
        ...
