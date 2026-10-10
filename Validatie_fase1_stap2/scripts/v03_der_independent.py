"""V03: onafhankelijke frame-DER (10 ms, collar 0, overlap meegeteld) zonder pyannote.metrics, op de bewaarde
notebook-hypothesen (zip_extract/nb_hyp.json, hash geverifieerd) en de GT-CSV's. Valideert de DER-rekenlogica van de Claude-audit (T4).
Aanvullend: gevoeligheid voor (a) behandeling van hyp-label 'None', (b) GT-overlapstructuur."""
import csv, json, os, sys, io
import numpy as np
from scipy.optimize import linear_sum_assignment
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT=r"C:\Users\School\Projects\StudieStap_WorkshopTool"
GT=os.path.join(ROOT,"Data-analysis","Experiments","diarization","hyperparameter_tuning")
H=json.load(open(os.path.join(ROOT,"Validatie_fase1_stap2","zip_extract","nb_hyp.json"),encoding="utf-8"))
FS=0.01
def gt_rows(n): return list(csv.DictReader(open(os.path.join(GT,f"ground_truth_testaudio{n}_fragment.csv"),encoding="utf-8-sig")))
def der(ref_iv, hyp_iv, t0, t1, excl, none_is_speaker=True):
    N=int(round((t1-t0)/FS)); 
    rl=sorted({s for _,_,s in ref_iv}); hl=sorted({s for _,_,s in hyp_iv if none_is_speaker or s!='None'})
    R=np.zeros((len(rl),N),bool); Hh=np.zeros((len(hl),N),bool); E=np.zeros(N,bool)
    def idx(a,b): return max(0,min(N,int(round((a-t0)/FS)))), max(0,min(N,int(round((b-t0)/FS))))
    for a,b,s in ref_iv: i,j=idx(a,b); R[rl.index(s),i:j]=True
    for a,b,s in hyp_iv:
        if s in hl: i,j=idx(a,b); Hh[hl.index(s),i:j]=True
    for a,b in excl: i,j=idx(a,b); E[i:j]=True
    keep=~E; R=R[:,keep]; Hh=Hh[:,keep]
    nref=R.sum(0); nhyp=Hh.sum(0)
    # optimale 1-op-1 mapping: maximaliseer gemeenschappelijke frames
    C=(R[:,None,:]&Hh[None,:,:]).sum(2)
    ri,hi=linear_sum_assignment(-C) if C.size else ([],[])
    corr=np.zeros(R.shape[1])
    for r,h in zip(ri,hi): corr+= (R[r]&Hh[h])
    total=nref.sum()
    miss=np.maximum(nref-nhyp,0).sum(); fa=np.maximum(nhyp-nref,0).sum()
    conf=(np.minimum(nref,nhyp)-corr).sum()
    return dict(total_s=round(total*FS,2),miss=round(miss/total,3),fa=round(fa/total,3),conf=round(conf/total,3),DER=round((miss+fa+conf)/total,3),
                ref_overlap_s=round((nref>1).sum()*FS,2),hyp_overlap_s=round((nhyp>1).sum()*FS,2))
out={}
for n,clip in [(2,None),(5,None),(7,None),(1,(4.1,24.5))]:
    rows=gt_rows(n); name=f"testaudio{n}"
    ref=[(float(r["start_seconds"]),float(r["end_seconds"]),r["speaker_id"].strip()) for r in rows if r["speaker_id"].strip() not in("GEEN","ONBEKEND","")]
    excl=[(float(r["start_seconds"]),float(r["end_seconds"])) for r in rows if r["speaker_id"].strip() in("GEEN","ONBEKEND","")]
    hyp=[(float(r["start"]),float(r["end"]),r["speaker"] or "None") for r in H[name] if float(r["end"])>float(r["start"])]
    t0,t1=clip if clip else (0.0,max(float(r["end_seconds"]) for r in rows))
    res=dict(strict=der(ref,hyp,t0,t1,excl,True), none_dropped=der(ref,hyp,t0,t1,excl,False))
    # GT: overlappende tijdsintervallen vs overlap=ja-vlag
    ov_flag=sum(1 for r in rows if r["overlap"].strip()=="ja")
    ivs=[(float(r["start_seconds"]),float(r["end_seconds"])) for r in rows]
    ov_int=sum(1 for i,(a,b) in enumerate(ivs) if any(i!=j and min(b,d)-max(a,c)>1e-9 for j,(c,d) in enumerate(ivs)))
    res.update(gt_rows_overlap_flag_ja=ov_flag, gt_rows_with_time_overlap=ov_int,
               hyp_label_None_s=round(sum(b-a for a,b,s in hyp if s=="None"),2),
               gt_speakers=sorted({s for _,_,s in ref}), hyp_speakers=sorted({s for _,_,s in hyp}))
    out[name]=res
json.dump(out,open(os.path.join(ROOT,"Validatie_fase1_stap2","resultaten","v03_der_independent.json"),"w",encoding="utf-8"),indent=1)
for k,v in out.items(): print(k,json.dumps(v,ensure_ascii=False))
