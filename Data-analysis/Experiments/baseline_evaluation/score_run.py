"""Scoort één afgeronde run (uitvoer van run_baseline.py) tegen de vaste referentie. Leest alleen; schrijft één NIEUW bestand.

    python score_run.py --run-dir <eval-root>/runs/<run_id>/<fragment> [--tag scores_v1]

Gebruik de venv van het project (pyannote.metrics): Data-analysis/src/.venv/Scripts/python.exe
"""
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from baseline_eval import settings as S                      # noqa: E402
from baseline_eval import text as T                           # noqa: E402
from baseline_eval import refs as R                           # noqa: E402
from baseline_eval import diar as D                           # noqa: E402
from baseline_eval.runlib import write_json_new               # noqa: E402


def _midpoint_masked(seg: dict, mask) -> bool:
    mid = (seg["start"] + seg["end"]) / 2
    return any(s.start <= mid <= s.end for s in mask)


def evidence_status(ref, circ: dict, hyp_segments: list, duration: float) -> dict:
    """Vooraf vastgelegde regels voor 'indicatief' versus 'exploratief' (zie PROTOCOL.md §10)."""
    rows = [r for r in ref.rows if r.kind == "speech"]
    int_grid = (sum(1 for r in rows if float(r.start).is_integer() and float(r.end).is_integer()) / len(rows)) if rows else 0
    asr_grid = 0.0
    if rows and hyp_segments:
        def near(x, vals):
            return any(abs(x - v) <= 0.06 for v in vals)
        starts = [s["start"] for s in hyp_segments]
        ends = [s["end"] for s in hyp_segments]
        asr_grid = sum(1 for r in rows if near(r.start, starts) and near(r.end, ends)) / len(rows)
    n_ov = sum(1 for r in rows if r.overlap)
    why_der = []
    if int_grid >= 0.9 or asr_grid >= 0.9:
        why_der.append(f"referentiegrenzen liggen op hele seconden/ASR-raster (hele sec: {int_grid:.2f}, ASR: {asr_grid:.2f})")
    why_der_keep = why_der + ([f"{n_ov} rijen met overlap=ja zonder tweede spreker geannoteerd"] if n_ov else [])
    if any(r.kind == "unknown" for r in ref.rows):
        why_der.append("ONBEKEND-gebieden gemaskeerd")
        why_der_keep.append("ONBEKEND-gebieden gemaskeerd")
    why_wer = ["referentie is (deels) voorgevuld vanuit Whisper (README hyperparameter_tuning)"]
    if circ.get("circular"):
        why_wer.insert(0, f"CIRCULAIR: {circ['identical_rows']}/{circ['rows']} rijen gelijk aan Whisper")
    if R.has_overlapping_text_rows(ref):
        why_wer.append("tekstrijen overlappen in tijd: volgorde van de referentietekst is dubbelzinnig")
    return {
        "wer_cer": "not_reportable_circular" if circ.get("circular") else "exploratory",
        "wer_cer_reasons": why_wer,
        "der_overlap_exclude": "exploratory" if why_der else "indicative",
        "der_overlap_exclude_reasons": why_der,
        "der_overlap_keep": "exploratory",
        "der_overlap_keep_reasons": why_der_keep or ["overlap wordt niet apart gescoord"],
        "segment_eval": "exploratory" if why_der else "indicative",
        "docent_roles": "exploratory",
        "docent_roles_reasons": ["dev-data; drempel 0,35 is in-sample gekozen op testaudio1/2/5"],
        "all_metrics": "dev, optimistisch: geen achtergehouden testdata",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--tag", default="scores_v1")
    args = ap.parse_args()
    d = Path(args.run_dir)
    if not d.is_dir():
        sys.exit(f"Rundirectory ontbreekt: {d}")
    manifest = json.loads((d / "run_manifest.json").read_text(encoding="utf-8"))
    frag = manifest["fragment"]
    spec = S.FRAGMENTS[frag]
    duration = manifest["inputs"]["audio_duration_s"]

    ref = R.load_reference(S.GT_DIR / spec["ref"], frag)
    if ref.sha256 != manifest["inputs"]["reference_sha256"]:
        sys.exit("Referentie is gewijzigd sinds de run (hash verschilt). Niet scoren.")
    override = None
    if spec["role_source"]:
        rs = R.load_reference(S.GT_DIR / spec["role_source"], frag)
        override = R.speaker_roles(rs)
    roles = R.speaker_roles(ref, override)

    out = {"protocol": "PROTOCOL.md v1", "fragment": frag, "run_dir": str(d), "audio_duration_s": duration,
           "reference": {"path": str(ref.path), "sha256": ref.sha256, "rows": len(ref.rows), "speakers": ref.speakers(),
                         "row_kinds": {k: sum(1 for r in ref.rows if r.kind == k) for k in {r.kind for r in ref.rows}},
                         "role_map": roles, "role_source": spec["role_source"]},
           "quality_warning_unintelligible": {
               "rows_ja": sum(1 for r in ref.rows if r.unintelligible == "ja"),
               "seconds_ja": round(sum(r.end - r.start for r in ref.rows if r.unintelligible == "ja"), 3),
               "used_for_exclusion": False}}

    tr_path = next((d / "01_transcript").glob("*.json"), None)
    segs = []
    if tr_path:
        tr = json.loads(tr_path.read_text(encoding="utf-8"))
        segs = tr["segments"]
        mask_text = R.masked_timeline(ref, duration, "keep", kinds=("nonspeech", "cut"))
        kept = [s for s in segs if not _midpoint_masked(s, mask_text)]
        hyp_text = " ".join(s["text"] for s in sorted(kept, key=lambda s: s["start"]))
        circ = D.circularity(ref, segs)
        out["circularity"] = circ
        ref_text = R.reference_text(ref)
        w = {"hyp_segments_used": len(kept), "hyp_segments_masked": len(segs) - len(kept),
             "primary_fillers_removed": T.wer(ref_text, hyp_text, True), "fillers_kept": T.wer(ref_text, hyp_text, False),
             "cer_fillers_removed": T.cer(ref_text, hyp_text, True),
             "status": "circular_reference_do_not_report" if circ.get("circular") else "ok"}
        if spec["manual_txt"]:
            mt = R.manual_txt_text(S.RAW_DIR / spec["manual_txt"])
            w["vs_manual_txt"] = {"wer": T.wer(mt, hyp_text, True), "cer": T.cer(mt, hyp_text, True),
                                  "ref_vs_manual_wer": T.wer(mt, ref_text, True)}
        out["text"] = w
        out["evidence"] = evidence_status(ref, circ, segs, duration)
    else:
        out["text"] = {"status": "no_transcript_in_run"}

    rttm = d / "02_diarization" / "raw_turns.rttm"
    out["der_raw_turns"] = D.der_grid(ref, D.read_rttm(rttm), duration) if rttm.exists() else {"status": "no_raw_turns"}

    dz = next((d / "02_diarization").glob("*_diarized.json"), None)
    if dz:
        dj = json.loads(dz.read_text(encoding="utf-8"))
        from pyannote.core import Annotation, Segment
        hyp = Annotation()
        for s in dj["segments"]:
            if s.get("speaker_raw") and s["end"] > s["start"]:
                hyp[Segment(s["start"], min(s["end"], duration))] = s["speaker_raw"]
        out["der_segment_level_hypothesis"] = D.der_grid(ref, hyp, duration)
        out["segment_eval"] = D.segment_eval(dj["segments"], ref, duration)
    dr = next((d / "04_docent").glob("*_docent_roles.json"), None)
    if dr:
        dj = json.loads(dr.read_text(encoding="utf-8"))
        out["docent_roles"] = D.score_docent_roles(dj["turns"], ref, duration, roles)
    else:
        out["docent_roles"] = {"status": "no_docent_output_in_run"}

    p = write_json_new(d / f"{args.tag}.json", out)
    print(f"geschreven: {p}")
    for k in ("text", "evidence"):
        if k in out:
            print(k, json.dumps({kk: vv for kk, vv in out[k].items() if not isinstance(vv, (list, dict))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
