"""V10: verschil tussen gecommitte (HEAD) en werkkopie-GT-CSV's: schema of inhoud? Alleen lezen (git show)."""
import subprocess, csv, io, sys, os, json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
ROOT=r"C:\Users\School\Projects\StudieStap_WorkshopTool"; os.chdir(ROOT)
base="Data-analysis/Experiments/diarization/hyperparameter_tuning/"; out={}
for f in ["ground_truth_testaudio2_fragment.csv","ground_truth_testaudio4_fragment.csv"]:
    old=subprocess.run(["git","show","HEAD:"+base+f],capture_output=True).stdout.decode("utf-8-sig")
    ro=list(csv.DictReader(io.StringIO(old))); rn=list(csv.DictReader(open(base+f,encoding="utf-8-sig")))
    out[f]=dict(head_columns=list(ro[0].keys()),worktree_columns=list(rn[0].keys()),rows=(len(ro),len(rn)),
        text_hint_equals_transcript=sum(1 for a,b in zip(ro,rn) if a["transcript_hint"]==b["transcript"]),
        time_speaker_overlap_equal=sum(1 for a,b in zip(ro,rn) if (a["start_seconds"],a["end_seconds"],a["speaker_id"],a["overlap"])==(b["start_seconds"],b["end_seconds"],b["speaker_id"],b["overlap"])))
json.dump(out,open(os.path.join(ROOT,"Validatie_fase1_stap2","resultaten","v10_git_head_vs_worktree.json"),"w",encoding="utf-8"),indent=1)
print(json.dumps(out,ensure_ascii=False))
