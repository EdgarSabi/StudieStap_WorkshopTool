"""
Experiment: helpt de sprekergrens-verfijning (src/speaker_boundaries.py) op
fragmenten met handmatige ground truth?

Vergelijkt per fragment en per min_cluster_size:
    pyannote alleen   vs.   pyannote + refinement
met dezelfde score als het hyperparameter-experiment (tijdlijn-dekking per
echte spreker, optimale 1-op-1-koppeling), plus — als er een transcript is —
de score op SEGMENTNIVEAU, want dat is wat preprocessing/docentherkenning
daarna echt gebruiken:
    * segment_accuracy        aandeel Whisper-segmenten met de juiste spreker
    * wrong_and_not_flagged   segmenten met de verkeerde spreker ZONDER
                              overlap/uncertain-vlag (de gevaarlijke fouten)

Draaien (vanuit Data-analysis/src, zelfde venv als de pipeline):
    .venv\\Scripts\\python.exe ..\\Experiments\\diarization\\boundary_refinement\\evaluate_refinement.py testaudio2_fragment testaudio4_fragment
    .venv\\Scripts\\python.exe ..\\Experiments\\diarization\\boundary_refinement\\evaluate_refinement.py testaudio6_fragment --min-cluster-size 12 8

Vereist per fragment:
    ..\\Experiments\\diarization\\hyperparameter_tuning\\ground_truth_<fragment>.csv
    Data-local/processed/diarization/<fragment>_16k_mono.wav   (ontstaat bij diarization.py)
    Data-local/processed/<fragment>.json   (Whisper-transcript; optioneel maar sterk aangeraden —
                                            zonder transcript werkt de refinement alleen op pyannote-grenzen)

Raakt de productiepipeline niet aan en schrijft alleen results_<fragment>.json in deze map.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC_DIR = HERE.parents[2] / "src"
TUNING_DIR = HERE.parent / "hyperparameter_tuning"
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(TUNING_DIR))

from config import (  # noqa: E402
    BoundaryRefinementConfig, DiarizationConfig, DIARIZATION_OUTPUT_DIR, PROCESSED_DATA_DIR,
)
from diarization import (  # noqa: E402
    DiarizationResult, PyannoteBackend, assign_speakers, build_label_map, refine_diarization,
)
from models import WorkshopTranscript  # noqa: E402
from speaker_boundaries import PyannoteWindowEmbedder  # noqa: E402
from evaluate_min_cluster_size import load_ground_truth, score  # noqa: E402


def segment_scores(segments, gt_rows, turns, turn_confidence_below):
    """Per Whisper-segment: welke echte spreker (meeste overlap met ground
    truth) vs. welk label de pipeline geeft."""
    def gt_speaker(seg):
        ov = Counter()
        for s, e, spk in gt_rows:
            o = min(seg.end, e) - max(seg.start, s)
            if o > 0:
                ov[spk] += o
        return ov.most_common(1)[0][0] if ov else None

    label_map = build_label_map(DiarizationResult(turns, "x", "x"))["map"]
    out = assign_speakers(segments, turns, label_map, turn_confidence_below=turn_confidence_below)
    truth = [gt_speaker(s) for s in segments]
    hyp = [o.speaker_raw for o in out]
    # koppel elk pipeline-label aan de echte spreker waar het het vaakst bij hoort
    mapping = {}
    for h in set(hyp):
        if h is not None:
            mapping[h] = Counter(t for t, x in zip(truth, hyp) if x == h).most_common(1)[0][0]
    pairs = [(t, mapping.get(h), o) for t, h, o in zip(truth, hyp, out) if t is not None]
    correct = [t == m for t, m, _ in pairs]
    flagged = [o.overlap or o.uncertain_assignment for _, _, o in pairs]
    return {
        "segments": len(pairs),
        "segment_accuracy": round(sum(correct) / len(pairs), 3) if pairs else None,
        "flagged_segments": sum(flagged),
        "wrong_and_not_flagged": sum(1 for c, f in zip(correct, flagged) if not c and not f),
        "wrong_but_flagged": sum(1 for c, f in zip(correct, flagged) if not c and f),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fragments", nargs="+", help="bv. testaudio2_fragment testaudio4_fragment")
    parser.add_argument("--min-cluster-size", type=int, nargs="+", default=[12, 8],
                        help="pyannote clustering.min_cluster_size-waarden om te testen (default: 12 8)")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    refine_cfg = BoundaryRefinementConfig(device=args.device)
    print(f"Embeddingmodel laden ({refine_cfg.embedding_model}) ...")
    embedder = PyannoteWindowEmbedder(refine_cfg.embedding_model, device=args.device)
    diar_cfg = DiarizationConfig(device=args.device)

    for fragment in args.fragments:
        gt_rows = load_ground_truth(fragment)
        wav_path = DIARIZATION_OUTPUT_DIR / f"{fragment}_16k_mono.wav"
        if not wav_path.exists():
            sys.exit(f"{wav_path} bestaat niet — draai eerst diarization.py voor dit fragment.")
        transcript_path = PROCESSED_DATA_DIR / f"{fragment}.json"
        segments = []
        if transcript_path.exists():
            segments = WorkshopTranscript.model_validate_json(transcript_path.read_text(encoding="utf-8")).segments
        else:
            print(f"  LET OP: geen transcript op {transcript_path} — refinement zonder Whisper-grenzen "
                  f"(zwakker) en geen segment-score.")

        results = {}
        for mcs in args.min_cluster_size:
            cfg = DiarizationConfig(device=args.device, clustering_min_cluster_size=mcs)
            backend = PyannoteBackend(cfg)
            print(f"\n=== {fragment} | min_cluster_size={mcs} ===", flush=True)
            raw = backend.diarize(wav_path)
            refined, meta = refine_diarization(raw, wav_path, segments, refine_cfg, embedder=embedder)

            row = {}
            for tag, res, conf in [("pyannote", raw, None),
                                   ("pyannote+refinement", refined, diar_cfg.turn_confidence_below)]:
                s = score(gt_rows, res.turns)
                if segments:
                    s["segment_level"] = segment_scores(segments, gt_rows, res.turns, conf)
                row[tag] = s
                seg = s.get("segment_level", {})
                print(f"  {tag:<21} tijdlijn {s['overall_correct_pct']:5.1f}%  sprekers {s['pyannote_speakers_found']}"
                      f"  per spreker {{{', '.join(f'{k}: {v['covered_pct']}' for k, v in s['per_gt_speaker'].items())}}}"
                      + (f"  | segmenten goed {seg.get('segment_accuracy')}  fout+niet-gevlagd "
                         f"{seg.get('wrong_and_not_flagged')}" if seg else ""), flush=True)
            row["refinement"] = {k: v for k, v in meta.items() if k != "config"}
            results[f"min_cluster_size={mcs}"] = row

        out_path = HERE / f"results_{fragment}.json"
        out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nUitkomsten weggeschreven naar {out_path}")


if __name__ == "__main__":
    main()
