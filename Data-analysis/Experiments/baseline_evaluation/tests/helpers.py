import csv
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

COLS = ["fragment", "turn_index", "start_seconds", "end_seconds", "speaker_id", "speaker_role", "overlap",
        "intelligible", "note", "transcript"]


def write_csv(dirpath, rows, name="ref.csv"):
    """rows: lijst dicts met start, end, spk, [role, overlap, intel, note, text]."""
    p = Path(dirpath) / name
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        for i, r in enumerate(rows):
            w.writerow(["synth", i, r["start"], r["end"], r.get("spk", ""), r.get("role", ""), r.get("overlap", "nee"),
                        r.get("intel", ""), r.get("note", ""), r.get("text", "")])
    return p


def make_ref(rows):
    from baseline_eval.refs import load_reference
    d = tempfile.mkdtemp(prefix="be_test_")
    return load_reference(write_csv(d, rows), "synth")


def hyp(*turns):
    """turns: (start, end, label)"""
    from pyannote.core import Annotation, Segment
    a = Annotation()
    for s, e, l in turns:
        a[Segment(s, e)] = l
    return a
