"""
STAP 2b — Speaker-boundary refinement: pyannote's sprekerbeurten achteraf
controleren met stem-embeddings, per stukje spraak dat tussen twee
aannemelijke grenzen ligt.

Waarom deze stap bestaat
------------------------
Uit de experimenten (Experiments/diarization/hyperparameter_tuning,
Experiments/word_level_speaker_attribution) en uit een nabouw van de
pyannote-pipeline met dezelfde modelgewichten
(Experiments/diarization/boundary_refinement/README.md) bleek:

  * In testaudio2 hoort pyannote's SEGMENTATIEmodel tussen 9 en 17 s maar één
    stem, terwijl leerling B daar twee keer iets zegt. Geen
    clustering-instelling kan een wissel terugvinden die het segmentatiemodel
    nooit gezien heeft. Een embedding van precies dat Whisper-segment ("Met
    zijn vrouw.") lijkt echter nauwelijks op de docent (cosine ≈ 0,1 terwijl
    docent-stukken onderling ≈ 0,5–0,6 scoren).
  * Vaste schuivende vensters (1–2 s) werken slecht in klasopnames: beurten
    van ~1 s zijn normaal, dus een venster bevat bijna altijd ook de vorige
    of volgende spreker. Daarom werkt deze module met EENHEDEN die precies
    tussen grenzen liggen in plaats van met vaste vensters.
  * De docent (dichtbij de microfoon, veel spreektijd) klinkt heel
    consistent; leerlingen (ver weg, kort, rumoer) veel minder. Een
    leerling herken je daardoor betrouwbaarder aan "past NIET bij de docent"
    dan aan "lijkt op leerling X". De beslisregels hieronder zijn daarom
    per spreker relatief: hoe ver wijkt een stuk af van wat normaal is
    voor díe spreker.

Hoe het werkt
-------------
  1. EENHEDEN       De tijdlijn wordt geknipt op elke Whisper-segmentgrens
                    en elke pyannote-grens. Elk stuk met één pyannote-spreker
                    (of geen, maar wel hoorbare spraak binnen een
                    Whisper-segment) is een eenheid. Overlap-stukken worden
                    niet aangeraakt.
  2. PROFIELEN      Per spreker: een stemprofiel (duur-gewogen gemiddelde
                    embedding) en de verdeling van "hoe goed past een eigen
                    eenheid bij de rest" (leave-one-out, mediaan + MAD).
                    Eenheden die al duidelijk afwijken tellen niet mee, zodat
                    verkeerd toegewezen spraak het profiel niet vervuilt.
  3. SAMENVOEGEN    Twee clusters met dezelfde stem worden één spreker
                    (over-segmentatie). Criterium: passen de eenheden van
                    het kleinste cluster (mediaan) even goed bij het grote
                    als bij hun eigen cluster?
  4. HERTOEWIJZEN   Een eenheid die een uitschieter is voor haar eigen
                    spreker (z ≤ -outlier_z) én wél normaal past bij een
                    andere spreker, met duidelijk verschil, krijgt die andere
                    spreker. → gemiste sprekerwissels.
  5. SPLITSEN       Lange eenheden (≥ split_min_seconds) worden op stiltes
                    geprobeerd te splitsen: als de twee helften bij
                    verschillende sprekers horen (zelfde regel als 4), wordt
                    er geknipt. → wissels die Whisper én pyannote misten.
  6. NIEUWE STEM    Eenheden die bij NIEMAND passen (uitschieter voor elke
                    spreker), lang genoeg zijn en onderling op elkaar
                    lijken, worden een nieuwe spreker (REFINED_NEW_n).
                    → korte derde/vierde spreker die pyannote wegclusterde.
                    Past zo'n eenheid bij niemand en ook niet bij elkaar,
                    dan blijft het label staan maar wordt de eenheid als
                    onzeker gemarkeerd.
  7. ONZEKERHEID    Elke eenheid krijgt "duidelijk" of "onduidelijk" (past
                    slecht bij eigen spreker of past bijna even goed bij een
                    ander). Per beurt wordt `confidence` = aandeel duidelijke
                    spreektijd. assign_speakers() in diarization.py zet een
                    transcriptsegment op uncertain_assignment als dat te laag
                    is. Onzekerheid wordt doorgegeven, niet weggegokt.

Wat deze stap NIET doet
-----------------------
  * Geen audio-scheiding. Door elkaar praten blijft overlap.
  * Eenheden korter dan min_unit_seconds worden niet beoordeeld (te weinig
    audio voor een betrouwbare embedding) — die houden pyannote's label.
  * Alle drempels zijn EXPERIMENTEEL (BoundaryRefinementConfig). Ze zijn
    relatief (z-scores per spreker) en dus niet aan één model gebonden, maar
    alleen gecontroleerd op de beschikbare ground-truth-fragmenten. Draai
    Experiments/diarization/boundary_refinement/evaluate_refinement.py op
    nieuwe fragmenten.

De logica is pure numpy en werkt met elk object met een
`embed(clips, sample_rate)`-methode (zie WindowEmbedder), zodat de tests
zonder model of HF_TOKEN kunnen draaien (tests/test_speaker_boundaries.py).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Protocol, Sequence

import numpy as np

from config import BoundaryRefinementConfig, get_hf_token
from diarization import SpeakerTurn

FRAME = 0.1  # tijdresolutie in seconden
NEW_SPEAKER_PREFIX = "REFINED_NEW_"


# ============================================================
# Embedding-backends
# ============================================================

class WindowEmbedder(Protocol):
    def embed(self, clips: Sequence[np.ndarray], sample_rate: int) -> np.ndarray:
        """clips: lijst 1-D float32 arrays. Geeft (n_clips, dim) terug.
        Een rij met NaN betekent "niet te embedden" (bv. te kort)."""
        ...


class PyannoteWindowEmbedder:
    """WeSpeaker-embeddings via pyannote — hetzelfde model dat
    docent_recognition.py al gebruikt (en dat pyannote 3.1 intern voor zijn
    clustering gebruikt). Geen nieuwe dependency of licentie."""

    def __init__(self, model_name: str, device: str = "cpu"):
        import torch
        from pyannote.audio import Inference, Model

        token = get_hf_token()
        try:
            model = Model.from_pretrained(model_name, token=token)
        except TypeError:
            model = Model.from_pretrained(model_name, use_auth_token=token)
        if model is None:
            raise RuntimeError(f"Kon embeddingmodel '{model_name}' niet laden (token/licentie?).")
        self._torch = torch
        self._inference = Inference(model, window="whole", device=torch.device(device))
        self.model_name = model_name

    def embed(self, clips: Sequence[np.ndarray], sample_rate: int) -> np.ndarray:
        out: list[Optional[np.ndarray]] = []
        for clip in clips:
            wf = self._torch.from_numpy(np.ascontiguousarray(clip, dtype=np.float32))[None, :]
            try:
                e = np.asarray(self._inference({"waveform": wf, "sample_rate": sample_rate}), dtype=np.float64).reshape(-1)
            except Exception:  # te kort / leeg — nooit de hele run laten crashen
                e = None
            out.append(e)
        dim = next((e.shape[0] for e in out if e is not None), 1)
        return np.vstack([e if e is not None else np.full(dim, np.nan) for e in out])


# ============================================================
# Datastructuren
# ============================================================

@dataclass
class Unit:
    """Een stuk spraak tussen twee aannemelijke grenzen, met één spreker."""
    f0: int                      # begin-frame (inclusief)
    f1: int                      # eind-frame (exclusief)
    label: Optional[str]         # huidige spreker (None = pyannote hoorde hier niemand)
    original: Optional[str]      # label vóór refinement
    emb: Optional[np.ndarray] = None
    clear: Optional[bool] = None  # None = niet beoordeeld (te kort / geen embedding)
    reason: str = ""

    @property
    def seconds(self) -> float:
        return (self.f1 - self.f0) * FRAME


@dataclass
class Profile:
    speaker: str
    centroid: np.ndarray
    mu: float                    # typische "past bij zichzelf"-similarity
    sd: float
    n_units: int
    seconds: float
    weak: bool                   # te weinig eenheden voor een eigen verdeling
    total: Optional[np.ndarray] = None   # duur-gewogen som van de leden (voor leave-one-out)
    members: frozenset = frozenset()     # id()'s van de eenheden die het profiel vormen

    def sim(self, u: "Unit", exclude_self: bool = True) -> float:
        """Similarity van u met dit profiel; zit u zelf in het profiel, dan
        wordt u eruit gelaten (anders past elke eenheid kunstmatig goed)."""
        if exclude_self and self.total is not None and id(u) in self.members:
            rest = self.total - u.emb * u.seconds
            n = np.linalg.norm(rest)
            if n > 0:
                return float(u.emb @ (rest / n))
        return float(u.emb @ self.centroid)

    def z(self, sim: float) -> float:
        return (sim - self.mu) / self.sd


@dataclass
class RefinementResult:
    turns: list[SpeakerTurn]
    merge_map: dict[str, str]
    new_speakers: list[dict]
    profiles: list[dict]
    changes: list[dict]
    stats: dict = field(default_factory=dict)

    def to_metadata(self) -> dict:
        return {
            "merge_map": self.merge_map,
            "new_speakers": self.new_speakers,
            "profiles": self.profiles,
            "changes": self.changes,
            "stats": self.stats,
        }


# ============================================================
# Hulpfuncties
# ============================================================

def _normalize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.where(n == 0, 1.0, n)


def _runs(values: Sequence) -> list[tuple[int, int, object]]:
    out, i, n = [], 0, len(values)
    while i < n:
        j = i
        while j < n and values[j] == values[i]:
            j += 1
        out.append((i, j, values[i]))
        i = j
    return out


def _frame_energy(samples: np.ndarray, sr: int, n_frames: int) -> np.ndarray:
    hop = int(FRAME * sr)
    padded = np.zeros(n_frames * hop, dtype=np.float64)
    m = min(len(samples), len(padded))
    padded[:m] = samples[:m]
    return np.sqrt((padded.reshape(n_frames, hop) ** 2).mean(axis=1))


def _robust(values: np.ndarray) -> tuple[float, float]:
    med = float(np.median(values))
    mad = float(np.median(np.abs(values - med))) * 1.4826
    return med, mad


# ============================================================
# 1. Eenheden
# ============================================================

def build_units(
    turns: Sequence[SpeakerTurn],
    n_frames: int,
    quiet: np.ndarray,
    asr_spans: Optional[Sequence[tuple[float, float]]],
) -> tuple[list[Unit], np.ndarray, list[str]]:
    """Geeft (eenheden, activiteit (T,K) bool, sprekerlijst)."""
    speakers = sorted({t.speaker for t in turns})
    act = np.zeros((n_frames, len(speakers)), dtype=bool)
    for t in turns:
        f0, f1 = max(0, int(round(t.start / FRAME))), min(n_frames, int(round(t.end / FRAME)))
        if f1 > f0:
            act[f0:f1, speakers.index(t.speaker)] = True
    n_active = act.sum(axis=1)

    # per frame: spreker-label, "OVERLAP", "ASR" (spraak volgens Whisper maar
    # niet volgens pyannote) of None (stil)
    in_asr = np.zeros(n_frames, dtype=bool)
    seg_id = np.full(n_frames, -1)
    for i, (s0, s1) in enumerate(sorted(asr_spans or [])):
        f0, f1 = max(0, int(round(s0 / FRAME))), min(n_frames, int(round(s1 / FRAME)))
        in_asr[f0:f1] = True
        seg_id[f0:f1] = i
    frame_lab: list = []
    for f in range(n_frames):
        if n_active[f] >= 2:
            frame_lab.append("<OVERLAP>")
        elif n_active[f] == 1:
            frame_lab.append(speakers[int(np.argmax(act[f]))])
        elif in_asr[f] and not quiet[f]:
            frame_lab.append("<ASR>")
        else:
            frame_lab.append(None)

    # knippen op labelwissel EN op Whisper-segmentgrens
    key = [(frame_lab[f], int(seg_id[f])) for f in range(n_frames)]
    units = []
    for f0, f1, (lab, _) in _runs(key):
        if lab is None or lab == "<OVERLAP>":
            continue
        real = None if lab == "<ASR>" else lab
        units.append(Unit(f0=f0, f1=f1, label=real, original=real))
    return units, act, speakers


def _embed_units(units: Sequence[Unit], samples: np.ndarray, sr: int, embedder, min_seconds: float) -> None:
    todo = [u for u in units if u.seconds >= min_seconds and u.emb is None]
    if not todo:
        return
    clips = [samples[int(u.f0 * FRAME * sr):int(u.f1 * FRAME * sr)] for u in todo]
    embs = np.asarray(embedder.embed(clips, sr), dtype=np.float64)
    for u, e in zip(todo, embs):
        if np.all(np.isfinite(e)) and np.linalg.norm(e) > 0:
            u.emb = _normalize(e)


# ============================================================
# 2. Profielen
# ============================================================

def build_profiles(units: Sequence[Unit], cfg: BoundaryRefinementConfig) -> dict[str, Profile]:
    by_spk: dict[str, list[Unit]] = {}
    for u in units:
        if u.label is not None and u.emb is not None:
            by_spk.setdefault(u.label, []).append(u)

    built: dict[str, tuple[np.ndarray, frozenset, list[Unit], np.ndarray]] = {}
    for spk, us in by_spk.items():
        E = np.stack([u.emb for u in us])
        w = np.array([u.seconds for u in us])
        keep = np.ones(len(us), dtype=bool)
        if len(us) >= 4:
            # Eén robuuste trim-ronde voor het PROFIEL: duidelijke uitschieters
            # (vaak spraak van iemand anders die pyannote hier neerzette)
            # tellen niet mee in het gemiddelde.
            loo = _loo(E, w)
            med, mad = _robust(loo)
            keep = loo >= med - cfg.outlier_z * max(mad, cfg.min_sd)
        total = (E[keep] * w[keep][:, None]).sum(axis=0)
        members = frozenset(id(u) for u, k in zip(us, keep) if k)
        built[spk] = (total, members, us, w)

    # "Hoe goed past een eigen eenheid normaal bij dit profiel": over ALLE
    # eigen eenheden (ook de weggetrimde), robuust (mediaan/MAD).
    stats: dict[str, tuple[float, float]] = {}
    for spk, (total, members, us, w) in built.items():
        if len(us) >= cfg.min_profile_units:
            tmp = Profile(spk, _normalize(total), 0.0, 1.0, 0, 0.0, False, total, members)
            sims = np.array([tmp.sim(u) for u in us])
            med, mad = _robust(sims)
            stats[spk] = (med, max(mad, cfg.min_sd))
    psd = float(np.median([v[1] for v in stats.values()])) if stats else 0.15
    pmu = float(np.median([v[0] for v in stats.values()])) if stats else 0.4

    profiles = {}
    for spk, (total, members, us, w) in built.items():
        if spk in stats:
            mu, sd = stats[spk]
            weak = False
        else:
            # Te weinig eigen eenheden om te weten wat "normaal" is: milde
            # schatting. Zo'n profiel trekt via _decide() ook minder makkelijk
            # eenheden naar zich toe.
            mu, sd = pmu - psd, psd * 1.5
            weak = True
        profiles[spk] = Profile(spk, _normalize(total), mu, sd, len(us), round(float(w.sum()), 2), weak,
                                total, members)
    return profiles


def _loo(E: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Leave-one-out similarity van elke eenheid t.o.v. de rest van haar spreker."""
    if len(E) < 2:
        return np.zeros(len(E))
    total = (E * w[:, None]).sum(axis=0)
    rest = _normalize(total[None, :] - E * w[:, None])
    return np.einsum("ij,ij->i", rest, E)


# ============================================================
# 3. Samenvoegen (over-segmentatie)
# ============================================================

def find_merges(units: Sequence[Unit], profiles: dict[str, Profile], cfg: BoundaryRefinementConfig) -> tuple[dict[str, str], list[dict]]:
    """Cluster X gaat op in een groter cluster Y als
      (1) X's eenheden (mediaan) voor Y heel gewoon zijn: z_Y ≥ -merge_fit_z, en
      (2) ze hooguit `merge_tolerance` (in z-eenheden van X) minder goed bij Y
          passen dan bij X zelf (voor een zwak X-profiel vervalt (2): de eigen
          verdeling is dan onbekend, dus beslist (1) alleen).
    Er wordt steeds één paar tegelijk samengevoegd (het meest overtuigende),
    waarna de profielen opnieuw worden opgebouwd. Wat géén van beide
    voorwaarden haalt blijft een eigen spreker — liever een korte echte
    spreker houden dan wegpoetsen."""
    mapping = {s: s for s in profiles}
    log: list[dict] = []
    if len(profiles) < 2:
        return mapping, log
    current = dict(profiles)
    while len(current) > 1:
        best = None
        names = sorted(current, key=lambda s: current[s].seconds)
        for x in names:
            ux = [u for u in units if u.label is not None and mapping.get(u.label) == x and u.emb is not None]
            if not ux:
                continue
            E = np.stack([u.emb for u in ux]); w = np.array([u.seconds for u in ux])
            own = float(np.median(_loo(E, w))) if len(ux) >= 2 else current[x].mu
            for y in names:
                if y == x or current[y].seconds < current[x].seconds:
                    continue
                cross = float(np.median(E @ current[y].centroid))
                gap_z = (own - cross) / current[x].sd
                zy = current[y].z(cross)
                # Twee voorwaarden: (1) X lijkt op Y ongeveer even veel als op
                # zichzelf, en (2) X's eenheden zijn voor Y heel gewoon (geen
                # uitschieters). (2) voorkomt dat een "verstrooide" stem (ver
                # van de microfoon, lijkt ook niet op zichzelf) wordt opgeslokt.
                ok = zy >= -cfg.merge_fit_z and (current[x].weak or gap_z <= cfg.merge_tolerance)
                entry = {"small": x, "big": y, "own_similarity": round(own, 4),
                         "cross_similarity": round(cross, 4), "gap_z": round(gap_z, 3),
                         "z_in_big": round(zy, 3), "merged": False}
                log.append(entry)
                if ok and (best is None or gap_z < best[0]):
                    best = (gap_z, x, y, entry)
        if best is None:
            break
        _, x, y, entry = best
        entry["merged"] = True
        for s in mapping:
            if mapping[s] == x:
                mapping[s] = y
        for u in units:
            if u.label == x:
                u.label = y
        current = {k: v for k, v in build_profiles(units, cfg).items()}
    return mapping, log


# ============================================================
# Beslisregel voor één eenheid
# ============================================================

def _scores(u: Unit, profiles: dict[str, Profile], exclude_self: bool = True) -> dict[str, tuple[float, float]]:
    """{spreker: (similarity, z)}."""
    out = {}
    for spk, p in profiles.items():
        sim = p.sim(u, exclude_self)
        out[spk] = (sim, p.z(sim))
    return out


def _decide(u: Unit, sc: dict[str, tuple[float, float]], profiles: dict[str, Profile],
            cfg: BoundaryRefinementConfig) -> tuple[Optional[str], bool, str]:
    """Geeft (nieuw_label, duidelijk?, reden).

    Omlabelen gebeurt alleen als de eenheid lang genoeg is, een duidelijke
    uitschieter is voor haar eigen spreker (z ≤ -outlier_z) én er een andere
    spreker is waar ze wél bij past:
      * sterk profiel: z ≥ -fit_z, minstens min_dz beter dan bij de eigen
        spreker, én in ruwe similarity echt dichter bij die spreker;
      * zwak profiel (heel weinig eigen spraak, verdeling onbekend): de
        eenheid moet absoluut meer op dat profiel lijken dan op de eigen
        spreker én dan op elke andere spreker. Een zwak profiel is dus geen
        'magneet' voor alles wat toevallig niet bij de docent past."""
    def fits(spk: str) -> bool:
        sim, z = sc[spk]
        if profiles[spk].weak:
            return all(sim > o_sim for o, (o_sim, _) in sc.items() if o != spk)
        own_sim, own_z = sc[u.label] if u.label is not None else (-math.inf, -math.inf)
        # relatief beter (z) én ook echt meer gelijkend (ruwe similarity)
        return z >= -cfg.fit_z and z - own_z >= cfg.min_dz and sim > own_sim

    others = sorted((s for s in sc if s != u.label), key=lambda s: sc[s][1], reverse=True)
    if u.seconds < cfg.min_relabel_seconds:
        # te kort om tegen pyannote in te gaan; wel onduidelijk als het slecht past
        if u.label is None:
            return None, False, ""
        return u.label, sc[u.label][1] > -cfg.outlier_z, ""

    if u.label is None:
        # Whisper hoorde spraak, pyannote niemand: alleen toewijzen als één spreker duidelijk past
        good = [s for s in others if fits(s)]
        if len(good) == 1:
            return good[0], True, "aangevuld: pyannote zag geen spraak, stem past bij deze spreker"
        return None, False, ""

    own_sim, own_z = sc[u.label]
    if own_z <= -cfg.outlier_z:
        good = [s for s in others if fits(s)]
        if good:
            tgt = good[0]
            return tgt, True, (f"omgelabeld: past niet bij {u.label} (z={own_z:.1f}, sim={own_sim:.2f}) "
                               f"maar wel bij {tgt} (z={sc[tgt][1]:.1f}, sim={sc[tgt][0]:.2f})")
        return u.label, False, f"onduidelijk: past slecht bij {u.label} (z={own_z:.1f}) en bij niemand anders duidelijk"
    rival = others[0] if others else None
    if (rival is not None and not profiles[rival].weak
            and sc[rival][1] - own_z > -cfg.min_dz / 2 and sc[rival][0] >= own_sim - cfg.rival_similarity_margin):
        return u.label, False, f"onduidelijk: past bijna even goed bij {rival}"
    return u.label, True, ""


# ============================================================
# De hoofdfunctie
# ============================================================

def refine_speaker_boundaries(
    samples: np.ndarray,
    sample_rate: int,
    turns: Sequence[SpeakerTurn],
    embedder: WindowEmbedder,
    cfg: BoundaryRefinementConfig,
    *,
    asr_spans: Optional[Sequence[tuple[float, float]]] = None,
) -> RefinementResult:
    """samples: 1-D mono audio. turns: pyannote's ruwe beurten.
    asr_spans: (start, end) van de Whisper-segmenten — hun grenzen zijn
    kandidaat-wisselpunten, en hoorbare spraak erin die pyannote miste wordt
    ook beoordeeld."""
    sr = sample_rate
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    n_frames = int(math.ceil(len(samples) / sr / FRAME))
    original_speakers = sorted({t.speaker for t in turns})

    def _unchanged(reason: str) -> RefinementResult:
        return RefinementResult(turns=list(turns), merge_map={s: s for s in original_speakers},
                                new_speakers=[], profiles=[], changes=[], stats={"skipped": reason})

    if not turns or n_frames == 0:
        return _unchanged("geen sprekerbeurten")

    energy = _frame_energy(samples, sr, n_frames)
    speech_frames = np.zeros(n_frames, dtype=bool)
    for t in turns:
        speech_frames[max(0, int(round(t.start / FRAME))):min(n_frames, int(round(t.end / FRAME)))] = True
    ref = np.median(energy[speech_frames]) if speech_frames.any() else np.median(energy)
    quiet = energy < cfg.pause_energy_ratio * ref

    units, act, speakers = build_units(turns, n_frames, quiet, asr_spans)
    _embed_units(units, samples, sr, embedder, cfg.min_unit_seconds)
    profiles = build_profiles(units, cfg)
    if not profiles:
        return _unchanged("geen eenheden lang genoeg voor een embedding")

    # ---- 3. samenvoegen --------------------------------------------------
    merge_map, merge_log = (find_merges(units, profiles, cfg) if cfg.merge_clusters
                            else ({s: s for s in profiles}, []))
    for s in original_speakers:
        merge_map.setdefault(s, s)
    profiles = build_profiles(units, cfg)

    # ---- 5. splitsen (vóór hertoewijzen, zodat beide helften beoordeeld worden)
    changes: list[dict] = []
    if cfg.split_long_units:
        new_units: list[Unit] = []
        for u in units:
            new_units.extend(_try_split(u, samples, sr, quiet, embedder, profiles, cfg, changes))
        if len(new_units) != len(units):
            units = new_units
            profiles = build_profiles(units, cfg)  # helften worden zelf lid van het profiel

    # ---- 4. hertoewijzen -------------------------------------------------
    misfits: list[Unit] = []
    for u in units:
        if u.emb is None:
            continue
        sc = _scores(u, profiles)
        new_label, clear, reason = _decide(u, sc, profiles, cfg)
        if new_label != u.label:
            changes.append({"start": round(u.f0 * FRAME, 2), "end": round(u.f1 * FRAME, 2),
                            "from": u.label, "to": new_label, "reason": reason})
            u.label = new_label
        u.clear = clear
        u.reason = reason
        if u.label is not None and u.seconds >= cfg.min_relabel_seconds and all(z <= -cfg.outlier_z for _, z in sc.values()):
            misfits.append(u)

    # ---- 6. nieuwe sprekers ----------------------------------------------
    new_speakers: list[dict] = []
    if cfg.detect_new_speakers:
        cands = [u for u in misfits if u.seconds >= cfg.min_new_unit_seconds]
        groups: list[list[Unit]] = []
        for u in cands:
            for g in groups:
                gc = _normalize(sum(v.emb * v.seconds for v in g))
                # bij een groep als hij daar meer op lijkt dan op elk bestaand profiel
                if float(u.emb @ gc) > max(float(u.emb @ p.centroid) for p in profiles.values()):
                    g.append(u)
                    break
            else:
                groups.append([u])
        for g in groups:
            secs = sum(u.seconds for u in g)
            if secs < cfg.min_new_speaker_seconds:
                continue
            if len(g) == 1 and secs < 2 * cfg.min_new_speaker_seconds:
                continue  # één los stukje dat op niemand lijkt: eerder rumoer dan een nieuwe spreker
            name = f"{NEW_SPEAKER_PREFIX}{len(new_speakers)}"
            gc = _normalize(sum(u.emb * u.seconds for u in g))
            for u in g:
                changes.append({"start": round(u.f0 * FRAME, 2), "end": round(u.f1 * FRAME, 2),
                                "from": u.label, "to": name, "reason": "past bij geen enkele bekende spreker"})
                u.label = name
                u.clear = False  # nieuwe spreker is per definitie een onzekere vondst
            new_speakers.append({
                "label": name, "seconds": round(secs, 2),
                "spans": [[round(u.f0 * FRAME, 2), round(u.f1 * FRAME, 2)] for u in g],
                "max_similarity_to_existing": round(max(float(gc @ p.centroid) for p in profiles.values()), 4),
            })

    # ---- 7. beurten opbouwen ---------------------------------------------
    frame_sets: list[tuple] = [() for _ in range(n_frames)]
    frame_clear = np.full(n_frames, np.nan)
    for f in range(n_frames):
        active = tuple(sorted({merge_map[speakers[k]] for k in np.flatnonzero(act[f])}))
        frame_sets[f] = active
    for u in units:
        if u.label is None:
            continue
        for f in range(u.f0, u.f1):
            frame_sets[f] = (u.label,)
        if u.clear is not None:
            frame_clear[u.f0:u.f1] = 1.0 if u.clear else 0.0

    new_turns: list[SpeakerTurn] = []
    for spk in sorted({s for fs in frame_sets for s in fs}):
        mask = [spk in fs for fs in frame_sets]
        for f0, f1, on in _runs(mask):
            if not on:
                continue
            c = frame_clear[f0:f1]
            c = c[np.isfinite(c)]
            new_turns.append(SpeakerTurn(start=round(f0 * FRAME, 3), end=round(f1 * FRAME, 3), speaker=spk,
                                         confidence=round(float(c.mean()), 4) if len(c) else None))
    new_turns.sort(key=lambda t: (t.start, t.end))

    judged = [u for u in units if u.clear is not None]
    stats = {
        "n_units": len(units),
        "n_units_judged": len(judged),
        "unclear_seconds": round(sum(u.seconds for u in judged if not u.clear), 2),
        "relabeled_seconds": round(sum(c["end"] - c["start"] for c in changes
                                       if c["from"] is not None and not c.get("split")), 2),
        "filled_seconds": round(sum(c["end"] - c["start"] for c in changes if c["from"] is None), 2),
        "n_splits": sum(1 for c in changes if c.get("split")),
        "merge_log": merge_log,
        "n_turns_before": len(turns),
        "n_turns_after": len(new_turns),
    }
    return RefinementResult(
        turns=new_turns,
        merge_map=merge_map,
        new_speakers=new_speakers,
        profiles=[{"speaker": p.speaker, "seconds": p.seconds, "n_units": p.n_units,
                   "typical_similarity": round(p.mu, 4), "spread": round(p.sd, 4), "weak_profile": p.weak}
                  for p in profiles.values()],
        changes=changes,
        stats=stats,
    )


def _try_split(u: Unit, samples, sr, quiet, embedder, profiles: dict[str, Profile],
               cfg: BoundaryRefinementConfig, changes: list[dict]) -> list[Unit]:
    """Probeer een lange eenheid op een stilte in twee te knippen. Alleen als
    de twee helften volgens de normale beslisregel bij verschillende sprekers
    horen. Anders blijft de eenheid heel."""
    if u.label is None or u.emb is None or u.seconds < cfg.split_min_seconds or u.label not in profiles:
        return [u]
    edge = int(round(cfg.split_min_part_seconds / FRAME))
    cands = [f for f in range(u.f0 + edge, u.f1 - edge + 1) if quiet[f]]
    if not cands:
        return [u]
    points, i = [], 0
    while i < len(cands):          # één kandidaat per stilte (midden van de stille reeks)
        j = i
        while j + 1 < len(cands) and cands[j + 1] == cands[j] + 1:
            j += 1
        points.append((cands[i] + cands[j] + 1) // 2)
        i = j + 1

    # profiel van de eigen spreker zonder deze hele eenheid
    prof = dict(profiles)
    own = profiles[u.label]
    if own.total is not None and id(u) in own.members:
        rest = own.total - u.emb * u.seconds
        if np.linalg.norm(rest) > 0:
            prof[u.label] = Profile(own.speaker, _normalize(rest), own.mu, own.sd, own.n_units,
                                    own.seconds, own.weak, None, frozenset())
    best = None
    for p in points[: cfg.max_split_candidates]:
        a = Unit(u.f0, p, u.label, u.original)
        b = Unit(p, u.f1, u.label, u.original)
        _embed_units([a, b], samples, sr, embedder, cfg.min_unit_seconds)
        if a.emb is None or b.emb is None:
            continue
        la, _, _ = _decide(a, _scores(a, prof, exclude_self=False), prof, cfg)
        lb, _, _ = _decide(b, _scores(b, prof, exclude_self=False), prof, cfg)
        if la is not None and lb is not None and la != lb:
            sep = float(a.emb @ b.emb)
            if best is None or sep < best[0]:
                best = (sep, a, b)
    if best is None:
        return [u]
    _, a, b = best
    changes.append({"start": round(u.f0 * FRAME, 2), "end": round(u.f1 * FRAME, 2), "from": u.label, "to": u.label,
                    "split": True, "split_at": round(a.f1 * FRAME, 2),
                    "reason": "eenheid geknipt op een stilte: helften klinken als verschillende sprekers"})
    return [a, b]
