"""Reproduceerbaar tegenvoorbeeld: waar in de verwerking gaat de tweede spreker verloren?

Draait ZONDER modellen. Importeert de ORIGINELE `assign_speakers` en `build_label_map` uit Data-analysis/src (ongewijzigd) en voert ze uit op
(A) de echte ruwe beurten + Whisper-segmenten van run 1 (herberekening, moet het bewaarde resultaat reproduceren),
(B) een synthetisch geval waarin pyannote de tweede spreker PERFECT vindt, en
(C) een controlegeval waarin de koppeling wél goed werkt (laat zien dat het geen kapotte functie is).

    Data-analysis/src/.venv/Scripts/python.exe -B Data-analysis/Experiments/baseline_evaluation/counterexample_assign.py [--run-dir <run/fragment>]
Exitcode 0 = alle verwachtingen kloppen.
"""
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "Data-analysis" / "src"))

from diarization import SpeakerTurn, DiarizationResult, assign_speakers, build_label_map   # noqa: E402
from models import TranscriptSegment                                                         # noqa: E402

CFG = dict(overlap_min_ratio=0.15, uncertain_coverage_below=0.60, uncertain_margin_below=0.15)   # = DiarizationConfig-defaults


def run(turns, segs):
    res = DiarizationResult(turns=[SpeakerTurn(s, e, l) for s, e, l in turns], backend="x", model="x", settings={}, runtime_seconds=0)
    lm = build_label_map(res)
    out = assign_speakers([TranscriptSegment(start=s, end=e, text="t") for s, e in segs], res.turns, lm["map"], **CFG)
    return [(o.start, o.end, o.speaker_raw, o.overlap) for o in out]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default=str(REPO / "Data-local/evaluation/baseline_v1/runs/20261012_dev_run1/testaudio2_fragment"))
    d = Path(ap.parse_args().run_dir)
    ok = True

    # (A) echte data
    raw = json.loads((d / "02_diarization" / "raw_turns.json").read_text(encoding="utf-8"))["turns"]
    tr = json.loads(next((d / "01_transcript").glob("*.json")).read_text(encoding="utf-8"))
    saved = json.loads(next((d / "02_diarization").glob("*_diarized.json")).read_text(encoding="utf-8"))["segments"]
    got = run([(t["start"], t["end"], t["speaker"]) for t in raw], [(s["start"], s["end"]) for s in tr["segments"]])
    same = [g[2] for g in got] == [s["speaker_raw"] for s in saved]
    print(f"(A) herberekening met originele assign_speakers == bewaarde run-uitvoer: {same}")
    print(f"    ruwe sprekers: {sorted({t['speaker'] for t in raw})}; behouden na koppeling: {sorted({g[2] for g in got})}")
    seg4 = got[4]
    print(f"    segment 7.0-9.0 s (referentie: B spreekt 7.2-8.9 s): winnaar {seg4[2]}, overlap-vlag {seg4[3]}")
    ok &= same and sorted({g[2] for g in got}) == ["SPEAKER_00"]

    # (B) synthetisch: model vindt B perfect, koppeling verliest B toch
    print("(B) synthetisch, pyannote vindt B PERFECT (B spreekt 4-6 s):")
    r1 = run([(0, 10, "SPEAKER_00"), (4, 6, "SPEAKER_01")], [(4, 6)])
    print(f"    B1 niet-exclusieve beurten (A loopt door, B erbij) + ASR-segment 4-6: winnaar {r1[0][2]} (verwacht SPEAKER_00)")
    r2 = run([(0, 4, "SPEAKER_00"), (4, 6, "SPEAKER_01"), (6, 10, "SPEAKER_00")], [(2.5, 7)])
    print(f"    B2 exclusieve beurten A|B|A + een ASR-segment 2,5-7 s dat de wissel omvat: winnaar {r2[0][2]} (verwacht SPEAKER_00; B heeft 2,0 s, A 2,5 s)")
    ok &= r1[0][2] == "SPEAKER_00" and r2[0][2] == "SPEAKER_00"

    # (C) controle: gelijke grenzen -> B wordt wel gevonden
    r3 = run([(0, 4, "SPEAKER_00"), (4, 6, "SPEAKER_01"), (6, 10, "SPEAKER_00")], [(0, 4), (4, 6), (6, 10)])
    print(f"(C) controle, exclusieve beurten en ASR-grenzen vallen samen: winnaars {[x[2] for x in r3]} (verwacht 00, 01, 00)")
    ok &= [x[2] for x in r3] == ["SPEAKER_00", "SPEAKER_01", "SPEAKER_00"]

    print("ALLE VERWACHTINGEN KLOPPEN" if ok else "AFWIJKING: zie hierboven")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
