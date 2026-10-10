import sys,os
sys.dont_write_bytecode=True
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
import json,csv,collections,hashlib,zipfile,ast,importlib.util
z=zipfile.ZipFile(ROOT/'Data-analysis/Audit/bewijspakket_claude.zip')
rec=OUT/'teruggevonden_bewijs'
(OUT/'wer_herberekend.json').write_bytes((rec/'wer_results.json').read_bytes());(rec/'wer_results.json').write_bytes(z.read('wer_results.json'))
h=json.loads((OUT/'nb_hyp.json').read_text(encoding='utf-8'));res={}
for n in ['testaudio2','testaudio5','testaudio7']:
    gt=list(csv.DictReader((ROOT/f'Data-analysis/Experiments/diarization/hyperparameter_tuning/ground_truth_{n}_fragment.csv').open(encoding='utf-8-sig')))
    conf=collections.Counter();role=collections.defaultdict(float);pairs=[]
    for s in h[n]:
        start,end=float(s['start']),float(s['end'])
        truth=any(r['overlap']=='ja' and min(end,float(r['end_seconds']))>max(start,float(r['start_seconds'])) for r in gt)
        flag=s.get('overlap')=='True'
        conf[('TP' if truth else 'FP') if flag else ('FN' if truth else 'TN')]+=1
        for r in gt:
            ov=max(0,min(end,float(r['end_seconds']))-max(start,float(r['start_seconds'])))
            if ov and r['overlap']=='nee' and 'docent_role' in s:role[r['speaker_role']+'/'+s['docent_role']]+=ov
    res[n]=dict(overlap_counts=dict(conf),role_seconds=dict(role),rule='GT overlap=ja met positieve tijdsnijding; gehele rij is referentiepositief, halfopen intervallen')
# Vergelijk actuele refs en scripts met kopieën in het pakket; geen historische verzegeling.
eq=[]
for n in z.namelist():
    if n.startswith('scripts/'):p=ROOT/'Data-analysis/Audit'/n
    elif n.startswith('referenties/'):p=ROOT/'Data-analysis/Experiments/diarization/hyperparameter_tuning'/Path(n).name
    elif n in ['wer_results.json','synth_results.json','edge_results.json']:p=ROOT/'Data-analysis/Audit'/n
    else:continue
    eq.append(dict(member=n,repo_path=p.relative_to(ROOT).as_posix(),equal=p.read_bytes()==z.read(n)))
res['package_repo_equality']=eq
# Statische controle echte library-toekenning: geen online documentatie of modelrun nodig.
spec=importlib.util.find_spec('faster_whisper');lp=Path(spec.origin).parent/'transcribe.py'
lines=lp.read_text(encoding='utf-8').splitlines()
res['library_quality_assignment']=dict(path=str(lp),sha256=hashlib.sha256(lp.read_bytes()).hexdigest(),snippets=[dict(line=i+1,text='\n'.join(lines[max(0,i-3):i+4])) for i,x in enumerate(lines) if 'avg_logprob=avg_logprob' in x or 'no_speech_prob=no_speech_prob' in x])
(OUT/'supplemental_results.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in res.items() if k.startswith('testaudio')},indent=2))
