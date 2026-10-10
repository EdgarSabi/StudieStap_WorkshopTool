import sys, os
sys.dont_write_bytecode=True
from pathlib import Path
OUT=Path(__file__).resolve().parent; ROOT=OUT.parent
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',MPLBACKEND='Agg',MPLCONFIGDIR=str(OUT/'mpl'))
import json,csv,re,ast,contextlib,io,importlib.util,hashlib,subprocess
sys.path.insert(0,str(ROOT/'Data-analysis/src'))
import diarization as d, transcription as tr, preprocessing as p, docent_recognition as dr
from models import TranscriptSegment as S
import torch, numpy as np
from pyannote.core import Annotation, Segment, Timeline
from pyannote.metrics.diarization import DiarizationErrorRate
rows=[]
def check(id,q,hypothesis,inp,expected,fn,conclusion,limit):
    try: actual=fn(); err=None
    except Exception as e:actual=None;err=f'{type(e).__name__}: {e}'
    rows.append(dict(id=id,question=q,hypothesis=hypothesis,input=inp,expected=expected,actual=actual,error=err,conclusion=conclusion,limitation=limit))
def annot(turns):
    a=Annotation()
    for i,(s,e,k) in enumerate(turns):a[Segment(s,e),i]=k
    return a
def der(ref,hyp): return DiarizationErrorRate(collar=0,skip_overlap=False)(annot(ref),annot(hyp),uem=Timeline([Segment(0,2)]),detailed=True)
check('V01','Is MAIN een docentlabel?','Claude E1 verwacht docent=MAIN, maar functiecontract is spreektijdrang.',[[0,10,'docent'],[10,40,'leerling']],{'docent':'OTHER_SPEAKER_1','leerling':'MAIN_SPEAKER'},lambda:d.build_label_map(d.DiarizationResult([d.SpeakerTurn(0,10,'docent'),d.SpeakerTurn(10,40,'leerling')],'mock','mock')), 'E1 toont de gedocumenteerde rangschikking; geen fout in rolherkenning.','Rollen in synthetische invoer bekend; geen embeddings.')
check('V02','Verbergt alignment korte simultane spraak?','Ook echte overlap kan onder de vlagdrempel verdwijnen.',[[0,10,'A'],[9,10,'B']],{'overlap':True,'second_speaker_activity_seconds':1},lambda:d.assign_speakers([S(start=0,end=10,text='x')],[d.SpeakerTurn(0,10,'A'),d.SpeakerTurn(9,10,'B')],{'A':'A','B':'B'})[0].model_dump(),'Werkelijke overlap is 1 s, maar vlag is False. T03/E5 generaliseren niet naar alle overlap.','Pure geometrie; geen modeltest.')
def bounds():
    r=[(0,1,'A'),(1,2,'B')]
    raw_bad=[(0,1,'X'),(0,1,'Y')]
    processed_bad=[(0,2,'X')]
    good=[(0,1,'X'),(1,2,'Y')]
    def processed(ts):
        result=d.assign_speakers([S(start=0,end=2,text='x')],[d.SpeakerTurn(*t) for t in ts],{'X':'X','Y':'Y'})[0]
        return [(result.start,result.end,result.speaker)]
    assert processed(raw_bad)==processed_bad and processed(good)==processed_bad
    return dict(raw_bad_der=der(r,raw_bad)['diarization error rate'],raw_good_der=der(r,good)['diarization error rate'],same_segment_der=der(r,processed(raw_bad))['diarization error rate'])
check('V03','Is segment-DER altijd een ondergrens voor raw-DER?','Er is geen gegarandeerde ordening.',{'ref':'A 0–1; B 1–2','raw_bad':'X+Y 0–1, daarna niets','segment':'X 0–2'}, {'raw_bad_der':1.0,'raw_good_der':0.0,'same_segment_der':0.5},bounds,'Segmentrepresentatie kan DER verhogen of verlagen; ondergrensclaim weerlegd.','Synthetisch; toont geen richting van bias in echte fragmenten.')
def overwrite():
    src=(ROOT/'Data-analysis/Audit/scripts/der.py').read_text(); tree=ast.parse(src)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='ref_ann')
    env=dict(Annotation=Annotation,Segment=Segment,Timeline=Timeline)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'der.py::ref_ann','exec'),env)
    a,_=env['ref_ann']([dict(start_seconds='0',end_seconds='1',speaker_id='A'),dict(start_seconds='0',end_seconds='1',speaker_id='B')])
    return dict(tracks=list(a.itertracks(yield_label=True)),labels=a.labels())
check('V04','Bewaart Claude DER twee identieke overlapintervallen?','Zonder track-ID wordt eerste spreker overschreven.','A en B beide 0–1',{'labels':['A','B'],'tracks':2},overwrite,'ref_ann verliest een spreker bij identieke intervallen; overlap=ja alleen voegt evenmin een tweede track toe.','Dit tegenvoorbeeld bewijst niet dat alle huidige CSV-rijen identiek overlappen.')
def normalizer(t):return re.sub(r'\s+',' ',re.sub(r"[^\w\s']",' ',t.lower()).replace('-',' ')).strip()
def distance(a,b):
    prev=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        cur=[i]
        for j,y in enumerate(b,1):cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+(x!=y)))
        prev=cur
    return prev[-1]
def metrics():
    import jiwer
    result={}
    for f in sorted((OUT/'teruggevonden_bewijs/asr').glob('*.json')):
        name=f.name.replace('_medium_baseline.json',''); data=json.loads(f.read_text(encoding='utf-8'))
        rs=list(csv.DictReader((ROOT/f'Data-analysis/Experiments/diarization/hyperparameter_tuning/ground_truth_{name}.csv').open(encoding='utf-8-sig')))
        ref=normalizer(' '.join(r['transcript'] for r in rs if r['speaker_id'].strip()!='GEEN' and r['transcript'].strip()))
        hyp=normalizer(' '.join(s['text'] for s in data['segments']))
        result[name]=dict(words=len(ref.split()),word_edits=distance(ref.split(),hyp.split()),WER=distance(ref.split(),hyp.split())/len(ref.split()),char_edits=distance(ref,hyp),CER=distance(ref,hyp)/len(ref),jiwer_WER=jiwer.wer(ref,hyp),jiwer_CER=jiwer.cer(ref,hyp),same_intervals=sum(any(abs(float(r['start_seconds'])-s['start'])<=.06 and abs(float(r['end_seconds'])-s['end'])<=.06 for s in data['segments']) for r in rs),rows=len(rs),end_reference=max(float(r['end_seconds']) for r in rs),duration=data['duration'])
    return result
check('V05','Zijn opgeslagen WER/CER aritmetisch juist?','Onafhankelijke edit distance geeft dezelfde cijfers.','5 teruggevonden ASR-JSON + huidige hashgelijke CSV','WER afgerond 0.032/0/0/0.123/0.031; CER 0.035/0/0/0.100/0.022',metrics,'Rekenkundige replicatie; geen ASR-run en geen onafhankelijkheid van annotaties bewezen.','Normalisatie gelijk gehouden voor vergelijking; spreker- en tijdcorrectheid niet getoetst.')
check('V06','Heeft to_wav contractuele plicht elke WAV te converteren?','Docstring belooft conversie van non-WAV; bestaand WAV blijft geldig pad.',str(ROOT/'Audit_fase1_2026-10-09/synthetic_48_stereo.wav'),'zelfde pad (gedocumenteerd non-WAV contract)',lambda:str(d.to_wav(ROOT/'Audit_fase1_2026-10-09/synthetic_48_stereo.wav',OUT/'wav_probe',False)),'Claude E16 is geen bewijs van contractbreuk; formaatcompatibiliteit is aparte vraag (T18).','Geen backendrun of interne resampling.')
def cache_config():
    dst=OUT/'cache_config';dst.mkdir(exist_ok=True);(dst/'x.json').write_text('{"model_size":"base"}',encoding='utf-8')
    return dict(cached=tr.cached_result_exists(Path('x.mp3'),dst),signature=str(__import__('inspect').signature(tr.cached_result_exists)),stored_model='base',requested_model='medium')
check('V07','Kan cache modelconfig beoordelen?','Helpers hebben geen modelconfigargument.','x.json met base; aanvraag medium','cache moet modelmismatch onderscheiden',cache_config,'Helpers tonen bestaan-only cache; CLI-inspectie bevestigt check vóór modelconstructie.','Geen model aangeroepen; verzoek medium is scenario, niet CLI-inference.')
def weak_pass():
    tree=ast.parse((ROOT/'Audit_fase1_2026-10-09/run_audit.py').read_text())
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='merge')
    class FakeP:
        @staticmethod
        def build_speaker_turns(ss,**kw):
            from types import SimpleNamespace
            return [SimpleNamespace(n_segments_merged=n,source_segments=[ss[0]]*n,model_dump=lambda:{'fake':'duplicated source'}) for n in [2,1,1]]
    env={'p':FakeP,'seg':lambda a,b,**kw:S(start=a,end=b,text='x',**kw)}
    exec(compile(ast.Module(body=[node],type_ignores=[]),'T07_mutation','exec'),env)
    return dict(actual=env['merge'](),duplicate_source_indices=[0,0,0,0])
check('V08','Bewijst T07 dat elk bronsegment exact eenmaal behouden is?','Een telling alleen kan duplicatie missen.','Fake preprocessing levert [2,1,1] maar herhaalt alleen eerste bron','T07 moet False geven bij gedupliceerde/ontbrekende bronnen',weak_pass,'T07 blijft True bij vier kopieën van bron 0; oorspronkelijke test is voor bronbehoud onvolledig.','Mutatie van afzonderlijke testdouble, geen originele bestanden gewijzigd.')
def snapshot_check():
    saved=json.loads((OUT/'teruggevonden_bewijs/nb_hyp.json').read_text(encoding='utf-8'))
    src=(ROOT/'Data-analysis/Audit/scripts/extract_nb.py').read_text(encoding='utf-8')
    argv=sys.argv[:];sys.argv=['extract_nb.py',str(OUT)]
    try:
        with contextlib.redirect_stdout(io.StringIO()):exec(compile(src,'extract_nb.py','exec'),{'__name__':'__main__'})
    finally:sys.argv=argv
    new=json.loads((OUT/'nb_hyp.json').read_text(encoding='utf-8'))
    return dict(equal=saved==new,counts={k:len(v) for k,v in new.items()})
check('V09','Komt teruggevonden nb_hyp overeen met huidige opgeslagen notebookuitvoer?','Parser herhaalt dezelfde tabellen.','notebook 03/05 HTML + extract_nb.py','inhoud gelijk',snapshot_check,'Toetst extractie en koppeling aan huidige snapshot; geen notebookbrondata/modelrun.','Historische invoerhash bij oorspronkelijke run ontbreekt.')
# Hetzelfde uitvoeringsmodel als ChatGPT: verse variabelenruimte per notebook, geen echte kernel.
nbs=[];old=os.getcwd();os.chdir(ROOT/'Data-analysis/Notebooks')
for f in sorted(Path('.').glob('*.ipynb')):
    nb=json.loads(f.read_text(encoding='utf-8')); env={}; executed=[];failure=None;buf=io.StringIO()
    for i,c in enumerate(nb['cells'],1):
        code=''.join(c['source'])
        if c['cell_type']!='code' or not code.strip():continue
        try:
            with contextlib.redirect_stdout(buf),contextlib.redirect_stderr(buf):exec(compile(code,f'{f}:cell{i}','exec'),env)
            executed.append(i)
        except Exception as e:failure=dict(cell=i,type=type(e).__name__,message=str(e));break
    nbs.append(dict(notebook=f.name,executed=executed,failure=failure,mode='exec fresh namespace; shared process, no Jupyter kernel',counts=[c.get('execution_count') for c in nb['cells'] if c['cell_type']=='code']))
os.chdir(old)
(OUT/'notebook_herhaling.json').write_text(json.dumps(nbs,indent=2,ensure_ascii=False),encoding='utf-8')
(OUT/'falsification_results.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
print(json.dumps(rows,ensure_ascii=False,default=str,indent=2))
