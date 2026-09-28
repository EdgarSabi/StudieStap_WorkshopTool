"""
Decide `docent_role` per speaker turn. Pure orchestration + an explicit,
explainable decision rule — no ML lives here (see backend.py).

Decision rule, in order (never falls through silently):
  1. `uncertain_assignment == True` -> ONZEKER. This means the diarization's
     OWN attribution of this stretch of audio to a speaker is already
     shaky — a speaker-identity embedding computed on top of an unreliable
     speaker attribution isn't trustworthy evidence either way, regardless
     of what the embedding itself would say.
  2. The turn is shorter than `min_clip_duration_seconds` -> ONZEKER
     ("clip_too_short"). Short clips gave unreliable similarity scores in
     Experiments/speaker_recognition's own tests.
  3. The embedding step itself fails or returns nothing usable -> ONZEKER
     ("embedding_failed: ..."). Never silently treated as OTHER.
  4. Otherwise: similarity is ALWAYS computed — including when
     `overlap == True`. DOCENT if similarity >= threshold, else OTHER. This
     is an explicit, configurable, EXPERIMENTAL threshold (see
     config.DocentRecognitionConfig) — not a proven-reliable cutoff.
  5. If `overlap == True`, the resulting DOCENT/OTHER label is still
     returned (not downgraded to ONZEKER), but `docent_role_note` records
     that overlap was flagged, as an explicit caution — the audio may
     contain a second voice even though one speaker was dominant enough for
     the embedding to still lean clearly one way. Verified by hand on
     testaudio6_fragment: several overlap=True turns do have one clearly
     dominant, recognizable voice, so treating overlap as an automatic hard
     block (the previous rule) discarded usable evidence.

Changed 2026: `uncertain_assignment` (rule 1) blocks recognition outright,
`overlap` (rule 5) no longer does — it becomes a caution alongside a
computed label instead. `uncertain_assignment` is preprocessing/turns.py's
signal that the speaker ID itself is in doubt (wrong speaker entirely is
possible); `overlap` only means a second voice is ALSO present, which
doesn't rule out the dominant voice still being identifiable — that
distinction is why the two are no longer treated the same way here.

Never re-merges or re-groups turns based on docent_role: turns keep their
original speaker identity (`speaker`/`speaker_raw`) and grouping exactly as
preprocessing/turns.py produced them. Two different OTHER_SPEAKER_n turns
are never combined just because both end up with docent_role="OTHER".
"""
from pathlib import Path
from typing import Optional

import torch

from config import DocentRecognitionConfig
from models.processed import SpeakerTurn
from .backend import DocentReferenceRecognizer

ROLE_DOCENT = "DOCENT"
ROLE_OTHER = "OTHER"
ROLE_ONZEKER = "ONZEKER"


def _slice_waveform(waveform: torch.Tensor, sample_rate: int, start: float, end: float) -> torch.Tensor:
    i0 = max(0, int(start * sample_rate))
    i1 = min(waveform.shape[-1], int(end * sample_rate))
    return waveform[:, i0:i1]


def assign_docent_roles(
    turns: list[SpeakerTurn],
    waveform: torch.Tensor,
    sample_rate: int,
    recognizer: DocentReferenceRecognizer,
    config: DocentRecognitionConfig,
) -> list[SpeakerTurn]:
    """Return a NEW list of turns with docent_role fields filled in. Input
    untouched (same convention as diarization/assign.py::assign_speakers)."""
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

        # overlap does NOT block recognition here — it's recorded as a
        # caution alongside whatever label the similarity produces, not a
        # reason to withhold one. See module docstring, rule 5.
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


# --- Why word-level attribution (Experiments/word_level_speaker_attribution)
# is NOT invoked here ---
#
# That experiment showed word-level speaker attribution CAN split a single
# ASR segment that mixes two speakers' words — but only when the underlying
# pyannote diarization turns themselves already contain the speaker-change
# boundary. It cannot invent a split the diarization never found, and
# preprocessing/turns.py's own merge rule already guarantees any turn with
# overlap=True or uncertain_assignment=True stays a singleton, never
# silently merged into a longer, falsely-homogeneous turn. So by the time a
# turn reaches this module, whether it MIGHT contain a second voice
# (overlap) or has a shaky speaker attribution (uncertain_assignment) is
# already known per-turn — re-running word-level attribution here would
# duplicate that check (a second, parallel pipeline) without resolving
# anything these flags don't already surface. Rule 1 still hard-blocks on
# uncertain_assignment; rule 5 now lets a clip with overlap=True still be
# embedded, on the basis that "possibly two voices present" and "the
# dominant voice is unidentifiable" are not the same thing (verified by
# hand on testaudio6_fragment — see the module docstring).
#
# What this route does NOT solve: if pyannote's diarization itself merges
# two different speakers into one turn WITHOUT flagging overlap/uncertain
# (the exact failure mode documented for testaudio2_fragment in
# word_level_speaker_attribution/comparison/results.md — the diarization
# found no turn boundary at all, so assign_speakers() had nothing to flag
# either), this module has no way to detect that from turn-level flags
# alone, and will embed the blended clip as if it were one speaker. That is
# a genuine, known gap — see run_docent_recognition.py's module docstring
# and the project-level report for how it was verified on the three test
# fragments.
