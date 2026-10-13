"""Vergelijkt de echte run met de verbeterde code (nieuw) met de twee oorspronkelijke baselineruns en zoekt actief naar afwijkingen.

    Data-analysis/src/.venv/Scripts/python.exe -B compare_real_run.py --new <run/fragment> --out <nieuw bestand>.json

Alleen lezen (behalve het ene nieuwe uitvoerbestand). Geen modelrun. De onafhankelijke verwachting voor de intersections wordt met EXACTE
rationale getallen (fractions) uit de ruwe beurten berekend, niet met de productiecode."""
import argparse
import hashlib
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "Data-analysis" / "src"))
RUNS = REPO / "Data-local" / "evaluation" / "baseline_v1" / "runs"
from models import WorkshopTranscript, ProcessedTranscript                        # noqa: E402

NEW_SEG = {"raw_speaker_intersections", "multiple_raw_speakers"}
NEW_TURN = {"raw_speaker_seconds", "multiple_raw_speakers"}
EXPECTED_MULTI = [1, 4, 5, 11, 12, 15, 16]
checks = []


def J(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def first(d, pat):
    return next(Path(d).glob(pat))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check(name, ok, detail=None):
    checks.append({"check": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + ("" if ok or detail is None else f"  -> {str(detail)[:300]}"))


def diff_dicts(a, b, ignore=(), path=""):
    out = []
    for k in sorted(set(a) | set(b)):
        if k in ignore:
            continue
        if k not in a or k not in b:
            out.append((path + k, "ontbreekt" if k not in a else a[k], "ontbreekt" if k not in b else b[k]))
        elif isinstance(a[k], dict) and isinstance(b[k], dict):
            out += diff_dicts(a[k], b[k], ignore, path + k + ".")
        elif a[k] != b[k]:
            out.append((path + k, a[k], b[k]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", required=True)
    ap.add_argument("--out", required=True)
    N = Path(ap.parse_args().new)
    out_path = Path(ap.parse_args().out)
    B1, B2 = RUNS / "20261012_dev_run1" / "testaudio2_fragment", RUNS / "20261012_dev_run2" / "testaudio2_fragment"
    mn, m1, m2 = J(N / "run_manifest.json"), J(B1 / "run_manifest.json"), J(B2 / "run_manifest.json")
    rn = J(N / "run_result.json")
    ev = {}

    # ---- A. technische status en setup
    check("A1 alle vier stappen ok", rn["all_stages_ok"] and all(s["status"] == "ok" for s in rn["stages"]), [(s["name"], s["status"], s["seconds"]) for s in rn["stages"]])
    check("A2 no_touch_check schoon (Data-local/processed, src, referenties)", rn["no_touch_check"]["data_local_processed_diff"] == {"added": [], "removed": [], "changed": []}
          and rn["no_touch_check"]["src_py_unchanged"] and rn["no_touch_check"]["reference_csv_unchanged"], rn["no_touch_check"])
    check("A3 invoer (audio-, referentie-, rolbron-, docentreferentiehash) gelijk aan baseline", mn["inputs"] == m1["inputs"] == m2["inputs"], diff_dicts(mn["inputs"], m1["inputs"]))
    check("A4 pipeline-instellingen gelijk", mn["pipeline_settings"] == m1["pipeline_settings"], diff_dicts(mn["pipeline_settings"], m1["pipeline_settings"]))
    check("A5 packages en modelrevisies gelijk", mn["environment"]["packages"] == m1["environment"]["packages"] and mn["environment"]["hf_snapshots"] == m1["environment"]["hf_snapshots"])
    src_changed = sorted(k for k in mn["environment"]["src_sha256"] if mn["environment"]["src_sha256"][k] != m1["environment"]["src_sha256"].get(k))
    check("A6 bronhashes: alleen models/diarization/preprocessing verschillen met de baseline", src_changed == ["diarization.py", "models.py", "preprocessing.py"], src_changed)
    ev["git"] = mn["git"]
    ev["src_sha256_new"] = mn["environment"]["src_sha256"]
    ev["runtimes_s_new_vs_run1"] = {s["name"]: (s["seconds"], t["seconds"]) for s, t in zip(rn["stages"], J(B1 / "run_result.json")["stages"])}

    # ---- B. Whisper (modeluitvoer)
    tn, t1, t2 = J(first(N / "01_transcript", "*.json")), J(first(B1 / "01_transcript", "*.json")), J(first(B2 / "01_transcript", "*.json"))
    d1 = [diff_dicts(a, b, ignore=NEW_SEG) for a, b in zip(tn["segments"], t1["segments"])]
    check("B1 Whisper: 19 segmenten, alle bestaande velden gelijk aan run 1 en run 2 (nieuwe velden alleen als lege standaardwaarde)", len(tn["segments"]) == len(t1["segments"]) == len(t2["segments"]) == 19
          and not any(d1) and all(not diff_dicts(a, b, ignore=NEW_SEG) for a, b in zip(tn["segments"], t2["segments"])), [x for x in d1 if x][:3])
    ev["transcript_json_new_fields_are_only_empty_defaults"] = all(s_["raw_speaker_intersections"] == [] and s_["multiple_raw_speakers"] is False for s_ in tn["segments"])

    # ---- C. ruwe pyannote-beurten (modeluitvoer)
    rawn, raw1 = J(N / "02_diarization" / "raw_turns.json"), J(B1 / "02_diarization" / "raw_turns.json")
    check("C1 ruwe beurten: 8 beurten, tijden en labels gelijk aan run 1", rawn["turns"] == raw1["turns"] and len(rawn["turns"]) == 8, diff_dicts({"t": rawn["turns"]}, {"t": raw1["turns"]}))
    check("C2 RTTM byte-gelijk aan run 1 en run 2", sha(N / "02_diarization" / "raw_turns.rttm") == sha(B1 / "02_diarization" / "raw_turns.rttm") == sha(B2 / "02_diarization" / "raw_turns.rttm"),
          sha(N / "02_diarization" / "raw_turns.rttm"))
    ev["rttm_sha256"] = sha(N / "02_diarization" / "raw_turns.rttm")
    raw_identical = rawn["turns"] == raw1["turns"]

    # ---- D. dominante labels en bestaande segmentvelden (effect van de codewijziging)
    dn, d1j = J(first(N / "02_diarization", "*_diarized.json")), J(first(B1 / "02_diarization", "*_diarized.json"))
    seg_diffs = [(i, diff_dicts(b, a, ignore=NEW_SEG)) for i, (a, b) in enumerate(zip(dn["segments"], d1j["segments"]))]
    seg_diffs = [(i, d) for i, d in seg_diffs if d]
    check("D1 19 dominante labels identiek (speaker, speaker_raw)", [s["speaker_raw"] for s in dn["segments"]] == [s["speaker_raw"] for s in d1j["segments"]] == ["SPEAKER_00"] * 19
          and [s["speaker"] for s in dn["segments"]] == [s["speaker"] for s in d1j["segments"]])
    check("D2 alle bestaande segmentvelden gelijk (confidence, overlap, uncertain, tekst, tijden, kwaliteitsmaten)", not seg_diffs, seg_diffs[:3])
    meta_ignore = {"runtime_seconds", "audio_file", "source_transcript"}
    check("D3 bestaande diarization-metadata gelijk (zonder runtime/paden)", not diff_dicts(dn["diarization"], d1j["diarization"], ignore=meta_ignore), diff_dicts(dn["diarization"], d1j["diarization"], ignore=meta_ignore))

    # ---- E. preprocessing: bestaande turnvelden
    pn, p1 = J(first(N / "03_preprocessing", "*.json")), J(first(B1 / "03_preprocessing", "*.json"))
    turn_diffs = []
    for i, (a, b) in enumerate(zip(pn["turns"], p1["turns"])):
        d = diff_dicts(b, a, ignore=NEW_TURN | {"source_segments"})
        for j, (sa, sb) in enumerate(zip(a["source_segments"], b["source_segments"])):
            d += diff_dicts(sb, sa, ignore=NEW_SEG, path=f"source_segments[{j}].")
        if len(a["source_segments"]) != len(b["source_segments"]):
            d.append(("n_source_segments", len(b["source_segments"]), len(a["source_segments"])))
        if d:
            turn_diffs.append((i, d))
    check("E1 tien turns, alle bestaande velden gelijk (grenzen, tekst, speaker, flags, context, bron-indices, bronsegmenten)", len(pn["turns"]) == len(p1["turns"]) == 10 and not turn_diffs, turn_diffs[:3])
    check("E2 preprocessing-configuratie gelijk", pn["preprocessing_config"] == p1["preprocessing_config"])

    # ---- F. extra intersections: bewaard en onafhankelijk geverifieerd
    turns_raw = [(Fraction(t["start"]), Fraction(t["end"]), t["speaker"]) for t in rawn["turns"]]
    exp_per_seg, exp_multi = [], []
    for sg in dn["segments"]:
        s0, s1 = Fraction(sg["start"]), Fraction(sg["end"])
        lst = []
        for a, b, lab in turns_raw:
            lo, hi = max(s0, a), min(s1, b)
            if hi > lo:
                lst.append((lab, lo, hi))
        lst.sort(key=lambda x: (x[1], x[2], x[0]))
        exp_per_seg.append(lst)
        exp_multi.append(len({x[0] for x in lst}) >= 2)
    bad = []
    for i, (sg, lst) in enumerate(zip(dn["segments"], exp_per_seg)):
        got = sg["raw_speaker_intersections"]
        if len(got) != len(lst):
            bad.append((i, "aantal", len(got), len(lst), sg["start"], sg["end"]))
            continue
        for g, (lab, lo, hi) in zip(got, lst):
            if g["speaker_raw"] != lab or abs(Fraction(g["start"]) - lo) > Fraction(1, 10**12) or abs(Fraction(g["end"]) - hi) > Fraction(1, 10**12) \
                    or abs(Fraction(g["duration"]) - (hi - lo)) > Fraction(1, 10**12):
                bad.append((i, "waarde", g, (lab, float(lo), float(hi)), sg["start"], sg["end"]))
    check("F1 alle intersections van alle 19 segmenten gelijk aan onafhankelijke exacte berekening (aantal, label, begin, eind, duur)", not bad, bad[:3])
    multi_idx = [i for i, sg in enumerate(dn["segments"]) if sg["multiple_raw_speakers"]]
    check("F2 precies de 7 verwachte segmenten hebben meerdere ruwe sprekers", multi_idx == EXPECTED_MULTI and multi_idx == [i for i, m in enumerate(exp_multi) if m], multi_idx)
    sec01 = sum(g["duration"] for sg in dn["segments"] for g in sg["raw_speaker_intersections"] if g["speaker_raw"] == "SPEAKER_01")
    raw01 = sum(float(b - a) for a, b, lab in turns_raw if lab == "SPEAKER_01")
    check("F3 SPEAKER_01 = 3,898125 s in de aanvullende informatie (= totaal ruwe SPEAKER_01)", abs(sec01 - 3.898125) < 1e-6 and abs(raw01 - 3.898125) < 1e-6, (sec01, raw01))
    ev["speaker_01_seconds"] = sec01
    ev["speaker_00_seconds_in_segments"] = sum(g["duration"] for sg in dn["segments"] for g in sg["raw_speaker_intersections"] if g["speaker_raw"] == "SPEAKER_00")
    ev["intersections_segments_multi"] = {i: [(g["speaker_raw"], round(g["start"], 3), round(g["end"], 3), round(g["duration"], 3)) for g in dn["segments"][i]["raw_speaker_intersections"]] for i in multi_idx}
    # tegenvoorbeeldzoektocht
    probes = {
        "buiten_segmentgrenzen": [(i, g) for i, sg in enumerate(dn["segments"]) for g in sg["raw_speaker_intersections"] if g["start"] < sg["start"] - 1e-12 or g["end"] > sg["end"] + 1e-12],
        "duur_ongelijk_eind_min_begin": [(i, g) for i, sg in enumerate(dn["segments"]) for g in sg["raw_speaker_intersections"] if abs(g["duration"] - (g["end"] - g["start"])) > 1e-9],
        "niet_gesorteerd": [i for i, sg in enumerate(dn["segments"]) if sg["raw_speaker_intersections"] != sorted(sg["raw_speaker_intersections"], key=lambda g: (g["start"], g["end"], g["speaker_raw"]))],
        "dominant_niet_in_intersections": [i for i, sg in enumerate(dn["segments"]) if sg["speaker_raw"] not in {g["speaker_raw"] for g in sg["raw_speaker_intersections"]}],
        "enkelvoudig_maar_gemarkeerd_multi": [i for i, sg in enumerate(dn["segments"]) if sg["multiple_raw_speakers"] and len({g["speaker_raw"] for g in sg["raw_speaker_intersections"]}) < 2],
        "multi_maar_niet_gemarkeerd": [i for i, sg in enumerate(dn["segments"]) if not sg["multiple_raw_speakers"] and len({g["speaker_raw"] for g in sg["raw_speaker_intersections"]}) >= 2],
        "segment_zonder_intersections": [i for i, sg in enumerate(dn["segments"]) if not sg["raw_speaker_intersections"]],
        "overlapvlag_zonder_multi": [i for i, sg in enumerate(dn["segments"]) if sg["overlap"] and not sg["multiple_raw_speakers"]],
    }
    check("F4 tegenvoorbeeldzoektocht: geen intersection buiten segmentgrenzen, duur klopt, gesorteerd, dominant altijd aanwezig, vlag consistent, geen leeg segment, overlapvlag altijd met multi",
          not any(probes.values()), {k: v for k, v in probes.items() if v})
    ev["probes"] = {k: len(v) for k, v in probes.items()}
    # vergelijking met eerdere herberekening op de opgeslagen runs
    prev = J(Path(__file__).parent / "correction_before_after_stored_runs.json")["20261012_dev_run1"]["segments"]
    check("F5 intersections gelijk aan de eerdere replay op de opgeslagen ruwe beurten (zonder modelrun)",
          [[[g["speaker_raw"], round(g["start"], 3), round(g["end"], 3), round(g["duration"], 3)] for g in sg["raw_speaker_intersections"]] for sg in dn["segments"]] == [[list(x) for x in r["intersections_after"]] for r in prev])

    # ---- G. na preprocessing en docentherkenning
    ok_turn = True
    detail = []
    for i, t in enumerate(pn["turns"]):
        want = {}
        for s in t["source_segments"]:
            for g in s["raw_speaker_intersections"]:
                want[g["speaker_raw"]] = want.get(g["speaker_raw"], 0.0) + g["duration"]
        got = t["raw_speaker_seconds"]
        if set(got) != set(want) or any(abs(got[k] - want[k]) > 1e-9 for k in want) or t["multiple_raw_speakers"] != any(s["multiple_raw_speakers"] for s in t["source_segments"]):
            ok_turn = False
            detail.append((i, got, want))
    check("G1 na preprocessing: raw_speaker_seconds/vlag per turn kloppen met de bronsegmenten", ok_turn, detail)
    s01_turns = {t["turn_id"]: round(t["raw_speaker_seconds"]["SPEAKER_01"], 3) for t in pn["turns"] if "SPEAKER_01" in t["raw_speaker_seconds"]}
    check("G2 SPEAKER_01 zichtbaar in turns 1, 3, 4, 6, 7, 8 (samen 3,898125 s)", sorted(s01_turns) == [1, 3, 4, 6, 7, 8] and abs(sum(t["raw_speaker_seconds"].get("SPEAKER_01", 0.0) for t in pn["turns"]) - 3.898125) < 1e-6, s01_turns)
    ev["speaker_01_per_turn"] = s01_turns
    cn, c1 = J(first(N / "04_docent", "*.json")), J(first(B1 / "04_docent", "*.json"))
    rd = [(i, diff_dicts(b, a, ignore=NEW_TURN | {"source_segments"})) for i, (a, b) in enumerate(zip(cn["turns"], c1["turns"]))]
    rd = [(i, d) for i, d in rd if d]
    check("G3 docentrollen, similarities, noten en alle bestaande turnvelden gelijk aan run 1", len(cn["turns"]) == 10 and not rd, rd[:3])
    check("G4 rolreeks D D D O D D O D D D", [t["docent_role"] for t in cn["turns"]] == list("DDDODDODDD".replace("D", "D")) or [t["docent_role"][0] for t in cn["turns"]] == list("DDDODDODDD"), [t["docent_role"] for t in cn["turns"]])
    check("G5 docentuitvoer bewaart de nieuwe velden (turnsamenvatting en intersections in bronsegmenten) ongewijzigd t.o.v. preprocessing",
          all(a["raw_speaker_seconds"] == b["raw_speaker_seconds"] and a["multiple_raw_speakers"] == b["multiple_raw_speakers"] and a["source_segments"] == b["source_segments"] for a, b in zip(cn["turns"], pn["turns"])))

    # ---- H. scores
    sn, s1 = J(N / "scores_v1.json"), J(B1 / "scores_v1.json")
    sd = diff_dicts(s1, sn, ignore={"run_dir"})
    check("H1 alle scores (WER/CER, DER-raster, segment, docentrol, circulariteit, evidence) gelijk aan run 1", not sd, sd[:5])
    ev["WER"] = sn["text"]["primary_fillers_removed"]["rate"]
    ev["DER_headline"] = sn["der_raw_turns"]["uem=labelled|overlap=exclude|collar=0.25"]["der"]

    # ---- I. JSON-herladen met de productiemodellen
    wt = WorkshopTranscript.model_validate_json(first(N / "02_diarization", "*_diarized.json").read_text(encoding="utf-8"))
    wt2 = WorkshopTranscript.model_validate_json(wt.model_dump_json())
    check("I1 gediarizeerd transcript: herladen en opnieuw serialiseren behoudt alle intersections", wt == wt2 and sum(len(s.raw_speaker_intersections) for s in wt2.segments) == sum(len(s["raw_speaker_intersections"]) for s in dn["segments"])
          and [i for i, s in enumerate(wt2.segments) if s.multiple_raw_speakers] == EXPECTED_MULTI)
    for name, p in (("preprocessing", first(N / "03_preprocessing", "*.json")), ("docentrol-uitvoer", first(N / "04_docent", "*.json"))):
        pt = ProcessedTranscript.model_validate_json(p.read_text(encoding="utf-8"))
        pt2 = ProcessedTranscript.model_validate_json(pt.model_dump_json())
        check(f"I2 {name}: herladen en opnieuw serialiseren behoudt turnsamenvatting en intersections in bronsegmenten", pt == pt2
              and abs(sum(t.raw_speaker_seconds.get("SPEAKER_01", 0.0) for t in pt2.turns) - 3.898125) < 1e-6
              and sum(len(s.raw_speaker_intersections) for t in pt2.turns for s in t.source_segments) == sum(len(s["raw_speaker_intersections"]) for s in dn["segments"]))

    # ---- J. integriteit
    st = subprocess.run(["git", "-C", str(REPO), "status", "--short", "--untracked-files=no"], capture_output=True, text=True).stdout.strip()
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    srcdiff = subprocess.run(["git", "-C", str(REPO), "diff", "HEAD", "--stat", "--", "Data-analysis/src"], capture_output=True, text=True).stdout.strip()
    check("J1 git: HEAD ongewijzigd t.o.v. de run, werkboom schoon, src gelijk aan commit", head == mn["git"]["head"] and st == "" and srcdiff == "", (head, st, srcdiff))
    cur_src = {p.name: sha(p) for p in (REPO / "Data-analysis" / "src").glob("*.py")}
    check("J2 huidige src-hashes gelijk aan het nieuwe runmanifest", cur_src == mn["environment"]["src_sha256"])
    ok_base = True
    for b in (B1, B2):
        res = J(b / "run_result.json")
        mp = {"transcript": first(b / "01_transcript", "*.json"), "diarized": first(b / "02_diarization", "*_diarized.json"), "raw_turns_rttm": b / "02_diarization" / "raw_turns.rttm",
              "turns": first(b / "03_preprocessing", "*.json"), "docent_roles": first(b / "04_docent", "*.json")}
        for s in res["stages"]:
            for k, h in s["outputs"].items():
                ok_base &= sha(mp[k]) == h
    check("J3 uitvoer van baselinerun 1 en 2 nog gelijk aan hun run_result-hashes", ok_base)
    check("J4 audio, rasterreferentie, rolbron, handmatige tekst en docentreferentie nog gelijk aan de baseline-hashes",
          sha(mn["inputs"]["audio_path"]) == m1["inputs"]["audio_sha256"] and sha(mn["inputs"]["reference_path"]) == m1["inputs"]["reference_sha256"]
          and sha(mn["inputs"]["role_source"]["path"]) == m1["inputs"]["role_source"]["sha256"] and sha(mn["inputs"]["docent_reference_audio"]) == m1["inputs"]["docent_reference_sha256"]
          and sha(mn["inputs"]["manual_txt"]["path"]) == m1["inputs"]["manual_txt"]["sha256"])

    summary = {"passed": sum(c["ok"] for c in checks), "failed": sum(not c["ok"] for c in checks), "raw_turns_identical_to_baseline": raw_identical}
    print(json.dumps(summary))
    with open(out_path, "x", encoding="utf-8") as f:
        json.dump({"summary": summary, "checks": checks, "evidence": ev}, f, indent=1, ensure_ascii=False, default=str)
    sys.exit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
