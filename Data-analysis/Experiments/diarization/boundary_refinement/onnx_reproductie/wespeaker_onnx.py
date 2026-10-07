import numpy as np, torch, torchaudio, onnxruntime as ort
from pathlib import Path
_S = ort.InferenceSession(str(Path(__file__).parent / "models" / "wespeaker_en_voxceleb_resnet34_LM.onnx"))
class WeSpeakerOnnxEmbedder:
    """Zelfde gewichten als pyannote/wespeaker-voxceleb-resnet34-LM (ONNX-export
    van WeSpeaker, via de sherpa-onnx GitHub-release). Kaldi-fbank (80 mel,
    25/10 ms) + mean-normalisatie, zoals WeSpeaker/pyannote dat doen.
    Implementeert dezelfde embed(clips, sample_rate)-interface als
    src/speaker_boundaries.PyannoteWindowEmbedder."""
    def _feats(self, clip, sr):
        wf = torch.from_numpy(np.asarray(clip, dtype=np.float32) * 32768.0)[None]
        f = torchaudio.compliance.kaldi.fbank(wf, num_mel_bins=80, frame_length=25, frame_shift=10,
                                              dither=0.0, sample_frequency=sr, window_type="hamming", use_energy=False)
        return (f - f.mean(dim=0, keepdim=True)).numpy()
    def embed(self, clips, sample_rate):
        out = []
        groups = {}
        for i, c in enumerate(clips):
            if len(c) < 0.25 * sample_rate:
                continue
            groups.setdefault(len(c), []).append(i)
        res = [None] * len(clips)
        for L, idx in groups.items():
            for b in range(0, len(idx), 64):
                ch = idx[b:b+64]
                F = np.stack([self._feats(clips[i], sample_rate) for i in ch])
                E = _S.run(None, {"feats": F})[0]
                for i, e in zip(ch, E): res[i] = e
        return np.vstack([r if r is not None else np.full(256, np.nan) for r in res])
