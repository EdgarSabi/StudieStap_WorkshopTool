# Experiment B — WhisperX + pyannote (word-level speaker assignment)

## 1. Doel

Niet zomaar "een ander diarizationmodel" testen, maar onderzoeken of
**woordniveau forced alignment + word-level speaker assignment** het
structurele probleem van de baseline oplost: één faster-whisper SEGMENT (bv.
`"Dit ben jij. Dit ben ik."`) kan tekst van twee sprekers bevatten, maar
`diarization/assign.py` in de baseline kan zo'n segment maar **één**
speakerlabel geven omdat het op segment-niveau (niet woord-niveau) werkt.

## 2. Gebruikte modellen

| | |
|---|---|
| ASR | WhisperX's eigen faster-whisper-wrapper, model `medium`, taal `nl` (**niet** hetzelfde transcript-JSON als de baseline — WhisperX doet zijn eigen VAD + segmentatie, dus segmentgrenzen wijken af, zie punt 7) |
| Forced alignment | `jonatasgrosman/wav2vec2-large-xlsr-53-dutch` (WhisperX's default wav2vec2-model voor `nl`) |
| Diarization | `pyannote/speaker-diarization-3.1` — **bewust hetzelfde model als de baseline**, niet community-1, om alleen het effect van woordniveau-koppeling te isoleren (community-1 wordt apart vergeleken in Experiment A) |
| Device | CPU |

## 3. Dependencies

**Volledig losse venv, niet de hoofd-`.venv`.** WhisperX en zijn dependency-keten
(`ctranslate2`, `nltk`, een eigen `torch`/`pyannote.audio`-resolutie) hoeven niet
overeen te komen met de baseline-pipeline, en de hoofd-`.venv` draait op
**Python 3.14** — daar bestaan nog geen wheels voor (een deel van) deze stack.

```
cd Data-analysis/Experiments/diarization/whisperx
py -3.12 -m venv .venv-whisperx
.venv-whisperx\Scripts\pip install -r requirements-whisperx.txt
```

Zie [requirements-whisperx.txt](requirements-whisperx.txt) voor de exacte
(gepinde) versielijst — dat is een volledige `pip freeze` van een schone
`pip install whisperx` op Python 3.12, zodat een her-run maanden later
dezelfde stack installeert. Installatie verliep **zonder** dependency-conflicten
(`pip` meldde geen resolver-errors). Noemenswaardig: whisperx trekt zelf
`pyannote-audio==4.0.7` binnen — **dezelfde versie** als de baseline en
Experiment A gebruiken, en `torch` loste op naar de CPU-only Windows-wheel
(`2.8.0+cpu`), zonder dat daarvoor een CUDA-index nodig was.

De hoofd-`.venv` (`Data-analysis/src/.venv`) is voor dit experiment **niet**
aangeraakt.

## 4. Hoe opnieuw runnen

```bash
cd Data-analysis/Experiments/diarization/whisperx
.venv-whisperx\Scripts\python.exe whisperx_test.py
# of specifieke fragmenten:
.venv-whisperx\Scripts\python.exe whisperx_test.py --fragment testaudio1_fragment --fragment testaudio5_fragment --force
```

Vereist `HF_TOKEN` in `<repo-root>/.env` (zelfde token/setup als de baseline —
`config.get_hf_token()` wordt hergebruikt). Geen aparte transcriptiestap nodig:
dit script doet ASR + alignment + diarizatie + speaker-assignment allemaal
zelf, in één run.

## 5. Inputpad

- `Data-analysis/src/test-files/<fragment>.mp3` — zelfde audio als de baseline
  en Experiment A. WhisperX transcribeert dit bestand zelf opnieuw (met zijn
  eigen VAD/segmentatie); er wordt geen bestaand transcript-JSON hergebruikt.

## 6. Outputpad

```
Data-local/processed/diarization_experiments/whisperx/
├── testaudio1_fragment_whisperx_raw.json
├── testaudio1_fragment_whisperx_normalized.json
├── testaudio2_fragment_whisperx_raw.json
├── testaudio2_fragment_whisperx_normalized.json
├── testaudio5_fragment_whisperx_raw.json
└── testaudio5_fragment_whisperx_normalized.json
```

- **`_raw.json`**: bijna-ruwe whisperx-output — alle segmenten mét hun
  `words`-lijst (`word`, `start`, `end`, `score`, `speaker`, `speaker_raw`),
  plus de losse diarization-turns en de timing-breakdown (`asr_seconds`,
  `alignment_seconds`, `diarization_seconds`, `total_seconds`).
- **`_normalized.json`**: projectvriendelijke vorm — segmenten met
  `start`/`end`/`text`/`speaker`/`speaker_raw` (zelfde velden als de baseline)
  plus een `mixed_speakers`-vlag per segment (True = dit ene ASR-segment bevat
  woorden van meer dan één spreker), een `speaker_inventory` (zelfde
  MAIN/OTHER_n-heuristiek als de baseline, hier toegepast op de
  whisperx-diarizatie-turns), én `readable_turns`: de woorden opnieuw
  aan elkaar geregen tot leesbare spreekbeurten **op basis van woordniveau
  sprekerwissels**, ongeacht de originele ASR-segmentgrenzen — bv.
  `{"speaker": "OTHER_SPEAKER_1", "text": "Dit ben ik."}`.

## 7. Resultaten (samenvatting — zie ook `../comparison/experiment_notes.md`)

| Fragment | Segmenten (whisperx) | mixed_speaker_segments | Runtime (asr/align/diar/totaal) |
|---|---|---|---|
| testaudio1_fragment | 10 | 2 | 19.9 / 14.2 / 13.3 / 47.3s |
| testaudio2_fragment | 21 | 0 | 28.9 / 6.9 / 14.0 / 49.8s |
| testaudio5_fragment | 14 | 3 | 27.0 / 8.4 / 23.8 / 59.2s |

**Kernresultaat testaudio1** (het "Dit ben jij / Dit ben ik"-geval): het
ASR-segment daarvoor werd door whisperx's eigen segmentatie toevallig al
anders geknipt dan bij de baseline (`"... Dus dit ben jij."` en
`"Dit ben ik."` als twee aparte segmenten), maar de `readable_turns`-
reconstructie op woordniveau laat wél precies zien wat het doel van dit
experiment was: woorden binnen `mixed_speakers`-segmenten (2 van de 10) worden
individueel aan een spreker gekoppeld. Voorbeeld uit
`testaudio1_fragment_whisperx_normalized.json`, segment 6.58–9.321s
(`"Oké, heel mooi."`, 1 whisper-segment): het woord `"Oké,"` → `OTHER_SPEAKER_2`,
`"heel mooi."` → `MAIN_SPEAKER` — **binnen één ASR-segment dus toch twee
sprekers**, precies wat de baseline niet kan.

**testaudio2**: `mixed_speaker_segments = 0` en de `readable_turns` blijven
grotendeels één lange `MAIN_SPEAKER`-beurt — zelfde patroon als baseline en
Experiment A. Woordniveau-koppeling helpt hier niet, want de **diarizatie
zelf** detecteert al nauwelijks sprekerwissels (niet een segmentatieprobleem).

**testaudio5**: 3 van de 14 segmenten mixed; de reconstructie laat zeer korte,
snel wisselende beurten zien (soms één woord per spreker) — plausibel gezien
de beschrijving (rumoerig, meerdere gelijktijdige sprekers), maar zonder
ground truth niet te verifiëren of dit ook daadwerkelijk correct is.

## 8. Bekende beperkingen

- **Tekst-encoding bug, onafhankelijk van diarizatie**: de ASR-tekst van
  WhisperX bevat op meerdere plekken een `�` (U+FFFD) waar een Nederlandse
  diakriet hoort te staan — bevestigd vóór de alignment-stap, dus in
  whisperx's eigen ASR-uitvoer zelf (`"Ok�, heel mooi."` i.p.v. `"Oké, heel
  mooi."`; `"ingredi�nten"` i.p.v. `"ingrediënten"`, beide in
  testaudio1_fragment). De baseline gebruikt **dezelfde** faster-whisper-versie
  (`1.2.1`) en heeft dit probleem niet — het zit dus specifiek in hoe WhisperX
  faster-whisper aanroept/decodeert (vermoedelijk een UTF-8-decodeprobleem op
  een chunk-grens in de gebatchte/VAD-gesegmenteerde transcriptie), niet in
  faster-whisper zelf. Dit is een **transcriptiekwaliteitsprobleem**, los van
  de diarizatie-vraag — zie punt 9 hieronder voor waarom dat onderscheid
  hier expliciet gemaakt wordt. Niet verder uitgezocht/opgelost binnen dit
  experiment (buiten scope).
- **Segmentgrenzen wijken af van de baseline**: whisperx gebruikt zijn eigen
  VAD en segmenteert dus anders (10/21/14 segmenten hier vs. 9/19/21 in de
  baseline-transcripten voor dezelfde fragmenten). Een 1-op-1 segment-voor-
  segment vergelijking met de baseline is daardoor niet mogelijk; vergelijk
  liever op het niveau van `readable_turns` / de uiteindelijke doorlopende
  tekst.
- Geen `min_speakers`/`max_speakers`-priors gezet.
- `torchcodec` faalt te laden op deze Windows-machine (ontbrekende shared
  FFmpeg-DLL's, zelfde onderliggende oorzaak als bij de baseline) — geen
  probleem hier, want `whisperx.load_audio()` gebruikt zijn eigen
  ffmpeg-CLI-gebaseerde decoder, niet torchcodec. De waarschuwing in de
  console-output is onschuldig maar wel storend; niet onderdrukt in dit
  experiment.
- Runtime is aanzienlijk hoger dan de baseline: baseline-diarizatie alleen was
  ~18-31s; hier komt daar nog een volledige eigen ASR-pass (~20-29s) en een
  forced-alignment-pass (~7-14s) bovenop, dus 2-3× de totale tijd voor
  hetzelfde fragment. Op deze korte testfragmenten (30-46s) is dat prima te
  overzien; bij hele workshopopnames (30-60 min) is dat een reële
  praktijkoverweging (zie punt 5 van de projectvragen).
- Alleen getest op CPU (GPU aanwezig maar 4GB VRAM en CPU-only torch
  standaard geïnstalleerd — zie hoofd-samenvatting van deze sessie).

## 9. Wat is er NIET veranderd aan de bestaande pipeline

- Niets in `Data-analysis/src/` is aangepast.
- De baseline-transcript-JSON's (`Data-local/processed/<fragment>.json`) en
  de baseline-diarizatie-output zijn niet gelezen, niet aangeraakt, niet
  overschreven — dit experiment transcribeert de audio zelf opnieuw, via een
  volledig aparte tool-chain.
- **Belangrijk interpretatiepunt** (zoals gevraagd): dit experiment vermengt
  twee dingen die je apart moet beoordelen. (A) Detecteert het
  diarizationmodel de juiste sprekerwissels? — dat is identiek aan de vraag
  in Experiment A, want hier wordt hetzelfde `speaker-diarization-3.1`-model
  gebruikt. (B) Kan de transcript↔speaker-koppeling die wissels ook correct
  terugbrengen in de tekst? — dát is wat dit experiment toevoegt t.o.v. de
  baseline en Experiment A: woordniveau-koppeling in plaats van
  segmentniveau-koppeling. De geconstateerde encoding-bug (punt 8) hoort bij
  een derde, apart aspect (ASR-tekstkwaliteit) en mag niet worden verward met
  (A) of (B).
