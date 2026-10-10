"""V04: herberekening van Claude-audit T9 (overlapvlag vs GT) en T10 (docentrol vs GT-rol, testaudio7) uit bewaarde nb_hyp.json + GT-CSV.
Voor deze twee tests bestaat in het bewijspakket GEEN script; dit is dus een eigen herberekening, geen reproductie."""
import csv, json, os, sys, io
from collections import defaultdict
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
ROOT=r"C:\Users\School\Projects\StudieStap_WorkshopTool"
GT=os.path.join(ROOT,"Data-analysis","Experiments","diarization","hyperparameter_tuning")
H=json.load(open(os.path.join(ROOT,"Validatie_fase1_stap2","zip_extract","nb_hyp.json"),encoding="utf-8"))
def gt(n): return list(csv.DictReader(open(os.path.join(GT,f"ground_truth_testaudio{n}_fragment.csv"),encoding="utf-8-sig")))
def ov(a,b,c,d): return max(0,min(b,d)-max(a,c))
out={}
# T9: segment-level overlap vlag
for n in (2,5,7):
    rows=gt(n); hy=H[f"testaudio{n}"]
    flagged=[r for r in hy if r["overlap"]=="True"]
    res={}
    for label,frac in (("any_time_overlap",1e-9),("majority>0.5",0.5)):
        tp=fp=0; fn_rows=set()
        for i,r in enumerate(hy):
            a,b=float(r["start"]),float(r["end"]); dur=b-a
            gtov=any(g["overlap"].strip()=="ja" and ov(a,b,float(g["start_seconds"]),float(g["end_seconds"]))>frac*(dur if frac>0.4 else 1)  for g in rows)
            f=r["overlap"]=="True"
            if f and gtov: tp+=1
            elif f: fp+=1
        # FN: GT ja-rijen die geen gevlagd segment (majority) raken
        fn=0
        for g in rows:
            if g["overlap"].strip()!="ja": continue
            a,b=float(g["start_seconds"]),float(g["end_seconds"])
            if not any(r["overlap"]=="True" and ov(a,b,float(r["start"]),float(r["end"]))>0.5*(b-a) for r in hy): fn+=1
        res[label]=dict(flagged=len(flagged),TP=tp,FP=fp,FN_gt_rows=fn)
    res["gt_rows_ja"]=sum(1 for g in rows if g["overlap"].strip()=="ja"); res["n_hyp_segments"]=len(hy)
    out[f"T9_testaudio{n}"]=res
# T10: audio7, docentrol per seconde vs GT-rol; alleen rijen overlap=nee
rows=gt(7); hy=H["testaudio7"]
for incl in ("alleen_overlap_nee","alle_rijen"):
    tab=defaultdict(lambda: defaultdict(float))
    for g in rows:
        if incl=="alleen_overlap_nee" and g["overlap"].strip()=="ja": continue
        a,b=float(g["start_seconds"]),float(g["end_seconds"])
        for t in hy:
            o=ov(a,b,float(t["start"]),float(t["end"]))
            if o>0: tab[g["speaker_role"]][t["docent_role"]]+=o
    out[f"T10_testaudio7_{incl}"]={k:{kk:round(vv,2) for kk,vv in v.items()} for k,v in tab.items()}
# T10b: per-spreker (GT-ID) rolconsistentie en het ontstaan van "MAIN=docent": MAIN-seconden per GT-rol
tab=defaultdict(lambda: defaultdict(float))
for g in rows:
    a,b=float(g["start_seconds"]),float(g["end_seconds"])
    for t in hy:
        o=ov(a,b,float(t["start"]),float(t["end"]))
        if o>0: tab[g["speaker_role"]][t["speaker"]]+=o
out["T10b_diar_label_per_gt_role_s"]={k:{kk:round(vv,2) for kk,vv in v.items()} for k,v in tab.items()}
json.dump(out,open(os.path.join(ROOT,"Validatie_fase1_stap2","resultaten","v04_overlap_role_recheck.json"),"w",encoding="utf-8"),indent=1)
for k,v in out.items(): print(k,json.dumps(v,ensure_ascii=False))
