# Implementatierapport StudieStap 2.0

Datum: 2026-10-13. Locatie: `C:\Users\School\StudieStap\StudieStap_V2` (eigen git-repo, nog **geen commits**).

## Samenvatting in een alinea

Mijlpalen A tot en met D zijn gebouwd. **87 synthetische tests slagen**, **19 van 19 bewust ingebouwde fouten worden afgekeurd**, en er is
**een echte modelrun** gedaan op `testaudio4_fragment.mp3` (zie "Echte modelrun"). Daarmee zijn criteria 3, 4 en 5 voor dit ene fragment aangetoond;
docentherkenning (WeSpeaker) is nog **niet** echt gedraaid.

## Inventarisatie van de oude repository (alleen gelezen)

* Werkend en overgenomen als idee: transcriptie-instellingen (medium, nl, cpu, int8, beam 5, VAD aan); pyannote 3.1;
  eigen WAV-inlezer (voorkomt torchcodec-problemen op Windows); lossless intersecties; WeSpeaker-docentherkenning met experimentele drempel 0.35.
* Bekende fouten/risico's meegenomen: sprekerlabel per segment gooide overlap weg (opgelost op de branch `feature/lossless-speaker-intersections`);
  `MAIN_SPEAKER` = "praat het meest" werd makkelijk als "docent" gelezen (hier vervangen door aparte identiteit en rol);
  ongevalideerde drempels (nu als experimenteel gemarkeerd); de oude `src/.venv` (Python 3.14) bevat pyannote maar geen whisperx.
* Lokaal aanwezig in de HF-cache (waargenomen met `studiestap check`, niet uitgevoerd): `Systran/faster-whisper-medium`,
  `pyannote/speaker-diarization-3.1`, `pyannote/segmentation-3.0`, `pyannote/wespeaker-voxceleb-resnet34-LM`,
  `jonatasgrosman/wav2vec2-large-xlsr-53-dutch` (Nederlandse WhisperX-aligner). Downloaden van modellen lijkt dus niet nodig.
* Oude repository na afloop: zelfde branch (`feature/lossless-speaker-intersections`), zelfde commit (`afefb0a`), dezelfde 15 untracked
  paden als bij de start, geen gewijzigde bestanden. Geen audio verplaatst, geen `.env` gekopieerd of gelezen.

## Mijlpaal A - Fundament

**Gemaakt:** `pyproject.toml`, `config.yaml`, `.env.example`, `.gitignore`, `src/studiestap/{__init__,models,settings}.py`,
`audio/loader.py`, `output/exporter.py`, `tests/conftest.py`, `tests/test_foundation.py`.
(CLI en pipeline zijn in mijlpaal B afgemaakt.)

**Uitgevoerd:** `pytest tests/test_foundation.py` - 16 tests. Verwachtingen stonden vooraf in de testcommentaren.
**Resultaat:** eerste run 15 geslaagd, 1 mislukt. De test vond een **echte fout**: op Windows schreef `write_text` regeleinden als `\r\n`,
waardoor de gerapporteerde sha256 niet bij het bestand paste. Opgelost (bytes schrijven). Daarna alles geslaagd.
Gedekt: modellen -> JSON; defaults = oude baseline; `config.yaml` = defaults; typfouten in config worden afgekeurd; token komt niet in provenance;
ontbrekend/leeg/verkeerd/kapot audiobestand; conversie naar 16 kHz mono 16-bit; origineel byte-identiek en mtime ongewijzigd;
`clean` weigert mappen zonder manifest; databasesamenvatting bevat geen tekst of pad.
**Niet gedaan:** MP3-specifieke test (alleen synthetische WAV en een kapot `.mp3`-bestand).

## Mijlpaal B - Spraakpipeline

**Gemaakt:** `transcription/whisper.py`, `diarization/pyannote.py`, `alignment/words.py`, `alignment/speakers.py`, `pipeline.py`, `cli.py`,
`tests/test_speakers.py` (19), `tests/test_models_wrappers.py` (10), `tests/test_pipeline.py` (18, deels mijlpaal C).

**Uitgevoerd:** unit-tests voor sprekerkoppeling (sprekerwissel, gelijkspel, echte overlap, dubbele intervallen van een spreker, rakende grens,
nul-duur, lege diarizatie, eigenschapstest over 200 willekeurige situaties dat elk overlappend interval precies een keer als intersectie bewaard blijft,
woorden `SINGLE/AMBIGUOUS/NO_TIMING/NO_SPEAKER`); integratietests met **nep-modellen** voor transcriptie, pyannote-uitvoer (v3- en v4-vorm), uitlijning
(geslaagd/gedeeltelijk/mislukt/niet beschikbaar/segmentmismatch) en de hele pipeline (cache, `--force`, gewijzigde instellingen, kapotte cache, falende diarizatie,
niet-beschikbare uitlijning, falende transcriptie, werkaudio verwijderd, geen token in uitvoer, hashes in provenance kloppen).
**Resultaat:** alle geslaagd.
**Vergelijking met de bestaande pipeline** (`tools/compare_with_old.py`, `docs/vergelijking_oude_pipeline.txt`; alleen opgeslagen oude uitvoer gelezen,
drie oude uitvoerbestanden met 87, 24 en 19 segmenten; twee oudere testaudio2-runs bevatten de intersectievelden nog niet en zijn overgeslagen): alle intersecties identiek (0 verschillen);
de dominante spreker verschilt nergens; in 9 segmenten (7 + 2) koos de oude code een dominante spreker waar de nieuwe geen kiest. De 7 van testaudio4 heb ik nagekeken: telkens bedekten
twee sprekers het volledige segment even lang (volledige gelijktijdigheid), dus de oude keuze was willekeurig; de 2 van testaudio5 zijn niet nagekeken. "Meerdere sprekers" komt overeen (57/57, 11/11, 7/7).
Dit vergelijkt twee implementaties van dezelfde tijdrekenkunde en zegt **niets** over de nauwkeurigheid van de diarizatie.
**Rooktest CLI (geen modellen):** `studiestap check`, `analyze` op niet-bestaand pad, `transcribe` op synthetische WAV: nette Nederlandse foutmelding met tip, exitcode 1, geen traceback.
**Niet gedaan:** geen echte modelrun. De aanroepen naar `faster_whisper`, `pyannote.audio` en `whisperx` (o.a. `whisperx.load_align_model`, `whisperx.align`,
`DEFAULT_ALIGN_MODELS_*`) volgen de oude code en mijn kennis van de API's maar zijn **niet tegen de geinstalleerde versies gecontroleerd**.

## Mijlpaal C - Docentrollen en kwaliteit

**Gemaakt:** `recognition/teacher.py`, `quality/checks.py`, `tests/test_teacher_quality.py` (16) + rollen/kwaliteit-tests in `test_pipeline.py`.
**Uitgevoerd:** `MATCH/NO_MATCH/UNKNOWN/NO_REFERENCE`, rol "docent" alleen bij `MATCH`; te korte of niet-embeddbare stukken zijn `UNKNOWN` (geen bewijs tegen);
drempelgrens; mediaan met uitschieter; overlappende spraak wordt uitgesloten van het embedden; falende herkenning geeft `UNKNOWN`, niet `NO_MATCH`;
kwaliteitssignalen (ASR, sprekers, overlap, ambigue woorden, uitlijning, onbekende identiteit, ontbrekende diarizatie) met `kind: "observed"`; tekst blijft bij onzekere rol; lege tekst = `NOT_ASSESSABLE`.
**Resultaat:** alle geslaagd. **Beperking:** zonder referentieopname krijgt elk segment het signaal `SPEAKER_IDENTITY_UNKNOWN`, dus ook `REVIEW_REQUIRED`
(bedoeld: voor docentspecifieke indicatoren is rol nodig, maar het maakt de segmentstatus weinig onderscheidend zonder referentie).

## Mijlpaal D - Classificatiebasis en eindcontrole

**Gemaakt:** `classification/base.py`, `classification/indicators.py` (leeg register), `examples/mijn_indicator.py`, `examples/example_result.json`
(synthetisch, `tools/make_example.py`), `tests/test_classification.py` (6), documentatie (README, ARCHITECTURE, HOW_IT_WORKS, DECISIONS, dit rapport).
**Uitgevoerd:** leeg register meldt `NOT_IMPLEMENTED`; sjabloon is standaard `NOT_IMPLEMENTED`; als student-implementatie gesimuleerd: `DETECTED` alleen met bewijs,
`UNKNOWN` bij onzekere kwaliteit, `NOT_ASSESSABLE` bij geen bruikbare tekst; kapotte indicator crasht de run niet; de pipeline geeft de indicator tekst, rollen en kwaliteitsstatus.
**Falsificatiecontrole:** `python tools/mutation_check.py` - **19 van 19** bewuste fouten afgekeurd (o.a. intersecties weggooien, gelijkspel toch kiezen, twijfelwoord toewijzen, cache negeert instellingen,
`--force` stuk, audiokopie blijft staan, elke map verwijderbaar, niet-docent = "leerling", typfout in config genegeerd, ruwe intervallen weggooien, lege classificatie meldt detectie).
**Eindcontrole privacy/Git:** `.env` en `.env.*` genegeerd, `.env.example` niet; `git add -n` bevat alleen broncode, tests, documentatie en synthetische voorbeelden;
geen `hf_`-tokenpatroon in de bestanden; er is **geen** `.env` aangemaakt of uit de oude repo gekopieerd.


## Echte modelrun (uitgevoerd 2026-10-13)

* **Invoer:** `Data-analysis/src/test-files/testaudio4_fragment.mp3` (120 s), alleen gelezen vanaf de oorspronkelijke plek. Geen referentieopname gebruikt.
* **Omgeving:** Python 3.12.6, faster-whisper 1.2.1, pyannote.audio 4.0.7, whisperx 3.8.6, torch 2.8.0 (CPU), ctranslate2 4.8.3, av 18.1.0 (`docs/requirements-lock.txt`).
  Modellen kwamen uit de lokale cache met `huggingface.offline: true`; er is **geen token en geen `.env` gebruikt**, er is niets gedownload.
* **Resultaat:** transcriptie 87 segmenten (144,8 s rekentijd), diarizatie 63 ruwe intervallen, 2 sprekers (90,1 s), woorduitlijning geslaagd (42,3 s),
  eindresultaat geschreven. Tweede run hergebruikte transcriptie en diarizatie (geen dubbele modeluitvoering) en duurde 44 s.
* **Vergelijking met de oude baseline (zelfde fragment):** 87/87 segmenten met identieke begin-/eindtijden en identieke tekst; dezelfde 2 ruwe sprekers;
  57 `MIXED`-segmenten, gelijk aan de 57 "meerdere sprekers" van de oude run. Dat laat zien dat de nieuwe pijplijn de oude reproduceert, **niet** dat de uitvoer juist is.
* **Woordniveau:** 420 woorden: 306 `SINGLE`, 114 `AMBIGUOUS` (27%, geen spreker toegewezen). Segmenten: 57 `MIXED`, 27 `SINGLE`, 3 `PARTIAL`.
  Alle 87 segmenten `REVIEW_REQUIRED` (door `MIXED` en/of onbekende docentidentiteit). Nauwkeurigheid van sprekers of woordtijden is **niet** gemeten.
* **Gevonden en opgelost tijdens de echte run (de mock-tests konden dit niet zien):**
  1. `av` 19 is niet compatibel met faster-whisper 1.2.1 -> `av==18.1.0` vastgezet in `pyproject.toml`.
  2. WhisperX splitst segmenten in zinnen (90 uitvoer- voor 87 invoersegmenten) -> woorden worden nu aan het invoersegment met de meeste tijdoverlap gehangen
     (nieuwe tests + aangepaste mutatiecontrole).
* **Waarschuwingen in de run:** pyannote meldt dat torchcodec niet laadt (FFmpeg-DLL's); dit is onschuldig omdat we een waveform meegeven. Eenmalige `std()`-waarschuwing van pyannote.

## Echte run docentherkenning (2026-10-13)

* **Invoer:** hetzelfde fragment + `testdocent.mp3` als referentie (alleen gelezen). Transcriptie, diarizatie en uitlijning kwamen uit de cache; WeSpeaker uit de lokale cache, offline.
* **Resultaat:** `SPEAKER_00` = `MATCH` (mediaan gelijkenis 0,549, 10 stukken) -> rol `docent`; `SPEAKER_01` = `NO_MATCH` (0,137, 10 stukken) -> rol `onbekend`. Totale rekentijd 14 s.
  Segmenten: 27 `ASSESSABLE`, 60 `REVIEW_REQUIRED`; geen globaal signaal `NO_TEACHER_REFERENCE` meer.
* **Vergelijking met de oude pipeline** (opgeslagen run, per beurt): oud noemde de beurten van `SPEAKER_00` voornamelijk `DOCENT` (61,0 s), met 15,1 s `ONZEKER` en 1,0 s `OTHER`; `SPEAKER_01` was `OTHER` (29,4 s) of `ONZEKER` (10,6 s).
  De mediane gelijkenis per beurt was 0,525 resp. 0,126, vergelijkbaar met onze 0,549 en 0,137. Dezelfde richting dus; de aanpak (per spreker, alleen stukken zonder overlap) verschilt.
* **Wat dit niet bewijst:** dat `SPEAKER_00` echt de docent is (er is geen onafhankelijke referentie gebruikt) of dat de drempel 0.35 bruikbaar is buiten dit ene fragment.
  `NO_MATCH` betekent alleen "lijkt niet op de referentie", niet "leerling".

## Wat nog niet werkt / nog te doen

1. *(opgelost, zie hieronder)* Docentherkenning is daarna wel echt gedraaid.
2. Of de experimentele drempel 0.35 algemeen bruikbaar is, blijft een onderzoeksvraag: hier is een fragment met een referentie bekeken.
3. Er zijn nog geen commits gemaakt in `StudieStap_V2`.

## Bekende beperkingen

* `MIXED` en `SPEAKER_MIXED` hebben geen minimale overlap: ook milliseconden randoverlap tussen sprekers telt mee (bewust, zodat er geen nieuwe ongevalideerde drempel is). Verwacht veel `MIXED`
  (oude runs: 57 van 87 segmenten). Gebruik `seconds_per_speaker`/`simultaneous_seconds` om later te drempelen.
* Woordniveau: elk woord dat meerdere sprekers overlapt is `AMBIGUOUS`; de nauwkeurigheid van WhisperX-woordtijden is niet gemeten.
* Docentherkenning werkt per ruwe spreker; als diarizatie een persoon splitst of twee personen samenvoegt, zegt `MATCH`/`NO_MATCH` daar niets over (signaal `MULTIPLE_TEACHER_MATCHES` dekt alleen het eerste deels).
* Geen herhalingsdetectie voor Whisper-"hallucinaties" (oude heuristiek niet overgenomen).
* Unit-tests en de reproductie van de oude baseline bewijzen **geen** modelnauwkeurigheid. Er zijn geen nauwkeurigheidsmetingen (WER/DER) uitgevoerd; ground truths zijn niet gebruikt of gewijzigd.
* SQLite-export is alleen gereserveerd (`summary_for_database`), niet gebouwd. Andere diarizatie-backends zijn alleen voorbereid (`BACKENDS`).
* `output\` is een gewone lokale map; er is geen Windows-rechtenbeheer ingesteld (alleen buiten Git gehouden).
