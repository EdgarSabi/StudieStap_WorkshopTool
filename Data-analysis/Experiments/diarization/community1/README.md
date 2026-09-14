# Experiment A — pyannote/speaker-diarization-community-1

## 1. Doel

Testen of `pyannote/speaker-diarization-community-1` (de opvolger/community-variant
van `speaker-diarization-3.1`) korte docent/leerlingwissels beter herkent dan de
baseline, zonder de productiepipeline aan te raken.

## 2. Gebruikte modellen

| | |
|---|---|
| ASR | faster-whisper `medium`, nl (**hergebruikt** — zelfde transcript-JSON als de baseline, niet opnieuw getranscribeerd) |
| Diarization (baseline) | `pyannote/speaker-diarization-3.1` |
| Diarization (dit experiment) | `pyannote/speaker-diarization-community-1` |
| Device | CPU |

## 3. Dependencies

**Geen nieuwe installs nodig.** Dit experiment draait in de bestaande projectvenv
(`Data-analysis/src/.venv`) — `pyannote.audio==4.0.7` (al geïnstalleerd voor de
baseline) kan community-1 laden via dezelfde `Pipeline.from_pretrained()`-API.
Het bestaande `HF_TOKEN` uit `<repo-root>/.env` werkt ook voor dit model; er is
geen aparte licentie-acceptatie nodig gebleken bovenop wat de baseline al vereist.

## 4. Hoe opnieuw runnen

```bash
cd Data-analysis/Experiments/diarization/community1
../../../src/.venv/Scripts/python.exe community1_test.py
# of specifieke fragmenten:
../../../src/.venv/Scripts/python.exe community1_test.py --fragment testaudio1_fragment --fragment testaudio5_fragment --force
```

Vereist dat de baseline-transcriptstap al gedraaid is (`run_transcription.py`) —
dit script leest het bestaande transcript-JSON en voegt er alleen een nieuwe
diarizatie-laag aan toe; het transcript zelf wordt niet opnieuw gegenereerd.

## 5. Inputpad

- `Data-local/processed/<fragment>.json` — bestaand Phase 1 baseline-transcript
- `Data-analysis/src/test-files/<fragment>.mp3` — zelfde audio als de baseline
- `Data-local/processed/diarization/<fragment>_16k_mono.wav` — hergebruikt indien
  al aanwezig (door de baseline-run aangemaakt), anders zelf aangemaakt via
  dezelfde `_to_wav()`-helper uit `run_diarization.py`

## 6. Outputpad

```
Data-local/processed/diarization_experiments/community1/
├── testaudio1_fragment_community1.json
├── testaudio2_fragment_community1.json
└── testaudio5_fragment_community1.json
```

Elk bestand bevat: `experiment`, `baseline_model`, `diarization_model`,
`source_transcript`, `audio_file`, alle ASR-segmenten met
`speaker`/`speaker_raw`/`speaker_confidence`/`overlap`/`uncertain_assignment`
(zelfde velden als de baseline), plus een `diarization`-blok met
backend/model/settings/runtime/speaker-inventaris, en `runtime_seconds`.

## 7. Resultaten (samenvatting — zie ook `../comparison/experiment_notes.md`)

| Fragment | Baseline raw speakers | Community-1 raw speakers | Baseline runtime | Community-1 runtime |
|---|---|---|---|---|
| testaudio1_fragment | 3 (21 turns) | 2 (16 turns) | 17.99s | 16.47s |
| testaudio2_fragment | 2 (8 turns) | 2 (8 turns) | 19.86s | 17.26s |
| testaudio5_fragment | 5 (23 turns) | 3 (21 turns) | 31.00s | 27.64s |

- **testaudio1**: community-1 vindt 1 spreker minder (een marginale 3e stem met
  maar 1.0s spreektijd in de baseline verdwijnt) — verder vergelijkbare
  MAIN/OTHER-verdeling. Het segment `"Dit ben jij. Dit ben ik."` (9.52–11.64s)
  wordt door de diarizer nog steeds als **overlap** gemarkeerd (`overlap: true`,
  `speaker_confidence: 0.745`), maar krijgt — net als bij de baseline — nog
  steeds maar **één** speakerlabel (`MAIN_SPEAKER`) voor het hele segment. Een
  beter diarizationmodel lost dit dus **niet** op; zie punt 8.
- **testaudio2**: nagenoeg identiek aan de baseline — nog steeds bijna alles
  `MAIN_SPEAKER` (19/19 segmenten). Community-1 verandert hier niets aan de
  onderliggende ASR-segmentatie.
- **testaudio5** (meerdere sprekers, rumoeriger): community-1 clustert naar
  **3** ruwe sprekers waar de baseline er **5** vond, met een vergelijkbaar
  vlakke verdeling (geen dominante MAIN_SPEAKER: 37.5% vs. 34.9% bij de
  baseline). Zonder ground truth is niet vast te stellen welk aantal correcter
  is — community-1 groepeert mogelijk stemmen samen die de baseline nog
  splitste, of de baseline overschat het aantal sprekers. Dit verschil is
  in elk geval het grootste van de drie fragmenten en verdient een handmatige
  check tegen de audio zelf voordat je hier conclusies aan verbindt.

## 8. Bekende beperkingen

- Dit is **alleen** een ander diarizationmodel, niet een andere manier om
  spreker-labels aan tekst te koppelen. Het fundamentele probleem — één
  Whisper-segment met tekst van twee sprekers krijgt hoe dan ook maar één
  `speaker`-label, omdat `assign_speakers()` per *segment* (niet per woord)
  toewijst — blijft bestaan, ongeacht welk pyannote-model je gebruikt. Dit is
  precies waarom Experiment B (WhisperX, woordniveau) apart wordt getest.
- Geen `min_speakers`/`max_speakers`-priors gezet (zelfde als baseline-default).
- Alleen getest op CPU, op drie korte testfragmenten. Geen handmatige
  ground-truth-annotatie van wie wanneer spreekt — alle vergelijkingen hierboven
  zijn gebaseerd op de modeluitvoer zelf, niet op een geverifieerde referentie.

## 9. Wat is er NIET veranderd aan de bestaande pipeline

- `Data-analysis/src/config.py`, `diarization/*`, `run_diarization.py`,
  `run_transcription.py`: **geen enkele regel aangepast.**
- De baseline `speaker-diarization-3.1`-config en -output
  (`Data-local/processed/diarization/*_diarized.json`) zijn ongewijzigd.
- Dit script importeert de bestaande modules alleen (`get_backend`,
  `build_label_map`, `assign_speakers`, `summarize`, `_to_wav`) met een andere
  `DiarizationConfig(hf_model=...)` — geen nieuwe backend-klasse nodig.
