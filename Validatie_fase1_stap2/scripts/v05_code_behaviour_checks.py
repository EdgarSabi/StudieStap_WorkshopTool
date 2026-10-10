"""V05: eigen falsificatietests op productiecode (alleen lezen/importeren; tijdelijke bestanden uitsluitend in Validatie_fase1_stap2/tmp).
Verwachte uitkomsten worden hier ONAFHANKELIJK afgeleid uit de gedocumenteerde drempels in config.py (overlap_min_ratio=0.15,
uncertain_coverage_below=0.60, uncertain_margin_below=0.15) of uit de tekst van de documentatie, niet uit de te testen uitvoer."""
import sys, os, json, io, math, csv, wave, tempfile, shutil, contextlib
sys.dont_write_bytecode=True
ROOT=r"C:\Users\School\Projects\StudieStap_WorkshopTool"
sys.path.insert(0,os.path.join(ROOT,"Data-analysis","src"))
TMP=os.path.join(ROOT,"Validatie_fase1_stap2","tmp"); os.makedirs(TMP,exist_ok=True)
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
import diarization as d, transcription as tr
from models import TranscriptSegment as S, WorkshopTranscript
from pathlib import Path
R={}
# ---- V05-1: spec-afgeleide verwachting vs implementatie, sweep van korte tweede spreker
def spec(dur,a,b):  # a,b = seconden van spreker A,B in het segment
    win,run=max(a,b),min(a,b)
    return dict(overlap=(run/dur)>=0.15, uncertain=((win/dur)<0.60) or (((win-run)/dur)<0.15))
sweep=[]
for x in (0.5,1.0,1.4,1.5,2.0,3.0,4.0,5.0):
    seg=S(start=0,end=10,text="t")
    turns=[d.SpeakerTurn(0,10-x,"A"),d.SpeakerTurn(10-x,10,"B")]
    o=d.assign_speakers([seg],turns,{"A":"MAIN_SPEAKER","B":"OTHER_SPEAKER_1"})[0]
    exp=spec(10,10-x,x)
    sweep.append(dict(B_seconds=x,spec_overlap=exp["overlap"],spec_uncertain=exp["uncertain"],got_overlap=o.overlap,got_uncertain=o.uncertain_assignment,
                      matches_spec=(exp["overlap"]==o.overlap and exp["uncertain"]==o.uncertain_assignment),B_visible=bool(o.overlap or o.uncertain_assignment),label=o.speaker))
R["V05-1_sweep_sequential_second_speaker"]=sweep
# ---- V05-2: sequentieel vs simultaan, zelfde B-aandeel -> onderscheidt de vlag?
seg=S(start=0,end=10,text="t"); lm={"A":"MAIN_SPEAKER","B":"OTHER_SPEAKER_1"}
seq=d.assign_speakers([seg],[d.SpeakerTurn(0,7,"A"),d.SpeakerTurn(7,10,"B")],lm)[0]
sim=d.assign_speakers([seg],[d.SpeakerTurn(0,10,"A"),d.SpeakerTurn(7,10,"B")],lm)[0]
R["V05-2_sequential_vs_simultaneous"]=dict(sequential=dict(overlap=seq.overlap,uncertain=seq.uncertain_assignment,conf=seq.speaker_confidence),
    simultaneous=dict(overlap=sim.overlap,uncertain=sim.uncertain_assignment,conf=sim.speaker_confidence),flags_identical=(seq.overlap,seq.uncertain_assignment)==(sim.overlap,sim.uncertain_assignment))
# ---- V05-3: orde-invariantie van assign_speakers
a=d.assign_speakers([seg],[d.SpeakerTurn(0,5,"A"),d.SpeakerTurn(5,10,"B")],lm)[0]
b=d.assign_speakers([seg],[d.SpeakerTurn(5,10,"B"),d.SpeakerTurn(0,5,"A")],lm)[0]
R["V05-3_tie_order_dependence_5s_5s"]=dict(order1=a.speaker,order2=b.speaker,uncertain=(a.uncertain_assignment,b.uncertain_assignment))
# ---- V05-4: cache E2E via transcription.main() met omgeleide mappen (geen model, geen echte data)
td=Path(tempfile.mkdtemp(dir=TMP)); proc=td/"processed"; proc.mkdir(); tf=td/"test"; tf.mkdir()
fake=dict(audio_file="x.mp3",language="nl",duration=1.0,segments=[],model_size="base",transcription_time_seconds=0.1,transcription_config={})
(proc/"clip.json").write_text(json.dumps(fake),encoding="utf-8")
tr.PROCESSED_DATA_DIR=proc; tr.TEST_FILES_DIR=tf; tr.RAW_DATA_DIR=td/"raw"
buf=io.StringIO(); code=None
sys.argv=["transcription.py","clip.mp3","--dir","test","--model","medium"]
with contextlib.redirect_stdout(buf):
    try: tr.main()
    except SystemExit as e: code=e.code
R["V05-4_cache_reuse_other_model_e2e"]=dict(cached_json_model="base",requested_model="medium",exit_code=code,stdout=buf.getvalue().strip(),
    engine_constructed=("Loading model" in buf.getvalue()))
# zelfde naam, andere inhoud/map
R["V05-4b_same_stem_other_folder"]=dict(path_a=str(tr.output_path_for(Path("raw/x.mp3"),proc)),path_b=str(tr.output_path_for(Path("test/x.wav"),proc)))
# ---- V05-5: NaN tijdstempel roundtrip
x=S(start=float("nan"),end=1.0,text="x"); js=x.model_dump_json()
try: S.model_validate_json(js); rt="roundtrip ok"
except Exception as e: rt=f"roundtrip faalt: {type(e).__name__}"
R["V05-5_nan_timestamp_roundtrip"]=dict(json=js[:60],roundtrip=rt)
# ---- V05-6: afgekapt WAV
p=Path(TMP)/"trunc.wav"
with wave.open(str(p),"wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(bytes(32000))
b=p.read_bytes()[:100]; p.write_bytes(b)
wf,sr=d._load_wav_waveform(p); R["V05-6_truncated_wav"]=dict(bytes=len(b),samples_loaded=int(wf.shape[-1]),header_claims=16000)
# ---- V05-7: echte ASR-JSON's: komen de pathologische preprocessing-scenario's (ongeordend/overlappend/end<=start) voor?
Z=os.path.join(ROOT,"Validatie_fase1_stap2","zip_extract","asr"); rr={}
for n in (1,2,4,5,7):
    dd=json.load(open(os.path.join(Z,f"testaudio{n}_fragment_medium_baseline.json"),encoding="utf-8")); sg=dd["segments"]
    rr[f"testaudio{n}"]=dict(n=len(sg),end_le_start=sum(s["end"]<=s["start"] for s in sg),
        non_monotone=sum(1 for i in range(1,len(sg)) if sg[i]["start"]<sg[i-1]["end"]-1e-9),
        beyond_duration_s=round(max(0,sg[-1]["end"]-dd["duration"]),2),
        unique_avg_logprob=len({s["avg_logprob"] for s in sg}),unique_no_speech=len({s["no_speech_prob"] for s in sg}),
        flags_nonempty=sum(1 for s in sg if s["quality_flags"]),audio_file_absolute=os.path.isabs(dd["audio_file"]))
R["V05-7_real_asr_json_properties"]=rr
# ---- V05-8: GEEN/ONBEKEND in alle GT-CSV's
GT=os.path.join(ROOT,"Data-analysis","Experiments","diarization","hyperparameter_tuning"); gg={}
for f in sorted(os.listdir(GT)):
    if f.startswith("ground_truth") and f.endswith(".csv"):
        rows=list(csv.DictReader(open(os.path.join(GT,f),encoding="utf-8-sig")))
        from collections import Counter
        gg[f]=dict(rows=len(rows),speaker_ids=dict(Counter(r.get("speaker_id","") for r in rows)),intelligible=dict(Counter(r.get("intelligible","<kolom ontbreekt>") for r in rows)),overlap=dict(Counter(r.get("overlap","") for r in rows)))
R["V05-8_gt_csv_codebook"]=gg
shutil.rmtree(td,ignore_errors=True)
json.dump(R,open(os.path.join(ROOT,"Validatie_fase1_stap2","resultaten","v05_code_behaviour_checks.json"),"w",encoding="utf-8"),indent=1,ensure_ascii=False)
for k,v in R.items(): print(k,json.dumps(v,ensure_ascii=False))
