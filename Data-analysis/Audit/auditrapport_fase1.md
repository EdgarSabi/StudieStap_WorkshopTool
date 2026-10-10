# Onafhankelijke technische audit — StudieStap fase 1

Uitgevoerd op de bestanden in de repo (branch `main`, commit 33cc8a1 + niet-gecommitte wijzigingen). Er zijn geen bestaande bestanden gewijzigd, niets verwijderd en niets geüpload. Nieuwe bestanden staan uitsluitend in `Data-analysis/Audit/`. Er is geen vergelijking gemaakt met andere auditrapporten.

**Leeswijzer:** *[GETEST]* = ik heb het uitgevoerd en het resultaat staat in dit rapport. *[CODE]* = alleen uit code-inspectie, niet uitgevoerd. *[NOTEBOOK-UITVOER]* = afgeleid uit de opgeslagen cel-uitvoer van een notebook (de onderliggende bestanden bestaan niet in de repo).

---

## 1. Samenvatting

**Voorlopig oordeel:** de code is netjes opgebouwd en de bestaande 68 unit-tests slagen, maar de *gerapporteerde betrouwbaarheid* van de resultaten is niet onderbouwd. De hoofdreden: **de "ground truth" is voor een groot deel afgeleid van de Whisper-uitvoer die ermee getoetst wordt**. Daardoor is WER nergens onafhankelijk meetbaar en is de diarizatie-"nauwkeurigheid" geen DER.

Belangrijkste bevindingen:

1. **Circulaire referentie (kritiek).** [GETEST] Mijn eigen herhaalde Whisper-run (medium, pipeline-standaard) geeft **WER 0,000** op `testaudio2_fragment` (118 woorden) en `testaudio4_fragment` (420 woorden); bij `testaudio2` en `testaudio7` vallen 100% van de ground-truth-rijgrenzen exact samen met de ASR-segmentgrenzen. De README van de tuning-map bevestigt: "startpunt voorgevuld uit de Whisper-segmenten". Een WER van 0 op rumoerige klasaudio is niet plausibel als onafhankelijke meting.
2. **Geen echte DER-meting aanwezig (hoog).** De "totaal juist %" in `evaluate_min_cluster_size.py` is geen DER: valse alarmen en gemiste spraak buiten de ground-truth-rijen tellen niet mee, en overlap wordt als "goed" geteld zodra één van de actieve sprekers klopt.
3. **De `overlap`-vlag meet geen overlap (hoog).** [GETEST] Een sprekerwissel *binnen* één segment (A 0–4 s, B 4–5 s, niemand praat tegelijk) wordt als `overlap=True` gevlagd. Tegen de eigen ground truth: 16 van 22 gevlagde segmenten zijn vals alarm (zie §5, T9).
4. **Kwaliteitsmaten van Whisper zijn per 30-seconden-venster, niet per segment (hoog).** [GETEST + bibliotheekcode] Alle segmenten in hetzelfde venster hebben identieke `avg_logprob`/`no_speech_prob`/`compression_ratio`. `quality_flags` kunnen dus geen individueel slecht segment aanwijzen.
5. **Er is geen "niet beoordeelbaar"-pad voor de ASR/diarizatie zelf (hoog).** Stilte en witte ruis geven stil 0 segmenten en geen status [GETEST]. Alleen docentherkenning kent `ONZEKER`.
6. **Reproduceerbaarheid is zwak (hoog).** De notebooks zijn niet uitvoerbaar op een andere computer: de data (`Data-local/processed`, `*_manual.txt`) staat niet in de repo, notebook 04 bevat een ander absoluut pad dan de huidige locatie, en cellen zijn out-of-order uitgevoerd.
7. **Er is géén scraper en géén NLP-voorbewerking met `CountVectorizer`/tokenization in de repo.** Onderdelen B en (deels) H uit de opdracht zijn daarmee niet van toepassing; de classificatie is een mock.

**Wat aantoonbaar werkt:** de ASR is reproduceerbaar (mijn run gaf dezelfde segmenten als de eerdere run in notebook 03); VAD onderdrukt stilte/ruis; tijdstempels blijven correct na 15 s stilte; transcriptie is robuust voor 8 kHz; `assign_speakers` behandelt segmenten zonder diarizatie-spraak correct; Pydantic-modellen weigeren een ontbrekend `text`-veld; preprocessing bewaart elk bronsegment (assert + `source_segments`).

**Geschikt als basis voor fase 2?** Voorwaardelijk. De architectuur (flags, ONZEKER, traceerbaarheid) is een goede basis, maar vóór classificatie moeten (a) een onafhankelijke referentie en echte DER/WER, (b) een correcte overlap-definitie en (c) een expliciete "niet beoordeelbaar"-status komen.

---

## 2. Projectinventarisatie

**Werkelijke pipeline** (`Data-analysis/src/`, start via `run_docent_pipeline.py`, dat via `subprocess` vier scripts aanroept):

| Stap | Bestand | Model / methode | In → uit |
|---|---|---|---|
| 1 | `transcription.py` | faster-whisper 1.2.1, `medium` (pipeline-default; `config.py` default `base`), cpu/int8, `nl`, beam 5, VAD aan | mp3/wav/m4a → `Data-local/processed/<stem>.json` |
| 2 | `diarization.py` | `pyannote/speaker-diarization-3.1` via pyannote.audio 4.0.7 (HF-token nodig); eigen tijd-overlap-koppeling aan ASR-segmenten | transcript-JSON + audio → `…/diarization/<stem>_diarized.json` |
| 3 | `preprocessing.py` | regelgebaseerd samenvoegen tot spreekbeurten + contextvlaggen | → `…/preprocessing/*_turns.json` |
| 4 | `docent_recognition.py` | `pyannote/wespeaker-voxceleb-resnet34-LM` embedding, cosine vs. 1 referentieclip, drempel 0,35 | → `…/docent_recognition/*_docent_roles.json` |

Overig: `models.py` (Pydantic), `config.py`, `evaluation/wer.py` (jiwer, niet in requirements), `OLD_benchmark_transcription.py`. Experimenten: `Experiments/` (classificatie-mock, diarizatie-tuning, speaker_recognition, word_level_speaker_attribution, whisperx), `Afgeronde_experimenten/`. Notebooks: 01–06. Testbestanden: 13 mp3 in `src/test-files/` (44,1/48 kHz, stereo).

**Ontbreekt of niet aanwezig:** scraper/downloader; `.env`/HF-token; `.venv`; `Data-local/processed/**` (alle pipeline-JSON's); `testaudio2_manual.txt`, `testaudio5_manual.txt`, `Breinschade_Uitleg_Sara.txt`; `pyannote_teacher_similarity.csv`; pyannote-modelgewichten (alleen `faster-whisper-medium` stond in de HF-cache). **Gevolg:** stap 2–4 en de diarizatie-tuning kon ik niet opnieuw uitvoeren; zie §5.

**Dependencies:** `requirements.txt` pint faster-whisper 1.2.1, pydantic 2.13.5, numpy 2.5.3, torch 2.14.0+cpu, torchaudio 2.11.0, pyannote.audio 4.0.7, python-dotenv 1.2.3. Geïnstalleerd op deze machine: numpy **2.4.6** (≠ 2.5.3), python-dotenv 1.1.1 (≠ 1.2.3), torch 2.14.0 (zonder `+cpu`). Niet in requirements maar wel gebruikt: scipy (tuning-script), pandas, matplotlib, jupyter, jiwer (uitgecommentarieerd), speechbrain.

---

## 3. Vastgestelde fouten

### F1 — Ground truth is afgeleid van de te toetsen ASR-uitvoer · **Kritiek**
- **Waar:** `Experiments/diarization/hyperparameter_tuning/ground_truth_*.csv`, README ("startpunt voorgevuld uit de Whisper-segmenten"), notebook 03/06.
- **Bewijs [GETEST]:** WER van verse pipeline-run vs. `transcript`-kolom: testaudio2 **0,000** (118 w), testaudio4 **0,000** (420 w), testaudio1 0,032, testaudio7 0,031, testaudio5 0,123. Rijgrenzen GT == ASR-segment (±0,06 s): testaudio2 19/19, testaudio7 38/38, testaudio5 12/20, testaudio1 6/12. Zelfs de overshoot van `testaudio1` (laatste segment eindigt op 30,56 s terwijl de audio 29,98 s duurt) staat letterlijk in de GT (30,6 s).
- **Gevolg:** WER/DER op deze fragmenten zegt niets over werkelijke kwaliteit; sprekerwissels *binnen* een ASR-segment kunnen in de GT niet bestaan, dus diarizatiefouten worden onderschat.
- **Correctie:** annoteer opnieuw onafhankelijk (eerst luisteren, zonder Whisper-voorinvulling; liefst 2 annotatoren, kappa rapporteren) en leg de boundaries vrij van ASR-segmenten vast.

### F2 — De "score" is geen DER; evaluatie-instellingen ontbreken · **Hoog**
- **Waar:** `evaluate_min_cluster_size.py::score`.
- **Beschrijving [CODE]:** alleen frames binnen GT-rijen worden geteld → **false alarm (spraak buiten GT) telt niet**; missed speech niet apart; overlap "mild" (goed zodra één actieve spreker klopt); 1-op-1-koppeling per GT-spreker; geen collar. Notebook 06 noemt het "totaal juist %" en trekt daaruit conclusies over parameters.
- **Gevolg:** de conclusie "tuning helpt niet" is niet verkeerd, maar niet onderbouwd met een standaardmaat; het 81 → 83,2%-verschil is niet te interpreteren.
- **Correctie:** `pyannote.metrics.DiarizationErrorRate` (is al geïnstalleerd) met vermelde collar (0 en 0,25 s) en overlapbehandeling; rapporteer missed / false alarm / confusion apart.

### F3 — `overlap` is gedefinieerd als "tweede spreker beslaat ≥15% van het segment", niet als gelijktijdige spraak · **Hoog**
- **Waar:** `diarization.py::assign_speakers`, regel `overlap = runner_ov/duration >= 0.15`.
- **Bewijs [GETEST, E4]:** A 0–4 s, B 4–5 s, segment 0–5 s → `overlap=True`, `uncertain=False`, speaker=MAIN, confidence 0,8. Echte overlap (E5) geeft hetzelfde signaal; de twee zijn niet te onderscheiden.
- **Bewijs tegen GT [NOTEBOOK-UITVOER + GT, T9]:** gevlagd/echt: testaudio7 14 gevlagd, GT-overlap in 5 segmenten (10 vals alarm); testaudio2 5 vs 2 (4 vals alarm); testaudio5 3 vs 4 (3 gemist). Let op: GT-overlapvlag is zelf grof (hele rij).
- **Gevolg:** (a) overlapkwaliteitsvlag is ruis; (b) een segment met één echte sprekerwissel binnen het segment krijgt **één** label met `uncertain=False` zodra de wissel <40% beslaat. Dit is het "twee sprekers in één turn"-probleem uit notebook 03.
- **Correctie:** overlap berekenen uit gelijktijdige activiteit van ≥2 sprekers in de diarizatie (pyannote levert die); sprekerwissel binnen segment apart vlaggen (`speaker_change_inside=True`) of segmenten splitsen via woord-timestamps (`word_timestamps=True`).

### F4 — `speaker_confidence` is geen betrouwbaarheid · **Middel**
- Berekend als aandeel van de winnaar in de *toegewezen* overlaptijd. Bij 20% dekking is confidence 1,0 [GETEST, E7]; bij 60/40 is het 0,6 terwijl de rest `uncertain=False` is [E7b]. Naam suggereert kans. **Correctie:** hernoemen (`speaker_share`) en niet in classificatie als waarschijnlijkheid gebruiken.

### F5 — Whisper-kwaliteitsmaten zijn venster-niveau · **Hoog**
- **Bewijs [GETEST]:** in mijn baseline-JSON's hebben 19 segmenten van testaudio2 maar 2 unieke `avg_logprob`-waarden, testaudio4 (87 seg.) 5, testaudio7 (38 seg.) 3. Notebook 02 toont hetzelfde (large-v3 testaudio2: eerste 3 segmenten identiek −0,2407). Bibliotheekcode `faster_whisper/transcribe.py` (r. 1362–1364) kent de venstergemiddelden aan elk segment toe.
- **Gevolg:** `quality_flags` (`low_avg_logprob` e.d.) markeren hele vensters of niets. Bij mijn test met ruis (SNR ≈ −5 dB) kreeg **elk** segment `high_no_speech_prob`; bij +8 dB geen enkel segment, terwijl de WER ten opzichte van schoon 0,23 was [GETEST].
- **Correctie:** `word_timestamps=True` en woord-`probability` gebruiken; documenteer dat de huidige flags venster-niveau zijn.

### F6 — Segmenten kunnen stil verdwijnen, zonder spoor · **Middel**
- **[CODE]** `no_speech_threshold`/`log_prob_threshold` in faster-whisper slaan vensters over (transcribe.py r. 1217 e.v.); VAD verwijdert niet-spraak. Resultaat: **geen segment** en geen vermelding. **[GETEST]** 30 s stilte en 30 s witte ruis → `n_segments=0`, geen waarschuwing, geen status in de JSON.
- **Gevolg:** gemiste spraak is in de JSON niet te onderscheiden van terecht stil. **Correctie:** schrijf `speech_coverage` (VAD-spraaktijd/duur) en lijst gedropte vensters in de JSON.

### F7 — Timestamp-resolutie in twee fragmenten is hele seconden · **Middel**
- **[GETEST]** testaudio2: 19/19 en testaudio7: 38/38 segmenten hebben begin én eind op hele seconden (testaudio1/5/4 niet). Dit reproduceert in mijn run (niet notebook-artefact). Segment 1 van testaudio1 eindigt 0,58 s na het einde van de audio.
- **Gevolg:** tijdgebaseerde koppeling aan diarizatie (en elke DER) heeft ±0,5 s ruis in die fragmenten; docent-embedding op die turns snijdt verkeerde stukken. **Correctie:** onderzoek oorzaak (vermoed: Whisper geeft geen fijne tijdstokens voor deze audio); gebruik woord-timestamps; clip eindtijden op `duration`. Oorzaak is niet vastgesteld.

### F8 — Cache en WAV-conversie sleutelen alleen op bestandsnaam · **Middel**
- **[GETEST, E17/E18]** Twee verschillende bestanden `fragment.mp3` (1 s en 2 s) uit verschillende mappen: tweede aanroep van `to_wav` hergebruikt de 1 s-WAV ("Reusing existing"). `output_path_for` geeft identiek pad voor `raw/x.mp3` en `test/x.mp3`. **[CODE]** `cached_result_exists` negeert modelgrootte: een eerder `base`-transcript wordt stil hergebruikt bij `--model medium`.
- **Correctie:** cache-key = hash(bestandsinhoud) + modelnaam/config.

### F9 — `to_wav` laat WAV-input ongewijzigd door · **Laag/Middel**
- **[GETEST, E16]** 8 kHz stereo WAV wordt niet geconverteerd (docstring belooft 16 kHz mono). Loader leest dan stereo/8 kHz; pyannote resamplet vermoedelijk intern (niet getest). 24-bit/8-bit geeft duidelijke `RuntimeError` (acceptabel).

### F10 — Modelvalidatie te los · **Middel**
- **[GETEST, E8–E11]** `end < start` wordt geaccepteerd; onbekende/verkeerd gespelde velden (`"spekaer"`) worden stil genegeerd; `speaker` accepteert willekeurige tekst. Pydantic `extra="forbid"`, `model_validator` (start<end, ≤duration) en `Literal` voor labels/rollen ontbreken.

### F11 — Batched-pad logt instellingen die niet gebruikt zijn · **Laag (latent)**
- **[CODE]** `use_batching=True`: `batched_model.transcribe(...)` krijgt alleen `language`, `batch_size`; `transcription_config` slaat toch alle kwargs op. Defaults van de batched variant verschillen (o.a. `without_timestamps=True`). Standaard staat batching uit.

### F12 — Padportabiliteit en `.gitignore` · **Middel**
- **[GETEST]** `audio_file` in elke JSON is een absoluut pad (`C:\Users\School\…`). Notebook 04-uitvoer toont `C:\Users\School\StudieStap\StudieStap_WorkshopTool\…` — niet de huidige locatie.
- `.gitignore` bevat `data-local/` maar de map heet `Data-local`: op Linux/macOS (hoofdlettergevoelig) wordt `Data-local` **niet** genegeerd → risico op committen van persoonsgebonden data. **Correctie:** schrijf `Data-local/`.
- `Data-analysis/src/None/speechbrain/*.ckpt` zijn 150-byte tekststubs met absoluut `C:\Users\School\.cache\…`-pad, in git. Verwijderen uit versiebeheer (door jou).

### F13 — Privacy / AVG-risico · **Middel**
- 13 mp3's met klaslokaalopnames (leerlingstemmen, namen genoemd in transcripten, gevoelige uitspraken in testaudio5) staan in git (`src/test-files/`), en de repo heeft een remote (merge van `EdgarSabi/patty`). Controleer toestemming/bron (YouTube-materiaal, TikTok) en overweeg ze uit de repo te halen. Niet juridisch beoordeeld.

---

## 4. Mogelijke problemen (onvoldoende bewijs)

- **M1 — MAIN_SPEAKER = meeste spreektijd.** [GETEST, E1–E3] Docent met 10 s vs leerling 30 s krijgt `OTHER_SPEAKER_1`; bij gelijke spreektijd hangt het label af van invoervolgorde; `main_speaker_uncertain` kan met default `main_speaker_min_share=0.0` **nooit** True worden. Op de drie fragmenten met GT klopt "MAIN = docent" grotendeels (testaudio2: MAIN omvat ook 6 s leerling; testaudio5: 9,7 s docent vs 1,6 s leerling; testaudio7: 42 s docent, 13 s leerling in MAIN [NOTEBOOK-UITVOER]), maar dat is 3 fragmenten, mogelijk met dezelfde docent. Aanname "eerste spreker = docent" wordt in de code **niet** gebruikt (goed).
- **M2 — Docentrol per turn, niet per spreker.** [NOTEBOOK-UITVOER testaudio7] dezelfde `MAIN_SPEAKER` heeft turns met `DOCENT`, `OTHER` én `ONZEKER`; er is geen consistentiecontrole of aggregatie per spreker.
- **M3 — Drempel 0,35 is in-sample gekozen** op 49 chunks, 1 docent, 1 referentieclip (`testdocent.mp3`, 44,1 kHz/320 kbps; klasfragmenten 44,1–48 kHz). `results.md` meldt 3 FN/1 FP op 39 chunks; notebook 04 toont 4 FN/1 FP op 37 chunks — de labelsets verschillen. Data-snooping: testaudio6 heet "unseen", maar de overlapregel is *daarna* aangepast.
- **M4 — Merged turn-duur.** [GETEST, E14] `min_clip_duration` controleert `end−start` (2,5 s) i.p.v. echte spraaktijd (1,1 s).
- **M5 — Niet-deterministisch.** Whisper-temperatuur-fallback `[0,…,1,0]` bemonstert willekeurig; geen seed gezet. Mijn run was identiek aan de eerdere, maar fallback werd niet geprovoceerd.
- **M6 — HF-modellen zonder revisie.** `pyannote/speaker-diarization-3.1`, wespeaker en Systran-Whisper worden zonder vaste revisie geladen.
- **M7 — Diarizatie met `speaker_diarization` i.p.v. `exclusive_speaker_diarization`** (pyannote 4.x biedt die laatste voor ASR-koppeling). Niet getest.
- **M8 — Diarizatie-opbrengst onbekend.** Tuning meldt 2 gevonden sprekers van 4 (testaudio4); gemiste kleine sprekers (7,3 s en 0,8 s) vallen weg of worden samengevoegd; zonder raw-uitvoer kan ik DER-componenten voor dit fragment niet bepalen.

---

## 5. Testresultaten

Alle runs: CPU, `faster-whisper medium int8`, standaard `TranscriptionConfig`. Voor ieder item geldt: vraag, invoer, verwacht, werkelijk, oordeel, beperking.

| # | Vraag / invoer | Verwacht | Werkelijk | Oordeel | Beperking |
|---|---|---|---|---|---|
| T1 | Bestaande unit-tests `src/tests` en `Experiments/classification/tests` | slagen | 17 + 51 geslaagd | ✔ | testen mocken subprocess/ML; testen geen kwaliteit |
| T2 | ASR-baseline op 5 fragmenten (testaudio1/2/4/5/7_fragment) | zinvolle segmenten | 9/19/87/21/38 segmenten; zelfde segmenten als eerdere notebook-run (testaudio2) | ✔ reproduceerbaar | andere Python/numpy-versie dan notebooks; dezelfde machine |
| T3 | WER/CER vs. GT-`transcript` (normalisatie: kleine letters, leestekens weg) | onafhankelijke meting | WER: t1 0,032 · t2 **0,000** · t4 **0,000** · t5 0,123 · t7 0,031; CER 0,035/0,0/0,0/0,100/0,022 | ✘ circulair (F1) | getallen **niet** als kwaliteit citeren; alleen t5 en t1 wijken af en zijn mogelijk handmatig gecorrigeerd |
| T4 | DER (pyannote.metrics) op segmentniveau-uitvoer uit notebooks, GT-rijen als referentie, `GEEN`/`ONBEKEND` buiten UEM | — | collar 0 / 0,25 s: testaudio2 **0,233 / 0,218** (alles confusion: B 7 s → MAIN); testaudio5 **0,424 / 0,384** (missed 2,1%, FA 2,7%, confusion 37,5%); testaudio7 **0,177 / 0,162** (alles confusion); testaudio1 (alleen 4,1–24,5 s beschikbaar) **0,354 / 0,320** (missed 24%) | informatief | hypothese = label per ASR-segment (niet ruwe diarizatie); GT circulair, dus **ondergrens**; optimale labelkoppeling; overlap niet apart gescoord; testaudio1 slechts deel |
| T5 | Randgevallen `assign_speakers`/`build_label_map`/modellen/to_wav (E1–E18, scripts in `Audit/scripts/edge_tests.py`) | zie §3 | 10 geslaagd / 22 (E13 was een onrealistisch scenario: label-map is injectief; E14 was een observatie) | F3, F8–F10, M1 | synthetische invoer |
| T6 | 30 s stilte en 30 s witte ruis | status "geen spraak" | 0 segmenten, geen melding | VAD werkt; F6 | alleen deze twee signalen |
| T7 | testaudio2 + roze ruis (≈+8 dB / ≈−5 dB SNR, grove schatting), WER t.o.v. schone run | stijgende fout + flags | WER 0,23 / 0,44; flag `high_no_speech_prob` bij −5 dB op alle segmenten, bij +8 dB nergens | F5 | SNR niet exact gemeten; referentie = schone Whisper-run |
| T8 | 8 kHz mono versie | geen verschil | WER 0,10 (t.o.v. schone run) | ✔ acceptabel | 1 bestand |
| T9 | Overlapvlag vs GT-`overlap=ja` (segmentniveau) | hoge precisie | testaudio2 TP1/FP4/FN1; testaudio5 TP1/FP2/FN3; testaudio7 TP4/FP10/FN1 | ✘ (F3) | GT-vlag per rij, grof; kleine n |
| T10 | Docentrol vs GT-rol, testaudio7 (alleen niet-overlap GT-rijen; seconden) | hoog | docent: DOCENT 31 s, OTHER 6 s, ONZEKER 6 s; leerling: OTHER 6 s, DOCENT 2 s, ONZEKER 5 s | recall docent bij beslissing 31/37 (84%) | n klein; testaudio7 is in-sample (drempel/regel is op testaudio6/7 bekeken); eerste turns uit notebook-uitvoer |
| T11 | JSON-validatie baseline-JSON's (`validate_json.py`) | geldig | alle schema-valide; bevindingen: audio_file absoluut (4×), hele-seconde-timestamps (2×), segment voorbij audio-einde (1×) | F7, F12 | alleen mijn eigen runs; pipeline-JSON's van jou ontbreken |
| T12 | `results_*.json` | geldig JSON | 5/5 geldig | ✔ | |

**Niet getest en waarom:** stap 2–4 end-to-end (geen HF-token, geen pyannote-gewichten; geen modellen gedownload zonder toestemming); DER op ruwe pyannote-turns; testaudio3/6/8; hardware-tijden; Jupyter opnieuw uitvoeren (data ontbreekt); scraper (bestaat niet).

---

## 6. Diarizatieanalyse

Gerapporteerd door jou: 2 van 4 sprekers gevonden op testaudio4 (12 → 8 geeft 4/4, 83,2%), merge-fout op testaudio2 (spreker B 17% gedekt). Mijn bevindingen, in volgorde van waarschijnlijkheid:

1. **Eén label per ASR-segment (bewezen, F3).** Alle sprekerwissels binnen een segment zijn niet representeerbaar. Op testaudio2 heeft de diarizatie in de notebookuitvoer *alle* 19 segmenten als MAIN_SPEAKER; de 7 s van B (23% van de GT-tijd) is 100% van de DER (0,233). Of pyannote zelf B wel had gedetecteerd kan ik zonder ruwe turns niet zeggen; de tuning-resultaten (B 17,1% gedekt, 2 sprekers gevonden) suggereren dat de clustering B grotendeels samenvoegt met A.
2. **Korte, kleine sprekers worden wegge-clustered (min_cluster_size = 12).** Bewijs uit jouw JSON's: bij 12/10 gevonden 2 sprekers, C (7,3 s) en D (0,8 s) 0%; bij 8 → 4 sprekers, C 97,3%; bij 6 → 6 sprekers. Aanvullende kanttekening: 8 is op hetzelfde fragment gekozen en gescoord (in-sample).
3. **Evaluatie is te mild** (F2) en referentie circulair (F1): de werkelijke fouten zijn waarschijnlijk groter dan gerapporteerd.
4. **Overlap en rumoer** zijn niet instelbaar; wel kan de overlapvlag gecorrigeerd worden (F3). Zonder ruwe turns is niet vast te stellen hoeveel gemiste spraak/valse alarm er in de ruwe diarizatie zit (T4 geeft alleen segmentniveau).
5. **Aanbevolen volgorde vóór andere modellen:** (a) onafhankelijke GT + echte DER met collar, (b) ruwe turns opslaan, (c) overlap/sprekerwissel binnen segment oplossen via woord-timestamps, (d) `exclusive_speaker_diarization` proberen, (e) pas dan modelwissel of scheiding. *(buiten scope fase 1)*

---

## 7. Jupyter Notebook-audit

| Notebook | Bevindingen |
|---|---|
| 01 | Leest `Data-local/raw/Breinschade_Uitleg_Sara.txt` (ontbreekt in repo). Telt "woorden" met `split()` incl. tijdstempels ("00:02") → 8457 woorden is te hoog. Vragen = regels met "?" — zinnen worden afgebroken, dus telling klopt niet met zinnen. Conclusie noemt "data scraper": die bestaat niet; bron is een online tool (handmatig). |
| 02 | Benchmark = tijd + aantal segmenten; "meer segmenten = nauwkeuriger/fijner" is geen kwaliteitsmaat; geen WER. Alle data uit `Data-local/processed/benchmark` (ontbreekt). Realtime-factor klopt rekenkundig, maar hardware niet vermeld. Python 3.12.6. |
| 03 | Python 3.11.5 (andere omgeving dan 02/04–06). Oordelen "voldoende/goed" zonder WER of GT-vergelijking. Kopjes zeggen "Duur: 45 sec" voor fragment 1 en 2 terwijl die 29,99 en 30,01 s zijn (fragment 3 klopt: 46 s). Fragmentselectie `df["end"] >= start & df["start"] <= end` neemt randsegmenten mee. Fragment 3 conclusie "diarization werkt beter dan fragment 2" is niet gemeten. Laatste cel leeg. Niet-gecommitte wijziging (1 regel). Manual-bestanden voor fragment 2 en 5 ontbreken. `load_manual_transcript` slaat regels zonder ":" over: in `testaudio1_manual.txt` hebben 4 van 9 regels geen label en vallen dus uit de handmatige referentie [GETEST, telling]; de tekstvergelijking in cel 11 toont daardoor een onvolledige referentie. |
| 04 | **Out-of-order uitvoering**: executietellers [2,3,4,**29**,22,23…28]; `manual_labels` (cel 8) is *na* de cellen die het gebruiken uitgevoerd → uitvoer komt uit een eerdere versie van die dictionary; bij "Restart & Run All" kunnen de getallen veranderen. Absoluut pad uit andere map in uitvoer. `manual_labels.get(…, "IGNORE")` sluit stil elke niet-gelabelde chunk uit; chunks met gemengde sprekers zijn bewust IGNORE (selectie-bias, accuracy 86% is dus optimistisch). Accuracy 32/37 klopt rekenkundig. |
| 05 | Executietellers [1,3,4,6,5,9,10]. "Unseen validation" is niet meer unseen na aanpassing van de regel. Succes = daling ONZEKER 28 → 11, maar OTHER steeg 9 → 23 **zonder referentielabels**; ONZEKER-daling is geen kwaliteitswinst. Testaudio7: geen vergelijking met de wél beschikbare GT-rollen (ik deed dat in T10). |
| 06 | Leest CSV's zonder `encoding="utf-8-sig"` → eerste kolom heet `\ufefffragment` (huidige bestanden hebben BOM); werkt nu toevallig omdat die kolom niet gebruikt wordt. Pad `../Experiments/…` relatief → werkt alleen met cwd = `Notebooks`. Conclusies kloppen met de JSON's, maar zie F2. Titel "5. Eindconclusie" na "Aanvullende test" (nummering 3→5, sectie 4 ontbreekt). |
| Alle | Geen `requirements` voor notebooks; `.ipynb_checkpoints` bevat een kopie van 02/03 (genegeerd door git). Geen tests. |

**NLP / CountVectorizer / tokenization:** niet aanwezig in de repo (grep op `CountVectorizer`, `TfidfVectorizer`, `nltk`, `spacy`, `sklearn` in `.py` en `.ipynb`: geen treffer). Dit onderdeel van de opdracht kan dus niet getoetst worden. De classificatiecode (`Experiments/classification`) is een mock die ongeacht input cyclisch 3 vaste antwoorden geeft; technisch: contextvensters op index (niet op tijd), geen validatie dat turns gesorteerd zijn, `status` kent alleen `OK`/`UNKNOWN`, en `flagged_uncertain`/`docent_role_unresolved` worden berekend maar **beïnvloeden `status` niet**. Een turn met `uncertain_assignment=True` krijgt dus `status="OK"` zodra een echte classifier de mock vervangt, tenzij dat wordt toegevoegd (aanbeveling fase 2).

---

## 8. Onbetrouwbare audio — advies voor volgende fase

Wat de modellen aanbieden: Whisper per segment/venster `avg_logprob`, `no_speech_prob`, `compression_ratio` (venster-niveau, F5), met `word_timestamps=True` ook woordwaarschijnlijkheden; pyannote turns zonder per-turn zekerheid maar met activiteit per spreker (→ overlap en aantal sprekers); embedding-cosine voor docentrol.

Huidige pipeline suggereert onterecht zekerheid in: (a) lege uitvoer bij stilte/ruis (geen status), (b) `speaker_confidence` (F4), (c) segmenten met sprekerwissel `uncertain=False` (F3), (d) hele-seconde-timestamps zonder waarschuwing (F7), (e) docentrol DOCENT/OTHER op merged turns met stilte.

Kansrijke controles voor een latere `NIET_BEOORDEELBAAR`-status (voorstel, *nog niet geïmplementeerd*):
1. **Spraakdekking** per fragment/venster (VAD-spraaktijd ÷ duur), en lijst met gedropte vensters.
2. **Ruiscontrole**: geschatte SNR of aandeel venster met `no_speech_prob>0,6` én lage woordwaarschijnlijkheid.
3. **Echte overlapfractie** per turn uit diarizatie; drempel voor "niet beoordeelbaar".
4. **Sprekerwissel binnen segment** → splitsen of markeren.
5. **Timestampcontrole**: hele-seconde-grenzen, segmenten voorbij audio-einde, niet-monotoon.
6. **Rolconsistentie** per diarizatie-spreker (percentage DOCENT-turns) en minimale turnduur op spraaktijd.
7. **Gradaties** (`beoordeelbaar / beperkt / niet beoordeelbaar`) met de reden als lijst; hervatten na een onbetrouwbaar fragment door een onafhankelijke, per-fragment evaluatie (stateloos).
Drempels moeten gekalibreerd worden op een onafhankelijke GT (F1).

---

## 9. Reproduceerbaarheid

- **Andere onderzoeker, andere computer: niet reproduceerbaar zoals het nu is.** Ontbreekt: data (`Data-local`), HF-token + licentie-acceptatie (beschreven), modelrevisies, `.venv`, requirements voor notebooks/tuning (scipy, pandas, matplotlib, jupyter, jiwer, speechbrain), en een commando-volgorde voor notebooks. Absolute paden in JSON en notebook-uitvoer; `.gitignore`-hoofdletterfout (F12).
- Omgevingen verschillen: notebooks 02/04/05/06 op Python 3.12.6, notebook 03 op 3.11.5, deze machine 3.11.5 met numpy 2.4.6 ≠ gepinde 2.5.3.
- Seeds: geen. Whisper fallback niet-deterministisch (M5); mijn run reproduceerde wel.
- Logging: alleen `print`; geen run-log met versies/tijd/hash van input; resultaten (`results_*.json`) hebben geen versie van pipeline/commit/model.
- Hardware: medium op CPU ≈ 1–1,2× realtime (mijn runs: 120 s audio in 143 s; notebook 02: large-v3 2,2× realtime).
- Positief: `PROMPT_VERSION`, `transcription_config`, `diarization`-blok met settings bewaard in JSON.

---

## 10. Geprioriteerd verbeterplan

**Nu oplossen (vóór fase 2):**
1. Onafhankelijke GT opnieuw maken (F1) en echte WER/DER met collar rapporteren (F2).
2. Overlap herdefiniëren en sprekerwissel binnen segment vlaggen (F3).
3. Ruwe diarizatie-turns opslaan in de JSON en `audio_file` relatief/hash maken (F12).
4. Cache-key op inhoud + modelconfig (F8).
5. `.gitignore` `Data-local/` corrigeren; testaudio-privacy beoordelen (F12, F13).
6. Notebooks: Restart & Run All, paden via `config`, dataset in een gedocumenteerde (niet-gepubliceerde) locatie, requirements/`environment.yml`.

**Later:** woord-timestamps voor segmentsplitsing (F7); `extra="forbid"`/validators in `models.py` (F10); venster-niveau flags documenteren/vervangen (F5); `speaker_confidence` hernoemen (F4); `main_speaker_uncertain` echt activeren (M1); rolconsistentie per spreker (M2); HF-revisies pinnen (M6); validatietests uit `Audit/scripts` in `src/tests` opnemen; classificatie laten reageren op `uncertain/overlap/ONZEKER` (§7).

**Optioneel (buiten scope fase 1):** `exclusive_speaker_diarization`; andere diarizatiemodellen of scheiding; drempelkalibratie met cross-validatie over meerdere docenten/referentieclips.

---

## 11. Concept voor het stageverslag

**Onderzoeksmethode.** Een onafhankelijke, falsificatiegerichte technische audit van de pipeline (transcriptie, diarizatie, preprocessing, docentherkenning), de notebooks en de classificatie-mock. Methoden: code-inspectie, uitvoeren van bestaande tests, uitvoeren van de transcriptiestap (faster-whisper medium, CPU) op vijf testfragmenten, berekenen van WER/CER (jiwer) en DER (pyannote.metrics) tegen de handmatige referentie, en synthetische randgevallen (stilte, ruis, 8 kHz, labelgrenzen, bestandsnaamcollisies). Diarizatie en docentherkenning zijn niet opnieuw uitgevoerd (geen token/modelgewichten); DER is berekend op de in notebooks opgeslagen segmentuitvoer.

**Gebruikte tests.** 68 bestaande unit-tests (geslaagd), 22 randgevalstests (10 geslaagd; bevindingen zie §3), 5 ASR-runs, DER op 4 fragmenten, overlapvlag-evaluatie op 3 fragmenten, docentrol-evaluatie op 1 fragment, robuustheidstests op 6 synthetische bestanden.

**Resultaten.** De transcriptie is reproduceerbaar en robuust voor stilte en lagere samplefrequentie. De WER-waarden t.o.v. de huidige referentie (0,000–0,123) zijn niet bruikbaar als kwaliteitsmaat omdat de referentie deels uit de Whisper-uitvoer is afgeleid. Op segmentniveau bedraagt de DER 0,18–0,42 (collar 0) op vier fragmenten, vrijwel volledig sprekerverwisseling; dit is een ondergrens. De `overlap`-vlag detecteert geen gelijktijdige spraak maar ook sprekerwissels binnen een segment, met veel valse alarmen (16 van 22 gevlagde segmenten in drie fragmenten). De Whisper-kwaliteitsmaten gelden per 30-seconden-venster. Docentherkenning scoorde op één fragment 31 van 37 beslissingen goed voor docent-spraak (in-sample).

**Beperkingen.** Kleine, niet-onafhankelijk geannoteerde set (1 annotator, voorgevulde referentie); één docent, één referentieclip; diarizatie en rolherkenning niet opnieuw uitgevoerd; SNR-schattingen grof; geen NLP- of echte classificatiecode beoordeeld, omdat die niet bestaat.

**Aanbevolen vervolgstappen.** Onafhankelijke referentie en standaardmaten (WER, DER met collar) invoeren; overlap en interne sprekerwissels correct modelleren; een expliciete kwaliteits-/"niet beoordeelbaar"-laag toevoegen en doorgeven aan de classificatie; reproduceerbare omgeving en datamanagement inrichten; pas daarna modelkeuzes heroverwegen.

---

## Bijlage — bestanden
`Audit/scripts/` (edge_tests.py, wer_eval.py, der.py, extract_nb.py, validate_json.py, run_asr_baseline.py, run_synth.py), `Audit/edge_results.json`, `wer_results.json`, `synth_results.json`. Scripts importeren `src/` alleen-lezen; paden in de scripts zijn mijn werkmap en moeten voor hergebruik aangepast worden.
