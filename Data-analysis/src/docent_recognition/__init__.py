"""
Phase 4: docent recognition as a separate layer on top of preprocessing.

Compares each speaker turn's own audio against a teacher reference recording
(pyannote WeSpeaker embeddings — the same model already used, read-only, in
Experiments/speaker_recognition/) to decide `docent_role` independently of
the diarization identity/talk-time heuristic. See models/processed.py's
SpeakerTurn docstring for why `speaker` (MAIN_SPEAKER/OTHER_SPEAKER_n) and
`docent_role` (DOCENT/OTHER/ONZEKER) are kept as two separate fields.

Design notes (mirrors diarization/'s own split):
- `backend.DocentReferenceRecognizer` is the ONLY thing in this package that
  imports pyannote. It loads the embedding model once and turns an audio
  clip into a similarity score against the reference (or None + a reason).
- `assign.assign_docent_roles` is pure orchestration + decision logic: given
  turns, a waveform, and a recognizer, it decides a role per turn. No ML
  happens in this module directly.
"""
from .backend import DocentReferenceRecognizer
from .assign import assign_docent_roles, summarize_docent_roles

__all__ = ["DocentReferenceRecognizer", "assign_docent_roles", "summarize_docent_roles"]
