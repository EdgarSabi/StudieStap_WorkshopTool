# Fase 4 — word-level speaker attribution

Verkennend experiment. **Raakt de bestaande pipeline in `Data-analysis/src`
niet aan** — niets wordt geïmporteerd-en-gewijzigd, alleen geïmporteerd en
read-only hergebruikt (zelfde patroon als `Afgeronde_experimenten/diarization/community1`
en `Experiments/speaker_recognition`). Geen nieuwe modellen getraind, geen
nieuw diarizationmodel onderzocht, geen dependencies toegevoegd.

## Vraag

Kunnen de bestaande Faster-Whisper- (`word_timestamps=True`) en
pyannote-componenten (bestaande diarization-turns + de WeSpeaker-embeddings
uit `speaker_recognition/`) gecombineerd worden om woorden nauwkeuriger aan
**DOCENT**/**OTHER** te koppelen — zonder WhisperX te adopteren?

## Structuur

```
word_level_speaker_attribution/
├── _common.py                              gedeelde paden/config, hergebruikt config.py + speaker_recognition/_common.py
├── 01_word_timestamps/
│   └── extract_word_timestamps.py          STAP 2: word_timestamps=True experiment
├── 02_word_level_attribution/
│   └── attribute_words_to_speakers.py      STAP 3: woorden koppelen aan bestaande pyannote-turns
├── 03_recognition_refinement/
│   └── refine_with_speaker_recognition.py  STAP 4: WeSpeaker-similarity op voldoende lange spraakstukken
└── comparison/
    └── results.md                          STAP 5+6: gerichte evaluatie + A/B/C-vergelijking + conclusie
```

Elke stap bouwt op de vorige (Step 3 heeft Step 2's output nodig, Step 4
heeft Step 2 én 3 nodig) en schrijft naar:

```
Data-local/processed/word_level_speaker_attribution/
├── <fragment>_words.json               (Stap 2: segmenten + per-woord timestamps/probability)
├── <fragment>_word_attribution.json    (Stap 3: woord-niveau speaker-labels + baseline-referentie)
└── <fragment>_recognition_refined.json (Stap 4: turn_level + segment_level recognition-check)
```

voor `testaudio1_fragment`, `testaudio2_fragment`, `testaudio5_fragment` —
dezelfde drie fragmenten als de eerdere `diarization/` en
`speaker_recognition/` experimenten.

## Draaien

Alles in de bestaande venv, geen nieuwe installs. Vanuit de repo-root, in
volgorde (elke stap heeft de vorige nodig):

```bash
Data-analysis/src/.venv/Scripts/python.exe Data-analysis/Experiments/word_level_speaker_attribution/01_word_timestamps/extract_word_timestamps.py
Data-analysis/src/.venv/Scripts/python.exe Data-analysis/Experiments/word_level_speaker_attribution/02_word_level_attribution/attribute_words_to_speakers.py
Data-analysis/src/.venv/Scripts/python.exe Data-analysis/Experiments/word_level_speaker_attribution/03_recognition_refinement/refine_with_speaker_recognition.py
```

Elk script accepteert `--fragment <naam>` (herhaalbaar) om één fragment te
draaien, en `--force` om bestaande output te overschrijven. Vereist
`HF_TOKEN` in `<repo-root>/.env` (zelfde als de bestaande diarization-setup)
voor Stap 3's pyannote-diarizationrun.

## Speaker recognition: labels, threshold, conflicten

Stap 4's output (`<fragment>_recognition_refined.json`) bewaart per
geëvalueerd spraakstuk altijd `diarization_label` (het oorspronkelijke,
ongewijzigde label), `similarity` (de recognition-score) en
`recognition_label` (het eventuele nieuwe label) **naast elkaar** —
`resolved_label` staat altijd op `null`: er wordt nooit automatisch een
winnaar gekozen. Spreken de twee elkaar tegen, dan wordt dat expliciet
gemarkeerd via `conflict: true` + een `agreement`-reden. De gebruikte
similarity-drempel (0.35) is een **experimentele instelling**, overgenomen
uit `speaker_recognition/comparison/results.md` — geen gevalideerd of
bewezen betrouwbaar criterium (zie `threshold_status` in elke output-file).

## Belangrijkste bevinding (kort)

- **AUDIO1** ("Dit ben jij. Dit ben ik.", één ASR-segment met twee sprekers):
  woordniveau-attributie (Stap 2+3) splitst dit **correct en zeker**, zonder
  WhisperX — hetzelfde resultaat als de eerdere WhisperX-vergelijking, maar
  zonder aparte omgeving/dependencies.
- **AUDIO2** (diarization ziet vrijwel geen sprekerwissel): woordniveau-
  attributie helpt hier **niet** — het probleem zit in het diarizationmodel
  zelf, niet in de koppelmethode (bevestigt de eerdere WhisperX-conclusie).
  Speaker recognition **op ASR-segmentniveau** (losgekoppeld van de
  diarization-turns) vindt hier wél 2 bruikbare conflictsignalen.
- Zie **[comparison/results.md](comparison/results.md)** voor de volledige
  onderbouwing, foutenanalyse en de A(bestaand)/B(word-level)/C(+recognition)
  vergelijking.
