"""V08: (a) komt Claudes verse ASR-run overeen met de eerder in notebook 03 opgeslagen segmenten (T2 'reproduceerbaar')?
(b) bevat ChatGPTs eigen manifest.json de 13 mp3's (tegenspraak met de claim 'audio ontbreekt')?"""
import json, os, sys, io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
ROOT=r"C:\Users\School\Projects\StudieStap_WorkshopTool"; Z=os.path.join(ROOT,"Validatie_fase1_stap2","zip_extract")
nb=json.load(open(os.path.join(Z,"nb_hyp.json"),encoding="utf-8")); out={}
for n in (1,2,5):
    base=json.load(open(os.path.join(Z,"asr",f"testaudio{n}_fragment_medium_baseline.json"),encoding="utf-8"))["segments"]
    rows=nb[f"testaudio{n}"]; match=0
    for r in rows:
        s,e,t=float(r["start"]),float(r["end"]),r["text"].strip()
        if any(abs(b["start"]-s)<0.011 and abs(b["end"]-e)<0.011 and b["text"].strip()==t for b in base): match+=1
    out[f"testaudio{n}"]=dict(nb_segments=len(rows),identical_in_fresh_run=match)
m=json.load(open(os.path.join(ROOT,"Audit_fase1_2026-10-09","manifest.json"),encoding="utf-8"))
mp3=[r["path"] for r in m if r["path"].lower().endswith(".mp3")]
out["chatgpt_manifest_mp3_count"]=len(mp3); out["chatgpt_manifest_mp3_dirs"]=sorted({os.path.dirname(p) for p in mp3})
inv=json.load(open(os.path.join(ROOT,"Audit_fase1_2026-10-09","inventory.json"),encoding="utf-8"))
out["chatgpt_inventory_python"]=inv["python"].split("\n")[0]; out["chatgpt_inventory_pkgs"]=inv["packages"]
json.dump(out,open(os.path.join(ROOT,"Validatie_fase1_stap2","resultaten","v08_repro_and_manifest.json"),"w",encoding="utf-8"),indent=1)
print(json.dumps(out,ensure_ascii=False,indent=1))
