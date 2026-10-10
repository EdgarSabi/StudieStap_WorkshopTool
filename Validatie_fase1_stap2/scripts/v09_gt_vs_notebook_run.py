"""V09: GT-grenzen t.o.v. (a) Claudes verse ASR-run en (b) de eerder in notebook 03 opgeslagen run (nb_hyp.json), voor testaudio5.
Vraag: waren de GT-tijden voorgevuld uit de oudere run? (Alleen start/end; GT-tijden zijn op 0,1 s afgerond -> tolerantie 0,12 s.)"""
import json, csv, os, sys, io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
ROOT=r"C:\Users\School\Projects\StudieStap_WorkshopTool"; Z=os.path.join(ROOT,"Validatie_fase1_stap2","zip_extract")
GT=os.path.join(ROOT,"Data-analysis","Experiments","diarization","hyperparameter_tuning")
nb=json.load(open(os.path.join(Z,"nb_hyp.json"),encoding="utf-8")); out={}
for n in (5,):
    rows=list(csv.DictReader(open(os.path.join(GT,f"ground_truth_testaudio{n}_fragment.csv"),encoding="utf-8-sig")))
    fresh=json.load(open(os.path.join(Z,"asr",f"testaudio{n}_fragment_medium_baseline.json"),encoding="utf-8"))["segments"]
    old=[(float(r["start"]),float(r["end"])) for r in nb[f"testaudio{n}"]]
    fr=[(s["start"],s["end"]) for s in fresh]
    def match(src,tol):
        return sum(1 for r in rows if any(abs(a-float(r["start_seconds"]))<=tol and abs(b-float(r["end_seconds"]))<=tol for a,b in src))
    tail=[r for r in rows if float(r["start_seconds"])>=27.9]
    def match_tail(src,tol):
        return sum(1 for r in tail if any(abs(a-float(r["start_seconds"]))<=tol and abs(b-float(r["end_seconds"]))<=tol for a,b in src))
    out[f"testaudio{n}"]=dict(gt_rows=len(rows),match_fresh_run_tol012=match(fr,0.12),match_notebook_run_tol012=match(old,0.12),
        tail_rows_from_27_9=len(tail),tail_match_fresh=match_tail(fr,0.12),tail_match_notebook=match_tail(old,0.12))
json.dump(out,open(os.path.join(ROOT,"Validatie_fase1_stap2","resultaten","v09_gt_vs_notebook_run.json"),"w",encoding="utf-8"),indent=1)
print(json.dumps(out))
