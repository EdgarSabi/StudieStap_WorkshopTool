"""
Optional Word Error Rate against a manually corrected reference transcript.
Only meaningful with a real reference — this utility does not estimate
accuracy without one.

Requires: pip install jiwer

Usage:
    python evaluation/wer.py --reference ref.txt --hypothesis ../Data-local/processed/benchmark/testaudio1_base.json
"""
import argparse
import json
from pathlib import Path


def transcript_json_to_text(json_path: Path) -> str:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return " ".join(seg["text"] for seg in data["segments"])


def compute_wer(reference_text: str, hypothesis_text: str) -> float:
    import jiwer
    return jiwer.wer(reference_text, hypothesis_text)


def main():
    parser = argparse.ArgumentParser(description="Compute WER against a manual reference transcript")
    parser.add_argument("--reference", required=True, help="Path to a plain-text manually corrected transcript")
    parser.add_argument("--hypothesis", required=True, help="Path to a transcript JSON from this pipeline")
    args = parser.parse_args()

    reference_text = Path(args.reference).read_text(encoding="utf-8")
    hypothesis_text = transcript_json_to_text(Path(args.hypothesis))
    print(f"WER: {compute_wer(reference_text, hypothesis_text):.3f}")


if __name__ == "__main__":
    main()