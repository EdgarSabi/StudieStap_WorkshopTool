import json, csv, sys, warnings
warnings.filterwarnings("ignore")
from pyannote.core import Annotation, Segment, Timeline
from pyannote.metrics.diarization import DiarizationErrorRate, JaccardErrorRate
SP=sys.argv[1]
GT='C:/Users/School/Projects/StudieStap_WorkshopTool/Data-analysis/Experiments/diarization/hyperparameter_tuning/'
hyp=json.load(open(SP+'/nb_hyp.json',encoding='utf-8'))
def load_gt(n):
    rows=list(csv.DictReader(open(GT+f'ground_truth_{n}_fragment.csv',encoding='utf-8-sig')))
    return rows
def ref_ann(rows):
    a=Annotation(); excl=Timeline()
    for r in rows:
        s,e=float(r['start_seconds']),float(r['end_seconds']); k=r['speaker_id'].strip()
        if k in('GEEN','ONBEKEND',''): excl.add(Segment(s,e)); continue
        a[Segment(s,e)]=k
    return a,excl
def hyp_ann(rows,lab='speaker'):
    a=Annotation()
    for r in rows:
        s,e=float(r['start']),float(r['end'])
        if e>s: a[Segment(s,e)]=r[lab] if r[lab] else 'NONE'
    return a
def run(name,hrows,clip=None,collar=0.0,skip=False):
    gr=load_gt(name.replace('_before','').replace('_after','')); ref,excl=ref_ann(gr); h=hyp_ann(hrows)
    uem=None
    if clip: 
        uem=Timeline([Segment(*clip)])
    else:
        end=max(float(r['end_seconds']) for r in gr); uem=Timeline([Segment(0,end)])
    # remove excluded time from UEM
    segs=[]
    for u in uem:
        cur=u.start
        for x in sorted(excl.support(), key=lambda s:s.start):
            if x.end<=cur or x.start>=u.end: continue
            if x.start>cur: segs.append(Segment(cur,x.start))
            cur=max(cur,x.end)
        if cur<u.end: segs.append(Segment(cur,u.end))
    uem=Timeline(segs)
    m=DiarizationErrorRate(collar=collar,skip_overlap=skip)
    d=m(ref,h,uem=uem,detailed=True)
    tot=d['total']
    return {k:round(v,2) for k,v in d.items()}, round(d['diarization error rate'],3), (round(d['missed detection']/tot,3),round(d['false alarm']/tot,3),round(d['confusion']/tot,3))
for name,clip in [('testaudio2',None),('testaudio5',None),('testaudio7',None),('testaudio1',(4.1,24.5))]:
    h=hyp[name]
    for collar,skip in [(0.0,False),(0.25,False),(0.25,True)]:
        d,der,parts=run(name,h,clip,collar,skip)
        print(name,'collar',collar,'skip_overlap',skip,'DER',der,'(miss,fa,conf)=',parts,'ref_speech_s',d['total'])
