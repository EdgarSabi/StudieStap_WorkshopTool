"""DER (ruwe pyannote-beurten), segmentgebaseerde sprekerevaluatie en docentrol-evaluatie.

Alles koppelt op TIJD, nooit op rij- of segmentindex."""
import warnings
from pathlib import Path

import numpy as np
from pyannote.core import Annotation, Segment, Timeline
from pyannote.metrics.diarization import DiarizationErrorRate
from scipy.optimize import linear_sum_assignment

from . import settings as S
from .refs import Reference, build_uem, speech_annotation, masked_timeline
from .text import normalize


# ---------------------------------------------------------------- RTTM
def write_rttm(turns, uri: str, path) -> None:
    """turns: objecten of dicts met start, end, speaker. Weigert te overschrijven."""
    lines = []
    for t in turns:
        s, e, spk = (t["start"], t["end"], t["speaker"]) if isinstance(t, dict) else (t.start, t.end, t.speaker)
        lines.append(f"SPEAKER {uri} 1 {s:.3f} {e - s:.3f} <NA> <NA> {spk} <NA> <NA>")
    with open(path, "x", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))


def read_rttm(path) -> Annotation:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"RTTM ontbreekt: {path}")
    ann = Annotation()
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        p = line.split()
        if len(p) < 8 or p[0] != "SPEAKER":
            raise ValueError(f"{path.name} regel {n}: geen geldige RTTM-regel")
        start, dur = float(p[3]), float(p[4])
        if dur <= 0:
            raise ValueError(f"{path.name} regel {n}: duur <= 0")
        ann[Segment(start, start + dur)] = p[7]
    return ann


# ---------------------------------------------------------------- DER
def compute_der(ref_ann: Annotation, hyp_ann: Annotation, uem: Timeline, collar_each_side: float = 0.0) -> dict:
    """pyannote.metrics rekent met 'collar' als TOTALE breedte (halve breedte per kant);
    wij leggen de collar PER KANT vast (NIST/DIHARD) en geven dus 2x door."""
    if len(uem) == 0:
        return {"status": "empty_uem", "der": None}
    metric = DiarizationErrorRate(collar=2.0 * collar_each_side, skip_overlap=False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        c = metric(ref_ann, hyp_ann, uem=uem, detailed=True)
    total = c["total"]
    out = {"status": "ok", "total_ref_speech_s": round(total, 3),
           "missed_s": round(c["missed detection"], 3), "false_alarm_s": round(c["false alarm"], 3),
           "confusion_s": round(c["confusion"], 3), "uem_s": round(sum(s.duration for s in uem), 3)}
    if total > 0:
        out["der"] = c["diarization error rate"]
        out["missed_rate"] = c["missed detection"] / total
        out["false_alarm_rate"] = c["false alarm"] / total
        out["confusion_rate"] = c["confusion"] / total
    else:
        out["der"] = None
        out["note"] = "geen referentiespraak in de UEM: DER niet gedefinieerd (false alarm blijft in seconden zichtbaar)"
    return out


def der_grid(ref: Reference, hyp_ann: Annotation, duration: float) -> dict:
    """Alle vooraf vastgelegde combinaties (geen selectie achteraf)."""
    if not ref.has_speaker_labels:
        return {"status": "no_reference_speakers"}
    ref_ann = speech_annotation(ref, duration)
    grid = {}
    for um in S.UEM_MODES:
        for om in S.OVERLAP_MODES:
            uem = build_uem(ref, duration, um, om)
            for col in S.COLLARS_EACH_SIDE:
                r = compute_der(ref_ann, hyp_ann, uem, col)
                r["n_ref_speakers"] = len(ref.speakers())
                r["n_hyp_speakers_total"] = len(hyp_ann.labels())
                grid[f"uem={um}|overlap={om}|collar={col}"] = r
    return grid


# ---------------------------------------------------------------- segmentgebaseerd
def _shares(seg: Segment, ref: Reference, duration: float) -> dict:
    ann = speech_annotation(ref, duration)
    dur = seg.duration
    per = {}
    for label in ann.labels():
        t = ann.label_timeline(label).support().crop(seg, mode="intersection")
        per[label] = sum(s.duration for s in t) / dur
    unknown = masked_timeline(ref, duration, "keep", kinds=("unknown",)).crop(seg, mode="intersection")
    masked = masked_timeline(ref, duration, "keep", kinds=("nonspeech", "cut")).crop(seg, mode="intersection")
    return {"speakers": per, "unknown": sum(s.duration for s in unknown) / dur,
            "masked": sum(s.duration for s in masked) / dur}


def segment_eval(segments: list, ref: Reference, duration: float, label_field: str = "speaker_raw") -> dict:
    """segments: dicts met start, end, <label_field>. Tijdgebaseerd. Elk segment krijgt een status; niets valt weg."""
    if not ref.has_speaker_labels:
        return {"status": "no_reference_speakers"}
    rows = []
    for i, sg in enumerate(segments):
        seg = Segment(sg["start"], min(sg["end"], duration))
        if seg.duration <= 0:
            rows.append({"segment": i, "status": "outside_audio", "start": sg["start"], "end": sg["end"]})
            continue
        sh = _shares(seg, ref, duration)
        ranked = sorted(sh["speakers"].items(), key=lambda kv: -kv[1])
        known = sum(v for _, v in ranked)
        top = ranked[0] if ranked else (None, 0.0)
        second = ranked[1][1] if len(ranked) > 1 else 0.0
        if sh["masked"] + sh["unknown"] >= S.SEG_MASKED_MAX_SHARE:
            status = "masked"
        elif known < S.SEG_MIN_KNOWN_SHARE:
            status = "no_ref_speech"
        elif second >= S.SEG_MIXED_MIN_SHARE:
            status = "mixed"
        else:
            status = "single"
        rows.append({"segment": i, "start": sg["start"], "end": sg["end"], "hyp_label": sg.get(label_field),
                     "ref_top": top[0] if status in ("single", "mixed") else None, "ref_top_share": round(top[1], 3),
                     "ref_second_share": round(second, 3), "ref_unknown_share": round(sh["unknown"], 3),
                     "ref_masked_share": round(sh["masked"], 3), "status": status,
                     "seconds": round(seg.duration, 3), "flags": {k: sg.get(k) for k in ("overlap", "uncertain_assignment")}})
    single = [r for r in rows if r["status"] == "single"]
    hyp_labels = sorted({r["hyp_label"] for r in single if r["hyp_label"] is not None})
    ref_labels = ref.speakers()
    mapping = {}
    if hyp_labels and ref_labels:
        m = np.zeros((len(hyp_labels), len(ref_labels)))
        for r in single:
            if r["hyp_label"] is not None:
                m[hyp_labels.index(r["hyp_label"]), ref_labels.index(r["ref_top"])] += r["seconds"]
        ri, ci = linear_sum_assignment(-m)
        mapping = {hyp_labels[a]: ref_labels[b] for a, b in zip(ri, ci) if m[a, b] > 0}
    correct = 0.0
    for r in single:
        r["correct"] = mapping.get(r["hyp_label"]) == r["ref_top"]
        correct += r["seconds"] if r["correct"] else 0.0
    sec_single = sum(r["seconds"] for r in single)
    counts: dict = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"status": "ok", "mapping_hyp_to_ref": mapping, "status_counts": counts,
            "single_segments_seconds": round(sec_single, 3),
            "single_correct_seconds": round(correct, 3),
            "single_accuracy_seconds": (correct / sec_single) if sec_single else None,
            "mixed_segments": [r["segment"] for r in rows if r["status"] == "mixed"],
            "n_hyp_labels_in_single": len(hyp_labels), "n_ref_speakers": len(ref_labels), "segments": rows}


# ---------------------------------------------------------------- circulariteit
def circularity(ref: Reference, hyp_segments: list) -> dict:
    """Aandeel referentierijen waarvan de tekst gelijk is aan het in tijd best overlappende Whisper-segment."""
    rows = [r for r in ref.rows if r.kind not in ("nonspeech", "cut") and r.text]
    if not rows or not hyp_segments:
        return {"status": "no_data"}
    same = 0
    for r in rows:
        best, best_ov = None, 0.0
        for sg in hyp_segments:
            ov = min(r.end, sg["end"]) - max(r.start, sg["start"])
            if ov > best_ov:
                best, best_ov = sg, ov
        if best is not None and normalize(best["text"]) == normalize(r.text):
            same += 1
    ratio = same / len(rows)
    return {"status": "ok", "rows": len(rows), "identical_rows": same, "ratio": ratio,
            "circular": ratio >= S.CIRCULARITY_THRESHOLD}


# ---------------------------------------------------------------- docentrol
def _ref_role_for(turn: Segment, ref: Reference, duration: float, roles: dict) -> tuple:
    ann = speech_annotation(ref, duration)
    per = {"docent": 0.0, "leerling": 0.0}
    for label in ann.labels():
        role = roles.get(label)
        if role in per:
            t = ann.label_timeline(label).support().crop(turn, mode="intersection")
            per[role] += sum(s.duration for s in t)
    tot = sum(per.values())
    if tot / turn.duration < S.SEG_MIN_KNOWN_SHARE:
        return "none", per
    top, sec = max(per.items(), key=lambda kv: kv[1])
    other = tot - sec
    if other / turn.duration >= S.SEG_MIXED_MIN_SHARE:
        return "mixed", per
    return top, per


def score_docent_roles(turns: list, ref: Reference, duration: float, roles: dict) -> dict:
    """turns: dicts met start, end, docent_role (DOCENT|OTHER|ONZEKER|None). ONZEKER blijft een eigen kolom."""
    if not roles:
        return {"status": "no_reference_roles"}
    matrix: dict = {}
    detail = []
    for i, t in enumerate(turns):
        seg = Segment(t["start"], min(t["end"], duration))
        if seg.duration <= 0:
            continue
        rr, per = _ref_role_for(seg, ref, duration, roles)
        pred = t.get("docent_role") or "NIET_BEOORDEELD"
        cell = matrix.setdefault(rr, {}).setdefault(pred, {"turns": 0, "seconds": 0.0})
        cell["turns"] += 1
        cell["seconds"] = round(cell["seconds"] + seg.duration, 3)
        detail.append({"turn": i, "start": t["start"], "end": t["end"], "ref_role": rr, "pred": pred,
                       "uncertain_assignment": t.get("uncertain_assignment"), "overlap": t.get("overlap")})
    dec_ok = dec_n = strict_ok = n = 0
    for d in detail:
        if d["ref_role"] not in ("docent", "leerling"):
            continue
        n += 1
        want = "DOCENT" if d["ref_role"] == "docent" else "OTHER"
        strict_ok += d["pred"] == want
        if d["pred"] in ("DOCENT", "OTHER"):
            dec_n += 1
            dec_ok += d["pred"] == want
    onz = sum(1 for d in detail if d["ref_role"] in ("docent", "leerling") and d["pred"] == "ONZEKER")
    return {"status": "ok", "matrix_ref_role_by_pred": matrix, "scored_turns": n,
            "decided_turns": dec_n, "onzeker_turns": onz,
            "coverage": (dec_n / n) if n else None,
            "decided_accuracy": (dec_ok / dec_n) if dec_n else None,
            "strict_accuracy_onzeker_counts_wrong": (strict_ok / n) if n else None,
            "turns_total": len(detail), "turns": detail}
