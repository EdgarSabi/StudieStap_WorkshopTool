"""
Experiment 2 — SpeechBrain ECAPA-TDNN: DOCENT vs OTHER.

Exploratory script, not production code. Does not touch or import the
Data-analysis/src pipeline; it only reuses the diarized transcript JSON +
16 kHz mono wav files that pipeline already wrote to
Data-local/processed/diarization/ (see _common.py).

Uses EXACTLY the same chunks as the pyannote experiment (same
_common.load_chunks / fragment wav files), so the two are a fair comparison.

Model
-----
speechbrain/spkrec-ecapa-voxceleb — SpeechBrain's standard pretrained
ECAPA-TDNN speaker-recognition/verification model. Not gated; downloaded
straight from the HF Hub on first run and cached under
Data-local/processed/speaker_recognition/_sb_model_cache/ (kept inside the
gitignored Data-local tree, not next to the code).

Note: on Windows, SpeechBrain's default fetch strategy tries to create a
symlink into that cache dir, which needs a privilege this machine's account
doesn't have by default. We pass local_strategy=LocalStrategy.COPY to avoid
that (copies the file instead) — see fetching.py in the speechbrain package.

Method
------
Same as experiment 1: one teacher-reference embedding, one embedding per
evaluation chunk, cosine similarity between the two. No threshold is
hardcoded; the distribution is printed first.

Run (from anywhere; use the project's own venv):
    Data-analysis\\src\\.venv\\Scripts\\python.exe Data-analysis\\Experiments\\speaker_recognition\\speechbrain_ecapa\\test_teacher_recognition.py
    Data-analysis\\src\\.venv\\Scripts\\python.exe Data-analysis\\Experiments\\speaker_recognition\\speechbrain_ecapa\\test_teacher_recognition.py --threshold 0.35
"""
import argparse
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _common as common  # noqa: E402

import numpy as np  # noqa: E402
import torch  # noqa: E402

MODEL_CACHE_DIR = common.OUTPUT_DIR / "_sb_model_cache" / "spkrec-ecapa-voxceleb"


def load_classifier():
    from speechbrain.inference.speaker import EncoderClassifier
    from speechbrain.utils.fetching import LocalStrategy

    # Model isn't gated, so HF_TOKEN isn't required here — but if it's set
    # (same .env as the rest of the pipeline) huggingface_hub will pick it up
    # from the environment automatically and avoid anonymous rate limits.
    common.get_hf_token()  # side effect: loads <repo-root>/.env into os.environ if present
    return EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir=str(MODEL_CACHE_DIR),
        run_opts={"device": "cpu"},
        local_strategy=LocalStrategy.COPY,
    )


def embed(classifier, samples: np.ndarray) -> tuple[np.ndarray | None, str | None]:
    """Returns (embedding, warning_text). embedding is None if the clip is empty."""
    if len(samples) == 0:
        return None, "empty clip"
    waveform = torch.from_numpy(samples).float().unsqueeze(0)  # (1, n_samples)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            embedding = classifier.encode_batch(waveform)
        except Exception as e:  # pragma: no cover - defensive, see results.md for when this triggers
            return None, f"{type(e).__name__}: {e}"
    warning_text = "; ".join(str(w.message) for w in caught) or None
    return embedding.squeeze().detach().cpu().numpy(), warning_text


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Cosine-similarity threshold for DOCENT vs OTHER. Omit to just inspect the distribution first.",
    )
    args = parser.parse_args()

    print("Loading SpeechBrain ECAPA-TDNN model (speechbrain/spkrec-ecapa-voxceleb)...")
    classifier = load_classifier()

    print(f"Teacher reference: {common.TEACHER_REF_AUDIO}")
    ref_wav = common.teacher_reference_wav()
    ref_samples, ref_sr = common.load_wav_mono(ref_wav)
    print(f"  duration: {len(ref_samples) / ref_sr:.2f}s  (sample rate {ref_sr})")
    teacher_embedding, ref_warning = embed(classifier, ref_samples)
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
            chunk_embedding, warn = embed(classifier, clip)
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

    out_path = common.OUTPUT_DIR / "speechbrain_teacher_similarity.csv"
    common.write_csv(rows, out_path)

    sims = [r["similarity"] for r in rows if r["similarity"] is not None]
    common.print_distribution("speechbrain (all chunks)", sims)
    for bucket in ("<0.5s", "0.5-1s", ">1s"):
        bucket_sims = [r["similarity"] for r in rows if r["similarity"] is not None and r["duration_bucket"] == bucket]
        common.print_distribution(f"speechbrain (duration {bucket})", bucket_sims)


if __name__ == "__main__":
    main()
