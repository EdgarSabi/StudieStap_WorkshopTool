"""V02: onafhankelijke herberekening van WER/CER met eigen Levenshtein (geen jiwer) + circulariteitsindicatoren.
Invoer: Claude's opgeslagen ASR-JSON's (zip_extract/asr, hash geverifieerd in V01) en de GT-CSV's in de repo. Geen ASR-run."""
import csv, json, re, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = r"C:\Users\School\Projects\StudieStap_WorkshopTool"
ASR = os.path.join(ROOT,"Validatie_fase1_stap2","zip_extract","asr")
GT = os.path.join(ROOT,"Data-analysis","Experiments","diarization","hyperparameter_tuning")
def norm(t):
    t=t.lower(); t=re.sub(r"[^\w\s']"," ",t).replace("-"," "); return re.sub(r"\s+"," ",t).strip()
def lev(a,b):
    n,m=len(a),len(b); prev=list(range(m+1))
    for i in range(1,n+1):
        cur=[i]+[0]*m
        for j in range(1,m+1):
            cur[j]=min(prev[j]+1,cur[j-1]+1,prev[j-1]+(a[i-1]!=b[j-1]))
        prev=cur
    return prev[m]
def wer(r,h): R,H=r.split(),h.split(); return lev(R,H)/len(R), len(R), len(H)
def cer(r,h): return lev(list(r),list(h))/len(r)
out={}
for n in (1,2,4,5,7):
    name=f"testaudio{n}_fragment"
    rows=list(csv.DictReader(open(os.path.join(GT,f"ground_truth_{name}.csv"),encoding="utf-8-sig")))
    d=json.load(open(os.path.join(ASR,f"{name}_medium_baseline.json"),encoding="utf-8"))
    segs=d["segments"]; hyp=" ".join(s["text"] for s in segs)
    # variant A = zoals Claude (GEEN uit ref, alle hyp)
    refA=" ".join(r["transcript"] for r in rows if r["speaker_id"].strip()!="GEEN" and r["transcript"].strip())
    # variant B = A + rijen met note 'niet meenemen' eruit
    refB=" ".join(r["transcript"] for r in rows if r["speaker_id"].strip()!="GEEN" and r["transcript"].strip() and "niet meenemen" not in r["note"])
    # variant C = GEEN uit beide kanten: ASR-segmenten die >50% binnen een GEEN-rij vallen ook weg
    geen=[(float(r["start_seconds"]),float(r["end_seconds"])) for r in rows if r["speaker_id"].strip()=="GEEN"]
    def in_geen(s):
        dur=s["end"]-s["start"]
        return any(max(0,min(s["end"],e)-max(s["start"],b))>0.5*dur for b,e in geen)
    hypC=" ".join(s["text"] for s in segs if not in_geen(s))
    res={}
    for lab,(r,h) in dict(A=(refA,hyp),B=(refB,hyp),C=(refA,hypC)).items():
        w,nr,nh=wer(norm(r),norm(h)); res[lab]=dict(WER=round(w,3),CER=round(cer(norm(r),norm(h)),3),ref_words=nr,hyp_words=nh)
    # circulariteit: GT-rij exact gelijk aan ASR-segment (genormaliseerd tekst) en tijdsgrenzen +-0.06
    exact_text=0; bound=0; ntext=0
    for r in rows:
        if not r["transcript"].strip(): continue
        ntext+=1; s0,e0=float(r["start_seconds"]),float(r["end_seconds"])
        if any(abs(s["start"]-s0)<=0.06 and abs(s["end"]-e0)<=0.06 for s in segs): bound+=1
        if any(norm(s["text"])==norm(r["transcript"]) for s in segs): exact_text+=1
    gt_whole=sum(1 for r in rows if float(r["start_seconds"]).is_integer() and float(r["end_seconds"]).is_integer())
    asr_whole=sum(1 for s in segs if float(s["start"]).is_integer() and float(s["end"]).is_integer())
    res.update(n_rows=len(rows),rows_with_text=ntext,rows_boundary_match=bound,rows_exact_text_match_segment=exact_text,
               gt_rows_whole_sec=gt_whole,asr_segs=len(segs),asr_segs_whole_sec=asr_whole,
               n_intelligible_nee=sum(1 for r in rows if r.get("intelligible","").strip()=="nee"),
               audio_duration=d["duration"],last_seg_end=segs[-1]["end"],last_gt_end=max(float(r["end_seconds"]) for r in rows))
    out[name]=res
json.dump(out,open(os.path.join(ROOT,"Validatie_fase1_stap2","resultaten","v02_wer_independent.json"),"w",encoding="utf-8"),indent=1)
for k,v in out.items(): print(k,json.dumps(v,ensure_ascii=False))
