"""
Experiment: wat doet clustering.min_cluster_size met onze diarisatie?

Raakt de productiepipeline NIET aan. Gebruikt alleen diarization.PyannoteBackend
(het model dat de pipeline ook gebruikt) en zet daar tijdelijk een andere
waarde in, in dit proces. Er wordt niets weggeschreven behalve een JSON met
de uitkomsten in deze map.

Draaien (vanuit Data-analysis/src):
    .venv\\Scripts\\python.exe ..\\Experiments\\diarization\\hyperparameter_tuning\\evaluate_min_cluster_size.py testaudio4_fragment --values 12 6 3

Hoe de score werkt (bewust simpel):
  1. We knippen de tijdlijn in blokjes van 0,1 s.
  2. Voor elk blokje binnen een door jou gelabelde spreekbeurt kijken we welke
     pyannote-sprekers op dat moment actief zijn.
  3. Daaruit volgt een tabel: "jouw spreker A viel vaak samen met pyannote-spreker X".
  4. We koppelen elke jouw-spreker aan maximaal één pyannote-spreker (zo, dat het
     totaal aantal overeenkomende blokjes zo groot mogelijk is).
  5. Per spreker van jou: welk deel van zijn/haar spreektijd is door de gekoppelde
     pyannote-spreker gedekt? Een spreker zonder koppeling (bv. een derde
     stem die pyannote nooit als eigen spreker ziet) krijgt dus 0%.
Overlap telt mild: als pyannote op een blokje twee sprekers actief heeft en één
daarvan is de goede, telt het blokje als goed. Overlap-detectie zelf is geen
tunbare instelling, dus die willen we hier niet straffen.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

HERE = Path(__file__).resolve().parent
SRC_DIR = HERE.parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from config import DiarizationConfig, DIARIZATION_OUTPUT_DIR  # noqa: E402
from diarization import PyannoteBackend  # noqa: E402

FRAME = 0.1


def load_ground_truth(fragment: str) -> list[tuple[float, float, str]]:
    path = HERE / f"ground_truth_{fragment}.csv"
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["speaker_id"].strip():
                rows.append((float(r["start_seconds"]), float(r["end_seconds"]), r["speaker_id"].strip()))
    return rows


def score(gt_rows, hyp_turns) -> dict:
    gt_speakers = sorted({s for _, _, s in gt_rows})
    hyp_speakers = sorted({t.speaker for t in hyp_turns})

    # frames[(gt_speaker)] -> lijst van sets met actieve pyannote-sprekers
    frames: dict[str, list[set]] = {s: [] for s in gt_speakers}
    for start, end, gt_spk in gt_rows:
        t = start + FRAME / 2
        while t < end:
            active = {h.speaker for h in hyp_turns if h.start <= t < h.end}
            frames[gt_spk].append(active)
            t += FRAME

    contingency = np.zeros((len(gt_speakers), max(1, len(hyp_speakers))))
    for gi, g in enumerate(gt_speakers):
        for active in frames[g]:
            for h in active:
                contingency[gi, hyp_speakers.index(h)] += 1

    rows, cols = linear_sum_assignment(-contingency)
    mapping = {gt_speakers[r]: (hyp_speakers[c] if hyp_speakers else None) for r, c in zip(rows, cols)}

    per_speaker = {}
    correct_total = 0
    frames_total = 0
    for g in gt_speakers:
        n = len(frames[g])
        matched = mapping.get(g)
        ok = sum(1 for active in frames[g] if matched in active)
        per_speaker[g] = {
            "seconds": round(n * FRAME, 1),
            "matched_pyannote_speaker": matched,
            "covered_pct": round(100 * ok / n, 1) if n else None,
        }
        correct_total += ok
        frames_total += n

    return {
        "gt_speakers": len(gt_speakers),
        "pyannote_speakers_found": len(hyp_speakers),
        "overall_correct_pct": round(100 * correct_total / frames_total, 1),
        "per_gt_speaker": per_speaker,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fragment", help="bv. testaudio4_fragment (ground_truth_<naam>.csv moet in deze map staan)")
    parser.add_argument("--param", choices=["min_cluster_size", "threshold"], default="min_cluster_size",
                        help="welke clustering-instelling je varieert (default: min_cluster_size)")
    parser.add_argument("--values", type=float, nargs="+", default=[12, 6, 3],
                        help="waarden om te testen. Huidig: min_cluster_size=12, threshold=0.7046")
    args = parser.parse_args()

    gt_rows = load_ground_truth(args.fragment)
    wav_path = DIARIZATION_OUTPUT_DIR / f"{args.fragment}_16k_mono.wav"
    if not wav_path.exists():
        sys.exit(f"{wav_path} bestaat niet — draai eerst diarization.py voor dit fragment.")

    backend = PyannoteBackend(DiarizationConfig())
    base_params = backend._pipeline.parameters(instantiated=True)
    print("Startinstellingen pipeline:", base_params)

    results = {}
    for value in args.values:
        params = json.loads(json.dumps(base_params))  # diepe kopie
        params["clustering"][args.param] = int(value) if args.param == "min_cluster_size" else value
        backend._pipeline.instantiate(params)
        print(f"\n=== {args.param} = {value} ===", flush=True)
        result = backend.diarize(wav_path)
        s = score(gt_rows, result.turns)
        s["pyannote_turns"] = len(result.turns)
        s["runtime_seconds"] = result.runtime_seconds
        results[f"{value:g}"] = s
        print(json.dumps(s, indent=2, ensure_ascii=False), flush=True)

    out_path = HERE / f"results_{args.param}_{args.fragment}.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nUitkomsten weggeschreven naar {out_path}")


if __name__ == "__main__":
    main()
