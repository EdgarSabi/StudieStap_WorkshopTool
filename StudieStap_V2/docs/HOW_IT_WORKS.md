# Hoe werkt het? Elke module met voorbeelden

Voor elke module: wat gaat erin, wat komt eruit, hoe pas je het aan en hoe test je het.
Alle gegevensvormen staan in `src/studiestap/models.py` (gewone dataclasses).

## Hoe bewegen de gegevens?

```
MP3  -->  Segment(id, start, end, text, ASR-cijfers)           [01_transcript.json]
MP3  -->  SpeakerInterval(speaker, start, end)  (mag overlappen) [02_diarization_raw.json]
Segment --WhisperX--> Word(text, start, end)                     [03_word_alignment.json]
Segment + SpeakerInterval (+ Word) --> SegmentSpeakers           [04_speaker_assignment.json]
SpeakerInterval + referentie --> SpeakerRole                     [05_teacher_roles.json]
SegmentSpeakers + SpeakerInterval --> SegmentVoiceCheck (optioneel) [05b_voice_consistency.json]
alles --> Signal / SegmentQuality                                [06_quality.json]
alles samen --> 07_result.json  -->  ConversationContext --> jouw indicatoren
```

## `audio/loader.py`
`prepare_audio("opname.mp3", werkmap)` controleert het bestand (bestaat, niet leeg, .mp3/.wav/.m4a), laat ffmpeg een
16 kHz mono WAV maken en berekent de sha256. Het origineel wordt alleen gelezen. Beschadigd bestand -> nette fout.
*Aanpassen:* extra formaten in `SUPPORTED_EXTENSIONS`. *Testen:* `tests/test_foundation.py` (synthetische WAV's).

## `transcription/whisper.py`
`transcribe(wav, settings)` -> `Transcript`. Instellingen (model, device, compute type, beam, VAD) komen uit `config.yaml`.
De ruwe ASR-cijfers (`avg_logprob`, `no_speech_prob`, `compression_ratio`) worden ongewijzigd bewaard.
*Testen zonder model:* geef `model_factory=` mee (zie `tests/test_models_wrappers.py`).

## `diarization/pyannote.py`
Geeft de ruwe intervallen van pyannote. Twee sprekers tegelijk = twee overlappende intervallen; die blijven zo bestaan.
Het model wordt geladen met je `HF_TOKEN` (als aanwezig) of uit de lokale cache (zet dan `huggingface.offline: true`).
Een andere backend later? Zie `BACKENDS` onderaan het bestand.

## `alignment/words.py`
WhisperX krijgt de **bestaande** Whisper-segmenten en geeft per woord een tijd (geen tweede transcriptie).
Statussen: `succeeded` / `partial` / `unavailable` (geen whisperx, model of taal) / `failed`. Bij `unavailable`/`failed` gaat de
pipeline door op segmentniveau en worden er geen woordnauwkeurige claims gedaan.

## `alignment/speakers.py` - het belangrijkste stuk
Voorbeeld: segment 0-4 s, sprekerintervallen A 0-3 en B 3-4.

```json
{"intersections": [{"speaker":"A","start":0,"end":3}, {"speaker":"B","start":3,"end":4}],
 "seconds_per_speaker": {"A":3.0,"B":1.0}, "attribution":"MIXED",
 "dominant_speaker":"A", "dominant_share":0.75}
```

* `intersections` = alles; `dominant_speaker` = alleen samenvatting (bij exact gelijkspel `null`).
* `attribution`: `SINGLE` (een spreker dekt genoeg), `PARTIAL` (een spreker dekt weinig), `MIXED` (>= 2 sprekerlabels),
  `NONE` (niemand). `simultaneous_seconds` = tijd dat >= 2 sprekers tegelijk actief zijn.
* Per woord (met woordtijden): `SINGLE`, `AMBIGUOUS` (meerdere sprekers; **geen** keuze, kandidaten staan erbij),
  `NO_SPEAKER`, `NO_TIMING` (woord zonder tijd: niets te koppelen).

*Testen:* `tests/test_speakers.py` (sprekerwissel, overlap, ontbrekende woorden, eigenschapstest dat niets verdwijnt).

## `recognition/teacher.py`
Vergelijkt de stem van elke ruwe spreker met een **expliciet opgegeven** referentieopname (`--teacher-reference`) via
WeSpeaker. Alleen stukken zonder andere sprekers en van minstens `min_clip_seconds` worden vergeleken; de mediaan van de
gelijkenis (ruwe cosinus, **geen kans**) wordt tegen de experimentele drempel gehouden.

| identity_status | betekenis | role |
|---|---|---|
| `MATCH` | stem lijkt op referentie | `docent` |
| `NO_MATCH` | stem lijkt er niet op | `onbekend` (niet automatisch "leerling") |
| `UNKNOWN` | te weinig bruikbare audio / embedden mislukt | `onbekend` |
| `NO_REFERENCE` | geen referentie opgegeven | `onbekend` |

## `recognition/voice_consistency.py` (optioneel, standaard uit)
Extra controle: klinkt de stem in een segment als de spreker aan wie pyannote het segment gaf? Aanleiding: pyannote kan
een lang interval als één spreker melden terwijl er meerdere beurten in zitten; de koppeling en de docentrol erven dat
dan zonder dat het ergens opvalt (zie `SPEAKER_ERROR_DIAGNOSIS.md`).

* **Wat ze ontvangt:** de sprekerkoppeling (`SegmentSpeakers`), de ruwe sprekerintervallen en de audio (via dezelfde WeSpeaker-
  functies als docentherkenning). Een referentieopname van de docent is niet nodig.
* **Wat ze berekent:** (1) per ruwe spreker een stemprofiel: het gemiddelde van de langste stukken zonder andere sprekers;
  (2) per segment het stuk waarin alleen de dominante spreker actief is (minstens `min_clip_seconds`, nu 1 s); (3) de
  cosinusgelijkenis van dat stuk met het profiel van het eigen label en van het andere label. Stukken die het segment zelf
  overlappen tellen niet mee in de profielen.
* **Wat ze teruggeeft** (`SegmentVoiceCheck`, in `05b_voice_consistency.json` en in `07_result.json` onder `voice_consistency`):
  `CONSISTENT` (stem past bij het label), `CLOSER_TO_OTHER_SPEAKER` (stem lijkt meer op het andere label **en** valt buiten wat
  de eigen stukken van die spreker onderling laten zien), of `INCONCLUSIVE` met een `reden` (te kort, overlap, geen
  dominante spreker, te weinig referentiestukken, of tegenstrijdige scores). Er is geen vaste drempel; alleen `CLOSER_TO_OTHER_SPEAKER` geeft in
  `quality/checks.py` het signaal `VOICE_CLOSER_TO_OTHER_SPEAKER` (dus `REVIEW_REQUIRED`). De scores staan er altijd bij.
* **Wat ze niet kan bewijzen:** dat een segment van een andere persoon is. De profielen komen van pyannote zelf (heeft pyannote
  twee mensen in één label gestopt, dan is dat profiel vervuild), korte stukken (< 1 s, in de testopname 48 van 87 segmenten) worden niet
  beoordeeld, en een stem kan door toon, afstand of ruis afwijken. Het blijft een waarneming: luister het segment na. De module past
  nooit sprekerlabels, intervallen of tekst aan.
* **Praktische, niet-gevalideerde keuze:** `MIN_OWN_CLIPS = 3` (bovenaan `voice_consistency.py`): een label met minder dan 3 eigen
  referentiestukken (na uitsluiten van het segment zelf) levert `INCONCLUSIVE`, omdat er dan geen "eigen bereik" te bepalen is. Dit getal is
  een pragmatische ondergrens, niet getoetst op gelabelde opnames; ook `min_clip_seconds` (1 s) is een overgenomen instelling.
* **Geen zekerheid door deze module:** `CONSISTENT` en `INCONCLUSIVE` voegen niets toe en verbeteren nooit een signaal of status
  (`ASSESSABLE` blijft "geen signalen waargenomen"); alleen `CLOSER_TO_OTHER_SPEAKER` kan een waarschuwing toevoegen.
* **In- of uitschakelen:** in `config.yaml`:
  ```yaml
  voice_consistency:
    enabled: true     # false (standaard) = de stap draait niet en er verschijnt geen bestand
  ```
  Staat de optie uit, dan is `07_result.json` gelijk aan de oude uitvoer (alleen de gedocumenteerde instellingen bevatten een extra sectie). Model en apparaat komen uit `teacher_recognition`. Het kost extra rekentijd (WeSpeaker op ongeveer 20 stukken plus elk segment) en wordt niet gecachet.
* *Testen:* `tests/test_voice_consistency.py` (nep-embeddings, inclusief gevallen die `INCONCLUSIVE` moeten blijven).

## `quality/checks.py`
Verzamelt **waargenomen** signalen (`kind: "observed"`): lage ASR-cijfers (Whisper-standaarddrempels), `SPEAKER_MIXED`,
`POSSIBLE_SIMULTANEOUS_SPEECH`, `AMBIGUOUS_WORD_SPEAKERS`, `WORDS_NOT_FULLY_ALIGNED`, `SPEAKER_IDENTITY_UNKNOWN`, `VOICE_CLOSER_TO_OTHER_SPEAKER` (alleen als de stemconsistentie aan staat), en globaal
`DIARIZATION_MISSING`, `WORD_ALIGNMENT_*`, `NO_TEACHER_REFERENCE`. Segmentstatus: `NOT_ASSESSABLE` (geen tekst),
`REVIEW_REQUIRED` (minstens een signaal), `ASSESSABLE` (geen signalen; **geen bewijs van betrouwbaarheid**).
De echte regels volgen uit jouw onderzoeksfases 3 en 4; pas ze dan hier aan.

## `pipeline.py` en `cli.py`
`run_pipeline(...)` voert de stappen uit, hergebruikt resultaten (zelfde audio + instellingen) en schrijft het manifest.
`Backends` bundelt de zware stappen als functies, zodat tests nep-modellen kunnen gebruiken.

## Je eigen indicator toevoegen (didactische classificatie)

1. Kopieer `examples/mijn_indicator.py` naar `src/studiestap/classification/mijn_indicator.py`.
2. Geef hem een `name` en schrijf `zoek_fragment(self, uiting)`: geef het **letterlijke fragment** terug waaraan je de indicator
   herkent, of `None`. Hier komt jouw Python-code:
   * **tokenization:** tekst in woorden splitsen (bijv. `uiting.text.lower().split()` of `nltk`/`spaCy`);
   * **POS-tagging:** woordsoorten (bijv. spaCy `nl_core_news_sm`), voor zinsbouw;
   * **regels:** patronen op woorden/zinsbouw;
   * **klassieke ML:** bijv. scikit-learn getraind op je eigen gelabelde, synthetische of toegestane data.
   Voeg het pakket zelf toe aan `pyproject.toml`.
3. Zet `geimplementeerd = True`.
4. Registreer: in `classification/indicators.py` -> `INDICATORS = [MijnIndicator()]`.
5. Schrijf tests met synthetische zinnen (wel/niet) naar het model van `tests/test_classification.py`, en draai `pytest`.

De uitingen die je krijgt (`Utterance`) hebben `text`, `speakers`, `roles` (`docent`/`onbekend`) en `review_status`.
Regels van het project: onzeker -> `UNKNOWN`/`NOT_ASSESSABLE`; `DETECTED` altijd met `Evidence`; nooit raden.

## Zelf een module aanpassen en testen
1. Bedenk het gewenste gedrag en schrijf eerst de test met de verwachte uitkomst (en een tegenvoorbeeld).
2. Pas de code aan; draai `pytest`.
3. Draai `python tools/mutation_check.py` of voeg daar je eigen "bewuste fout" toe: de tests moeten die afkeuren.
