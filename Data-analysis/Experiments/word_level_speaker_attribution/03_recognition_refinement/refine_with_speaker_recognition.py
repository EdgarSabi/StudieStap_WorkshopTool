# EXPERIMENT ONLY
# Does not modify Data-analysis/src or the speaker_recognition/ experiment.
"""
STAP 4 — speaker recognition refinement.

Applies the pyannote WeSpeaker embedding technique from the previous
speaker_recognition/ experiment to sufficiently long speech chunks — per the
assignment: "Bereken niet zomaar een speaker embedding voor ieder
afzonderlijk woord. Gebruik voldoende lange spraakstukken en koppel de
uitkomsten waar mogelijk terug aan de woorden."

Kept as THREE separate, comparable signals rather than one blended score:
  1. Sprekerwisselingen detecteren     -> pyannote diarization turns (Step 3 input, unchanged here)
  2. Woorden aan sprekers koppelen     -> Step 3's word-level attribution (which turn owns which word)
  3. De docent identificeren           -> THIS step: is a chunk's VOICE close to the
                                           testdocent.mp3 reference, independent of which
                                           raw diarization cluster it was assigned to?

Evaluated at TWO granularities on purpose, because they turned out to give a
genuinely different answer for testaudio2 (see comparison/results.md):

  - `turn_level`    Step 3's diarization-turn-based `readable_turns`. These
                     inherit whatever turn boundaries pyannote's diarization
                     found — if diarization never split a stretch of audio
                     into two turns, a readable_turn spanning that stretch
                     can mix docent + leerling words with no way to tell.
  - `segment_level`  Step 2's own ASR segments (faster-whisper's VAD-based
                     segmentation), which is INDEPENDENT of diarization turn
                     boundaries — this is the same granularity the earlier
                     speaker_recognition/ experiment used. Each segment's
                     "diar_label" for the agreement check is looked up by
                     best time-overlap against Step 3's
                     `baseline_segment_level_reference` (assign_speakers()
                     on the baseline's own segments with the same fresh
                     turns), not assumed to line up 1:1 by index (Step 2's
                     own segmentation doesn't always match the baseline's
                     segment count/boundaries exactly — see Step 2's output).

Reused, unmodified:
  - speaker_recognition/_common.py            (wav loading/slicing, cosine_similarity,
                                                 duration_bucket, teacher reference wav+cache,
                                                 compute_agreement())
  - speaker_recognition/pyannote_embeddings/test_teacher_recognition.py's
    load_inference()/embed() functions        (WeSpeaker model loading + per-clip embedding,
                                                 including its short-clip warning capture)

IMPORTANT — never-overwrite guarantee: every evaluated chunk keeps THREE
separate fields side by side — `diarization_label` (the ORIGINAL pyannote/
assign_speakers label, untouched), `similarity` (the recognition score), and
`recognition_label` (the recognition-only DOCENT/OTHER verdict, computed
independently). `resolved_label` is always `None` — this script does NOT
pick a winner when the two disagree; `agreement`/`conflict` only classify
the relationship (see speaker_recognition/_common.py::compute_agreement()),
they never merge into or replace either label.

IMPORTANT — threshold status: SIMILARITY_THRESHOLD (0.35) is the SAME value
used in speaker_recognition/pyannote_embeddings/test_teacher_recognition.py,
carried over as an EXPERIMENTAL setting — it is explicitly NOT a validated
or proven-reliable classification criterion (see that experiment's
comparison/results.md for the full caveat and error analysis). Every output
row/section restates this via `threshold_status`.

Input:
  Data-local/processed/word_level_speaker_attribution/<fragment>_words.json             (Step 2)
  Data-local/processed/word_level_speaker_attribution/<fragment>_word_attribution.json  (Step 3)
  Data-local/processed/diarization/<fragment>_16k_mono.wav                              (existing)
  Data-local/processed/speaker_recognition/testdocent_16k_mono.wav                      (existing, cached)

Output:
  Data-local/processed/word_level_speaker_attribution/<fragment>_recognition_refined.json

Usage (existing project venv):
    Data-analysis\\src\\.venv\\Scripts\\python.exe refine_with_speaker_recognition.py
    Data-analysis\\src\\.venv\\Scripts\\python.exe refine_with_speaker_recognition.py --fragment testaudio2_fragment --force
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _common as common  # noqa: E402

EXPERIMENT_NAME = "recognition_refinement"

# EXPERIMENTAL setting, carried over from speaker_recognition/comparison/results.md
# for pyannote/wespeaker-voxceleb-resnet34-LM — chosen by eyeballing a
# similarity distribution on a 49-chunk sample, NOT a validated or
# proven-reliable classification criterion. See that experiment's threshold
# section for the full caveat and error analysis before relying on it for
# anything beyond flagging candidates for human review.
SIMILARITY_THRESHOLD = 0.35
# Below this, a chunk is not embedded at all — see speaker_recognition/comparison/results.md's
# finding that sub-1s clips give unreliable/noisy similarity scores.
MIN_DURATION_S = 1.0
# A step-2 ASR segment needs at least this much time-overlap with a baseline
# segment (as a fraction of the shorter of the two) to borrow its diarization
# label for the segment_level agreement check.
MIN_OVERLAP_FRACTION_FOR_MATCH = 0.5


def _load_pyannote_recognition_module():
    """Reuse speaker_recognition/pyannote_embeddings/test_teacher_recognition.py's
    load_inference()/embed() as-is, instead of re-implementing WeSpeaker model
    loading here. Loaded under a distinct module name for the same reason
    _common.py loads speaker_recognition/_common.py that way (name collision
    avoidance, not a functional need)."""
    path = (common.SPEAKER_RECOGNITION_DIR / "pyannote_embeddings" / "test_teacher_recognition.py")
    spec = importlib.util.spec_from_file_location("speaker_recognition_pyannote", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _overlap_seconds(a0, a1, b0, b1) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def _best_matching_label(start: float, end: float, baseline_segments: list[dict]) -> str | None:
    """Best time-overlapping baseline (assign_speakers) segment's speaker
    label, or None if nothing overlaps enough. Used to look up a diarization
    reference label for a Step-2 ASR segment that doesn't necessarily line up
    1:1 with the baseline's own segmentation."""
    duration = end - start
    if duration <= 0:
        return None
    best_ov, best_label = 0.0, None
    for bseg in baseline_segments:
        ov = _overlap_seconds(start, end, bseg["start"], bseg["end"])
        if ov > best_ov:
            best_ov, best_label = ov, bseg["speaker"]
    shorter = min(duration, min((b["end"] - b["start"] for b in baseline_segments), default=duration))
    if shorter <= 0 or best_ov / duration < MIN_OVERLAP_FRACTION_FOR_MATCH:
        return None
    return best_label


def _evaluate_clip(start: float, end: float, text: str, diarization_label: str | None,
                    samples, sr, inference, teacher_embedding, embed_fn) -> dict:
    """Never overwrites diarization_label. Always returns it unchanged
    alongside (at most) a similarity score and a SEPARATE recognition_label
    — `resolved_label` stays None always: no automatic winner is picked when
    the two disagree, by design (see module docstring)."""
    duration = end - start
    entry = {
        "start": start, "end": end, "text": text, "duration_s": round(duration, 3),
        "diarization_label": diarization_label,   # ORIGINAL label, never mutated below
        "resolved_label": None,                    # always None — no auto-resolution, ever
        "threshold_status": common.sr_common.THRESHOLD_STATUS_NOTE,
    }

    if duration < MIN_DURATION_S:
        entry.update(embeddable=False, similarity=None, recognition_label=None,
                     agreement="not_evaluated", conflict=False,
                     note=f"shorter than {MIN_DURATION_S}s ({duration:.2f}s)")
        return entry

    clip = common.sr_common.slice_samples(samples, sr, start, end)
    embedding, warn = embed_fn(inference, clip, sr)
    if embedding is None:
        entry.update(embeddable=False, similarity=None, recognition_label=None,
                     agreement="not_evaluated", conflict=False, note=f"could not embed: {warn}")
        return entry

    similarity = common.sr_common.cosine_similarity(embedding, teacher_embedding)
    recognition_label = "DOCENT" if similarity >= SIMILARITY_THRESHOLD else "OTHER"
    agreement, conflict = common.sr_common.compute_agreement(diarization_label, recognition_label)

    entry.update(embeddable=True, similarity=round(similarity, 4),
                 recognition_label=recognition_label, agreement=agreement,
                 conflict=conflict, note=warn)
    return entry


def _stats(entries: list[dict]) -> dict:
    return {
        "n_total": len(entries),
        "n_evaluated": sum(1 for e in entries if e["embeddable"]),
        "n_consistent": sum(1 for e in entries if e["agreement"] in ("consistent_docent", "consistent_other")),
        "n_conflict_total": sum(1 for e in entries if e["conflict"]),
        "n_conflict_diar_says_docent_sim_low": sum(1 for e in entries if e["agreement"] == "conflict_diar_main_sim_low"),
        "n_conflict_diar_says_other_sim_high": sum(1 for e in entries if e["agreement"] == "conflict_diar_other_sim_high"),
    }


def run_one(fragment: str, inference, teacher_embedding, embed_fn, force: bool) -> dict:
    words_path = common.OUTPUT_DIR / f"{fragment}_words.json"
    attribution_path = common.OUTPUT_DIR / f"{fragment}_word_attribution.json"
    if not words_path.exists() or not attribution_path.exists():
        sys.exit(f"Run Step 2 and Step 3 for {fragment} first ({words_path.name}, {attribution_path.name}).")
    words_data = json.loads(words_path.read_text(encoding="utf-8"))
    attribution = json.loads(attribution_path.read_text(encoding="utf-8"))

    out_path = common.OUTPUT_DIR / f"{fragment}_recognition_refined.json"
    if out_path.exists() and not force:
        sys.exit(f"{out_path} already exists. Pass --force to overwrite.")

    wav_path = common.diarization_wav_path(fragment)
    samples, sr = common.sr_common.load_wav_mono(wav_path)

    # --- turn_level: Step 3's diarization-turn-based readable_turns ---
    readable_turns = attribution["word_level"]["readable_turns"]
    turn_level = [
        _evaluate_clip(t["start"], t["end"], t["text"], t["speaker"], samples, sr,
                       inference, teacher_embedding, embed_fn)
        for t in readable_turns
    ]

    # --- segment_level: Step 2's own ASR segments, diarization-turn-independent ---
    baseline_segments = attribution["baseline_segment_level_reference"]["segments"]
    segment_level = []
    for seg in words_data["segments"]:
        diar_label = _best_matching_label(seg["start"], seg["end"], baseline_segments)
        segment_level.append(
            _evaluate_clip(seg["start"], seg["end"], seg["text"], diar_label, samples, sr,
                           inference, teacher_embedding, embed_fn)
        )

    output = {
        "experiment": EXPERIMENT_NAME,
        "fragment": fragment,
        "embedding_model": "pyannote/wespeaker-voxceleb-resnet34-LM",
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "threshold_status": common.sr_common.THRESHOLD_STATUS_NOTE,
        "min_duration_s": MIN_DURATION_S,
        "teacher_reference": str(common.sr_common.TEACHER_REF_AUDIO),
        "turn_level": {
            "note": "Evaluated on Step 3's readable_turns (diarization-turn boundaries).",
            "entries": turn_level,
            "stats": _stats(turn_level),
        },
        "segment_level": {
            "note": "Evaluated on Step 2's own ASR segments (diarization-turn-independent); "
                    "diar_label looked up by best time-overlap against the baseline "
                    "assign_speakers() result, not assumed to align 1:1 by index.",
            "entries": segment_level,
            "stats": _stats(segment_level),
        },
    }

    common.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    for level_name, level in (("turn_level", output["turn_level"]), ("segment_level", output["segment_level"])):
        s = level["stats"]
        print(f"[{fragment}] {level_name}: {s['n_total']} chunks, {s['n_evaluated']} evaluated "
              f"(>= {MIN_DURATION_S}s) | consistent={s['n_consistent']} conflicts={s['n_conflict_total']} "
              f"(MAIN-but-low-sim={s['n_conflict_diar_says_docent_sim_low']} "
              f"OTHER-but-high-sim={s['n_conflict_diar_says_other_sim_high']})")
        for e in level["entries"]:
            if e["conflict"]:
                print(f"    CONFLICT [{e['start']:.2f}-{e['end']:.2f}] diarization_label={e['diarization_label']} "
                      f"sim={e['similarity']} recognition_label={e['recognition_label']}  text={e['text'][:60]!r}")
    print(f"  written to {out_path}\n")
    return output


def main():
    parser = argparse.ArgumentParser(description="STAP 4: pyannote WeSpeaker recognition refinement")
    parser.add_argument(
        "--fragment", action="append", dest="fragments",
        help="Fragment name (no extension), repeatable. Default: all 3 eval fragments.",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    fragments = args.fragments or common.EVAL_FRAGMENTS

    sr_module = _load_pyannote_recognition_module()

    print("Loading pyannote embedding model (pyannote/wespeaker-voxceleb-resnet34-LM)...")
    inference = sr_module.load_inference()

    ref_wav = common.sr_common.teacher_reference_wav()
    ref_samples, ref_sr = common.sr_common.load_wav_mono(ref_wav)
    teacher_embedding, ref_warning = sr_module.embed(inference, ref_samples, ref_sr)
    if teacher_embedding is None:
        sys.exit(f"Could not embed the teacher reference clip: {ref_warning}")
    print(f"Teacher reference embedded ({common.sr_common.TEACHER_REF_AUDIO.name}, "
          f"{len(ref_samples) / ref_sr:.2f}s)\n")

    for fragment in fragments:
        run_one(fragment, inference, teacher_embedding, sr_module.embed, args.force)


if __name__ == "__main__":
    main()
