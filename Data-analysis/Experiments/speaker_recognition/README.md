# Speaker recognition experiment — DOCENT vs OTHER

> **Status: pyannote WeSpeaker (`pyannote_embeddings/`) is actief** — blijft
> in gebruik, o.a. door `Experiments/word_level_speaker_attribution`.
> **SpeechBrain ECAPA (`speechbrain_ecapa/`) is afgerond, niet actief in
> gebruik.** Beide mappen blijven hier staan (niet verplaatst): het script
> importeert `_common.py` via een pad relatief aan zijn eigen locatie
> (`speaker_recognition/`), en die map moet in zijn geheel blijven staan
> omdat actieve onderdelen (`pyannote_embeddings/`,
> `word_level_speaker_attribution`) `_common.py` gebruiken. "Afgerond"
> betekent hier niet dat SpeechBrain bewezen slechter is dan pyannote — zie
> `comparison/results.md` voor de (genuanceerde) vergelijking — alleen dat we
> er voorlopig niet verder aan werken. `Notebooks/04-diarization.ipynb`
> (actief) analyseert de output van beide modellen.

Verkennend, losstaand experiment. **Raakt de bestaande transcriptie-/diarizatiepipeline in
`Data-analysis/src` niet aan** — er wordt niets in dat pakket geïmporteerd, overschreven of
opnieuw gedraaid. Dit experiment *leest alleen* wat die pipeline al eerder produceerde:

- `Data-local/processed/diarization/{testaudio1,testaudio2,testaudio5}_fragment_diarized.json` — chunks (start/end/tekst)
- `Data-local/processed/diarization/{testaudio1,testaudio2,testaudio5}_fragment_16k_mono.wav` — bijbehorende audio

## Vraag

Kan een speaker-embeddingmodel, met maar één referentiefragment van de docent
(`Data-analysis/src/test-files/testdocent.mp3`), per audiochunk betrouwbaar onderscheiden of
dat **DOCENT** of **OTHER** (elke andere spreker) is — als lichter alternatief voor volledige
sprekerherkenning van alle individuele leerlingen?

## Structuur

```
speaker_recognition/
├── _common.py                              gedeelde helpers (paden, wav-slicing, cosine similarity, CSV-writer)
├── pyannote_embeddings/
│   └── test_teacher_recognition.py         experiment 1: pyannote/wespeaker-voxceleb-resnet34-LM
├── speechbrain_ecapa/
│   └── test_teacher_recognition.py         experiment 2: speechbrain/spkrec-ecapa-voxceleb
└── comparison/
    └── results.md                          volledige resultaten, distributie, threshold-keuze, conclusie
```

Output (buiten git, in `Data-local`, zoals de rest van de pipeline):

```
Data-local/processed/speaker_recognition/
├── testdocent_16k_mono.wav          (referentie, eenmalig geconverteerd, cache)
├── pyannote_teacher_similarity.csv
├── speechbrain_teacher_similarity.csv
└── _sb_model_cache/                 (lokale SpeechBrain modelcache)
```

## Referentie-audio

`Data-analysis/src/test-files/testdocent.mp3` was het enige docent-specifieke referentiebestand
in die map (naast de bestaande `testaudio*` en `testaudio*_fragment` bestanden) — dat is gebruikt
als teacher-enrollment-clip voor beide experimenten. Het bestand is niet verplaatst, hernoemd of
gewijzigd.

## Testaudio: waarom de `_fragment` bestanden, niet de volledige testaudio1/2/5.mp3

De opdracht noemde testaudio1, testaudio2 en testaudio5. Alleen de **`_fragment`**-versies
daarvan zijn al door de bestaande pipeline getranscribeerd én gediarizeerd (zie
`Data-local/processed/diarization/*_diarized.json`) — de volledige bestanden hebben geen
bestaande chunk-segmentatie. Conform de instructie om geen nieuwe zware segmentatiepipeline te
bouwen, hergebruikt dit experiment die bestaande `_fragment`-chunks (49 in totaal: 9 + 19 + 21).

## Draaien

Beide scripts draaien in de bestaande venv `Data-analysis/src/.venv` (geen nieuwe environment
nodig — zie `comparison/results.md` voor de dependency-check). Vanuit de repo-root:

```bash
Data-analysis/src/.venv/Scripts/python.exe Data-analysis/Experiments/speaker_recognition/pyannote_embeddings/test_teacher_recognition.py
Data-analysis/src/.venv/Scripts/python.exe Data-analysis/Experiments/speaker_recognition/speechbrain_ecapa/test_teacher_recognition.py
```

Zonder `--threshold` printen beide scripts alleen de similarity-distributie (geen
DOCENT/OTHER-voorspelling) — zo eerst kijken vóór je een grens kiest. Met een gekozen threshold:

```bash
Data-analysis/src/.venv/Scripts/python.exe Data-analysis/Experiments/speaker_recognition/pyannote_embeddings/test_teacher_recognition.py --threshold 0.35
Data-analysis/src/.venv/Scripts/python.exe Data-analysis/Experiments/speaker_recognition/speechbrain_ecapa/test_teacher_recognition.py --threshold 0.40
```

(0.35 / 0.40 zijn EXPERIMENTELE instellingen — gekozen door de similarity-distributie op
deze steekproef te inspecteren, geen gevalideerd/bewezen betrouwbaar criterium. Elke rij in
de CSV-output bewaart `pipeline_speaker` (origineel, ongewijzigd), `similarity` en `prediction`
apart naast elkaar, plus een expliciete `conflict`-kolom als de twee elkaar tegenspreken — zie
de kanttekeningen in `comparison/results.md`.)

## Resultaten

Zie **[comparison/results.md](comparison/results.md)** voor de volledige resultatentabel,
similarity-distributie, threshold-onderbouwing, duur-analyse en conclusie.
