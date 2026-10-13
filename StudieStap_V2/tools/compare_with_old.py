"""Vergelijk onze sprekerkoppeling met de OPGESLAGEN uitvoer van de oude pipeline.

Alleen-lezen: er wordt niets in de oude repository gewijzigd en er wordt geen oude code
geimporteerd. We lezen de oude `*_diarized.json`-bestanden, bouwen daaruit de sprekerintervallen
terug (uit `raw_speaker_intersections`) en laten onze `couple_speakers` er dezelfde segmenten
op los. De uitvoer bevat alleen aantallen, geen tekst van opnames.

Beperking: dit vergelijkt twee implementaties van dezelfde tijdrekenkunde, het zegt NIETS over
de nauwkeurigheid van de diarizatie zelf (daarvoor is een onafhankelijke referentie nodig).

Gebruik:  python tools/compare_with_old.py <map met *_diarized.json> [--out resultaat.json]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from studiestap.alignment.speakers import couple_speakers  # noqa: E402
from studiestap.models import Segment, SpeakerInterval  # noqa: E402

EPS = 1e-6


def compare_file(path: Path) -> dict | None:
    old = json.loads(path.read_text(encoding="utf-8"))
    segs = old.get("segments", [])
    if not segs or not any("raw_speaker_intersections" in s for s in segs):
        return None
    intervals = sorted({(x["speaker_raw"], round(x["start"], 6), round(x["end"], 6))
                        for s in segs for x in s.get("raw_speaker_intersections", [])})
    ivs = [SpeakerInterval(sp, a, b) for sp, a, b in intervals]
    mine = couple_speakers([Segment(i, s["start"], s["end"], "") for i, s in enumerate(segs)], ivs)

    same_inters = diff_inters = same_dom = diff_dom = tie_new = none_both = 0
    mixed_old = mixed_new = 0
    for s, m in zip(segs, mine):
        old_set = sorted((x["speaker_raw"], round(x["start"], 4), round(x["end"], 4))
                         for x in s.get("raw_speaker_intersections", []))
        new_set = sorted((x.speaker, round(x.start, 4), round(x.end, 4)) for x in m.intersections)
        # onze intersecties komen uit gededupliceerde intervallen -> vergelijk als verzameling
        if set(old_set) == set(new_set):
            same_inters += 1
        else:
            diff_inters += 1
        old_dom = s.get("speaker_raw")
        if old_dom is None and m.dominant_speaker is None:
            none_both += 1
        elif m.dominant_speaker is None:
            tie_new += 1          # wij kiezen bij exact gelijkspel niet
        elif old_dom == m.dominant_speaker:
            same_dom += 1
        else:
            diff_dom += 1
        mixed_old += bool(s.get("multiple_raw_speakers"))
        mixed_new += m.attribution == "MIXED"
    return {"file": path.name, "segments": len(segs), "intersections_gelijk": same_inters,
            "intersections_verschillend": diff_inters, "dominant_gelijk": same_dom,
            "dominant_verschillend": diff_dom, "dominant_beide_geen": none_both,
            "dominant_alleen_nieuw_geen_door_gelijkspel": tie_new,
            "multiple_raw_speakers_oud": mixed_old, "MIXED_nieuw": mixed_new}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--out")
    args = ap.parse_args()
    rows = [r for p in sorted(Path(args.folder).glob("*_diarized.json")) if (r := compare_file(p))]
    for r in rows:
        print(json.dumps(r, ensure_ascii=False))
    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
