# EXPERIMENT ONLY
# Does not modify Data-analysis/src/diarization/assign.py or anything else in src.
"""
STAP 3 — word-level speaker attribution.

Couples the Step 2 word timestamps onto the EXISTING pyannote diarization
turns, using the exact same time-overlap geometry as the production
`diarization/assign.py::assign_speakers()` — just applied per WORD instead of
per ASR segment. `assign.py` itself is imported and reused unmodified, both
for its `_overlap_seconds` helper and to compute a same-turns segment-level
baseline for a fair side-by-side comparison (see `baseline_segment_level` in
the output).

pyannote's raw diarization turns are NOT persisted anywhere in the existing
pipeline output (Data-local/processed/diarization/*_diarized.json only stores
the aggregated per-ASR-segment result), so this script re-runs the existing
`PyannoteBackend` on the wav the baseline diarization run already produced —
same model, same settings, nothing in Data-analysis/src changed.

What this deliberately does NOT do, per the assignment:
  - It does not force a single speaker onto a word when the overlap evidence
    is genuinely tied or absent. Those words get speaker=None and an explicit
    `uncertain`/`note` explaining why (no_overlapping_turn, zero_duration_word,
    ambiguous_margin, low_coverage) — never a silent guess.
  - It does not merge an uncertain word into a neighbouring turn. This mirrors
    preprocessing/turns.py's own isolation policy for uncertain/overlap
    ASR segments (that module isn't imported here — it operates on
    TranscriptSegment objects, not words — but the same design principle is
    applied at word level: uncertain -> always its own turn).

Input:
  Data-local/processed/word_level_speaker_attribution/<fragment>_words.json  (Step 2)
  Data-local/processed/diarization/<fragment>_16k_mono.wav                   (existing, from run_diarization.py)
  Data-local/processed/<fragment>.json                                      (baseline transcript, for the A/B reference comparison)

Output:
  Data-local/processed/word_level_speaker_attribution/<fragment>_word_attribution.json

Usage (existing project venv):
    Data-analysis\\src\\.venv\\Scripts\\python.exe attribute_words_to_speakers.py
    Data-analysis\\src\\.venv\\Scripts\\python.exe attribute_words_to_speakers.py --fragment testaudio1_fragment --force
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _common as common  # noqa: E402

from diarization import get_backend  # noqa: E402
from diarization.assign import _overlap_seconds, assign_speakers, summarize  # noqa: E402
from diarization.labeling import build_label_map  # noqa: E402

EXPERIMENT_NAME = "word_level_attribution"


def _attribute_one_word(word: dict, turns, label_map: dict, cfg) -> dict:
    """Same geometry as diarization/assign.py::assign_speakers, applied to one
    word instead of one segment. Returns the word dict extended with speaker
    fields, never guessing when the evidence doesn't support it."""
    start, end = word["start"], word["end"]
    duration = end - start

    out = dict(word)

    if duration <= 0:
        # A handful of words per fragment (see Step 2's zero-duration count)
        # collapse to a single instant in faster-whisper's word timestamps.
        # There's no time span to compute coverage/margin over, so this is
        # always uncertain — but if exactly one turn contains that instant we
        # still record it as a (flagged) best guess rather than throwing the
        # information away.
        containing = [t for t in turns if t.start <= start <= t.end]
        if len(containing) == 1:
            raw = containing[0].speaker
            out.update(speaker=label_map.get(raw, raw), speaker_raw=raw,
                       coverage=None, margin=None, overlap=False,
                       uncertain=True, note="zero_duration_word")
        else:
            out.update(speaker=None, speaker_raw=None, coverage=None, margin=None,
                       overlap=False, uncertain=True,
                       note="zero_duration_word_no_unique_turn")
        return out

    per_speaker: dict[str, float] = {}
    for t in turns:
        ov = _overlap_seconds(start, end, t.start, t.end)
        if ov > 0:
            per_speaker[t.speaker] = per_speaker.get(t.speaker, 0.0) + ov

    if not per_speaker:
        out.update(speaker=None, speaker_raw=None, coverage=None, margin=None,
                    overlap=False, uncertain=True, note="no_overlapping_turn")
        return out

    ranked = sorted(per_speaker.items(), key=lambda kv: kv[1], reverse=True)
    winner_raw, winner_ov = ranked[0]
    runner_ov = ranked[1][1] if len(ranked) > 1 else 0.0

    coverage = winner_ov / duration
    margin = (winner_ov - runner_ov) / duration
    is_overlap = (runner_ov / duration) >= cfg.overlap_min_ratio
    is_uncertain = coverage < cfg.uncertain_coverage_below or margin < cfg.uncertain_margin_below

    note = None
    if is_uncertain:
        note = "low_coverage" if coverage < cfg.uncertain_coverage_below else "ambiguous_margin"

    out.update(
        speaker=label_map.get(winner_raw, winner_raw),
        speaker_raw=winner_raw,
        coverage=round(coverage, 4),
        margin=round(margin, 4),
        overlap=is_overlap,
        uncertain=is_uncertain,
        note=note,
    )
    return out


def _reconstruct_readable_turns(segments: list[dict]) -> list[dict]:
    """Merge consecutive words with the same speaker into readable turns,
    across original ASR-segment boundaries — same idea as the WhisperX
    experiment's _reconstruct_turns (Experiments/diarization/whisperx). An
    uncertain word is NEVER folded into a neighbouring turn (isolation
    policy, see module docstring) — it becomes its own singleton turn with
    speaker=None so the uncertainty stays visible instead of silently
    inheriting a neighbour's label."""
    turns = []
    current_speaker = None
    current_words: list[dict] = []

    def flush():
        if current_words:
            turns.append({
                "speaker": current_speaker,
                "text": " ".join(w["word"].strip() for w in current_words),
                "start": current_words[0]["start"],
                "end": current_words[-1]["end"],
                "n_words": len(current_words),
                "any_uncertain": any(w["uncertain"] for w in current_words),
            })

    for seg in segments:
        for w in seg["words"]:
            if w["uncertain"]:
                flush()
                current_speaker, current_words = None, []
                turns.append({
                    "speaker": None, "text": w["word"].strip(),
                    "start": w["start"], "end": w["end"],
                    "n_words": 1, "any_uncertain": True, "note": w.get("note"),
                })
                continue
            if w["speaker"] != current_speaker:
                flush()
                current_speaker, current_words = w["speaker"], []
            current_words.append(w)
    flush()
    return turns


def run_one(fragment: str, force: bool) -> dict:
    words_path = common.OUTPUT_DIR / f"{fragment}_words.json"
    if not words_path.exists():
        sys.exit(f"{words_path} not found — run extract_word_timestamps.py (Step 2) first.")
    words_data = json.loads(words_path.read_text(encoding="utf-8"))

    out_path = common.OUTPUT_DIR / f"{fragment}_word_attribution.json"
    if out_path.exists() and not force:
        sys.exit(f"{out_path} already exists. Pass --force to overwrite.")

    wav_path = common.diarization_wav_path(fragment)
    if not wav_path.exists():
        sys.exit(f"{wav_path} not found — expected run_diarization.py to have already produced it.")

    cfg = common.base_diarization_config()
    print(f"[{fragment}] diarizing (fresh run, same model as baseline: {cfg.hf_model}) ...")
    backend = get_backend(cfg)
    t0 = time.time()
    diar_result = backend.diarize(wav_path)
    diar_runtime = round(time.time() - t0, 2)

    label_info = build_label_map(diar_result, main_speaker_min_share=cfg.main_speaker_min_share)
    label_map = label_info["map"]
    turns = diar_result.turns

    # --- word-level attribution (this experiment's contribution) ---
    n_mixed_loose = 0    # >1 distinct speaker label among ALL words (incl. uncertain ones, speaker=None counts as its own bucket only if non-None)
    n_mixed_confident = 0  # >1 distinct speaker label among words attributed WITHOUT uncertainty
    attributed_segments = []
    for seg in words_data["segments"]:
        words_out = [_attribute_one_word(w, turns, label_map, cfg) for w in seg["words"]]
        confident_speakers = {w["speaker"] for w in words_out if w["speaker"] and not w["uncertain"]}
        all_speakers = {w["speaker"] for w in words_out if w["speaker"]}
        if len(all_speakers) > 1:
            n_mixed_loose += 1
        if len(confident_speakers) > 1:
            n_mixed_confident += 1
        attributed_segments.append({
            "start": seg["start"], "end": seg["end"], "text": seg["text"],
            "mixed_speakers_loose": len(all_speakers) > 1,
            "mixed_speakers_confident": len(confident_speakers) > 1,
            "words": words_out,
        })

    readable_turns = _reconstruct_readable_turns(attributed_segments)

    n_words = sum(len(s["words"]) for s in attributed_segments)
    n_uncertain = sum(1 for s in attributed_segments for w in s["words"] if w["uncertain"])
    n_overlap = sum(1 for s in attributed_segments for w in s["words"] if w.get("overlap"))
    n_unassigned = sum(1 for s in attributed_segments for w in s["words"] if w["speaker"] is None)

    # --- reference: same-turns baseline-style SEGMENT-level assignment ---
    # Reuses assign_speakers()/summarize() from diarization/assign.py UNMODIFIED,
    # on the baseline transcript's own segments, with these SAME fresh turns
    # (so any difference vs. the original Data-local/processed/diarization/
    # <fragment>_diarized.json is isolated to run-to-run diarization variance,
    # not to a different set of turns).
    baseline_transcript = common.load_baseline_transcript(fragment)
    baseline_style_segments = assign_speakers(baseline_transcript.segments, turns, label_map,
                                               overlap_min_ratio=cfg.overlap_min_ratio,
                                               uncertain_coverage_below=cfg.uncertain_coverage_below,
                                               uncertain_margin_below=cfg.uncertain_margin_below)
    baseline_stats = summarize(baseline_style_segments)

    output = {
        "experiment": EXPERIMENT_NAME,
        "fragment": fragment,
        "diarization_model": diar_result.model,
        "diarization_runtime_seconds": diar_runtime,
        "n_turns": len(turns),
        "raw_speakers": diar_result.raw_speakers,
        "speaker_inventory": label_info["inventory"],
        "word_level": {
            "segments": attributed_segments,
            "readable_turns": readable_turns,
            "stats": {
                "n_words": n_words,
                "n_uncertain": n_uncertain,
                "n_overlap": n_overlap,
                "n_unassigned": n_unassigned,
                "n_segments": len(attributed_segments),
                "n_mixed_speaker_segments_loose": n_mixed_loose,
                "n_mixed_speaker_segments_confident": n_mixed_confident,
            },
        },
        "baseline_segment_level_reference": {
            "note": "Same fresh turns as above, but the baseline's own ASR segments "
                    "and the EXISTING assign_speakers() (unmodified) — segment-level, "
                    "for direct comparison with word_level above.",
            "segments": [s.model_dump() for s in baseline_style_segments],
            "stats": baseline_stats,
        },
    }

    common.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  raw speakers: {diar_result.raw_speakers}  ({len(turns)} turns, {diar_runtime}s)")
    print(f"  word-level  : {n_words} words | uncertain={n_uncertain} overlap={n_overlap} unassigned={n_unassigned}")
    print(f"  mixed ASR segments (word-level split found >1 speaker): "
          f"loose={n_mixed_loose}/{len(attributed_segments)}  confident={n_mixed_confident}/{len(attributed_segments)}")
    print(f"  baseline-style (segment-level, same turns): "
          f"per_label={baseline_stats['per_label']}  overlap={baseline_stats['overlap_segments']} "
          f"uncertain={baseline_stats['uncertain_segments']} unassigned={baseline_stats['unassigned_segments']}")
    print(f"  readable turns: {len(readable_turns)}")
    print(f"  written to {out_path}\n")
    return output


def main():
    parser = argparse.ArgumentParser(description="STAP 3: word-level speaker attribution using existing pyannote turns")
    parser.add_argument(
        "--fragment", action="append", dest="fragments",
        help="Fragment name (no extension), repeatable. Default: all 3 eval fragments.",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    fragments = args.fragments or common.EVAL_FRAGMENTS
    for fragment in fragments:
        run_one(fragment, args.force)


if __name__ == "__main__":
    main()
