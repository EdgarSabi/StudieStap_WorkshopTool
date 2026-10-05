# EXPERIMENT ONLY
# Does not modify Data-analysis/src. Uses a mock classifier only — no real
# didactic classification, no real indicator definitions yet.
"""
STAP 4-6 — building a prompt from a context window, "classifying" it (mock
classifier only, for now), and running the whole thing end to end.

    load fragment -> one context window per turn -> build prompt
    -> classify -> validate into ClassificationResult -> write JSON

See classification_data.py for the turn/context/result data models and the
two input-format loaders.

Draaien:
    python classification.py --input <manual-fixture-of-ProcessedTranscript.json> --mode B

Works identically for both supported input formats (a hand-written
Data-local/raw/classification/*.json fixture, or an existing
Data-local/processed/preprocessing/*_turns.json ProcessedTranscript,
optionally enriched by docent_recognition.py) — load_fragment() picks the
right loader; everything after that point is the same code path for both.
"""
import argparse
import json
import sys
from pathlib import Path

from classification_data import (
    OUTPUT_DIR, MODES, ContextWindow, ClassificationResult, load_fragment, iter_context_windows,
)

# v1: added docent_role per turn (Phase 4 integration) — bumped because the
# rendered prompt text itself changed; a stored prompt_version must identify
# which template actually produced a prompt.
PROMPT_VERSION = "placeholder-v1"


def build_prompt(window: ContextWindow, indicator_id: str) -> str:
    """This is a PLACEHOLDER template — no real didactic indicator
    definitions live here yet. Swapping in a real one later only means
    changing this function/version, nothing else in the pipeline."""
    lines = [
        f"INDICATOR: {indicator_id}  (placeholder — not yet operationalized)",
        f"CONTEXT MODE: {window.mode}",
        "",
        "CONTEXT (chronological order, [*] marks the turn to judge):",
    ]
    for t in window.turns:
        marker = "*" if t.turn_id == window.center_turn_id else " "
        speaker = t.speaker or "UNKNOWN_SPEAKER"
        # docent_role is a separate, independently-computed judgement (Phase 4
        # voice recognition) — NEVER inferred from `speaker` here either.
        # None means "not evaluated", shown as-is rather than guessed.
        docent_role = t.docent_role or "ONBEKEND"
        lines.append(f"  [{marker}] turn {t.turn_id} ({speaker}, docent_role={docent_role}): {t.text}")
    lines.append("")
    lines.append(
        "This is a placeholder prompt for pipeline testing only — it does not "
        "encode a real didactic indicator definition or scoring rule."
    )
    return "\n".join(lines)


# A tiny class because it needs to remember one thing between calls: how
# many times it has already been asked (`_call_count`), so it can cycle
# through its 3 canned answers instead of always giving the same one. That's
# the only reason this isn't a plain function.
#
# It deliberately ignores `prompt` and `indicator_id` completely — it exists
# to prove the rest of the pipeline (loading -> context -> prompt ->
# classify -> save) works end to end, not to produce plausible-looking
# answers. A later, real classifier just needs the same two things this one
# has (name/version attributes, a classify(prompt, indicator_id) method
# returning a dict with detected/evidence/status) — nothing else in this
# file needs to change to swap it in.
class MockClassifier:
    name = "mock"
    version = "0.1"

    # "raw" is always None here (the mock invents nothing) but stays present
    # on every result so the JSON shape doesn't change once a real classifier
    # starts filling it in with, e.g., the LLM's raw response text.
    DEFAULT_CANNED_RESULTS = [
        {"detected": True, "evidence": "mock: fixed positive result", "status": "OK", "raw": None},
        {"detected": False, "evidence": "mock: fixed negative result", "status": "OK", "raw": None},
        {"detected": None, "evidence": "mock: fixed insufficient-information result", "status": "UNKNOWN", "raw": None},
    ]

    def __init__(self, canned_results: list[dict] | None = None):
        self._canned = canned_results or self.DEFAULT_CANNED_RESULTS
        self._call_count = 0

    def classify(self, prompt: str, indicator_id: str) -> dict:
        result = self._canned[self._call_count % len(self._canned)]
        self._call_count += 1
        return result


DEFAULT_INDICATORS = ["PLACEHOLDER_INDICATOR"]  # no real indicators defined yet


def run(input_path: Path, mode: str, indicators: list[str], classifier: MockClassifier) -> dict:
    fragment = load_fragment(input_path)

    results = []
    raw_outputs = []   # one entry per result, same order, for the reproducibility record
    errors = []

    for indicator_id in indicators:
        for window in iter_context_windows(fragment.turns, mode):
            try:
                prompt = build_prompt(window, indicator_id)
                raw = classifier.classify(prompt, indicator_id)
                result = ClassificationResult(
                    fragment_id=fragment.fragment_id,
                    center_turn_id=window.center_turn_id,
                    context_turn_ids=window.context_turn_ids,
                    indicator_id=indicator_id,
                    detected=raw["detected"],
                    evidence=raw["evidence"],
                    status=raw["status"],
                    model_name=classifier.name,
                    model_version=classifier.version,
                    prompt_version=PROMPT_VERSION,
                )
                results.append(result.model_dump())
                raw_outputs.append({
                    "center_turn_id": window.center_turn_id,
                    "indicator_id": indicator_id,
                    "prompt": prompt,
                    "raw_output": raw,
                    "unknown_reliability": window.unknown_reliability,
                    "flagged_uncertain": window.flagged_uncertain,
                    "docent_role_unresolved": window.docent_role_unresolved,
                })
            except Exception as e:  # keep going — one bad turn/indicator shouldn't kill the run
                errors.append({
                    "center_turn_id": window.center_turn_id,
                    "indicator_id": indicator_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                })

    return {
        "experiment": "classification_fase5a",
        "input": {
            "path": str(input_path),
            "fragment_id": fragment.fragment_id,
            "source_format": fragment.source,
            "n_turns": len(fragment.turns),
        },
        "context_config": {"mode": mode, "turns_before_after": MODES[mode]},
        "prompt_version": PROMPT_VERSION,
        "model_config": {"name": classifier.name, "version": classifier.version},
        "raw_outputs": raw_outputs,
        "results": results,
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description="Stap 4-6: run the classification pipeline (mock classifier)")
    parser.add_argument("--input", required=True, help="Path to a manual fixture or ProcessedTranscript JSON")
    parser.add_argument("--mode", choices=sorted(MODES), default="B", help="Context window mode (A/B/C)")
    parser.add_argument("--indicator", action="append", dest="indicators",
                         help="Indicator id (repeatable). Default: one placeholder indicator.")
    parser.add_argument("--out", default=None, help="Output JSON path (default: Data-local/processed/classification/)")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"Not found: {input_path}")
    indicators = args.indicators or DEFAULT_INDICATORS

    classifier = MockClassifier()
    output = run(input_path, args.mode, indicators, classifier)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else (
        OUTPUT_DIR / f"{output['input']['fragment_id']}__{args.mode}__{classifier.name}.json"
    )
    if out_path.exists() and not args.force:
        sys.exit(f"{out_path} already exists. Pass --force to overwrite.")
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"fragment        : {output['input']['fragment_id']} ({output['input']['source_format']}, "
          f"{output['input']['n_turns']} turns)")
    print(f"context mode    : {args.mode} {MODES[args.mode]}  indicators: {indicators}")
    print(f"results         : {len(output['results'])}   errors: {len(output['errors'])}")
    n_unknown = sum(1 for r in output["results"] if r["status"] == "UNKNOWN")
    print(f"status UNKNOWN  : {n_unknown}/{len(output['results'])}")
    print(f"written to      : {out_path}")


if __name__ == "__main__":
    main()
