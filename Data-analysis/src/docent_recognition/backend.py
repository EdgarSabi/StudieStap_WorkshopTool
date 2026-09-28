"""
pyannote WeSpeaker embedding backend for docent recognition.

This is the ONLY module in docent_recognition/ that imports pyannote —
mirrors diarization/pyannote_backend.py's own "one module owns the ML
dependency" split. Ported from (not imported from — Data-analysis/src must
never depend on Experiments/) the logic already validated in
Experiments/speaker_recognition/pyannote_embeddings/test_teacher_recognition.py:
same model, same embed()/warning-capture behaviour, same cosine similarity.

Reuses diarization.pyannote_backend._load_wav_waveform for wav decoding
instead of duplicating that logic — it already handles the same 16-bit PCM
mono/stereo cases this needs.
"""
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import torch

from config import get_hf_token
from diarization.pyannote_backend import _load_wav_waveform


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a).reshape(-1).astype(np.float64)
    b = np.asarray(b).reshape(-1).astype(np.float64)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


class DocentReferenceRecognizer:
    """Loads the WeSpeaker embedding model once, embeds the reference clip
    once, and thereafter compares any audio clip's embedding against it via
    cosine similarity. The similarity is a raw cosine value in [-1, 1] — see
    models/processed.py's SpeakerTurn docstring: it is NOT a calibrated
    probability, and callers (docent_recognition/assign.py) must not present
    it as one.
    """

    def __init__(self, reference_wav_path: Path, model_name: str, device: str = "cpu"):
        from pyannote.audio import Inference, Model

        token = get_hf_token()
        if not token:
            raise RuntimeError(
                "No HuggingFace token found. Put HF_TOKEN=... in <repo-root>/.env "
                "(same setup as diarization/pyannote_backend.py)."
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
