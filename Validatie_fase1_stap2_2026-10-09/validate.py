"""Offline testvalidatie. Alleen nieuwe bestanden onder deze map; geen modellen."""
import sys, os
sys.dont_write_bytecode = True
from pathlib import Path
OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', MPLBACKEND='Agg', MPLCONFIGDIR=str(OUT/'mpl'))
import json, csv, hashlib, zipfile, re, subprocess, importlib.metadata, contextlib, io, ast, traceback, math
def sha(b): return hashlib.sha256(b).hexdigest()
def clean(x):
    if isinstance(x,float) and not math.isfinite(x):return str(x)
    if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    return x
def save(n,x): (OUT/n).write_text(json.dumps(clean(x),ensure_ascii=False,indent=2,default=str,allow_nan=False),encoding='utf-8')
baseline = {}
for base in ['Audit_fase1_2026-10-09','Data-analysis/Audit','Data-analysis/src','Data-analysis/Notebooks','Data-analysis/Experiments','Data-local']:
    for p in (ROOT/base).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            baseline[p.relative_to(ROOT).as_posix()] = sha(p.read_bytes())
save('before_hashes.json',baseline)
checks=[]
for name in ['Audit_fase1_2026-10-09/manifest.json','Data-analysis/Audit/manifest_claude.csv']:
    p=ROOT/name
    rows=json.loads(p.read_text()) if p.suffix=='.json' else list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
    for r in rows:
        rel=r.get('path',r.get('pad')); f=ROOT/rel
        actual=sha(f.read_bytes()) if f.is_file() else None
        checks.append(dict(manifest=name,path=rel,expected=r['sha256'],actual=actual,status='MATCH' if actual==r['sha256'] else 'MISSING' if actual is None else 'DIFFERENT'))
save('manifest_checks.json',checks)
zpath=ROOT/'Data-analysis/Audit/bewijspakket_claude.zip'
z=zipfile.ZipFile(zpath)
zipchecks=[]
for line in z.read('SHA256SUMS.txt').decode('utf-8-sig').splitlines():
    if not line.strip():continue
    h,n=line.split(maxsplit=1); n=n.lstrip('* ')
    actual=sha(z.read(n)) if n in z.namelist() else None
    zipchecks.append(dict(path=n,expected=h,actual=actual,status='MATCH' if actual==h else 'DIFFERENT'))
save('zip_checks.json',dict(zip_path=str(zpath),zip_sha256=sha(zpath.read_bytes()),members=[dict(path=i.filename,size=i.file_size,sha256=sha(z.read(i.filename))) for i in z.infolist()],checks=zipchecks))
# Alleen specifiek geselecteerd oorspronkelijk/teruggevonden bewijs; geen nieuwe validatierapporten.
REC=OUT/'teruggevonden_bewijs'; REC.mkdir(exist_ok=True)
for n in z.namelist():
    if n.startswith(('asr/','referenties/','scripts/','tasks/')) or n in ['nb_hyp.json','asr_log.txt','README_bewijspakket.md','commando_overzicht_RECONSTRUCTIE.md','instellingen.md','hashes_referenties.md','wer_results.json','synth_results.json','edge_results.json','SHA256SUMS.txt']:
        dest=REC/n; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(z.read(n))
packages={}
for n in ['pydantic','numpy','torch','torchaudio','faster-whisper','pyannote.audio','pyannote.core','pyannote.metrics','jiwer','scipy','nbformat','nbclient','matplotlib','pandas','python-dotenv']:
    try: packages[n]=importlib.metadata.version(n)
    except importlib.metadata.PackageNotFoundError:packages[n]=None
save('environment.json',dict(python=sys.version,executable=sys.executable,packages=packages,commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),initial_git_status=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),specified_zip_exists=(ROOT/'Audit_bewijs/bewijspakket_claude.zip').exists()))
commands=[]
def run(cmd,cwd,log):
    r=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    (OUT/log).write_text(r.stdout+r.stderr,encoding='utf-8'); commands.append(dict(command=cmd,cwd=str(cwd),returncode=r.returncode,log=log)); return r
# Uitvoeren geselecteerde originele ChatGPT-testdefinities, met uitsluitend OUT/ROOT omgeleid.
src=(ROOT/'Audit_fase1_2026-10-09/run_audit.py').read_text(encoding='utf-8')
prefix=src.split('\nmanifest=[]')[0]
tree=ast.parse(prefix)
tree.body=[n for n in tree.body if not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'OUT','ROOT'} for t in n.targets))]
GOUT=OUT/'chatgpt_herhaling'; GOUT.mkdir(exist_ok=True)
env={'__file__':str(ROOT/'Audit_fase1_2026-10-09/run_audit.py'),'OUT':GOUT,'ROOT':ROOT}
buf=io.StringIO()
try:
    with contextlib.redirect_stdout(buf),contextlib.redirect_stderr(buf): exec(compile(tree,str(ROOT/'Audit_fase1_2026-10-09/run_audit.py'),'exec'),env)
    save('chatgpt_herhaling.json',env['sanitize'](env['rows']) if 'sanitize' in env else env['rows'])
except Exception: buf.write(traceback.format_exc())
(OUT/'chatgpt_herhaling.log').write_text(buf.getvalue(),encoding='utf-8')
commands.append(dict(command='AST-prefix run_audit.py tot manifest=[], OUT/ROOT omgeleid; geen verdere audit/notebook-loop',log='chatgpt_herhaling.log'))
COUT=OUT/'claude_herhaling'; COUT.mkdir(exist_ok=True)
run([sys.executable,'-B',str(ROOT/'Data-analysis/Audit/scripts/edge_tests.py'),str(COUT)],ROOT,'claude_edge.log')
for label,cwd in [('src',ROOT/'Data-analysis/src'),('classification',ROOT/'Data-analysis/Experiments/classification')]:
    run([sys.executable,'-B','-m','unittest','discover','-s','tests','-t','.','-v'],cwd,'unittest_'+label+'.log')
run([sys.executable,'-B',str(ROOT/'Data-analysis/Audit/scripts/wer_eval.py'),str(REC)],ROOT,'wer_herberekening.log')
(OUT/'wer_herberekend.json').write_bytes((REC/'wer_results.json').read_bytes())
(REC/'wer_results.json').write_bytes(z.read('wer_results.json'))
run([sys.executable,'-B',str(ROOT/'Data-analysis/Audit/scripts/der.py'),str(REC)],ROOT,'der_herberekening.log')
save('commands.json',commands)
after={k:sha((ROOT/k).read_bytes()) if (ROOT/k).is_file() else None for k in baseline}
save('unchanged_originals.json',dict(checked=len(baseline),changes=[k for k in baseline if baseline[k]!=after[k]]))
print('Manifest:',{s:sum(r['status']==s for r in checks) for s in ['MATCH','MISSING','DIFFERENT']})
print('Zip:',{s:sum(r['status']==s for r in zipchecks) for s in ['MATCH','DIFFERENT']})
print('Commands:',commands)
print('Original changes:',[k for k in baseline if baseline[k]!=after[k]])
