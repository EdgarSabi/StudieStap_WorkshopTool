# EXPERIMENT ONLY
# Does not modify Data-analysis/src. Uses MockClassifier only — no real
# didactic classification, no real indicator definitions (Fase 5A scope).
"""
STAP 6 — orchestrates the classification pipeline and writes one
reproducible output JSON per run:

    load fragment (loaders) -> one context window per turn (context.selector)
    -> build prompt (classifiers.prompt) -> classify (classifiers.*)
    -> validate into ClassificationResult (schemas.result) -> write JSON

The output file records EVERYTHING STAP 6 asks for: the input used, the
context configuration, the prompt version, the model configuration, the raw
model output per result, the validated results, and any errors — nothing is
silently dropped.

Works identically for both supported input formats (a hand-written
Data-local/raw/classification/*.json fixture, or an existing
Data-local/processed/preprocessing/*_turns.json ProcessedTranscript) —
loaders.load_fragment() picks the right loader; everything after that point
is the same code path for both.

Usage (existing project venv, no new installs):
    Data-analysis\\src\\.venv\\Scripts\\python.exe run_classification.py --input <path> --mode B
    Data-analysis\\src\\.venv\\Scripts\\python.exe run_classification.py --input <path> --mode A --indicator PLACEHOLDER_INDICATOR --force
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as common  # noqa: E402

from loaders import load_fragment  # noqa: E402
from context.selector import iter_context_windows, MODES  # noqa: E402
from classifiers.prompt import build_prompt, PROMPT_VERSION  # noqa: E402
from classifiers.mock import MockClassifier  # noqa: E402
from classifiers.base import Classifier  # noqa: E402
from schemas.result import ClassificationResult  # noqa: E402

DEFAULT_INDICATORS = ["PLACEHOLDER_INDICATOR"]  # no real indicators defined yet — Fase 5A scope


def run(input_path: Path, mode: str, indicators: list[str], classifier: Classifier) -> dict:
    fragment = load_fragment(input_path)

    results = []
    raw_outputs = []   # one entry per result, same order, for the reproducibility record
    errors = []

    for indicator_id in indicators:
        for window in iter_context_windows(fragment.turns, mode):
            try:
                prompt = build_prompt(window, indicator_id)
                raw = classifier.classify(prompt, indicator_id=indicator_id)
                result = ClassificationResult(
                    fragment_id=fragment.fragment_id,
                    center_turn_id=window.center_turn_id,
                    context_turn_ids=window.context_turn_ids,
                    indicator_id=indicator_id,
                    detected=raw.detected,
                    evidence=raw.evidence,
                    status=raw.status,
                    model_name=classifier.name,
                    model_version=classifier.version,
                    prompt_version=PROMPT_VERSION,
                )
                results.append(result.model_dump())
                raw_outputs.append({
                    "center_turn_id": window.center_turn_id,
                    "indicator_id": indicator_id,
                    "prompt": prompt,
                    "raw_output": raw.model_dump(),
                    "unknown_reliability": window.unknown_reliability,
                    "flagged_uncertain": window.flagged_uncertain,
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
    parser = argparse.ArgumentParser(description="STAP 6: run the classification pipeline (mock classifier)")
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

    common.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else (
        common.OUTPUT_DIR / f"{output['input']['fragment_id']}__{args.mode}__{classifier.name}.json"
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
