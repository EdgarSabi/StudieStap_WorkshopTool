"""Onafhankelijke validatie van pipeline-JSON (alleen lezen). Gebruik: python validate_json.py <bestand.json> ..."""
import json, sys, glob
from pathlib import Path
sys.path.insert(0, r"C:\Users\School\Projects\StudieStap_WorkshopTool\Data-analysis\src")
from models import WorkshopTranscript, ProcessedTranscript


def check_transcript(d):
    issues = []
    segs = d["segments"]
    dur = d["duration"]
    prev_end = -1
    whole = 0
    for i, s in enumerate(segs):
        if s["end"] <= s["start"]: issues.append(f"seg {i}: end<=start")
        if s["start"] < prev_end - 1e-6: issues.append(f"seg {i}: begint voor einde vorige ({s['start']}<{prev_end})")
        if s["end"] > dur + 0.05: issues.append(f"seg {i}: einde {s['end']} > duur {dur}")
        if not s["text"].strip(): issues.append(f"seg {i}: lege tekst")
        if abs(s["start"] - round(s["start"])) < 1e-6 and abs(s["end"] - round(s["end"])) < 1e-6: whole += 1
        prev_end = max(prev_end, s["end"])
        if s.get("speaker") is not None and not s.get("speaker_raw"): issues.append(f"seg {i}: speaker zonder speaker_raw")
    if segs and whole / len(segs) > 0.5: issues.append(f"{whole}/{len(segs)} segmenten met hele-seconde-grenzen (timestamp-resolutie verdacht)")
    if d.get("diarization") is None: issues.append("geen diarization-blok (alleen ASR)")
    if Path(d["audio_file"]).is_absolute(): issues.append(f"absoluut pad in audio_file: {d['audio_file']}")
    return issues


for pat in sys.argv[1:]:
    for f in glob.glob(pat):
        raw = json.loads(Path(f).read_text(encoding="utf-8"))
        kind = "ProcessedTranscript" if "turns" in raw and "source_transcript_path" in raw else "WorkshopTranscript" if "segments" in raw else "overig"
        issues = []
        if kind == "WorkshopTranscript":
            WorkshopTranscript.model_validate(raw); issues = check_transcript(raw)
        elif kind == "ProcessedTranscript":
            ProcessedTranscript.model_validate(raw)
        print(f"{Path(f).name}: {kind}; {len(issues)} bevindingen")
        for x in issues: print("   -", x)
