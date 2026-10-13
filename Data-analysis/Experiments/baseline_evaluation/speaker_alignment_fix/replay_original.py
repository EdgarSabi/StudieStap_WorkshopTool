"""Draait de ORIGINELE koppeling en preprocessing (commit 0a4ab99, uitgepakt in --src) op de ruwe beurten en Whisper-segmenten van een NIEUWE run.
Geen modellen. Schrijft JSON naar stdout. Wordt aangeroepen door final_dev_checks.py in een apart proces (de oude en nieuwe modules hebben dezelfde namen)."""
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True)
ap.add_argument("--run-dir", required=True)
a = ap.parse_args()
sys.path.insert(0, a.src)

from config import PreprocessingConfig                                                             # noqa: E402
from models import WorkshopTranscript                                                              # noqa: E402
from diarization import SpeakerTurn as RawTurn, DiarizationResult, assign_speakers, build_label_map  # noqa: E402
from preprocessing import build_speaker_turns, attach_context                                      # noqa: E402

d = Path(a.run_dir)
raw = json.loads((d / "02_diarization" / "raw_turns.json").read_text(encoding="utf-8"))["turns"]
tr = WorkshopTranscript.model_validate_json(next((d / "01_transcript").glob("*.json")).read_text(encoding="utf-8"))
res = DiarizationResult(turns=[RawTurn(t["start"], t["end"], t["speaker"]) for t in raw], backend="x", model="x", settings={}, runtime_seconds=0)
segs = assign_speakers(tr.segments, res.turns, build_label_map(res)["map"], overlap_min_ratio=0.15, uncertain_coverage_below=0.60, uncertain_margin_below=0.15)
cfg = PreprocessingConfig()
turns = attach_context(build_speaker_turns(segs, max_gap_within_turn_seconds=cfg.max_gap_within_turn_seconds), large_context_gap_seconds=cfg.large_context_gap_seconds)
print(json.dumps({"segments": [s.model_dump() for s in segs], "turns": [t.model_dump() for t in turns]}))
