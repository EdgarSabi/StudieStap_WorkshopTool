"""
Experiment: is NVIDIA Streaming Sortformer beter dan pyannote op onze klasaudio?

Raakt de productiepipeline niet aan. Gebruikt diarization.SortformerBackend
(en optioneel PyannoteBackend als vergelijking) op dezelfde wav en scoort met
precies dezelfde score() als het hyperparameter-tuning-experiment, zodat de
getallen direct naast de oude tabel kunnen.

Draaien (vanuit Data-analysis/src):
    .venv\\Scripts\\python.exe ..\\Experiments\\diarization\\sortformer\\evaluate_sortformer.py testaudio4_fragment testaudio2_fragment
    # alle postprocessing-presets proberen:
    .venv\\Scripts\\python.exe ..\\Experiments\\diarization\\sortformer\\evaluate_sortformer.py testaudio4_fragment testaudio2_fragment --presets default dihard3 callhome
    # pyannote opnieuw meedraaien als vergelijking (HF_TOKEN nodig):
    .venv\\Scripts\\python.exe ..\\Experiments\\diarization\\sortformer\\evaluate_sortformer.py testaudio4_fragment testaudio2_fragment --with-pyannote

Naast "totaal (mild)" (precies de score uit de oude tabel) rapporteert dit
script een strenge variant, dezelfde twee scores voor korte beurten (< 1,5 s,
de tussenkomsten waar pyannote op stukloopt) en hoeveel onterechte overlap het
model geeft. Zie extra_scores() voor waarom de strenge score nodig is.
"""
import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC_DIR = HERE.parents[2] / "src"
TUNING_DIR = HERE.parent / "hyperparameter_tuning"
sys.path.insert(0, str(SRC_DIR))

from config import (  # noqa: E402
    DiarizationConfig, DIARIZATION_OUTPUT_DIR, TEST_FILES_DIR, SORTFORMER_POSTPROCESSING_PRESETS,
)
from diarization import get_backend, to_wav  # noqa: E402

# score() en load_ground_truth() hergebruiken uit het tuning-experiment, zodat
# de scoringsmethode gegarandeerd identiek is.
_spec = importlib.util.spec_from_file_location("tuning_eval", TUNING_DIR / "evaluate_min_cluster_size.py")
_tuning = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tuning)
FRAME = _tuning.FRAME


def load_ground_truth(fragment: str):
    """Zelfde rijen als het tuning-experiment, plus de overlap-kolom (ja/nee)."""
    path = TUNING_DIR / f"ground_truth_{fragment}.csv"
    if not path.exists():
        sys.exit(f"Geen ground truth gevonden: {path}")
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["speaker_id"].strip():
                rows.append((
                    float(r["start_seconds"]), float(r["end_seconds"]), r["speaker_id"].strip(),
                    r.get("overlap", "").strip().lower() == "ja",
                ))
    return rows


def extra_scores(gt_rows, hyp_turns, mapping: dict, max_len: float) -> dict:
    """Aanvullende scores bovenop score().

    score() telt een blokje als goed zodra de juiste spreker ERGENS tussen de
    actieve sprekers zit. Dat is mild: een model dat overal alle sprekers
    actief zet, haalt dan 100%. Sortformer markeert van nature vaker overlap
    dan pyannote, dus daarmee zou de vergelijking scheef zijn. Daarom ook:

      - streng: het blokje telt alleen als goed als de juiste spreker actief
        is EN er geen andere spreker bij staat — behalve waar jij zelf
        overlap=ja hebt genoteerd (dan mag een tweede spreker wel).
      - korte beurten: dezelfde twee scores, alleen over handmatige beurten
        korter dan max_len seconden (de korte tussenkomsten).
      - onterechte overlap: aandeel blokjes zonder handmatige overlap waarin
        het model toch 2+ sprekers actief heeft.
    """
    c = {"mild": 0, "strict": 0, "total": 0,
         "short_mild": 0, "short_strict": 0, "short_total": 0,
         "false_ovl": 0, "no_ovl_total": 0}
    n_short = 0
    for start, end, gt_spk, gt_overlap in gt_rows:
        is_short = (end - start) < max_len
        n_short += is_short
        matched = mapping.get(gt_spk)
        t = start + FRAME / 2
        while t < end:
            active = {h.speaker for h in hyp_turns if h.start <= t < h.end}
            mild = matched in active
            strict = mild and (gt_overlap or len(active) == 1)
            c["mild"] += mild
            c["strict"] += strict
            c["total"] += 1
            if is_short:
                c["short_mild"] += mild
                c["short_strict"] += strict
                c["short_total"] += 1
            if not gt_overlap:
                c["no_ovl_total"] += 1
                c["false_ovl"] += len(active) > 1
            t += FRAME

    def pct(a, b):
        return round(100 * a / b, 1) if b else None

    return {
        "strict_correct_pct": pct(c["strict"], c["total"]),
        "n_short_turns": n_short,
        "short_turns_seconds": round(c["short_total"] * FRAME, 1),
        "short_turns_correct_pct": pct(c["short_mild"], c["short_total"]),
        "short_turns_strict_pct": pct(c["short_strict"], c["short_total"]),
        "false_overlap_pct": pct(c["false_ovl"], c["no_ovl_total"]),
    }


def evaluate(backend, wav_path: Path, gt_rows, short_turn: float) -> dict:
    result = backend.diarize(wav_path)
    s = _tuning.score([r[:3] for r in gt_rows], result.turns)
    mapping = {g: v["matched_pyannote_speaker"] for g, v in s["per_gt_speaker"].items()}
    s.update(extra_scores(gt_rows, result.turns, mapping, short_turn))
    s["hyp_turns"] = len(result.turns)
    s["runtime_seconds"] = result.runtime_seconds
    s["turns"] = [
        {"start": round(t.start, 2), "end": round(t.end, 2), "speaker": t.speaker} for t in result.turns
    ]
    return s


def stored_pyannote_baseline(fragment: str):
    """Pyannote-uitkomst met de huidige instellingen uit het tuning-experiment."""
    path = TUNING_DIR / f"results_threshold_{fragment}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return next(iter(data.values()), None)  # eerste key = huidige threshold 0.7046


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fragments", nargs="+", help="bv. testaudio4_fragment testaudio2_fragment")
    parser.add_argument("--presets", nargs="+", default=["default", "dihard3"],
                        choices=sorted(SORTFORMER_POSTPROCESSING_PRESETS),
                        help="postprocessing-presets voor Sortformer (default: default dihard3)")
    parser.add_argument("--with-pyannote", action="store_true",
                        help="pyannote ook opnieuw draaien (voor de korte-beurten-score)")
    parser.add_argument("--short-turn", type=float, default=1.5,
                        help="beurten korter dan dit (s) tellen als 'kort' (default 1.5)")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--model", default=None,
                        help="ander Sortformer-model (HF-naam of pad naar .nemo); default uit config.py")
    args = parser.parse_args()

    wavs = {}
    gts = {}
    for frag in args.fragments:
        gts[frag] = load_ground_truth(frag)
        wav = DIARIZATION_OUTPUT_DIR / f"{frag}_16k_mono.wav"
        if not wav.exists():
            src = TEST_FILES_DIR / f"{frag}.mp3"
            if not src.exists():
                sys.exit(f"Geen audio gevonden voor {frag} ({wav} of {src})")
            wav = to_wav(src, DIARIZATION_OUTPUT_DIR, force=False)
        wavs[frag] = wav

    results: dict = {frag: {} for frag in args.fragments}

    # Sortformer één keer laden, daarna per preset alleen de postprocessing wisselen.
    config = DiarizationConfig(backend="sortformer", device=args.device)
    if args.model:
        config.sortformer_model = args.model
    print(f"Sortformer laden ({config.sortformer_model})...", flush=True)
    backend = get_backend(config)
    for preset in args.presets:
        backend.config.sortformer_postprocessing = SORTFORMER_POSTPROCESSING_PRESETS[preset]
        for frag in args.fragments:
            print(f"\n=== sortformer/{preset} — {frag} ===", flush=True)
            s = evaluate(backend, wavs[frag], gts[frag], args.short_turn)
            results[frag][f"sortformer/{preset}"] = s
            print(json.dumps({k: v for k, v in s.items() if k != "turns"}, indent=2, ensure_ascii=False), flush=True)

    if args.with_pyannote:
        pconfig = DiarizationConfig(backend="pyannote", device=args.device)
        pbackend = get_backend(pconfig)
        for frag in args.fragments:
            print(f"\n=== pyannote — {frag} ===", flush=True)
            s = evaluate(pbackend, wavs[frag], gts[frag], args.short_turn)
            results[frag]["pyannote"] = s
            print(json.dumps({k: v for k, v in s.items() if k != "turns"}, indent=2, ensure_ascii=False), flush=True)

    # --- samenvattende tabel ---
    def fmt(v):
        return "–" if v is None else f"{v}%"

    print("\n\n| fragment | backend | sprekers (echt) | totaal (mild) | totaal (streng) "
          "| korte beurten (mild) | korte beurten (streng) | onterechte overlap | runtime |")
    print("|---|---|---|---|---|---|---|---|---|")
    for frag in args.fragments:
        if "pyannote" not in results[frag]:
            base = stored_pyannote_baseline(frag)
            if base:
                print(f"| {frag} | pyannote (opgeslagen) | {base['pyannote_speakers_found']} ({base['gt_speakers']}) "
                      f"| {base['overall_correct_pct']}% | – | – | – | – | {base.get('runtime_seconds', '–')}s |")
        for name, s in results[frag].items():
            print(f"| {frag} | {name} | {s['pyannote_speakers_found']} ({s['gt_speakers']}) "
                  f"| {s['overall_correct_pct']}% | {fmt(s['strict_correct_pct'])} "
                  f"| {fmt(s['short_turns_correct_pct'])} | {fmt(s['short_turns_strict_pct'])} "
                  f"| {fmt(s['false_overlap_pct'])} | {s['runtime_seconds']}s |")
    if not args.with_pyannote:
        print("\nLet op: van de opgeslagen pyannote-run is alleen de milde score bekend. "
              "Draai met --with-pyannote voor een eerlijke vergelijking op alle kolommen.")

    out_path = HERE / "results_sortformer.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nUitkomsten (incl. alle turns, om terug te luisteren) weggeschreven naar {out_path}")


if __name__ == "__main__":
    main()
