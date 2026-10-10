import sys, json, time
from pathlib import Path
SRC = Path(r"C:\Users\School\Projects\StudieStap_WorkshopTool\Data-analysis\src")
sys.path.insert(0, str(SRC))
OUT = Path(sys.argv[1]); OUT.mkdir(exist_ok=True)
from config import TranscriptionConfig
from transcription import TranscriptionEngine
cfg = TranscriptionConfig(model_size="medium")   # = run_docent_pipeline default
eng = TranscriptionEngine(cfg)
for name in sys.argv[2:]:
    t=time.time()
    r = eng.transcribe(SRC/"test-files"/f"{name}.mp3")
    (OUT/f"{name}_medium_baseline.json").write_text(r.model_dump_json(indent=2), encoding="utf-8")
    print(name, len(r.segments), "segs", round(time.time()-t,1), "s", flush=True)
