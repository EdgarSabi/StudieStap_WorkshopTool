"""
Reproduceert de cijfers uit ../README.md ZONDER pyannote.audio of HF-token:
pyannote 3.1 wordt nagebouwd met dezelfde gewichten via ONNX (zie
pyannote_repro.py), daarna draait src/speaker_boundaries.py (ongewijzigd)
erop, en alles wordt gescoord tegen de handmatige ground truth.

Eenmalig (eigen venv, los van de pipeline):
    pip install onnxruntime torch torchaudio scipy numpy pydantic
    python reproduce_local_results.py --download

Daarna:
    python reproduce_local_results.py

Whisper-grenzen: zonder transcript gebruikt dit script de grenzen uit de
ground-truth-CSV (die zijn oorspronkelijk uit Whisper voorgevuld), met ±0,15 s
ruis zodat ze niet "te perfect" zijn. Dat is een benadering van de echte
pipeline, die de Whisper-segmenten zelf gebruikt.
"""
import argparse
import subprocess
import sys
import tarfile
import urllib.request
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[3] / "src"
GT_DIR = HERE.parents[1] / "hyperparameter_tuning"
MODELS = HERE / "models"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(GT_DIR))
sys.path.insert(0, str(HERE))

SEG_URL = ("https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/"
           "sherpa-onnx-pyannote-segmentation-3-0.tar.bz2")
EMB_URL = ("https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/"
           "wespeaker_en_voxceleb_resnet34_LM.onnx")


def download():
    MODELS.mkdir(exist_ok=True)
    emb = MODELS / "wespeaker_en_voxceleb_resnet34_LM.onnx"
    if not emb.exists():
        print("download", EMB_URL); urllib.request.urlretrieve(EMB_URL, emb)
    seg_dir = MODELS / "sherpa-onnx-pyannote-segmentation-3-0"
    if not seg_dir.exists():
        tar = MODELS / "seg.tar.bz2"
        print("download", SEG_URL); urllib.request.urlretrieve(SEG_URL, tar)
        with tarfile.open(tar) as t:
            t.extractall(MODELS)
        tar.unlink()


def load_audio(fragment: str):
    mp3 = SRC / "test-files" / f"{fragment}.mp3"
    wav = MODELS / f"{fragment}_16k_mono.wav"
    if not wav.exists():
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(mp3), "-ac", "1", "-ar", "16000", str(wav)], check=True)
    with wave.open(str(wav)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768, w.getframerate()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--fragments", nargs="+", default=["testaudio2_fragment", "testaudio4_fragment"])
    ap.add_argument("--min-cluster-size", type=int, nargs="+", default=[12, 8])
    args = ap.parse_args()
    if args.download:
        download()

    from config import BoundaryRefinementConfig
    from speaker_boundaries import refine_speaker_boundaries
    from evaluate_min_cluster_size import load_ground_truth, score
    import pyannote_repro as pr
    from wespeaker_onnx import WeSpeakerOnnxEmbedder

    emb = WeSpeakerOnnxEmbedder()
    for fragment in args.fragments:
        audio, sr = load_audio(fragment)
        rows = load_ground_truth(fragment)
        rng = np.random.default_rng(1)
        asr = [(s + rng.uniform(-.15, .15), e + rng.uniform(-.15, .15)) for s, e, _ in rows]
        for mcs in args.min_cluster_size:
            turns = pr.diarize(audio, sr, min_cluster_size=mcs)
            res = refine_speaker_boundaries(audio, sr, turns, emb, BoundaryRefinementConfig(), asr_spans=asr)
            for tag, tt in [("pyannote (nabouw)", turns), ("+ refinement", res.turns)]:
                s = score(rows, tt)
                per = ", ".join(f"{k[-1]}={v['covered_pct']}" for k, v in s["per_gt_speaker"].items())
                print(f"{fragment:<20} mcs={mcs:<3} {tag:<18} {s['overall_correct_pct']:5.1f}%  "
                      f"sprekers={s['pyannote_speakers_found']}  {per}")
            merged = {k: v for k, v in res.merge_map.items() if k != v}
            print(f"{'':<28} samengevoegd={merged or '-'}  nieuw={[n['label'] for n in res.new_speakers] or '-'}  "
                  f"omgelabeld={res.stats['relabeled_seconds']}s")


if __name__ == "__main__":
    main()
