"""V06: falsificatietest circulariteit. testaudio1 heeft een handmatige transcriptie (Data-local/raw/testaudio1_manual.txt),
losstaand van de GT-CSV. Vraag: lijkt de CSV-kolom 'transcript' meer op Whisper of op de handmatige tekst?
Hypothese H1 (circulair): CSV ~ Whisper, dus WER(ASR,CSV) << WER(ASR,manual). H0: CSV en manual zijn even dicht bij ASR."""
import csv, json, re, os, sys, io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
ROOT=r"C:\Users\School\Projects\StudieStap_WorkshopTool"
def norm(t):
    t=t.lower(); t=re.sub(r"[^\w\s']"," ",t).replace("-"," "); return re.sub(r"\s+"," ",t).strip()
def lev(a,b):
    n,m=len(a),len(b); prev=list(range(m+1))
    for i in range(1,n+1):
        cur=[i]+[0]*m
        for j in range(1,m+1): cur[j]=min(prev[j]+1,cur[j-1]+1,prev[j-1]+(a[i-1]!=b[j-1]))
        prev=cur
    return prev[m]
def wer(r,h): R,H=norm(r).split(),norm(h).split(); return round(lev(R,H)/len(R),3),len(R)
man=[l.strip() for l in open(os.path.join(ROOT,"Data-local","raw","testaudio1_manual.txt"),encoding="utf-8") if l.strip()]
man_text=" ".join(re.sub(r"^(Docent|Leerling_\d+)\s*:\s*","",l) for l in man)
GT=os.path.join(ROOT,"Data-analysis","Experiments","diarization","hyperparameter_tuning","ground_truth_testaudio1_fragment.csv")
rows=list(csv.DictReader(open(GT,encoding="utf-8-sig")))
csv_text=" ".join(r["transcript"] for r in rows if float(r["start_seconds"])>=4.0 and r["speaker_id"]!="GEEN")
asr=json.load(open(os.path.join(ROOT,"Validatie_fase1_stap2","zip_extract","asr","testaudio1_fragment_medium_baseline.json"),encoding="utf-8"))
asr_text=" ".join(s["text"] for s in asr["segments"] if s["start"]>=4.0)
res=dict(
 manual_words=len(norm(man_text).split()),
 WER_asr_vs_csv=wer(csv_text,asr_text),
 WER_asr_vs_manual=wer(man_text,asr_text),
 WER_csv_vs_manual=wer(man_text,csv_text),
 WER_manual_vs_csv=wer(csv_text,man_text))
print(json.dumps(res,ensure_ascii=False))
print("MANUAL :",norm(man_text)); print("CSV    :",norm(csv_text)); print("ASR    :",norm(asr_text))
json.dump(res,open(os.path.join(ROOT,"Validatie_fase1_stap2","resultaten","v06_manual_vs_csv.json"),"w",encoding="utf-8"),indent=1)
