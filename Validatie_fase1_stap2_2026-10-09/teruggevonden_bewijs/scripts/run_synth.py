import sys, json, time, re
from pathlib import Path
import jiwer
SRC = Path(r"C:\Users\School\Projects\StudieStap_WorkshopTool\Data-analysis\src")
sys.path.insert(0, str(SRC))
SP = Path(sys.argv[1])
from config import TranscriptionConfig
from transcription import TranscriptionEngine
import csv

GT = Path(r"C:\Users\School\Projects\StudieStap_WorkshopTool\Data-analysis\Experiments\diarization\hyperparameter_tuning\ground_truth_testaudio2_fragment.csv")
ref = " ".join(r["transcript"] for r in csv.DictReader(open(GT, encoding="utf-8-sig")))


def norm(t):
    t = re.sub(r"[^\w\s']", " ", t.lower()).replace("-", " ")
    return re.sub(r"\s+", " ", t).strip()


eng = TranscriptionEngine(TranscriptionConfig(model_size="medium"))
out = {}
for f in sorted((SP / "synth").glob("*.wav")):
    t = time.time()
    r = eng.transcribe(f)
    text = " ".join(s.text for s in r.segments)
    row = dict(n_segments=len(r.segments), text=text[:300],
               flags=[s.quality_flags for s in r.segments][:10],
               no_speech=[round(s.no_speech_prob, 2) for s in r.segments][:10],
               avg_logprob=[round(s.avg_logprob, 2) for s in r.segments][:10],
               first_start=[(round(s.start, 2), round(s.end, 2)) for s in r.segments][:6],
               secs=round(time.time() - t, 1))
    if f.name.startswith("speech"):
        row["WER_vs_testaudio2_GT"] = round(jiwer.wer(norm(ref), norm(text)), 3) if text.strip() else 1.0
    out[f.name] = row
    print(f.name, json.dumps(row, ensure_ascii=False), flush=True)
(SP / "synth_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
