import csv, json, re, sys, glob
from pathlib import Path
import jiwer

SP = Path(sys.argv[1])
GT = Path(r"C:\Users\School\Projects\StudieStap_WorkshopTool\Data-analysis\Experiments\diarization\hyperparameter_tuning")


def norm(t):
    t = t.lower()
    t = re.sub(r"[^\w\s']", " ", t)       # leestekens weg, apostrof blijft (z'n, heeft-ie)
    t = t.replace("-", " ")
    return re.sub(r"\s+", " ", t).strip()


def ref_text(name):
    rows = list(csv.DictReader(open(GT / f"ground_truth_{name}.csv", encoding="utf-8-sig")))
    parts = []
    for r in rows:
        if r["speaker_id"].strip() in ("GEEN",):      # applaus e.d.
            continue
        if r["transcript"].strip():
            parts.append(r["transcript"])
    return " ".join(parts), rows


out = {}
for f in sorted(glob.glob(str(SP / "asr" / "*_medium_baseline.json"))):
    name = Path(f).name.replace("_medium_baseline.json", "")
    d = json.load(open(f, encoding="utf-8"))
    hyp = " ".join(s["text"] for s in d["segments"])
    ref, rows = ref_text(name)
    r, h = norm(ref), norm(hyp)
    if not r:
        continue
    m = jiwer.process_words(r, h)
    c = jiwer.process_characters(r, h)
    out[name] = dict(ref_words=len(r.split()), hyp_words=len(h.split()), WER=round(m.wer, 3), S=m.substitutions,
                     D=m.deletions, I=m.insertions, CER=round(c.cer, 3), n_segments=len(d["segments"]),
                     duration=d["duration"], first_logprob_values=sorted({round(s["avg_logprob"], 4) for s in d["segments"]})[:6],
                     n_distinct_logprob=len({s["avg_logprob"] for s in d["segments"]}))
    # ook: alleen woorden die in rijen met intelligible=nee / ja
    print(name, out[name], flush=True)
(SP / "wer_results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
