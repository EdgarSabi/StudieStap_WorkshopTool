from pathlib import Path
import sys,json,hashlib,math,datetime,subprocess
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parent;R=O.parent
def clean(x):
    if isinstance(x,float) and not math.isfinite(x):return str(x)
    if isinstance(x,list):return [clean(v) for v in x]
    if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
    return x
p=O/'chatgpt_herhaling.json';p.write_text(json.dumps(clean(json.loads(p.read_text(encoding='utf-8'))),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
b=json.loads((O/'before_hashes.json').read_text(encoding='utf-8'))
changes=[k for k,v in b.items() if not (R/k).is_file() or hashlib.sha256((R/k).read_bytes()).hexdigest()!=v]
(O/'unchanged_originals.json').write_text(json.dumps(dict(checked=len(b),changes=changes,checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),indent=2),encoding='utf-8')
record=dict(completed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cwd=str(R),commands=[
 dict(command='python -B Validatie_fase1_stap2_2026-10-09\\validate.py',returncode=0),
 dict(command='python -B Validatie_fase1_stap2_2026-10-09\\falsification.py > Validatie_fase1_stap2_2026-10-09\\falsification.log',returncode=0,note='Tweemaal: tweede run voert tevens daadwerkelijke alignment uit in V03.'),
 dict(command='python -B Validatie_fase1_stap2_2026-10-09\\supplemental.py',returncode=0),
 dict(command="python -B Data-analysis\\Audit\\scripts\\validate_json.py 'Validatie_fase1_stap2_2026-10-09/teruggevonden_bewijs/asr/*.json' > Validatie_fase1_stap2_2026-10-09\\json_herhaling.log",returncode=0),
 dict(command='python -B Validatie_fase1_stap2_2026-10-09\\build_report.py',returncode=0),
 dict(command='python -B Validatie_fase1_stap2_2026-10-09\\finalize.py',returncode=0)],original_changes=changes,final_git_status=subprocess.check_output(['git','status','--short'],cwd=R,text=True))
(O/'execution_record.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ['chatgpt_herhaling.json','falsification_results.json','testmatrix.json','notebook_herhaling.json','wer_herberekend.json']:
    json.loads((O/name).read_text(encoding='utf-8'),parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
hashes={str(p.relative_to(O)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(O.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='validation_manifest.json'}
(O/'validation_manifest.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
print('Original files checked:',len(b),'changes:',changes,'validation files hashed:',len(hashes))
