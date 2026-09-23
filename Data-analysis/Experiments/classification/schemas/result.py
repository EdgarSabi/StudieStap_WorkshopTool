"""
STAP 5 — provisional classification-result schema.

Deliberately minimal: exactly the fields requested, no didactic scoring, no
indicator definitions, no confidence/severity fields. `detected`/`evidence`
are placeholders a real classifier will fill in later — the MockClassifier
(classifiers/mock.py) only ever returns fixed, non-content-derived values.

status:
  - "OK"      the classifier produced a usable detected/evidence pair.
  - "UNKNOWN" not enough information to judge (e.g. missing context, or the
              classifier itself said so) — detected/evidence may be None.
Not a Literal/enum on purpose (see module note below) — kept as plain str so
adding a status later (e.g. "ERROR") doesn't require touching this schema;
run_classification.py's reproducibility record is where actual pipeline
errors are captured, not this per-result schema.
"""
from typing import Optional
from pydantic import BaseModel, field_validator

VALID_STATUSES = {"OK", "UNKNOWN"}


class ClassificationResult(BaseModel):
    fragment_id: str
    center_turn_id: int
    context_turn_ids: list[int]
    indicator_id: str

    detected: Optional[bool] = None
    evidence: Optional[str] = None
    status: str = "OK"

    model_name: str
    model_version: str
    prompt_version: str

    @field_validator("status")
    @classmethod
    def _status_known(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}, got {v!r}")
        return v

    @field_validator("context_turn_ids")
    @classmethod
    def _center_in_context(cls, v: list[int], info) -> list[int]:
        center = info.data.get("center_turn_id")
        if center is not None and center not in v:
            raise ValueError(f"center_turn_id {center} must be included in context_turn_ids {v}")
        return v
