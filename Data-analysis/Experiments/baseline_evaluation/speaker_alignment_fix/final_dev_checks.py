"""Toetst de vier vooraf vastgelegde verwachtingen (final_dev_preregistration.md) op één nieuwe run en verzamelt diagnostische gegevens.

    Data-analysis/src/.venv/Scripts/python.exe -B final_dev_checks.py --run-dir <run/fragment> --out <nieuw>.json
Alleen lezen (plus één nieuw uitvoerbestand). Geen modelrun."""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "Data-analysis" / "src"))
sys.path.insert(0, str(HERE.parent))
from models import WorkshopTranscript, ProcessedTranscript                      # noqa: E402
from baseline_eval import refs as R, settings as S                              # noqa: E402
from pyannote.core import Annotation, Segment, Timeline                         # noqa: E402

NEW_SEG = {"raw_speaker_intersections", "multiple_raw_speakers"}
NEW_TURN = {"raw_speaker_seconds", "multiple_raw_speakers"}
checks = []


def J(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def first(d, pat):
    return next(Path(d).glob(pat))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check(name, ok, detail=None):
    checks.append({"check": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + ("" if ok or detail is None else f"  -> {str(detail)[:400]}"))


def diff(a, b, ignore=(), path=""):
    out = []
    for k in sorted(set(a) | set(b)):
        if k in ignore:
            continue
        if k not in a or k not in b:
            out.append((path + k, "ontbreekt" if k not in a else "aanwezig", "ontbreekt" if k not in b else "aanwezig"))
        elif isinstance(a[k], dict) and isinstance(b[k], dict):
            out += diff(a[k], b[k], ignore, path + k + ".")
        elif a[k] != b[k]:
            out.append((path + k, a[k], b[k]))
    return out


def union_len(iv):
    iv = sorted(iv)
    tot, cur_s, cur_e = Fraction(0), None, None
    for s, e in iv:
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                tot += cur_e - cur_s
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        tot += cur_e - cur_s
    return tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    D = Path(a.run_dir)
    man, res = J(D / "run_manifest.json"), J(D / "run_result.json")
    frag = man["fragment"]
    ev = {"fragment": frag, "run_dir": str(D), "git": man["git"], "stage_seconds": {s["name"]: s["seconds"] for s in res["stages"]}}
    check("0 alle vier stappen ok, no_touch_check schoon", res["all_stages_ok"] and res["no_touch_check"]["data_local_processed_diff"] == {"added": [], "removed": [], "changed": []}
          and res["no_touch_check"]["src_py_unchanged"] and res["no_touch_check"]["reference_csv_unchanged"], res["no_touch_check"])

    raw = J(D / "02_diarization" / "raw_turns.json")["turns"]
    dz = J(first(D / "02_diarization", "*_diarized.json"))
    segs = dz["segments"]
    pre = J(first(D / "03_preprocessing", "*.json"))
    doc = J(first(D / "04_docent", "*.json"))
    dur = man["inputs"]["audio_duration_s"]

    # ---------- sprekeraantallen
    labels_raw = sorted({t["speaker"] for t in raw})
    raw_sec = {l: round(sum(t["end"] - t["start"] for t in raw if t["speaker"] == l), 3) for l in labels_raw}
    dom = {}
    for s in segs:
        dom[s["speaker_raw"]] = dom.get(s["speaker_raw"], 0) + 1
    inter_labels = sorted({g["speaker_raw"] for s in segs for g in s["raw_speaker_intersections"]})
    ev["counts"] = {"raw_turns": len(raw), "raw_speakers": len(labels_raw), "raw_seconds_per_label": raw_sec,
                    "segments": len(segs), "dominant_labels_segments": dom, "dominant_speakers": len(dom),
                    "labels_in_intersections": inter_labels, "segments_with_multiple_raw_speakers": [i for i, s in enumerate(segs) if s["multiple_raw_speakers"]],
                    "turns": len(pre["turns"]), "turn_speakers_dominant": sorted({t["speaker"] or "None" for t in pre["turns"]}),
                    "turns_with_multiple_raw_speakers": [t["turn_id"] for t in pre["turns"] if t["multiple_raw_speakers"]],
                    "roles": {r: sum(1 for t in doc["turns"] if t["docent_role"] == r) for r in ("DOCENT", "OTHER", "ONZEKER")},
                    "overlap_segments_legacy_flag": sum(1 for s in segs if s["overlap"]), "uncertain_segments": sum(1 for s in segs if s["uncertain_assignment"])}

    # ---------- E1 exacte herberekening
    tr = [(Fraction(t["start"]), Fraction(t["end"]), t["speaker"]) for t in raw]
    bad, pairs = [], 0
    for i, sg in enumerate(segs):
        s0, s1 = Fraction(sg["start"]), Fraction(sg["end"])
        exp = sorted(((max(s0, a_), min(s1, b_), l) for a_, b_, l in tr if min(s1, b_) > max(s0, a_)), key=lambda x: (x[0], x[1], x[2]))
        pairs += len(exp)
        got = sg["raw_speaker_intersections"]
        if len(got) != len(exp):
            bad.append((i, "aantal", len(got), len(exp)))
            continue
        for g, (lo, hi, l) in zip(got, exp):
            tol = Fraction(1, 10**12)
            if g["speaker_raw"] != l or abs(Fraction(g["start"]) - lo) > tol or abs(Fraction(g["end"]) - hi) > tol or abs(Fraction(g["duration"]) - (hi - lo)) > tol:
                bad.append((i, g, (l, float(lo), float(hi))))
    check(f"E1 alle {pairs} (ruwe beurt, segment)-paren met positieve overlap staan als juiste intersection in het segment", not bad, bad[:3])
    ev["pairs_positive_overlap"] = pairs

    # ---------- E2 meerdere sprekers zichtbaar na preprocessing, docentstap en herladen
    want_multi = [i for i, sg in enumerate(segs) if len({g["speaker_raw"] for g in sg["raw_speaker_intersections"]}) >= 2]
    check("E2a segmentvlag consistent met de lijst", want_multi == ev["counts"]["segments_with_multiple_raw_speakers"], (want_multi, ev["counts"]["segments_with_multiple_raw_speakers"]))
    bad_t = []
    for t in pre["turns"]:
        w = {}
        for s in t["source_segments"]:
            for g in s["raw_speaker_intersections"]:
                w[g["speaker_raw"]] = w.get(g["speaker_raw"], 0.0) + g["duration"]
        if set(w) != set(t["raw_speaker_seconds"]) or any(abs(w[k] - t["raw_speaker_seconds"][k]) > 1e-9 for k in w) \
                or t["multiple_raw_speakers"] != any(s["multiple_raw_speakers"] for s in t["source_segments"]):
            bad_t.append(t["turn_id"])
    check("E2b turnsamenvatting en vlag per turn kloppen met de bronsegmenten", not bad_t, bad_t)
    check("E2c docentuitvoer bewaart de nieuwe velden ongewijzigd", all(x["raw_speaker_seconds"] == y["raw_speaker_seconds"] and x["multiple_raw_speakers"] == y["multiple_raw_speakers"]
                                                                   and x["source_segments"] == y["source_segments"] for x, y in zip(doc["turns"], pre["turns"])))
    wt = WorkshopTranscript.model_validate_json(first(D / "02_diarization", "*_diarized.json").read_text(encoding="utf-8"))
    ok_reload = wt == WorkshopTranscript.model_validate_json(wt.model_dump_json())
    for p in (first(D / "03_preprocessing", "*.json"), first(D / "04_docent", "*.json")):
        pt = ProcessedTranscript.model_validate_json(p.read_text(encoding="utf-8"))
        ok_reload &= pt == ProcessedTranscript.model_validate_json(pt.model_dump_json())
        ok_reload &= [t.multiple_raw_speakers for t in pt.turns] == [t["multiple_raw_speakers"] for t in pre["turns"]]
    check("E2d herladen en opnieuw serialiseren (gediarizeerd, preprocessing, docent) behoudt alles", ok_reload)

    # ---------- E3 replay met de ORIGINELE code (0a4ab99) op dezelfde invoer
    with tempfile.TemporaryDirectory() as td:
        for f in ("config", "models", "diarization", "preprocessing"):
            (Path(td) / f"{f}.py").write_bytes(subprocess.run(["git", "-C", str(REPO), "show", f"0a4ab99:Data-analysis/src/{f}.py"], capture_output=True, check=True).stdout)
        out = subprocess.run([sys.executable, "-B", str(HERE / "replay_original.py"), "--src", td, "--run-dir", str(D)], capture_output=True, text=True)
    if out.returncode != 0:
        check("E3 replay met originele code", False, out.stderr[-500:])
    else:
        old = json.loads(out.stdout)
        sd = [(i, diff(o, n, ignore=NEW_SEG)) for i, (o, n) in enumerate(zip(old["segments"], segs))]
        sd = [(i, d) for i, d in sd if d]
        check("E3a originele koppeling op dezelfde ruwe beurten: alle bestaande segmentvelden (dominant label, confidence, overlap, uncertain, tekst, tijden) identiek", len(old["segments"]) == len(segs) and not sd, sd[:3])
        td_ = []
        for i, (o, n) in enumerate(zip(old["turns"], pre["turns"])):
            d = diff(o, n, ignore=NEW_TURN | {"source_segments"})
            for j, (so, sn) in enumerate(zip(o["source_segments"], n["source_segments"])):
                d += diff(so, sn, ignore=NEW_SEG, path=f"src[{j}].")
            if d:
                td_.append((i, d))
        check("E3b originele preprocessing: turngrenzen, sprekers, flags, context en bronsegmenten identiek", len(old["turns"]) == len(pre["turns"]) and not td_, td_[:3])
        dd = [(i, diff({k: v for k, v in p.items() if k != "source_segments"}, {k: v for k, v in c.items() if k != "source_segments"},
                       ignore={"docent_role", "docent_role_similarity", "docent_role_threshold", "docent_role_reference_audio", "docent_role_note"})) for i, (p, c) in enumerate(zip(pre["turns"], doc["turns"]))]
        check("E3c docentstap wijzigt geen turnveld buiten de eigen rolvelden", not [x for x in dd if x[1]], [x for x in dd if x[1]][:2])
        ev["replay_original_commit"] = "0a4ab99"

    # ---------- E4 korte activiteit en rumoer: binnen en buiten de segmenten
    segiv = [(Fraction(s["start"]), Fraction(s["end"])) for s in segs]
    outside, short = [], []
    per_label = {l: {"raw": Fraction(0), "inside_segments": Fraction(0)} for l in labels_raw}
    lost_inside = []
    for t in raw:
        a_, b_, l = Fraction(t["start"]), Fraction(t["end"]), t["speaker"]
        inside = union_len([(max(a_, s0), min(b_, s1)) for s0, s1 in segiv if min(b_, s1) > max(a_, s0)])
        per_label[l]["raw"] += b_ - a_
        per_label[l]["inside_segments"] += inside
        n_inter = sum(1 for sg in segs for g in sg["raw_speaker_intersections"] if g["speaker_raw"] == l and abs(g["start"] - max(t["start"], sg["start"])) < 1e-9 and abs(g["end"] - min(t["end"], sg["end"])) < 1e-9)
        if inside > 0 and n_inter == 0:
            lost_inside.append(t)
        row = {"label": l, "start": t["start"], "end": t["end"], "dur": round(t["end"] - t["start"], 3), "inside_segments_s": round(float(inside), 3), "n_intersections": n_inter}
        if inside == 0:
            outside.append(row)
        if t["end"] - t["start"] < 1.0:
            short.append(row)
    check("E4a geen ruwe beurt met positieve segmentoverlap ontbreekt in de intersections (ook korte en rumoerige)", not lost_inside, lost_inside[:3])
    check("E4b elk ruw label met activiteit binnen een segment komt in de intersections voor",
          all(per_label[l]["inside_segments"] == 0 or l in inter_labels for l in labels_raw), {l: (float(v["raw"]), float(v["inside_segments"])) for l, v in per_label.items()})
    ev["raw_per_label_seconds"] = {l: {"raw": round(float(v["raw"]), 3), "inside_segments": round(float(v["inside_segments"]), 3), "outside_segments": round(float(v["raw"] - v["inside_segments"]), 3)} for l, v in per_label.items()}
    ev["raw_turns_fully_outside_all_segments"] = outside
    ev["raw_turns_shorter_than_1s"] = short
    ev["labels_never_dominant_but_present_in_intersections"] = [l for l in inter_labels if l not in dom]
    ev["labels_in_raw_but_not_in_dominant"] = [l for l in labels_raw if l not in dom]

    # ---------- referentie-gerelateerd (EXPLORATIEF, Whisper-voorgevulde grenzen)
    spec = S.FRAGMENTS[frag]
    ref = R.load_reference(S.GT_DIR / spec["ref"], frag)
    ev["reference"] = {"file": spec["ref"], "sha256_ok": ref.sha256 == man["inputs"]["reference_sha256"], "speakers": ref.speakers(),
                       "seconds_per_speaker": {k: round(sum(r.end - r.start for r in ref.rows if r.kind == "speech" and r.speaker_id == k), 3) for k in ref.speakers()},
                       "row_kinds": {k: sum(1 for r in ref.rows if r.kind == k) for k in {r.kind for r in ref.rows}}}
    ra = R.speech_annotation(ref, dur)

    def tl(pred):
        return Timeline([Segment(g["start"], g["end"]) for s in segs for g in s["raw_speaker_intersections"] if pred(g)]).support()
    rawtl = {l: Annotation() for l in labels_raw}
    ann_raw = Annotation()
    for t in raw:
        ann_raw[Segment(t["start"], t["end"])] = t["speaker"]
    mat_raw, mat_inter = {}, {}
    for spk in ref.speakers():
        rt = ra.label_timeline(spk).support()
        mat_raw[spk] = {l: round(sum(s.duration for s in rt.crop(ann_raw.label_timeline(l).support(), mode="intersection")), 3) for l in labels_raw}
        mat_inter[spk] = {l: round(sum(s.duration for s in rt.crop(tl(lambda g, l=l: g["speaker_raw"] == l), mode="intersection")), 3) for l in labels_raw}
    ev["reference_speaker_x_raw_label_seconds"] = mat_raw
    ev["reference_speaker_x_intersection_label_seconds"] = mat_inter
    ev["reference_speaker_seconds_not_in_any_raw_turn"] = {spk: round(sum(s.duration for s in ra.label_timeline(spk).support().extrude(ann_raw.get_timeline().support())), 3) for spk in ref.speakers()}
    small = sorted(ref.speakers(), key=lambda k: ev["reference"]["seconds_per_speaker"][k])[:2]
    ev["smallest_reference_speakers"] = {k: {"ref_seconds": ev["reference"]["seconds_per_speaker"][k], "raw_label_seconds": mat_raw[k], "intersection_label_seconds": mat_inter[k],
                                              "rows": [(r.start, r.end, r.overlap) for r in ref.rows if r.kind == "speech" and r.speaker_id == k][:8]} for k in small}

    # ---------- scores (indien aanwezig)
    sp = D / "scores_v1.json"
    if sp.exists():
        sc = J(sp)
        ev["scores"] = {"circularity": sc.get("circularity"), "evidence": sc.get("evidence"), "wer_status": sc["text"].get("status"),
                        "wer_primary": sc["text"].get("primary_fillers_removed", {}).get("rate"), "wer_vs_manual": sc["text"].get("vs_manual_txt", {}).get("wer", {}).get("rate"),
                        "ref_vs_manual_wer": sc["text"].get("vs_manual_txt", {}).get("ref_vs_manual_wer", {}).get("rate"),
                        "der_raw_turns": {k: {x: v.get(x) for x in ("der", "missed_s", "false_alarm_s", "confusion_s", "total_ref_speech_s", "n_hyp_speakers_total")} for k, v in sc["der_raw_turns"].items()},
                        "der_segment_level": {k: v.get("der") for k, v in sc["der_segment_level_hypothesis"].items()},
                        "segment_eval": {k: v for k, v in sc["segment_eval"].items() if k != "segments"},
                        "docent_roles": {k: v for k, v in sc["docent_roles"].items() if k != "turns"},
                        "unintelligible_warning": sc.get("quality_warning_unintelligible")}

    # ---------- integriteit
    cur = {p.name: sha(p) for p in (REPO / "Data-analysis" / "src").glob("*.py")}
    status = subprocess.run(["git", "-C", str(REPO), "status", "--short", "--untracked-files=no"], capture_output=True, text=True).stdout.strip()
    check("I1 src-hashes gelijk aan het runmanifest en werkboom (tracked) schoon", cur == man["environment"]["src_sha256"] and status == "", status)
    check("I2 audio- en referentiehash gelijk aan het runmanifest", sha(man["inputs"]["audio_path"]) == man["inputs"]["audio_sha256"] and ev["reference"]["sha256_ok"])
    summary = {"passed": sum(c["ok"] for c in checks), "failed": sum(not c["ok"] for c in checks)}
    print(json.dumps(summary))
    with open(a.out, "x", encoding="utf-8") as f:
        json.dump({"summary": summary, "checks": checks, "evidence": ev}, f, indent=1, ensure_ascii=False, default=str)
    sys.exit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
