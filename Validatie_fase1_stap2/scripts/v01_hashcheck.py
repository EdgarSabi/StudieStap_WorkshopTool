"""V01: hashcontrole van manifests (ChatGPT manifest.json, Claude manifest_claude.csv, zip SHA256SUMS) tegen huidige bestanden. Alleen lezen."""
import hashlib, json, csv, os, sys
ROOT = r"C:\Users\School\Projects\StudieStap_WorkshopTool"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1<<20), b""): h.update(b)
    return h.hexdigest()
out = {}
# 1 ChatGPT manifest
m = json.load(open(os.path.join(ROOT,"Audit_fase1_2026-10-09","manifest.json"),encoding="utf-8"))
res = {"n":len(m),"missing":[],"diff":[],"ok":0}
for r in m:
    p = os.path.join(ROOT, r["path"])
    if not os.path.exists(p): res["missing"].append(r["path"]); continue
    if os.path.getsize(p)!=r["bytes"] or sha(p)!=r["sha256"]: res["diff"].append(r["path"])
    else: res["ok"]+=1
out["chatgpt_manifest"]=res
# 2 Claude manifest
rows = list(csv.DictReader(open(os.path.join(ROOT,"Data-analysis","Audit","manifest_claude.csv"),encoding="utf-8-sig")))
out["claude_manifest_columns"]=list(rows[0].keys())
pk = [k for k in rows[0] if "path" in k.lower() or "pad" in k.lower()][0]
hk = [k for k in rows[0] if "sha" in k.lower()][0]
res = {"n":len(rows),"missing":[],"diff":[],"ok":0}
for r in rows:
    p = os.path.join(ROOT, r[pk])
    if not os.path.exists(p): res["missing"].append(r[pk]); continue
    if sha(p)!=r[hk]: res["diff"].append(r[pk])
    else: res["ok"]+=1
out["claude_manifest"]=res
# 3 zip SHA256SUMS vs extracted
Z = os.path.join(ROOT,"Validatie_fase1_stap2","zip_extract")
res={"bad":[],"ok":0,"badformat":[]}
for line in open(os.path.join(Z,"SHA256SUMS.txt"),encoding="utf-8"):
    line=line.strip()
    if not line: continue
    h,_,p = line.partition("  ")
    if len(h)!=64: res["badformat"].append((p,len(h))); 
    q=os.path.join(Z,p)
    if not os.path.exists(q): res["bad"].append((p,"missing")); continue
    if sha(q)!=h: res["bad"].append((p,"hash"))
    else: res["ok"]+=1
out["zip_sums_vs_extracted"]=res
# 4 zip vs repo copies
pairs=[]
A=os.path.join(ROOT,"Data-analysis","Audit")
for f in ["edge_results.json","synth_results.json","wer_results.json"]:
    pairs.append((os.path.join(A,f),os.path.join(Z,f)))
for f in os.listdir(os.path.join(A,"scripts")):
    pairs.append((os.path.join(A,"scripts",f),os.path.join(Z,"scripts",f)))
GT=os.path.join(ROOT,"Data-analysis","Experiments","diarization","hyperparameter_tuning")
for n in [1,2,4,5,7]:
    f=f"ground_truth_testaudio{n}_fragment.csv"
    pairs.append((os.path.join(GT,f),os.path.join(Z,"referenties",f)))
out["zip_vs_repo"]={os.path.relpath(a,ROOT):(sha(a)==sha(b)) if os.path.exists(a) and os.path.exists(b) else "missing" for a,b in pairs}
# 5 hashes in hashes_referenties.md vs current repo
import re
txt=open(os.path.join(Z,"hashes_referenties.md"),encoding="utf-8").read()
res={}
for m_ in re.finditer(r"\| (Data-analysis/\S+) \| (\d+) \| ([0-9a-f]{64}) \|",txt):
    p=os.path.join(ROOT,m_.group(1)); res[m_.group(1)] = (sha(p)==m_.group(3)) if os.path.exists(p) else "missing"
out["hashes_referenties_vs_repo"]=res
json.dump(out,open(os.path.join(ROOT,"Validatie_fase1_stap2","resultaten","v01_hashcheck.json"),"w",encoding="utf-8"),indent=1,ensure_ascii=False)
print(json.dumps(out,indent=1,ensure_ascii=False))
