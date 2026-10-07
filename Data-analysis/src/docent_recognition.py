"""
STAP 4 — Docent recognition: is THIS speaker turn the teacher's voice?

Phase 3 ProcessedTranscript (speaker turns) + a teacher reference recording
-> the same turns, each with a `docent_role` (DOCENT / OTHER / ONZEKER).

Draaien:
    python docent_recognition.py --processed <Phase 3 JSON> --reference <docent-referentie.mp3>

This is deliberately a SEPARATE judgement from the diarization `speaker`
label (MAIN_SPEAKER/OTHER_SPEAKER_n, which is just "who talks the most" —
see diarization.py). MAIN_SPEAKER does NOT automatically become DOCENT here.
`docent_role` is decided by comparing this turn's own audio to a reference
recording of the teacher's voice, using a pyannote WeSpeaker embedding
model — the same technique already validated in
Experiments/speaker_recognition/. The logic here is PORTED from that
experiment (not imported from it — Data-analysis/src must never depend on
Experiments/).
"""
import argparse
import json
import sys
import time
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import torch

from config import DocentRecognitionConfig, DOCENT_RECOGNITION_OUTPUT_DIR, DIARIZATION_OUTPUT_DIR, get_hf_token
from models import ProcessedTranscript, SpeakerTurn
from diarization import _load_wav_waveform, to_wav

ROLE_DOCENT = "DOCENT"
ROLE_OTHER = "OTHER"
ROLE_ONZEKER = "ONZEKER"


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """A number from -1 to 1 saying how similar two voice-embeddings are:
    1 = same voice, 0 = unrelated, -1 = opposite. This is NOT a percentage
    chance of being correct — see DocentReferenceRecognizer's docstring."""
    a = np.asarray(a).reshape(-1).astype(np.float64)
    b = np.asarray(b).reshape(-1).astype(np.float64)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


# A class because it bundles two things that always belong together and get
# reused for EVERY turn in the recording: the loaded WeSpeaker model, and the
# one-time embedding of the teacher's reference clip. Passing those two
# pieces of state into every function call separately would be more
# confusing than keeping them on one object.
class DocentReferenceRecognizer:
    """Loads the WeSpeaker embedding model once, embeds the reference clip
    once, and thereafter compares any audio clip's embedding against it via
    cosine similarity. The similarity is a raw cosine value in [-1, 1] — see
    models.py's SpeakerTurn docstring: it is NOT a calibrated probability,
    and callers (assign_docent_roles below) must not present it as one.
    """

    def __init__(self, reference_wav_path: Path, model_name: str, device: str = "cpu"):
        from pyannote.audio import Inference, Model

        token = get_hf_token()
        if not token:
            raise RuntimeError(
                "No HuggingFace token found. Put HF_TOKEN=... in <repo-root>/.env "
                "(same setup as diarization.py)."
            )
        model = Model.from_pretrained(model_name, token=token)
        self._inference = Inference(model, window="whole", device=torch.device(device))
        self.model_name = model_name
        self.reference_wav_path = Path(reference_wav_path)

        ref_waveform, ref_sr = _load_wav_waveform(self.reference_wav_path)
        embedding, warning = self._embed(ref_waveform, ref_sr)
        if embedding is None:
            raise RuntimeError(f"Could not embed the reference clip {self.reference_wav_path}: {warning}")
        self._reference_embedding = embedding
        self.reference_warning = warning

    def _embed(self, waveform: torch.Tensor, sample_rate: int) -> tuple[Optional[np.ndarray], Optional[str]]:
        """Returns (embedding, warning_text). embedding is None if the clip is
        too short/empty/unembeddable — callers must treat that as "unknown",
        never as evidence of anything."""
        if waveform.numel() == 0:
            return None, "empty clip"
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                embedding = self._inference({"waveform": waveform, "sample_rate": sample_rate})
            except Exception as e:  # defensive — a bad clip should never crash the whole run
                return None, f"{type(e).__name__}: {e}"
        warning_text = "; ".join(str(w.message) for w in caught) or None
        return np.asarray(embedding), warning_text

    def similarity_to_reference(self, waveform: torch.Tensor, sample_rate: int) -> tuple[Optional[float], Optional[str]]:
        """Returns (similarity, warning_or_reason). similarity is None if the
        clip could not be embedded at all — that is NOT the same as a low
        similarity score, and must be surfaced as "unknown", not as "OTHER"."""
        embedding, warning = self._embed(waveform, sample_rate)
        if embedding is None:
            return None, warning
        return _cosine_similarity(embedding, self._reference_embedding), warning


def _slice_waveform(waveform: torch.Tensor, sample_rate: int, start: float, end: float) -> torch.Tensor:
    i0 = max(0, int(start * sample_rate))
    i1 = min(waveform.shape[-1], int(end * sample_rate))
    return waveform[:, i0:i1]


# ============================================================
# The decision rule: for each turn, is it DOCENT, OTHER, or ONZEKER?
# ============================================================
# In order, never falling through silently:
#   1. `uncertain_assignment == True` -> ONZEKER. This means the diarization's
#      OWN attribution of this stretch of audio to a speaker is already
#      shaky — a voice-identity comparison on top of an unreliable speaker
#      attribution isn't trustworthy evidence either way.
#   2. The turn is shorter than `min_clip_duration_seconds` -> ONZEKER. Short
#      clips gave unreliable similarity scores in
#      Experiments/speaker_recognition's own tests.
#   3. The embedding step itself fails or returns nothing usable -> ONZEKER.
#      Never silently treated as OTHER.
#   4. Otherwise: similarity is ALWAYS computed — including when
#      `overlap == True`. DOCENT if similarity >= threshold, else OTHER. This
#      is an explicit, configurable, EXPERIMENTAL threshold (see
#      config.DocentRecognitionConfig) — not a proven-reliable cutoff.
#   5. If `overlap == True`, the resulting DOCENT/OTHER label is still kept
#      (not downgraded to ONZEKER), but `docent_role_note` records that
#      overlap was flagged, as an explicit caution — the audio may contain a
#      second voice even though one speaker was dominant enough for the
#      embedding to still lean clearly one way. Verified by hand on
#      testaudio6_fragment: several overlap=True turns do have one clearly
#      dominant, recognizable voice, so treating overlap as an automatic hard
#      block discarded usable evidence.
#
# `uncertain_assignment` (rule 1) blocks recognition outright; `overlap`
# (rule 5) no longer does — it becomes a caution alongside a computed label
# instead. `uncertain_assignment` is preprocessing.py's signal that the
# speaker ID itself is in doubt (wrong speaker entirely is possible);
# `overlap` only means a second voice is ALSO present, which doesn't rule
# out the dominant voice still being identifiable.
#
# Never re-merges or re-groups turns based on docent_role: turns keep their
# original speaker identity (`speaker`/`speaker_raw`) and grouping exactly as
# preprocessing.py produced them. Two different OTHER_SPEAKER_n turns are
# never combined just because both end up with docent_role="OTHER".
#
# Why word-level attribution (Experiments/word_level_speaker_attribution) is
# NOT invoked here: that experiment showed word-level speaker attribution CAN
# split a single ASR segment that mixes two speakers' words — but only when
# the underlying pyannote diarization turns themselves already contain the
# speaker-change boundary. It cannot invent a split the diarization never
# found, and preprocessing.py's own merge rule already guarantees any turn
# with overlap=True or uncertain_assignment=True stays a singleton, never
# silently merged into a longer, falsely-homogeneous turn. So by the time a
# turn reaches this module, whether it MIGHT contain a second voice or has a
# shaky speaker attribution is already known per-turn — re-running word-level
# attribution here would duplicate that check without resolving anything
# these flags don't already surface.
#
# What this route does NOT solve: if pyannote's diarization itself merges two
# different speakers into one turn WITHOUT flagging overlap/uncertain (a
# known failure mode — documented for testaudio2_fragment in
# word_level_speaker_attribution/comparison/results.md, where the diarization
# found no turn boundary at all), this module has no way to detect that from
# turn-level flags alone, and will embed the blended clip as if it were one
# speaker. That is a genuine, known gap.
#
# Update: diarization.py heeft nu een stap 2b (speaker_boundaries.py) die dit
# gat gedeeltelijk dicht: elk stuk spraak tussen Whisper-/pyannote-grenzen
# wordt met een stem-embedding gecontroleerd, en een stuk dat duidelijk niet
# bij "zijn" spreker past wordt omgelabeld (of, als het nergens bij past,
# een nieuwe spreker of uncertain_assignment). Wat er dan nog misgaat — een
# wissel midden in één Whisper-segment zonder pauze — blijft een bekend gat.

def assign_docent_roles(
    turns: list[SpeakerTurn],
    waveform: torch.Tensor,
    sample_rate: int,
    recognizer: DocentReferenceRecognizer,
    config: DocentRecognitionConfig,
) -> list[SpeakerTurn]:
    """Return a NEW list of turns with docent_role fields filled in. Input untouched."""
    out: list[SpeakerTurn] = []
    reference_audio = str(config.reference_audio)

    def _finish(turn: SpeakerTurn, role: str, similarity: Optional[float], note: Optional[str]) -> SpeakerTurn:
        return turn.model_copy(update={
            "docent_role": role,
            "docent_role_similarity": round(similarity, 4) if similarity is not None else None,
            "docent_role_threshold": config.similarity_threshold,
            "docent_role_reference_audio": reference_audio,
            "docent_role_note": note,
        })

    for turn in turns:
        if turn.uncertain_assignment:
            out.append(_finish(
                turn, ROLE_ONZEKER, None,
                "turn zelf is uncertain_assignment (diarization-onzekerheid over de sprekertoewijzing) — "
                "docentrol niet betrouwbaar te bepalen op basis van dit spraakstuk",
            ))
            continue

        duration = turn.end - turn.start
        if duration < config.min_clip_duration_seconds:
            out.append(_finish(
                turn, ROLE_ONZEKER, None,
                f"spraakstuk te kort voor betrouwbare embedding ({duration:.2f}s < "
                f"{config.min_clip_duration_seconds}s)",
            ))
            continue

        clip = _slice_waveform(waveform, sample_rate, turn.start, turn.end)
        similarity, embed_warning = recognizer.similarity_to_reference(clip, sample_rate)
        if similarity is None:
            out.append(_finish(turn, ROLE_ONZEKER, None, f"embedding mislukt: {embed_warning}"))
            continue

        role = ROLE_DOCENT if similarity >= config.similarity_threshold else ROLE_OTHER
        note_parts = []
        if turn.overlap:
            note_parts.append(
                "let op: turn is overlap=True (mogelijk ook een tweede stem hoorbaar) — "
                "rol is gebaseerd op de dominante stem in dit spraakstuk en moet met enige "
                "voorzichtigheid geïnterpreteerd worden"
            )
        if embed_warning:
            note_parts.append(embed_warning)
        note = "; ".join(note_parts) or None
        out.append(_finish(turn, role, similarity, note))

    return out


def summarize_docent_roles(turns: list[SpeakerTurn]) -> dict:
    """Counts for the CLI printout / reproducibility record."""
    per_role: dict[str, int] = {}
    for t in turns:
        key = t.docent_role or "NOT_EVALUATED"
        per_role[key] = per_role.get(key, 0) + 1
    return {"turns": len(turns), "per_role": per_role}


# ============================================================
# CLI: ProcessedTranscript JSON + reference audio -> enriched ProcessedTranscript JSON
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Stap 4: attach docent_role to a ProcessedTranscript's turns")
    parser.add_argument("--processed", required=True, help="Path to a Phase 3 ProcessedTranscript JSON")
    parser.add_argument("--reference", required=True, help="Path to the teacher's reference audio (mp3/wav)")
    parser.add_argument("--audio", default=None, help="Override fragment audio path (default: audio_file in the ProcessedTranscript)")
    parser.add_argument("--threshold", type=float, default=None, help="Override DocentRecognitionConfig.similarity_threshold (experimental)")
    parser.add_argument("--min-duration", type=float, default=None, help="Override DocentRecognitionConfig.min_clip_duration_seconds")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--out", default=None, help="Output JSON path (default: Data-local/processed/docent_recognition/)")
    parser.add_argument("--force", action="store_true", help="Redo wav conversion and overwrite output")
    args = parser.parse_args()

    processed_path = Path(args.processed)
    if not processed_path.exists():
        sys.exit(f"ProcessedTranscript JSON not found: {processed_path}")
    processed = ProcessedTranscript.model_validate_json(processed_path.read_text(encoding="utf-8"))

    reference_path = Path(args.reference)
    if not reference_path.exists():
        sys.exit(f"Reference audio not found: {reference_path}")

    audio_path = Path(args.audio) if args.audio else Path(processed.audio_file)
    if not audio_path.exists():
        sys.exit(
            f"Fragment audio not found: {audio_path}\n"
            f"(from {'--audio' if args.audio else 'ProcessedTranscript.audio_file'}). "
            f"Pass --audio explicitly if the transcript's recorded path has moved."
        )

    config = DocentRecognitionConfig(reference_audio=str(reference_path), device=args.device)
    if args.threshold is not None:
        config.similarity_threshold = args.threshold
    if args.min_duration is not None:
        config.min_clip_duration_seconds = args.min_duration

    DOCENT_RECOGNITION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else DOCENT_RECOGNITION_OUTPUT_DIR / f"{processed_path.stem}_docent_roles.json"
    if out_path.exists() and not args.force:
        sys.exit(f"{out_path} already exists. Use --force to overwrite.")

    # Reuse the diarization step's wav cache dir for the fragment audio (same
    # audio, likely already converted there); the reference gets its own
    # cache dir since it isn't tied to any one fragment.
    fragment_wav = to_wav(audio_path, DIARIZATION_OUTPUT_DIR, args.force)
    reference_wav = to_wav(reference_path, DOCENT_RECOGNITION_OUTPUT_DIR, args.force)

    print(f"Loading docent recognition model '{config.embedding_model}' on {config.device} ...")
    t0 = time.time()
    recognizer = DocentReferenceRecognizer(reference_wav, config.embedding_model, device=config.device)
    model_load_seconds = round(time.time() - t0, 2)
    if recognizer.reference_warning:
        print(f"  (warning while embedding reference clip: {recognizer.reference_warning})")

    print(f"Comparing {len(processed.turns)} turns in {processed_path.name} against {reference_path.name} ...")
    fragment_waveform, fragment_sr = _load_wav_waveform(fragment_wav)

    t0 = time.time()
    new_turns = assign_docent_roles(processed.turns, fragment_waveform, fragment_sr, recognizer, config)
    assignment_seconds = round(time.time() - t0, 2)

    stats = summarize_docent_roles(new_turns)

    docent_recognition_meta = {
        "embedding_model": config.embedding_model,
        "reference_audio": str(reference_path),
        "similarity_threshold": config.similarity_threshold,
        "threshold_status": "experimentele instelling, niet gevalideerd als bewezen betrouwbaar criterium "
                             "(zie Experiments/speaker_recognition/comparison/results.md)",
        "min_clip_duration_seconds": config.min_clip_duration_seconds,
        "device": config.device,
        "model_load_seconds": model_load_seconds,
        "assignment_seconds": assignment_seconds,
        "source_processed_transcript": str(processed_path),
        "fragment_audio": str(audio_path),
        "summary": stats,
    }

    enriched = processed.model_copy(update={"turns": new_turns, "docent_recognition": docent_recognition_meta})
    out_path.write_text(enriched.model_dump_json(indent=2), encoding="utf-8")

    print("\n--- docent recognition summary ---")
    print(f"per role          : {stats['per_role']}")
    print(f"threshold (exp.)  : {config.similarity_threshold}")
    print(f"min clip duration : {config.min_clip_duration_seconds}s")
    print(f"model load        : {model_load_seconds}s   assignment: {assignment_seconds}s")
    print(f"\nwritten to {out_path}")


if __name__ == "__main__":
    main()
