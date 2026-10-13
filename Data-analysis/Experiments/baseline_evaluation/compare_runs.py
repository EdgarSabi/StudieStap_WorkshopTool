"""Vergelijkt twee runs van HETZELFDE fragment (alleen lezen) en analyseert waar de tweede spreker verdwijnt.

    python compare_runs.py --run-a <run1/fragment> --run-b <run2/fragment> --out <nieuw bestand .json>

Gebruik de venv van het project (pyannote.core). Schrijft één NIEUW bestand (modus 'x')."""
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pyannote.core import Annotation, Segment, Timeline                     # noqa: E402
from baseline_eval import settings as S, refs as R, diar as D               # noqa: E402
from baseline_eval.runlib import write_json_new                             # noqa: E402


def J(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def first(d, pat):
    return next(Path(d).glob(pat))


def cmp_lists(a, b, keys, tol=1e-9):
    """Vergelijk twee lijsten dicts veldgewijs; geeft verschillen (positie, veld, a, b)."""
    diffs = []
    if len(a) != len(b):
        diffs.append(("len", len(a), len(b)))
    for i, (x, y) in enumerate(zip(a, b)):
        for k in keys:
            u, v = x.get(k), y.get(k)
            if isinstance(u, float) and isinstance(v, float):
                if abs(u - v) > tol:
                    diffs.append((i, k, u, v))
            elif u != v:
                diffs.append((i, k, u, v))
    return diffs


def secs(tl):
    return round(sum(s.duration for s in tl), 3)


def raw_ann(d):
    a = Annotation()
    for t in J(Path(d) / "02_diarization" / "raw_turns.json")["turns"]:
        a[Segment(t["start"], t["end"])] = t["speaker"]
    return a


def second_speaker_analysis(rundir, ref, duration):
    """Waar gaat spreker B (referentie) verloren: model (ruwe beurten), koppeling (alignment) of referentiebeperking?"""
    d = Path(rundir)
    raw = raw_ann(d)
    refann = R.speech_annotation(ref, duration)
    seg_json = J(first(d / "02_diarization", "*_diarized.json"))
    segs = seg_json["segments"]
    labels = sorted(raw.labels())
    out = {"raw_speakers": labels, "raw_seconds": {l: secs(raw.label_timeline(l).support()) for l in labels}}

    # (1) MODEL: waar valt referentiespraak van B in de ruwe beurten?
    B = refann.label_timeline("SPREKER_B").support()
    A = refann.label_timeline("SPREKER_A").support()
    flagged = Timeline([Segment(r.start, min(r.end, duration)) for r in ref.rows if r.kind == "speech" and r.speaker_id == "SPREKER_B" and r.overlap]).support()
    B_ov = B.crop(flagged, mode="intersection") if len(flagged) else Timeline()
    B_noov = B.extrude(flagged) if len(flagged) else B
    def where(tl):
        r = {"ref_seconds": secs(tl)}
        for l in labels:
            r[f"in_{l}"] = secs(tl.crop(raw.label_timeline(l).support(), mode="intersection"))
        r["in_no_raw_speaker"] = secs(tl.extrude(raw.get_timeline().support())) if len(tl) else 0.0
        return r
    out["ref_B_all"] = where(B)
    out["ref_B_flagged_overlap_ja"] = where(B_ov)
    out["ref_B_not_flagged_overlap"] = where(B_noov)
    out["ref_A_all"] = where(A)
    out["raw_SPEAKER_01_intervals"] = [(round(s.start, 3), round(s.end, 3)) for s in raw.label_timeline("SPEAKER_01").support()] if "SPEAKER_01" in labels else []
    out["raw_turns"] = [(round(s.start, 3), round(s.end, 3), l) for s, _, l in raw.itertracks(yield_label=True)]

    # (2) ALIGNMENT: per Whisper-segment seconden per ruwe spreker en de winnaar (Hungarian niet nodig: pipeline pakt max overlap)
    table = []
    lost = 0.0
    for i, sg in enumerate(segs):
        seg = Segment(sg["start"], min(sg["end"], duration))
        row = {"segment": i, "start": sg["start"], "end": sg["end"], "winner": sg["speaker_raw"], "overlap_flag": sg["overlap"]}
        for l in labels:
            row[f"sec_{l}"] = secs(raw.label_timeline(l).support().crop(seg, mode="intersection"))
        row["ref_B_sec"] = secs(B.crop(seg, mode="intersection"))
        row["ref_A_sec"] = secs(A.crop(seg, mode="intersection"))
        table.append(row)
    out["segments"] = table
    s01 = [r["sec_SPEAKER_01"] for r in table] if "SPEAKER_01" in labels else []
    out["alignment"] = {
        "segments_won_by": {l: sum(1 for r in table if r["winner"] == l) for l in labels},
        "SPEAKER_01_seconds_total": round(sum(s01), 3),
        "SPEAKER_01_seconds_in_segments_it_lost": round(sum(r["sec_SPEAKER_01"] for r in table if r["winner"] != "SPEAKER_01"), 3) if s01 else 0.0,
        "max_SPEAKER_01_share_in_any_segment": max((r["sec_SPEAKER_01"] / (r["end"] - r["start"]) for r in table), default=0.0) if s01 else 0.0,
        "segments_where_ref_B_gt_half_of_segment": [r["segment"] for r in table if r["ref_B_sec"] > 0.5 * (r["end"] - r["start"])],
        "of_those_labelled_B_like_raw_SPEAKER_01": [r["segment"] for r in table if r["ref_B_sec"] > 0.5 * (r["end"] - r["start"]) and r["winner"] == "SPEAKER_01"],
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-a", required=True)
    ap.add_argument("--run-b", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    A, B = Path(a.run_a), Path(a.run_b)
    ma, mb = J(A / "run_manifest.json"), J(B / "run_manifest.json")
    frag = ma["fragment"]
    assert frag == mb["fragment"], "verschillende fragmenten"
    duration = ma["inputs"]["audio_duration_s"]
    ref = R.load_reference(S.GT_DIR / S.FRAGMENTS[frag]["ref"], frag)
    out = {"fragment": frag, "run_a": str(A), "run_b": str(B)}

    # 0. invoer en instellingen
    keys = ["inputs", "pipeline_settings"]
    same_inputs = {k: ma[k] == mb[k] for k in keys}
    same_env = {k: ma["environment"][k] == mb["environment"][k] for k in ("packages", "hf_snapshots", "src_sha256", "python")}
    out["setup_identical"] = {"inputs_and_settings": same_inputs, "environment": same_env, "git_head": ma["git"]["head"] == mb["git"]["head"]}
    ra, rb = J(A / "run_result.json"), J(B / "run_result.json")
    out["runtimes_s"] = {s["name"]: (s["seconds"], t["seconds"]) for s, t in zip(ra["stages"], rb["stages"])}
    out["stage_output_sha256_equal"] = {s["name"]: s["outputs"] == t["outputs"] for s, t in zip(ra["stages"], rb["stages"])}

    # 1. Whisper
    ta, tb = J(first(A / "01_transcript", "*.json")), J(first(B / "01_transcript", "*.json"))
    fields = ["start", "end", "text", "avg_logprob", "no_speech_prob", "compression_ratio", "quality_flags"]
    out["whisper"] = {"n_segments": (len(ta["segments"]), len(tb["segments"])),
                      "field_differences": cmp_lists(ta["segments"], tb["segments"], fields),
                      "text_identical": [x["text"] for x in ta["segments"]] == [x["text"] for x in tb["segments"]]}

    # 2. ruwe pyannote
    ja, jb = J(A / "02_diarization" / "raw_turns.json"), J(B / "02_diarization" / "raw_turns.json")
    out["raw_pyannote"] = {"n_turns": (len(ja["turns"]), len(jb["turns"])),
                           "turn_differences": cmp_lists(ja["turns"], jb["turns"], ["start", "end", "speaker"]),
                           "max_abs_boundary_diff_s": max((max(abs(x["start"] - y["start"]), abs(x["end"] - y["end"])) for x, y in zip(ja["turns"], jb["turns"])), default=None),
                           "raw_speakers": (sorted({t["speaker"] for t in ja["turns"]}), sorted({t["speaker"] for t in jb["turns"]}))}
    # 3. koppeling
    da, db = J(first(A / "02_diarization", "*_diarized.json")), J(first(B / "02_diarization", "*_diarized.json"))
    out["coupling"] = {"segment_label_differences": cmp_lists(da["segments"], db["segments"], ["speaker", "speaker_raw", "speaker_confidence", "overlap", "uncertain_assignment"]),
                       "label_map": (da["diarization"]["label_map"], db["diarization"]["label_map"]),
                       "assignment": (da["diarization"]["assignment"], db["diarization"]["assignment"]),
                       "speakers_kept_after_coupling": (sorted({s["speaker_raw"] for s in da["segments"] if s["speaker_raw"]}),
                                                         sorted({s["speaker_raw"] for s in db["segments"] if s["speaker_raw"]}))}
    # 4. preprocessing + rollen
    pa, pb = J(first(A / "03_preprocessing", "*.json")), J(first(B / "03_preprocessing", "*.json"))
    out["preprocessing"] = {"n_turns": (len(pa["turns"]), len(pb["turns"])),
                            "differences": cmp_lists(pa["turns"], pb["turns"], ["start", "end", "speaker", "overlap", "uncertain_assignment", "context_uncertain_before", "context_uncertain_after"])}
    ca, cb = J(first(A / "04_docent", "*.json")), J(first(B / "04_docent", "*.json"))
    out["docent_roles"] = {"roles_a": [t["docent_role"] for t in ca["turns"]], "roles_b": [t["docent_role"] for t in cb["turns"]],
                           "role_differences": cmp_lists(ca["turns"], cb["turns"], ["docent_role"]),
                           "similarity_max_abs_diff": max(abs(x["docent_role_similarity"] - y["docent_role_similarity"]) for x, y in zip(ca["turns"], cb["turns"])),
                           "similarities": [(round(x["docent_role_similarity"], 4), round(y["docent_role_similarity"], 4)) for x, y in zip(ca["turns"], cb["turns"])]}
    # 5. scores
    sa, sb = J(A / "scores_v1.json"), J(B / "scores_v1.json")
    def flat(d, pre=""):
        r = {}
        for k, v in d.items():
            if isinstance(v, dict):
                r.update(flat(v, pre + k + "."))
            elif isinstance(v, (int, float, str)) or v is None:
                r[pre + k] = v
        return r
    fa, fb = flat({k: v for k, v in sa.items() if k not in ("run_dir",)}), flat({k: v for k, v in sb.items() if k not in ("run_dir",)})
    out["scores"] = {"n_values": len(fa), "differing": {k: (fa[k], fb.get(k)) for k in fa if fa[k] != fb.get(k)},
                     "WER": (sa["text"]["primary_fillers_removed"]["rate"], sb["text"]["primary_fillers_removed"]["rate"]),
                     "DER_headline": (sa["der_raw_turns"]["uem=labelled|overlap=exclude|collar=0.25"]["der"], sb["der_raw_turns"]["uem=labelled|overlap=exclude|collar=0.25"]["der"]),
                     "coverage": (sa["der_raw_turns"]["uem=labelled|overlap=exclude|collar=0.25"]["total_ref_speech_s"], sb["der_raw_turns"]["uem=labelled|overlap=exclude|collar=0.25"]["total_ref_speech_s"]),
                     "segment_status_counts": (sa["segment_eval"]["status_counts"], sb["segment_eval"]["status_counts"])}
    # 6. tweede spreker
    out["second_speaker"] = {"run_a": second_speaker_analysis(A, ref, duration), "run_b": second_speaker_analysis(B, ref, duration)}
    write_json_new(a.out, out)
    print(json.dumps({k: out[k] for k in ("setup_identical", "runtimes_s", "stage_output_sha256_equal")}, ensure_ascii=False, indent=1))
    for k in ("whisper", "raw_pyannote", "coupling", "preprocessing"):
        print(k, json.dumps(out[k], ensure_ascii=False)[:700])
    print("docent", json.dumps({k: v for k, v in out["docent_roles"].items() if k != "similarities"}, ensure_ascii=False))
    print("scores", json.dumps({k: v for k, v in out["scores"].items()}, ensure_ascii=False)[:1200])


if __name__ == "__main__":
    main()
