"""Independent offline audit. Writes only in this new audit directory; no model loads."""
import sys
sys.dont_write_bytecode = True
import ast, contextlib, csv, hashlib, importlib.util, importlib.metadata, io, json, math, pathlib, subprocess, types, wave, os
from unittest.mock import patch

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parent.parent
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['MPLBACKEND'] = 'Agg'
os.environ['MPLCONFIGDIR'] = str(OUT / 'matplotlib_cache')
SRC = ROOT / 'Data-analysis/src'
sys.path.insert(0, str(SRC))
from models import TranscriptSegment as S, WorkshopTranscript, SpeakerTurn as T, ProcessedTranscript
import diarization as d
import preprocessing as p
import docent_recognition as dr
import numpy as np
import torch
from config import TranscriptionConfig, DocentRecognitionConfig

rows = []
def test(id, question, input_desc, expected, fn, limitation='Synthetisch; geen meting van modelkwaliteit.'):
    try:
        actual, passed = fn()
        rows.append(dict(id=id, vraag=question, invoer=input_desc, verwacht=expected, werkelijk=actual,
                         geslaagd=bool(passed), conclusie='Verwachte eigenschap bevestigd.' if passed else 'Verwachte eigenschap weerlegd.', beperking=limitation))
    except Exception as e:
        rows.append(dict(id=id, vraag=question, invoer=input_desc, verwacht=expected, werkelijk=f'{type(e).__name__}: {e}',
                         geslaagd=None, conclusie='Uitvoering geblokkeerd.', beperking=limitation))

def seg(a=0,b=10,**kwargs): return S(start=a,end=b,text='synthetische tekst',**kwargs)
def assigned(turns): return d.assign_speakers([seg()],turns,{'A':'MAIN_SPEAKER','B':'OTHER_SPEAKER_1'})[0]
test('T01','Wordt opeenvolgende spraak onderscheiden van simultane spraak?','A 0–8 s; B 8–10 s; ASR 0–10 s','overlap=False',lambda: (assigned([d.SpeakerTurn(0,8,'A'),d.SpeakerTurn(8,10,'B')]).model_dump(), not assigned([d.SpeakerTurn(0,8,'A'),d.SpeakerTurn(8,10,'B')]).overlap))
test('T02','Wordt ontbrekende diarizatie onzeker?','ASR 0–10 s; geen turns','speaker=None; onzeker=True',lambda: (assigned([]).model_dump(),assigned([]).speaker is None and assigned([]).uncertain_assignment))
test('T03','Wordt volledige gelijktijdige spraak onzeker?','A en B beide 0–10 s','overlap=True; onzeker=True',lambda: (assigned([d.SpeakerTurn(0,10,'A'),d.SpeakerTurn(0,10,'B')]).model_dump(),assigned([d.SpeakerTurn(0,10,'A'),d.SpeakerTurn(0,10,'B')]).uncertain_assignment))
test('T04','Kan een korte tweede spreker onzichtbaar blijven?','A 0–9 s; B 9–10 s; ASR 0–10 s','Tweede spreker zichtbaar als waarschuwing',lambda: (assigned([d.SpeakerTurn(0,9,'A'),d.SpeakerTurn(9,10,'B')]).model_dump(),assigned([d.SpeakerTurn(0,9,'A'),d.SpeakerTurn(9,10,'B')]).overlap or assigned([d.SpeakerTurn(0,9,'A'),d.SpeakerTurn(9,10,'B')]).uncertain_assignment))
def bad_model():
    x=S(start=-1,end=-2,text='x',speaker_confidence=3,extra_marker='preserve')
    return x.model_dump(),False
test('T05','Worden onlogische tijden en confidence geweigerd?','start=-1; end=-2; confidence=3','ValidationError',bad_model)
def missing_text():
    try:S(start=0,end=1)
    except Exception as e:return type(e).__name__,True
    return 'accepted',False
test('T06','Wordt verplicht tekstveld gecontroleerd?','segment zonder text','ValidationError',missing_text)
def merge():
    ss=[seg(0,1,speaker='A'),seg(1.2,2,speaker='A'),seg(2,3,speaker='A',uncertain_assignment=True),seg(3,4,speaker='A')]
    ts=p.build_speaker_turns(ss,max_gap_within_turn_seconds=1.5)
    return [t.model_dump() for t in ts], [t.n_segments_merged for t in ts]==[2,1,1] and sum(len(t.source_segments) for t in ts)==4
test('T07','Blijven onzekere segmenten apart en bronsegmenten behouden?','Twee schone, één onzeker, één schoon segment','merge-aantallen [2,1,1]; alle vier bronnen',merge)
def out_of_order():
    ts=p.build_speaker_turns([seg(5,6,speaker='A'),seg(0,1,speaker='A')],max_gap_within_turn_seconds=1.5)
    return [t.model_dump() for t in ts],all(t.end>=t.start for t in ts)
test('T08','Is preprocessing bestand tegen ongeordende segmenten?','A 5–6 s gevolgd door A 0–1 s','Geen turn met end<start',out_of_order)
def context_gap():
    ts=p.attach_context([T(turn_id=0,start=0,end=1,text='x'),T(turn_id=1,start=10,end=11,text='y')],large_context_gap_seconds=3)
    return [t.model_dump() for t in ts],ts[0].context_uncertain_after and ts[1].context_uncertain_before
test('T09','Wordt lange stilte in context gemarkeerd?','9 s tussen twee turns','Context onzeker',context_gap)
class FakeRecognizer:
    def __init__(self,v):self.v=v;self.calls=[]
    def similarity_to_reference(self,clip,sr):self.calls.append(clip.shape[-1]);return self.v,None
def role(v,turn=None,waveform=None):
    turn=turn or T(turn_id=0,start=0,end=2,text='x',speaker='OTHER_SPEAKER_1')
    r=FakeRecognizer(v)
    o=dr.assign_docent_roles([turn],waveform if waveform is not None else torch.zeros(1,32000),16000,r,DocentRecognitionConfig(reference_audio='synthetic.wav'))[0]
    return o,r
test('T10','Wordt NaN-similarity als onbruikbaar behandeld?','Fake recognizer retourneert NaN','ONZEKER',lambda:(role(float('nan'))[0].model_dump(),role(float('nan'))[0].docent_role=='ONZEKER'))
test('T11','Is een nulvector bewijs voor OTHER?','Cosine van twee nulvectoren','ONZEKER bij onbruikbare embedding',lambda:(dict(similarity=dr._cosine_similarity(np.zeros(3),np.zeros(3)),role=role(dr._cosine_similarity(np.zeros(3),np.zeros(3)))[0].docent_role),role(dr._cosine_similarity(np.zeros(3),np.zeros(3)))[0].docent_role=='ONZEKER'))
test('T12','Wordt werkelijke cliplengte gecontroleerd?','Turn 0–2 s; audio slechts 0.25 s; similarity 0.8','ONZEKER zonder embedding',lambda:(dict(role=role(0.8,waveform=torch.zeros(1,4000))[0].docent_role,samples=role(0.8,waveform=torch.zeros(1,4000))[1].calls),role(0.8,waveform=torch.zeros(1,4000))[0].docent_role=='ONZEKER'))
test('T13','Is docentrol onafhankelijk van MAIN_SPEAKER?','OTHER_SPEAKER_1; similarity 0.8','DOCENT',lambda:(role(0.8)[0].model_dump(),role(0.8)[0].docent_role=='DOCENT'))
test('T14','Blijven meerdere leerlingidentiteiten afzonderlijk?','A/B/C; A spreekt korter dan B','Drie afzonderlijke friendly labels',lambda:(d.build_label_map(d.DiarizationResult([d.SpeakerTurn(0,1,'A'),d.SpeakerTurn(1,4,'B'),d.SpeakerTurn(4,5,'C')],'synthetic','none')),len(d.build_label_map(d.DiarizationResult([d.SpeakerTurn(0,1,'A'),d.SpeakerTurn(1,4,'B'),d.SpeakerTurn(4,5,'C')],'synthetic','none'))['map'])==3))

# Importing the transcription module does not instantiate/download a model.
import transcription as tr
test('T15','Hebben verschillende bronnen verschillende cachepaden?','/a/clip.mp3 en /b/clip.wav','Verschillende outputpaden',lambda:(str(tr.output_path_for(pathlib.Path('/a/clip.mp3'),OUT))+' | '+str(tr.output_path_for(pathlib.Path('/b/clip.wav'),OUT)),tr.output_path_for(pathlib.Path('/a/clip.mp3'),OUT)!=tr.output_path_for(pathlib.Path('/b/clip.wav'),OUT)))
def batch():
    calls=[]
    class FakeModel:
        def __init__(self,*a,**k):pass
        def transcribe(self,*a,**k):
            calls.append(k)
            return iter([types.SimpleNamespace(start=0,end=1,text='x',avg_logprob=-0.1,no_speech_prob=0.1,compression_ratio=1,words=['synthetic'])]),types.SimpleNamespace(duration=1)
    with patch.object(tr,'WhisperModel',FakeModel),patch('faster_whisper.BatchedInferencePipeline',lambda model:FakeModel()):
        cfg=TranscriptionConfig(use_batching=True,beam_size=2,vad_filter=False,word_timestamps=True)
        result=tr.TranscriptionEngine(cfg).transcribe(OUT/'synthetic_16.wav')
    return dict(actual_call=calls,recorded=result.transcription_config,segment=result.segments[0].model_dump()),calls[0].get('beam_size')==2 and calls[0].get('vad_filter') is False
def wav(name,width=2,sr=16000,channels=1):
    path=OUT/name
    with wave.open(str(path),'wb') as w:
        w.setnchannels(channels);w.setsampwidth(width);w.setframerate(sr);w.writeframes(bytes(sr*channels*width))
    return path
wav('synthetic_16.wav')
test('T16','Komen batchinginstellingen overeen met opgeslagen config?','Fake Whisper; beam=2; VAD=False; words=True','Alle ingestelde parameters doorgestuurd',batch,'Modelaanroepen vervangen door testdoubles; uitsluitend wrapperlogica getest.')
test('T17','Wordt herhalende tekst gemarkeerd?','de de de de de de','possible_repetition_hallucination',lambda:(tr._detect_quality_flags('de de de de de de',-0.1,0.1,1,TranscriptionConfig()),'possible_repetition_hallucination' in tr._detect_quality_flags('de de de de de de',-0.1,0.1,1,TranscriptionConfig())))
path24=wav('synthetic_24.wav',width=3)
def wav24():
    converted=d.to_wav(path24,OUT,False)
    try:d._load_wav_waveform(converted)
    except Exception as e:return dict(returned_unchanged=converted==path24,error=str(e)),False
    return 'loaded',True
test('T18','Kan WAV met 24-bit samples via conversie worden verwerkt?','Synthetisch geldige 24-bit PCM WAV','Conversie of succesvolle verwerking',wav24)
path48=wav('synthetic_48_stereo.wav',sr=48000,channels=2)
test('T19','Wordt onverwachte sample rate correct doorgegeven door WAV-loader?','48 kHz; stereo; één seconde','sample_rate=48000; shape [2,48000]',lambda: (dict(sr=d._load_wav_waveform(path48)[1],shape=list(d._load_wav_waveform(path48)[0].shape)),d._load_wav_waveform(path48)[1]==48000 and list(d._load_wav_waveform(path48)[0].shape)==[2,48000]),'Geen test van resampling binnen pyannote.')
trunc=OUT/'synthetic_truncated.wav';trunc.write_bytes((OUT/'synthetic_16.wav').read_bytes()[:100])
def truncated():
    x,sr=d._load_wav_waveform(trunc)
    return dict(samples=x.shape[-1],header_samples=16000),False
test('T20','Wordt een gedeeltelijke WAV gedetecteerd?','Header zegt 16000 frames; bestand afgekapt tot 100 bytes','Expliciete fout of incompleet-status',truncated)
spec=importlib.util.spec_from_file_location('audit_scoring',ROOT/'Data-analysis/Experiments/diarization/hyperparameter_tuning/evaluate_min_cluster_size.py')
sc=importlib.util.module_from_spec(spec);spec.loader.exec_module(sc)
test('T21','Bestraft de bestaande score false alarms en extra speakers?','GT A 0–1 s; hyp X 0–100 s plus Y 0–1 s','Score lager dan 100%',lambda:(sc.score([(0,1,'A')],[d.SpeakerTurn(0,100,'X'),d.SpeakerTurn(0,1,'Y')]),sc.score([(0,1,'A')],[d.SpeakerTurn(0,100,'X'),d.SpeakerTurn(0,1,'Y')])['overall_correct_pct']<100))
def empty_score():
    try:result=sc.score([],[])
    except ZeroDivisionError as e:return 'ZeroDivisionError: '+str(e),False
    return result,True
test('T22','Kan lege referentie veilig worden gescoord?','Geen GT; geen hypothese','Geen score; expliciete onbruikbare referentie',empty_score)
sys.path.insert(0,str(ROOT/'Data-analysis/Experiments/classification'))
import classification_data as cd
def status():
    x=cd.ClassificationResult(fragment_id='x',center_turn_id=0,context_turn_ids=[0],indicator_id='placeholder',status='OK',detected=None,evidence=None,model_name='mock',model_version='0',prompt_version='0')
    return x.model_dump(),False
test('T23','Dwingt status OK een bruikbaar resultaat af?','OK; detected=None; evidence=None','ValidationError',status)
def finite():
    x=S(start=float('nan'),end=float('inf'),text='x')
    return dict(start_is_nan=math.isnan(x.start),json=x.model_dump_json()),False
test('T24','Weigert schema niet-eindige tijdstempels?','start NaN; end Infinity','ValidationError',finite)
test('T25','Blijft een onbekend extra bronveld behouden?','TranscriptSegment met extra_marker=preserve','Extra bronveld in JSON',lambda:(S(start=0,end=1,text='x',extra_marker='preserve').model_dump(),'extra_marker' in S(start=0,end=1,text='x',extra_marker='preserve').model_dump()))
test('T26','Blijven ontbrekende kwaliteitsvelden onbekend?','Segment met alleen start,end,text,speaker','Niet automatisch als schoon behandeld',lambda:(S(start=0,end=1,text='x',speaker='A').model_dump(),S(start=0,end=1,text='x',speaker='A').uncertain_assignment))
def special_labels():
    a=sc.load_ground_truth('testaudio1_fragment');b=sc.load_ground_truth('testaudio5_fragment')
    return dict(audio1=sorted({s for _,_,s in a}),audio5=sorted({s for _,_,s in b})),not any(s in {'GEEN','ONBEKEND'} for _,_,s in a+b)
test('T27','Worden niet-spraak en onbekende identiteit apart gehouden in scoring?','Bestaande CSV 1 en 5','GEEN/ONBEKEND geen gewone sprekeridentiteit',special_labels,'CSV gelezen; geen verificatie van annotaties tegen audio.')
def corrupt_cache():
    path=OUT/'cache_probe.json';path.write_text('{',encoding='utf-8')
    return dict(cache_found=tr.cached_result_exists(pathlib.Path('cache_probe.mp3'),OUT),contents='{'),not tr.cached_result_exists(pathlib.Path('cache_probe.mp3'),OUT)
test('T28','Wordt een corrupte transcriptcache afgewezen?','Bestaand cachebestand met alleen {','Cache niet bruikbaar',corrupt_cache)
def manual_parser():
    notebook=json.loads((ROOT/'Data-analysis/Notebooks/03-transcription-evaluation.ipynb').read_text(encoding='utf-8'))
    env={};exec(''.join(notebook['cells'][4]['source']),env)
    src=ROOT/'Data-local/raw/testaudio1_manual.txt'
    all_lines=[x.strip() for x in src.read_text(encoding='utf-8').splitlines() if x.strip()]
    loaded=env['load_manual_transcript'](src)
    return dict(nonempty_lines=len(all_lines),loaded_rows=len(loaded),omitted_lines=sum(':' not in x for x in all_lines)),len(loaded)==len(all_lines)
test('T29','Blijven ongelabelde tekstregels van de bestaande handmatige referentie behouden?','testaudio1_manual.txt via Notebook 03 cel 5','Alle niet-lege gesproken regels behouden',manual_parser,'Geen controle van de woorden tegen ontbrekende audio.')
def agreement():
    spec=importlib.util.spec_from_file_location('audit_recognition_common',ROOT/'Data-analysis/Experiments/speaker_recognition/_common.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    result=mod.compute_agreement('MAIN_SPEAKER','OTHER')
    return dict(scenario='Leerling spreekt het meest; recognizer correct OTHER',agreement=result),not result[1]
test('T30','Is agreement vrij van de aanname MAIN=docent?','MAIN is leerling; recognition OTHER','Geen conflict over correct herkende leerling',agreement)
def matching():
    src=(ROOT/'Data-analysis/Experiments/word_level_speaker_attribution/03_recognition_refinement/refine_with_speaker_recognition.py').read_text(encoding='utf-8')
    node=next(n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='_best_matching_label')
    env={'MIN_OVERLAP_FRACTION_FOR_MATCH':0.5,'_overlap_seconds':d._overlap_seconds}
    exec(compile(ast.Module(body=[node],type_ignores=[]),'original_matching_function','exec'),env)
    result=env['_best_matching_label'](0,10,[{'start':0,'end':1,'speaker':'A'}])
    return dict(result=result,overlap_over_shorter=1.0,overlap_over_new_segment=0.1),result=='A'
test('T31','Volgt refinement de gedocumenteerde overlapratio?','Nieuw segment 0–10 s; baseline 0–1 s','A: volledige overlap van kortste segment',matching,'Originele functie uit AST uitgevoerd; rest van experimentele module niet uitgevoerd.')
def quality_role():
    turn=T(turn_id=0,start=0,end=2,text='x',speaker='A',source_segments=[S(start=0,end=2,text='x',quality_flags=['high_no_speech_prob','low_avg_logprob'])])
    result,_=role(0.8,turn=turn)
    return result.model_dump(),result.docent_role=='ONZEKER'
test('T32','Blokkeren slechte ASR-signalen een stellige docentrol?','Schone diarizatie; twee ASR-quality_flags; fake similarity 0.8','Rol onzeker of expliciet kwaliteitsvoorbehoud',quality_role,'Bewezen gedrag; ontbreken blokkade is een methodologisch risico, geen bewezen verkeerde stemherkenning.')

manifest=[]
for path in sorted(ROOT.rglob('*')):
    if not path.is_file() or any(x in path.parts for x in ['.git','.idea','__pycache__',OUT.name]):continue
    manifest.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
inventory={'python':sys.version,'executable':sys.executable,'files':manifest,'packages':{}}
inventory['existing_tests']=[]
for label,cwd in [('src',SRC),('classification',ROOT/'Data-analysis/Experiments/classification')]:
    result=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-t','.','-v'],cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (OUT/f'baseline_{label}.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    inventory['existing_tests'].append({'suite':label,'returncode':result.returncode,'log':f'baseline_{label}.txt'})
result=subprocess.run([sys.executable,'-B','-m','pip','check'],capture_output=True,text=True)
(OUT/'dependency_check.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
for name in ['faster-whisper','pydantic','numpy','torch','torchaudio','pyannote.audio','python-dotenv','jiwer','scipy','pandas','matplotlib','scikit-learn','speechbrain','whisperx','nbclient','soundfile']:
    try:inventory['packages'][name]=importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:inventory['packages'][name]=None
inventory['json_files']=[]
for path in ROOT.rglob('*.json'):
    if OUT in path.parents or '.git' in path.parts:continue
    try:data=json.loads(path.read_text(encoding='utf-8'));entry={'path':path.relative_to(ROOT).as_posix(),'valid':True,'keys':list(data) if isinstance(data,dict) else None}
    except Exception as e:entry={'path':str(path),'valid':False,'error':str(e)}
    inventory['json_files'].append(entry)
inventory['csv_references']=[]
for path in (ROOT/'Data-analysis/Experiments/diarization/hyperparameter_tuning').glob('ground_truth*.csv'):
    data=list(csv.DictReader(path.open(encoding='utf-8-sig',newline='')))
    inventory['csv_references'].append({'path':path.name,'rows':len(data),'speaker_ids':sorted({r.get('speaker_id','') for r in data}),'overlap_yes':sum(r.get('overlap')=='ja' for r in data),'intelligible':dict(__import__('collections').Counter(r.get('intelligible','') for r in data))})
inventory['syntax']=[]
for path in (ROOT/'Data-analysis').rglob('*.py'):
    try:ast.parse(path.read_text(encoding='utf-8-sig'));ok=True;err=None
    except Exception as e:ok=False;err=str(e)
    inventory['syntax'].append({'path':path.relative_to(ROOT).as_posix(),'valid':ok,'error':err})
inventory['notebooks']=[]
os.chdir(ROOT/'Data-analysis/Notebooks')
for path in sorted(pathlib.Path('.').glob('*.ipynb')):
    data=json.loads(path.read_text(encoding='utf-8'));env={};entry={'path':path.name,'code_cells':0,'first_failure':None,'executed_cells':[]}
    for i,c in enumerate(data['cells']):
        if c['cell_type']!='code' or not ''.join(c['source']).strip():continue
        entry['code_cells']+=1
    for i,c in enumerate(data['cells']):
        if c['cell_type']!='code' or not ''.join(c['source']).strip():continue
        try:
            with contextlib.redirect_stdout(io.StringIO()):exec(compile(''.join(c['source']),f'{path}:cell{i+1}','exec'),env)
            entry['executed_cells'].append(i+1)
        except Exception as e:
            entry['first_failure']={'cell':i+1,'error_type':type(e).__name__,'message':str(e)};break
    inventory['notebooks'].append(entry)
(OUT/'inventory.json').write_text(json.dumps(inventory,indent=2,ensure_ascii=False),encoding='utf-8')
def sanitize(value):
    if isinstance(value,float) and not math.isfinite(value):return str(value)
    if isinstance(value,dict):return {k:sanitize(v) for k,v in value.items()}
    if isinstance(value,list):return [sanitize(v) for v in value]
    return value
(OUT/'test_results.json').write_text(json.dumps(sanitize(rows),indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
print(json.dumps({'tests':[{k:r[k] for k in ['id','geslaagd']} for r in rows],'notebooks':inventory['notebooks'],'json_count':len(inventory['json_files']),'python_count':len(inventory['syntax'])},indent=2,ensure_ascii=False))
