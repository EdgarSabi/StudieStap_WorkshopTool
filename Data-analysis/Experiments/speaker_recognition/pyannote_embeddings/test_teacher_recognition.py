"""
Experiment 1 — pyannote speaker embeddings: DOCENT vs OTHER.

Exploratory script, not production code. Does not touch or import the
Data-analysis/src pipeline; it only reuses the diarized transcript JSON +
16 kHz mono wav files that pipeline already wrote to
Data-local/processed/diarization/ (see _common.py).

Model
-----
pyannote/wespeaker-voxceleb-resnet34-LM — the speaker-embedding model that
pyannote/speaker-diarization-3.1 already uses internally. It was already
downloaded to the local HF cache by earlier diarization runs, so this does
not require accepting a new gated-model licence (only the HF_TOKEN already
in <repo-root>/.env, same as the rest of the pipeline).

Method
------
1. One embedding of the teacher reference clip (testdocent.mp3).
2. One embedding per existing ASR/diarization chunk in testaudio1_fragment,
   testaudio2_fragment, testaudio5_fragment.
3. cosine_similarity(chunk_embedding, teacher_embedding) per chunk.
4. Print the similarity distribution — no threshold is hardcoded.
5. Optionally apply a threshold (--threshold) to also print a DOCENT/OTHER
   prediction per chunk. Omit it on the first run to inspect the
   distribution before picking one (see comparison/results.md for what was
   chosen and why).

Run (from anywhere; use the project's own venv):
    Data-analysis\\src\\.venv\\Scripts\\python.exe Data-analysis\\Experiments\\speaker_recognition\\pyannote_embeddings\\test_teacher_recognition.py
    Data-analysis\\src\\.venv\\Scripts\\python.exe Data-analysis\\Experiments\\speaker_recognition\\pyannote_embeddings\\test_teacher_recognition.py --threshold 0.45
"""
import argparse
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _common as common  # noqa: E402

import numpy as np  # noqa: E402
import torch  # noqa: E402


def load_inference():
    from pyannote.audio import Inference, Model

    token = common.get_hf_token()
    if not token:
        sys.exit(
            "No HuggingFace token found. Put HF_TOKEN=... in <repo-root>/.env "
            "(same setup as Data-analysis/src/diarization/pyannote_backend.py)."
        )
    model = Model.from_pretrained("pyannote/wespeaker-voxceleb-resnet34-LM", token=token)
    return Inference(model, window="whole")


def embed(inference, samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray | None, str | None]:
    """Returns (embedding, warning_text). embedding is None if the clip is
    too short/empty to embed at all."""
    if len(samples) == 0:
        return None, "empty clip"
    waveform = torch.from_numpy(samples).float().unsqueeze(0)  # (1, n_samples)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            embedding = inference({"waveform": waveform, "sample_rate": sample_rate})
        except Exception as e:  # pragma: no cover - defensive, see results.md for when this triggers
            return None, f"{type(e).__name__}: {e}"
    warning_text = "; ".join(str(w.message) for w in caught) or None
    return np.asarray(embedding), warning_text


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Cosine-similarity threshold for DOCENT vs OTHER. Omit to just inspect the distribution first.",
    )
    args = parser.parse_args()

    print("Loading pyannote embedding model (pyannote/wespeaker-voxceleb-resnet34-LM)...")
    inference = load_inference()

    print(f"Teacher reference: {common.TEACHER_REF_AUDIO}")
    ref_wav = common.teacher_reference_wav()
    ref_samples, ref_sr = common.load_wav_mono(ref_wav)
    print(f"  duration: {len(ref_samples) / ref_sr:.2f}s")
    teacher_embedding, ref_warning = embed(inference, ref_samples, ref_sr)
    if teacher_embedding is None:
        sys.exit(f"Could not embed the teacher reference clip: {ref_warning}")
    if ref_warning:
        print(f"  (warning while embedding reference: {ref_warning})")

    rows = []
    for fragment in common.EVAL_FRAGMENTS:
        wav_path = common.fragment_wav_path(fragment)
        samples, sr = common.load_wav_mono(wav_path)
        chunks = common.load_chunks(fragment)
        print(f"\n{fragment}: {len(chunks)} chunks")
        for chunk in chunks:
            clip = common.slice_samples(samples, sr, chunk.start, chunk.end)
            duration = len(clip) / sr if sr else 0.0
            chunk_embedding, warn = embed(inference, clip, sr)
            similarity = common.cosine_similarity(chunk_embedding, teacher_embedding) if chunk_embedding is not None else None
            prediction = None
            if similarity is not None and args.threshold is not None:
                prediction = "DOCENT" if similarity >= args.threshold else "OTHER"
            rows.append(
                {
                    "fragment": fragment,
                    "chunk_index": chunk.index,
                    "start": round(chunk.start, 2),
                    "end": round(chunk.end, 2),
                    "duration_s": round(duration, 3),
                    "duration_bucket": common.duration_bucket(duration),
                    "text": chunk.text,
                    "pipeline_speaker": chunk.pipeline_speaker,
                    "similarity": round(similarity, 4) if similarity is not None else None,
                    "prediction": prediction,
                    "warning": warn,
                }
            )
            sim_str = f"{similarity:.3f}" if similarity is not None else "  n/a"
            flag = "  <-- " + warn if warn else ""
            print(f"  [{chunk.start:6.2f}-{chunk.end:6.2f}] ({duration:4.2f}s) sim={sim_str}  {chunk.text[:55]!r}{flag}")

    out_path = common.OUTPUT_DIR / "pyannote_teacher_similarity.csv"
    common.write_csv(rows, out_path)

    sims = [r["similarity"] for r in rows if r["similarity"] is not None]
    common.print_distribution("pyannote (all chunks)", sims)
    for bucket in ("<0.5s", "0.5-1s", ">1s"):
        bucket_sims = [r["similarity"] for r in rows if r["similarity"] is not None and r["duration_bucket"] == bucket]
        common.print_distribution(f"pyannote (duration {bucket})", bucket_sims)


if __name__ == "__main__":
    main()
