# Afgeronde experimenten — overzicht

"Afgerond" betekent hier: **we werken er voorlopig niet verder aan**, niet
dat de methode bewezen onbruikbaar is. Alle onderliggende code, data,
modelbestanden en omgevingen blijven bestaan en draaibaar — er is niets
verwijderd of inhoudelijk gewijzigd bij deze reorganisatie, alleen
verplaatst en waar nodig van een statusnotitie voorzien.

**Niet elk afgerond experiment staat fysiek in deze map** — twee ervan
blijven op hun oorspronkelijke plek staan omdat verplaatsen ofwel een risico
op stilzwijgend kapotte paden/omgevingen gaf, ofwel een gedeelde helper zou
breken die actieve code nog gebruikt. Zie de tabel hieronder voor de
werkelijke locatie van elk experiment.

## De actieve route

| Onderdeel | Waar |
|---|---|
| Transcriptie — Faster-Whisper `medium` | `Data-analysis/src/transcription.py` |
| Diarizatie — pyannote `speaker-diarization-3.1` | `Data-analysis/src/diarization.py` |
| Preprocessing (speaker turns, context, onzekerheid, traceability) | `Data-analysis/src/preprocessing.py` |
| **Docentherkenning (productieroute)** — pyannote WeSpeaker vs. een configureerbare referentiestem, apart van diarizatie-identiteit | `Data-analysis/src/docent_recognition.py` — voegt `docent_role` (DOCENT/OTHER/ONZEKER) toe aan elke turn |
| Docentherkenning (oorspronkelijk experiment, model-/drempelkeuze onderbouwd) | `Data-analysis/Experiments/speaker_recognition/pyannote_embeddings/` (+ `_common.py`) — logica hergebruikt door `docent_recognition.py`, niet geïmporteerd |
| Woordniveau-koppeling (`word_timestamps=True` + bestaande pyannote-turns) | `Data-analysis/Experiments/word_level_speaker_attribution/` |
| Classificatiebasis (contextvensters, schema, mockclassifier, tests) — leest nu ook `docent_role` | `Data-analysis/Experiments/classification/` |
| Onderzoeksverslag | `Data-analysis/Notebooks/*.ipynb` |
| Alles-in-één gemakskoppeling | `Data-analysis/src/run_docent_pipeline.py` — draait de eerste 4 stappen na elkaar |

**Volledige route, workshopaudio + docentreferentie → classificatie-invoer:**
`transcription.py` → `diarization.py` → `preprocessing.py` →
`docent_recognition.py` → `Experiments/classification/classification.py`.
Elke stap is een los, herhaalbaar CLI-commando dat naar een eigen bestand
schrijft. **Update:** `Data-analysis/src` is opgeschoond — elke stap was eerst
een submap met 3-5 losse bestanden (`diarization/base.py` +
`pyannote_backend.py` + `assign.py` + `labeling.py`, enz.), nu is dat één
bestand per stap, inclusief het bijbehorende commando (de vroegere
`run_*.py`-scripts zijn daarin opgegaan — zie de hoofdrapportage van deze
opschoning voor het exacte, ongewijzigde gedrag en de vóór/na-vergelijking).

## Afgeronde experimenten

| Experiment | Werkelijke locatie | Waarom afgerond | Waarom (niet) fysiek verplaatst |
|---|---|---|---|
| **Community-1** (alternatief diarizationmodel) | `Afgeronde_experimenten/diarization/community1/` | Geen overtuigende verbetering aangetoond t.o.v. de baseline (`speaker-diarization-3.1`) in onze beperkte tests (3 korte fragmenten, geen ground truth). | Verplaatst — importeert alleen uit `Data-analysis/src`, geen gedeelde helpers binnen `Experiments/diarization/`, dus geen enkele coderegel hoefde aangepast (padberekening bleek onafhankelijk van de exacte locatie zolang de diepte vanaf `Data-analysis/` gelijk blijft). |
| **Vergelijking BASELINE / Community-1 / WhisperX** | `Afgeronde_experimenten/diarization/comparison/` | Documenteert de twee bovenstaande, afgeronde experimenten. | Verplaatst samen met Community-1 (relatieve links intern blijven kloppen); de link naar WhisperX is aangepast omdat die map wél op zijn oude plek is gebleven. |
| **WhisperX** (transcriptie/alignment/sprekerkoppelingsroute) | `Data-analysis/Experiments/diarization/whisperx/` (**ongewijzigd, niet verplaatst**) | Lost het "één ASR-segment, twee sprekers"-probleem wél op, maar tegen de prijs van een volledig aparte Python 3.12-omgeving, ~100 extra dependencies en 2-3× de runtime. Het lichtere, actieve alternatief (`word_level_speaker_attribution`, zonder WhisperX) bereikt hetzelfde resultaat op het geteste geval zonder die kosten. **Geen alternatief diarizationmodel** — gebruikt hetzelfde pyannote 3.1 als de baseline; het verschil zit in eigen ASR + forced alignment + woordniveau-koppeling. | **Niet verplaatst.** Bevat een eigen venv (`.venv-whisperx/`) en mogelijk andere bestanden met absolute paden die bij verplaatsing stilzwijgend kapot kunnen gaan — dat risico wilden we niet lopen zonder elk bestand individueel te controleren. Alleen gemarkeerd als afgerond in het eigen `README.md`. |
| **SpeechBrain ECAPA-TDNN** (alternatief speaker-recognition-model) | `Data-analysis/Experiments/speaker_recognition/speechbrain_ecapa/` (**ongewijzigd, niet verplaatst**) | Vergelijkbaar bruikbaar DOCENT/OTHER-signaal als pyannote WeSpeaker, iets minder scherpe scheiding in onze test — zie `speaker_recognition/comparison/results.md`. Niet slechter bewezen, alleen niet de gekozen actieve route. | **Niet verplaatst.** Het script importeert `_common.py` via een pad relatief aan zijn eigen map (`speaker_recognition/`); die map moet in zijn geheel blijven staan omdat actieve onderdelen (`pyannote_embeddings/`, en indirect `word_level_speaker_attribution`) dezelfde `_common.py` gebruiken. Fysiek verplaatsen zou `_common.py` moeten dupliceren (drift-risico) of de importlogica moeten ombouwen. Alleen gemarkeerd als afgerond in `speaker_recognition/README.md`. |

## Wat NIET is veranderd

- Geen code, data, modelbestanden of Python-omgevingen verwijderd.
- Geen inhoudelijke pipeline-logica aangepast — alleen documentatie
  (status-notities, padverwijzingen) en de fysieke locatie van twee mappen
  (Community-1 + de vergelijkingsnotitie).
- `Data-analysis/src/*` niet aangeraakt.
- Alle actieve experimenten (`speaker_recognition/pyannote_embeddings`,
  `speaker_recognition/_common.py`, `word_level_speaker_attribution/*`,
  `classification/*`) ongewijzigd, op twee tekstuele padverwijzingen na die
  nu naar de nieuwe Community-1-locatie wijzen (zie hoofdrapportage).
