# Architectuur

## De pipeline in een oogopslag

```
audio (mp3/wav)
   |  audio/loader.py        controleren, naar 16 kHz mono WAV (werkkopie), sha256
   v
01_transcript.json           transcription/whisper.py     faster-whisper medium      (RUW)
02_diarization_raw.json      diarization/pyannote.py      pyannote 3.1, incl. overlap (RUW)
03_word_alignment.json       alignment/words.py           WhisperX op bestaande segmenten + status
   |
   v
04_speaker_assignment.json   alignment/speakers.py        ALLE intersecties + samenvatting (AFGELEID)
05_teacher_roles.json        recognition/teacher.py       WeSpeaker vs. referentie: identiteit <> rol (AFGELEID)
06_quality.json              quality/checks.py            waargenomen signalen, geen oordeel
   |
   v
07_result.json               pipeline.py                  alles samengevoegd + provenance
run_manifest.json            instellingen, versies, stapstatus, hashes
```

`classification/` (lege interface) krijgt aan het eind een `ConversationContext` en schrijft zijn resultaat onder
`classification` in `07_result.json`. `output/exporter.py` schrijft JSON, verwijdert runs en bevat de reservering
voor een toekomstige, geaggregeerde SQLite-export.

## Verantwoordelijkheden (een module = een taak)

| Module | Doet | Doet bewust NIET |
|---|---|---|
| `audio/loader.py` | valideren, omzetten, hash | het origineel wijzigen of verplaatsen |
| `transcription/whisper.py` | audio -> segmenten + ruwe ASR-signalen | sprekers, woordtijden |
| `diarization/pyannote.py` | ruwe sprekerintervallen | rollen, "hoofdspreker", overlap oplossen |
| `alignment/words.py` | woordtijden via WhisperX; status | opnieuw transcriberen |
| `alignment/speakers.py` | intersecties, woord-/sprekerkoppeling | een model gebruiken; raden bij twijfel |
| `recognition/teacher.py` | stem vs. referentie | een spreker-ID als rol behandelen |
| `quality/checks.py` | signalen verzamelen | betrouwbaarheid bewijzen of kalibreren |
| `classification/` | interface voor jouw indicatoren | iets classificeren |
| `pipeline.py` | stappen verbinden, cache, foutafhandeling | eigen logica |
| `cli.py` | commando's en uitleg aan de gebruiker | |

## Gegevensregels

* **Ruw en afgeleid zijn gescheiden.** 01-03 worden nooit door latere stappen aangepast.
* **Niets stilzwijgend weggooien.** Alle sprekerintervallen en alle intersecties worden bewaard.
  Een "dominante spreker" is een samenvatting en heet zo in de uitvoer.
* **Twijfel is zichtbaar.** Woordstatus `AMBIGUOUS`/`NO_TIMING`, segmentstatus `MIXED`/`PARTIAL`/`NONE`,
  identiteit `UNKNOWN`/`NO_REFERENCE`, kwaliteitssignalen.
* **Tekst blijft behouden**, ook als sprekers of rol onzeker zijn (alleen als de tekst zelf ontbreekt is een segment `NOT_ASSESSABLE`).
* **Herleidbaar:** `07_result.json -> provenance.parts` bevat per deelbestand de sha256; `run_manifest.json` bevat
  de configuratie en pakketversies. Geen token, geen audio in de uitvoer.

## Stapstatussen

`succeeded`, `partial`, `unavailable`, `failed`, `skipped`. Alleen een mislukte transcriptie stopt de run; alle andere
stappen laten de pipeline gecontroleerd doorgaan (bijv. zonder woordtijden, zonder sprekers of zonder referentie).

## Later uitbreiden

* Andere diarizatie-backend: nieuwe klasse met `diarize(wav) -> Diarization`, registreren in `BACKENDS`
  (`diarization/pyannote.py`), naam in `config.yaml`. Niet geimplementeerd, alleen voorbereid.
* SQLite: `output/exporter.py::summary_for_database` geeft alleen geaggregeerde getallen (geen tekst, pad of embeddings).
