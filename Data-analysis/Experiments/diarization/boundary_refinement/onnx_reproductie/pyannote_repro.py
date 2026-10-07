"""Nabouw van pyannote/speaker-diarization-3.1 met DEZELFDE modelgewichten
(segmentation-3.0 + wespeaker-voxceleb-resnet34-LM), maar via ONNX in plaats
van pyannote.audio. Alleen bedoeld om de refinement te kunnen testen in een
omgeving zonder HuggingFace-toegang — niet voor productie.

Stappen zoals pyannote 3.1: segmentatie in vensters van 10 s (stap 1 s,
powerset -> max 3 lokale sprekers), één embedding per (venster, lokale
spreker) zonder overlap-frames, centroid-agglomeratieve clustering
(threshold 0.7046, min_cluster_size 12 -> kleine clusters naar dichtstbijzijnde
grote), toewijzen aan centroids, en reconstructie met het geschatte aantal
sprekers per frame. Benadering: de embedding gebruikt de actieve samples
i.p.v. pyannote's gewogen pooling; daardoor kunnen uitkomsten iets afwijken
(zie ../README.md voor de vergelijking met de echte pyannote-uitkomsten)."""
import numpy as np
import onnxruntime as ort
from pathlib import Path
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import cdist

from wespeaker_onnx import WeSpeakerOnnxEmbedder

HERE = Path(__file__).parent
_seg = ort.InferenceSession(str(HERE / "models" / "sherpa-onnx-pyannote-segmentation-3-0" / "model.onnx"))
_meta = _seg.get_modelmeta().custom_metadata_map
WIN = int(_meta["window_size"])          # 160000
SHIFT = int(0.1 * WIN)                   # 1 s
RF_SHIFT = int(_meta["receptive_field_shift"])
RF_SIZE = int(_meta["receptive_field_size"])
EMB = WeSpeakerOnnxEmbedder()

def _mapping():
    m = np.zeros((7, 3)); k = 1
    for j in range(3): m[k, j] = 1; k += 1
    for j in range(3):
        for l in range(j + 1, 3): m[k, j] = m[k, l] = 1; k += 1
    return m
MAP = _mapping()

def segment(audio):
    n = max(1, int(np.ceil((len(audio) - WIN) / SHIFT)) + 1)
    pad = (n - 1) * SHIFT + WIN - len(audio)
    a = np.pad(audio, (0, max(0, pad)))
    chunks = np.stack([a[i * SHIFT:i * SHIFT + WIN] for i in range(n)]).astype(np.float32)
    ys = []
    for b in range(0, n, 16):
        ys.append(_seg.run(None, {_seg.get_inputs()[0].name: chunks[b:b + 16][:, None, :]})[0])
    y = np.vstack(ys)
    return MAP[np.argmax(y, -1)], chunks  # (n, F, 3)

def diarize(audio, sr=16000, threshold=0.7045654963945799, min_cluster_size=12, exclude_overlap=True, constrained=False, return_internals=False):
    labels, chunks = segment(audio)
    n, F, S = labels.shape
    frame_dur = WIN / sr / F
    # embeddings per (chunk, local speaker)
    clips, pairs = [], []
    for c in range(n):
        lab = labels[c]
        clean = lab * (lab.sum(-1, keepdims=True) < 2)
        for s in range(S):
            m = clean[:, s] if (exclude_overlap and clean[:, s].sum() >= 10) else lab[:, s]
            if lab[:, s].sum() == 0:
                continue
            idx = np.repeat(m.astype(bool), int(np.ceil(WIN / F)))[:WIN]
            x = chunks[c][idx[:len(chunks[c])]]
            clips.append(x); pairs.append((c, s))
    E = EMB.embed(clips, sr)
    ok = np.all(np.isfinite(E), 1)
    # train = active & valid
    En = E[ok] / np.linalg.norm(E[ok], axis=1, keepdims=True)
    tr_pairs = [p for p, o in zip(pairs, ok) if o]
    mcs = min(min_cluster_size, max(1, round(0.1 * len(En))))
    if len(En) >= 2:
        cl = fcluster(linkage(En, method="centroid", metric="euclidean"), threshold, criterion="distance") - 1
    else:
        cl = np.zeros(len(En), int)
    u, cnt = np.unique(cl, return_counts=True)
    large = u[cnt >= mcs]
    if len(large) == 0:
        cl[:] = 0; large = np.array([0])
    small = u[cnt < mcs]
    if len(small):
        lc = np.vstack([En[cl == k].mean(0) for k in large]); sc = np.vstack([En[cl == k].mean(0) for k in small])
        for si, li in enumerate(np.argmin(cdist(lc, sc, "cosine"), axis=0)):
            cl[cl == small[si]] = large[li]
    _, cl = np.unique(cl, return_inverse=True)
    K = cl.max() + 1
    cent = np.vstack([En[cl == k].mean(0) for k in range(K)])
    # assign every (chunk, speaker) embedding to closest centroid
    hard = -np.ones((n, S), int)
    allE = np.where(ok[:, None], E, 0); allE = allE / np.maximum(np.linalg.norm(allE, axis=1, keepdims=True), 1e-9)
    sims = allE @ (cent / np.linalg.norm(cent, axis=1, keepdims=True)).T
    if constrained:
        from scipy.optimize import linear_sum_assignment
        soft = np.full((n, S, K), -9.0)
        for (c, s), o, row in zip(pairs, ok, sims):
            if o: soft[c, s] = row
        for c in range(n):
            rs, ks = linear_sum_assignment(soft[c], maximize=True)
            for s_, k_ in zip(rs, ks):
                if soft[c, s_, 0] > -9: hard[c, s_] = k_
            for s_ in range(S):
                if hard[c, s_] == -1 and soft[c, s_, 0] > -9: hard[c, s_] = int(np.argmax(soft[c, s_]))
    else:
        for (c, s), o, row in zip(pairs, ok, sims):
            hard[c, s] = int(np.argmax(row)) if o else -2
    # reconstruct: clustered segmentation, aggregate, top-count
    total_frames = int((WIN + (n - 1) * SHIFT) / RF_SHIFT) + 1
    act = np.zeros((total_frames, K)); cntf = np.zeros(total_frames); spk = np.zeros(total_frames)
    for c in range(n):
        st = int(round(c * SHIFT / RF_SHIFT)); en = st + F
        cs = np.zeros((F, K))
        for s in range(S):
            if hard[c, s] >= 0:
                cs[:, hard[c, s]] = np.maximum(cs[:, hard[c, s]], labels[c, :, s])
        act[st:en] += cs; cntf[st:en] += 1; spk[st:en] += labels[c].sum(-1)
    act /= np.maximum(cntf, 1)[:, None]
    count = np.rint(spk / np.maximum(cntf, 1)).astype(int)
    out = np.zeros_like(act, dtype=bool)
    for f in range(total_frames):
        if count[f] > 0:
            top = np.argsort(-act[f])[:count[f]]
            out[f, top] = True
    dur = len(audio) / sr
    turns = []
    step = RF_SHIFT / sr
    off = RF_SIZE / sr / 2
    from diarization import SpeakerTurn
    for k in range(K):
        f = 0
        while f < total_frames:
            if out[f, k]:
                g = f
                while g < total_frames and out[g, k]: g += 1
                a = min(dur, f * step + off - step / 2); b = min(dur, g * step + off - step / 2)
                if b > a: turns.append(SpeakerTurn(round(a, 3), round(b, 3), f"SPEAKER_{k:02d}"))
                f = g
            else:
                f += 1
    turns.sort(key=lambda t: t.start)
    if return_internals:
        return turns, dict(labels=labels, hard=hard, pairs=pairs, E=E, ok=ok, cent=cent, sims=sims, cl=cl)
    return turns
