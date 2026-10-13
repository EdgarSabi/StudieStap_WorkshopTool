"""Voor/na-vergelijking op de BEWAARDE ruwe pyannote-beurten van baselineruns 1 en 2 (geen modelrun, geen schrijfactie naar de runs).

VOOR  = bewaarde uitvoer van de run (`*_diarized.json`, `03_preprocessing/*.json`), gemaakt met de oorspronkelijke code.
NA    = dezelfde ruwe beurten + dezelfde Whisper-segmenten door de GEWIJZIGDE assign_speakers/build_speaker_turns.
Schrijft één NIEUW JSON-bestand (modus 'x') en print een samenvatting.

    Data-analysis/src/.venv/Scripts/python.exe -B before_after_stored_runs.py --out before_after_stored_runs.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "Data-analysis" / "src"))

from config import PreprocessingConfig                                                            # noqa: E402
from models import WorkshopTranscript                                                             # noqa: E402
from diarization import SpeakerTurn as RawTurn, DiarizationResult, assign_speakers, build_label_map  # noqa: E402
from preprocessing import build_speaker_turns, attach_context                                     # noqa: E402

CFG = dict(overlap_min_ratio=0.15, uncertain_coverage_below=0.60, uncertain_margin_below=0.15)
LEGACY = ("speaker", "speaker_raw", "speaker_confidence", "overlap", "uncertain_assignment", "start", "end", "text")
RUNS = REPO / "Data-local" / "evaluation" / "baseline_v1" / "runs"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    out_path = Path(ap.parse_args().out)
    result = {}
    for run_id in ("20261012_dev_run1", "20261012_dev_run2"):
        d = RUNS / run_id / "testaudio2_fragment"
        raw = json.loads((d / "02_diarization" / "raw_turns.json").read_text(encoding="utf-8"))["turns"]
        tr = WorkshopTranscript.model_validate_json(next((d / "01_transcript").glob("*.json")).read_text(encoding="utf-8"))
        before = json.loads(next((d / "02_diarization").glob("*_diarized.json")).read_text(encoding="utf-8"))["segments"]
        before_pre = json.loads(next((d / "03_preprocessing").glob("*.json")).read_text(encoding="utf-8"))["turns"]
        res = DiarizationResult(turns=[RawTurn(t["start"], t["end"], t["speaker"]) for t in raw], backend="x", model="x", settings={}, runtime_seconds=0)
        after = assign_speakers(tr.segments, res.turns, build_label_map(res)["map"], **CFG)
        cfg = PreprocessingConfig()
        turns = attach_context(build_speaker_turns(after, max_gap_within_turn_seconds=cfg.max_gap_within_turn_seconds),
                               large_context_gap_seconds=cfg.large_context_gap_seconds)
        rows = []
        for i, (b, a) in enumerate(zip(before, after)):
            ad = a.model_dump()
            rows.append({
                "segment": i, "start": a.start, "end": a.end,
                "dominant_before": b["speaker_raw"], "dominant_after": a.speaker_raw,
                "legacy_fields_equal": all(ad[f] == b[f] for f in LEGACY),
                "had_new_fields_before": "raw_speaker_intersections" in b,
                "multiple_raw_speakers_after": a.multiple_raw_speakers,
                "intersections_after": [(x.speaker_raw, round(x.start, 3), round(x.end, 3), round(x.duration, 3)) for x in a.raw_speaker_intersections],
            })
        sec = {}
        for a in after:
            for x in a.raw_speaker_intersections:
                sec[x.speaker_raw] = sec.get(x.speaker_raw, 0.0) + x.duration
        result[run_id] = {
            "n_segments": len(after),
            "all_legacy_fields_equal": all(r["legacy_fields_equal"] for r in rows),
            "dominant_labels_before": sorted({r["dominant_before"] for r in rows}),
            "dominant_labels_after": sorted({r["dominant_after"] for r in rows}),
            "raw_speakers_visible_before_in_segments": sorted({r["dominant_before"] for r in rows}),
            "raw_speakers_visible_after_in_segments": sorted({x[0] for r in rows for x in r["intersections_after"]}),
            "segments_with_multiple_raw_speakers_after": [r["segment"] for r in rows if r["multiple_raw_speakers_after"]],
            "seconds_per_raw_speaker_in_segments_after": {k: round(v, 6) for k, v in sorted(sec.items())},
            "turns_before": len(before_pre), "turns_after": len(turns),
            "turn_grouping_unchanged": [(t.start, t.end, t.speaker, t.overlap, t.uncertain_assignment) for t in turns]
                                       == [(t["start"], t["end"], t["speaker"], t["overlap"], t["uncertain_assignment"]) for t in before_pre],
            "turns_raw_speaker_seconds_after": [{"turn": t.turn_id, "start": t.start, "end": t.end, "speaker": t.speaker,
                                                 "raw_speaker_seconds": {k: round(v, 3) for k, v in t.raw_speaker_seconds.items()},
                                                 "multiple_raw_speakers": t.multiple_raw_speakers} for t in turns],
            "segments": rows,
        }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "x", encoding="utf-8") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)
    for run_id, r in result.items():
        print(run_id)
        for k in ("n_segments", "all_legacy_fields_equal", "dominant_labels_before", "dominant_labels_after",
                  "raw_speakers_visible_before_in_segments", "raw_speakers_visible_after_in_segments",
                  "segments_with_multiple_raw_speakers_after", "seconds_per_raw_speaker_in_segments_after",
                  "turns_before", "turns_after", "turn_grouping_unchanged"):
            print(f"  {k}: {r[k]}")


if __name__ == "__main__":
    main()
