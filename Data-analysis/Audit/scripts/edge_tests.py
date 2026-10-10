import sys, wave, tempfile, subprocess, shutil, json
from pathlib import Path
sys.path.insert(0, r"C:\Users\School\Projects\StudieStap_WorkshopTool\Data-analysis\src")
from diarization import (SpeakerTurn as T, DiarizationResult, build_label_map, assign_speakers,
                         _load_wav_waveform, to_wav)
from models import TranscriptSegment, WorkshopTranscript
from preprocessing import build_speaker_turns
import config
import transcription

SP = Path(sys.argv[1])


def seg(s, e, t="x", **kw):
    return TranscriptSegment(start=s, end=e, text=t, **kw)


def res(turns):
    return DiarizationResult(turns=turns, backend="t", model="t")


R = []


def rec(id, q, exp, act, ok):
    R.append(dict(id=id, question=q, expected=exp, actual=act, passed=ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {id}: {q}\n    verwacht: {exp}\n    werkelijk: {act}", flush=True)


# E1 docent praat minder dan leerling
lm = build_label_map(res([T(0, 10, "S0"), T(10, 40, "S1")]))
rec("E1", "Docent (S0) spreekt 10 s, leerling (S1) 30 s: wie wordt MAIN_SPEAKER?",
    "label mag niet blind aan spreektijd hangen (docent niet 'OTHER')",
    f"map={lm['map']}", lm["map"]["S0"] == "MAIN_SPEAKER")

# E2 gelijke spreektijd
a = build_label_map(res([T(0, 10, "S0"), T(10, 20, "S1")]))
b = build_label_map(res([T(0, 10, "S1"), T(10, 20, "S0")]))
rec("E2", "Gelijke spreektijd (10 s/10 s), turns in omgekeerde volgorde aangeleverd",
    "zelfde toekenning of main_speaker_uncertain=True",
    f"volgorde1={a['map']}; volgorde2={b['map']}; uncertain={a['main_speaker_uncertain']}",
    a["map"] == b["map"] or a["main_speaker_uncertain"])

# E3 main_speaker_uncertain met default
dflt = config.DiarizationConfig().main_speaker_min_share
r4 = res([T(0, 10, "S0"), T(10, 20, "S1"), T(20, 30, "S2"), T(30, 40, "S3")])
v = build_label_map(r4, main_speaker_min_share=dflt)["main_speaker_uncertain"]
rec("E3", "4 sprekers met 25% spreektijd elk, default-config: main_speaker_uncertain?",
    "True (geen duidelijke hoofdspreker)", f"{v} (default main_speaker_min_share={dflt})", v is True)

# E4 sprekerwissel binnen segment zonder simultane spraak
out = assign_speakers([seg(0, 5)], [T(0, 4, "S0"), T(4, 5, "S1")],
                      {"S0": "MAIN_SPEAKER", "S1": "OTHER_SPEAKER_1"})[0]
rec("E4", "Sprekerwissel BINNEN een segment (S0 0-4 s, S1 4-5 s), niemand praat tegelijk: overlap?",
    "overlap=False", f"overlap={out.overlap}, uncertain={out.uncertain_assignment}, speaker={out.speaker}, conf={out.speaker_confidence}",
    out.overlap is False)

# E5 echte overlap
out = assign_speakers([seg(0, 5)], [T(0, 5, "S0"), T(1, 4, "S1")],
                      {"S0": "MAIN_SPEAKER", "S1": "OTHER_SPEAKER_1"})[0]
rec("E5", "Echt gelijktijdig praten (S1 3 s binnen S0)", "overlap=True",
    f"overlap={out.overlap}, uncertain={out.uncertain_assignment}, conf={out.speaker_confidence}", out.overlap is True)

# E6 geen diarization-spraak
out = assign_speakers([seg(10, 12)], [T(0, 5, "S0")], {"S0": "MAIN_SPEAKER"})[0]
rec("E6", "ASR-segment zonder enige diarization-spraak", "speaker=None, uncertain=True",
    f"speaker={out.speaker}, uncertain={out.uncertain_assignment}", out.speaker is None and out.uncertain_assignment)

# E7 slechts 20% gedekt
out = assign_speakers([seg(0, 10)], [T(0, 2, "S0")], {"S0": "MAIN_SPEAKER"})[0]
rec("E7", "Slechts 20% van segment door diarization gedekt (rest onbekend)", "uncertain=True",
    f"confidence={out.speaker_confidence}, uncertain={out.uncertain_assignment}", out.uncertain_assignment is True)

# E7b: wat betekent confidence=1.0
out = assign_speakers([seg(0, 10)], [T(0, 6, "S0"), T(6, 10, "S1")],
                      {"S0": "MAIN_SPEAKER", "S1": "OTHER_SPEAKER_1"})[0]
rec("E7b", "60/40 verdeling S0/S1 binnen een segment", "confidence 0.6 is 'aandeel van overlap-tijd', geen kans",
    f"speaker={out.speaker}, conf={out.speaker_confidence}, overlap={out.overlap}, uncertain={out.uncertain_assignment}", True)

# E8 modelvalidatie
try:
    TranscriptSegment(start=5, end=2, text="x"); a8, ok8 = "geaccepteerd (start=5, end=2)", False
except Exception:
    a8, ok8 = "afgewezen", True
rec("E8", "Segment met end < start", "ValidationError", a8, ok8)

base = '{"audio_file":"a","language":"nl","duration":1,"segments":[%s],"model_size":"m","transcription_time_seconds":1%s}'
try:
    WorkshopTranscript.model_validate_json(base % ('{"start":0,"end":1,"text":"t","spekaer":"X"}', ',"onbekend":1'))
    a9, ok9 = "geaccepteerd; typfout-veld 'spekaer' en 'onbekend' stil genegeerd", False
except Exception:
    a9, ok9 = "afgewezen", True
rec("E9", "JSON met typfout in veldnaam / onbekend veld", "ValidationError of waarschuwing", a9, ok9)

try:
    WorkshopTranscript.model_validate_json(base % ('{"start":0,"end":1}', ""))
    a10, ok10 = "geaccepteerd", False
except Exception:
    a10, ok10 = "afgewezen (text verplicht)", True
rec("E10", "Segment zonder text-veld", "afgewezen", a10, ok10)

try:
    w = WorkshopTranscript.model_validate_json(base % ('{"start":0,"end":1,"text":"t","speaker":"Docent"}', ""))
    a11, ok11 = f"geaccepteerd, speaker='{w.segments[0].speaker}' (geen vocabulaire-check)", False
except Exception:
    a11, ok11 = "afgewezen", True
rec("E11", "Segment met willekeurig speaker-label", "alleen toegestane labels/None", a11, ok11)

# E12/E13 preprocessing merge-regels
s1 = seg(0, 2, speaker="A"); s2 = seg(1, 3, speaker="A"); s3 = seg(10, 12, speaker="A")
t = build_speaker_turns([s1, s2, s3], max_gap_within_turn_seconds=1.5)
rec("E12", "Segmenten A(0-2), A(1-3, overlapt in tijd), A(10-12): turns?", "2 turns",
    f"{len(t)} turns: {[(x.start, x.end) for x in t]}", len(t) == 2)

a = seg(0, 2, speaker="MAIN_SPEAKER", speaker_raw="S0"); b = seg(2.1, 4, speaker="MAIN_SPEAKER", speaker_raw="S9")
t = build_speaker_turns([a, b], max_gap_within_turn_seconds=1.5)
rec("E13", "Zelfde friendly label, andere speaker_raw", "niet samenvoegen", f"{len(t)} turn(s)", len(t) == 2)

a = seg(0, 1, speaker="A"); b = seg(2.4, 2.5, speaker="A")
t = build_speaker_turns([a, b], max_gap_within_turn_seconds=1.5)[0]
rec("E14", "Merged turn: span vs. werkelijke spraak (docent_recognition min-duur check gebruikt end-start)",
    "check op spraaktijd (1.1 s)",
    f"span={t.end - t.start:.1f}s, spraak={sum(s.end - s.start for s in t.source_segments):.1f}s", False)

# E15 WAV-loader
d = Path(tempfile.mkdtemp(dir=SP))


def mkwav(path, sr, ch, width, secs=1.0):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(ch); w.setsampwidth(width); w.setframerate(sr)
        w.writeframes(b"\x00" * (int(sr * secs) * ch * width))


for sr, ch, wd in [(8000, 2, 2), (44100, 1, 2), (16000, 1, 3), (16000, 1, 1)]:
    p = d / f"t_{sr}_{ch}_{wd}.wav"; mkwav(p, sr, ch, wd)
    try:
        wf, s = _load_wav_waveform(p)
        out_ = f"geladen shape={tuple(wf.shape)} sr={s} (loader doet zelf geen resample/downmix)"; ok = True
    except Exception as e:
        out_ = f"{type(e).__name__}: {e}"; ok = True   # duidelijke fout is acceptabel
    rec(f"E15-{sr}Hz-{ch}ch-{wd * 8}bit", "WAV-loader met afwijkend formaat", "geladen of duidelijke fout", out_, ok)

p = d / "t_8000_2_2.wav"
o = to_wav(p, d / "out", False)
rec("E16", "to_wav() met 8 kHz stereo WAV (docstring: 'convert non-wav inputs')",
    "pipeline krijgt 16 kHz mono of weet dat het afwijkt", f"{'ongewijzigd doorgegeven' if o == p else 'geconverteerd'}",
    o != p)

# E17 cache-collisie
ff = shutil.which("ffmpeg")
A = d / "A"; B = d / "B"; A.mkdir(); B.mkdir()
subprocess.run([ff, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(A / "fragment.mp3")], capture_output=True)
subprocess.run([ff, "-y", "-f", "lavfi", "-i", "sine=frequency=880:duration=2", str(B / "fragment.mp3")], capture_output=True)
w1 = to_wav(A / "fragment.mp3", d / "cache", False); n1 = wave.open(str(w1)).getnframes()
w2 = to_wav(B / "fragment.mp3", d / "cache", False); n2 = wave.open(str(w2)).getnframes()
rec("E17", "Twee verschillende bestanden met dezelfde naam (map A: 1 s, map B: 2 s) -> WAV-cache",
    "tweede bestand krijgt eigen WAV van 2 s", f"WAV na 2e aanroep = {n2 / 16000:.1f}s (1e was {n1 / 16000:.1f}s); zelfde cachepad: {w1 == w2}",
    n2 / 16000 > 1.5)

pa = transcription.output_path_for(Path("raw/x.mp3"), Path("P"))
pb = transcription.output_path_for(Path("test/x.mp3"), Path("P"))
rec("E18", "transcription.output_path_for: zelfde bestandsnaam in raw/ en test-files/",
    "verschillende outputpaden", f"{pa} == {pb}: {pa == pb}", pa != pb)

(SP / "edge_results.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
print("\nsamenvatting:", sum(r["passed"] for r in R), "pass /", len(R))
