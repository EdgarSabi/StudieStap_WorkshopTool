# Baseline-preflight — StudieStap fase 1, stap 4A (Claude)

Opgesteld op 2026-10-12 op de repo-staat `main` @ `0a4ab99` (ná de audit- en validatiestappen).
Een eerdere versie van dit rapport was gebaseerd op de verkeerde (oudere) checkout en is vervangen; die versie had een andere
bestandsnaam en is verwijderd (het was mijn eigen, niet-gecommitte bestand).

**Wat ik gedaan heb:** alleen lezen en tellen. Geen Whisper-, pyannote- of docentherkenningsrun, geen netwerkaanroep, geen
bestaand bestand gewijzigd. Het enige nieuwe bestand is dit rapport. Tijdelijke analysescripts staan buiten de repo.
**Status git:** werkboom bevat alleen ongetrackte bestanden: `ground_truth_testaudio2_fragment_raster.csv`, `diarization/sortformer/`,
`Docs/Interview_Melle.docx` en deze map. `src/*.py` is inhoudelijk identiek aan `5b6f856` (`git diff` leeg).

Bewijslabels: **[GELEZEN]** uit bestand/code · **[BEREKEND]** eigen telling op bestaande bestanden · **[AFGELEID]** uit eerdere
audit/validatie, door mij niet opnieuw uitgevoerd · **[NIET GETEST]**.

---

## 1. Kern in tien punten

1. Er zijn **5 ground-truthbestanden met sprekerlabels** (testaudio1, 2, 4, 5, 7), 1 extra variant (`…2_raster`, ongecommit) en 1 leeg sjabloon (`final_testfragment`, 137 rijen zonder speaker/overlap). **[GELEZEN]**
2. De bruikbaarheid voor **WER/CER verschilt sterk per bestand**. De `transcript`-kolom is voor testaudio4 (87/87 rijen) en testaudio2 (19/19) woord voor woord gelijk aan de bestaande Whisper-uitvoer, voor testaudio7 35/38. Alleen testaudio1, testaudio5 en de raster-variant van testaudio2 wijken aantoonbaar af. **[BEREKEND]**
3. Voor testaudio2, 4 en 7 liggen de rijgrenzen op het ASR-raster (testaudio2/7: hele seconden; testaudio4: gemiddeld 0,02 s van Whisper). Sprekerlabels zijn wel handmatig, maar de tijdlijn is **niet onafhankelijk van Whisper**. **[BEREKEND]**
4. Een **echte, ruwe DER is nog niet te berekenen uit de bestaande uitvoer**: de pipeline-JSON bewaart alleen `speaker_raw` per Whisper-segment, niet de pyannote-beurten. Daarvoor is een apart evaluatiehulpscript nodig (nieuwe code, geen wijziging van `src/`). **[GELEZEN]**
5. **Whisper, pyannote en docentherkenning kunnen op deze machine draaien**: venv, packages en alle vier de modelsnapshots zijn aanwezig, `HF_TOKEN` staat in `.env`. Dit is nog niet daadwerkelijk getest. **[GELEZEN]**
6. **Risico op overschrijven bij gebruik van de bestaande scripts**: `transcription.py` heeft geen `--out`, hergebruikt stilzwijgend een bestaande cache en `--force` overschrijft die; `diarization.py` en `docent_recognition.py` delen één wav-cache op bestandsnaam. Er is een wrapper nodig (§6).
7. **Reproduceerbaarheid van Whisper is voor 4 van 5 fragmenten bevestigd door twee bestaande runs, voor testaudio5 niet**: 9 van 21 segmenten verschillen tussen de cache in `Data-local` en de auditrun (woordgelijkenis 0,93), vooral in de rumoerige staart. **[BEREKEND]** (verschil in Python/machine kan meespelen; oorzaak niet vastgesteld)
8. **Alle vijf de gelabelde fragmenten zijn al gebruikt voor ontwikkelkeuzes** (min_cluster_size/threshold-tuning, docentdrempel 0,35, overlapregel, audit-in-sample). Er is **nog geen onaangeroerde testset**. Die moet nieuw worden aangemaakt (§8).
9. Geen enkel getal uit dit rapport is een kwaliteitsclaim over Whisper of pyannote; het zijn bestandstellingen.
10. Open beslissingen voor jou staan in §10 (o.a. welke van de twee testaudio2-varianten de referentie is, betekenis van `intelligible`, herkomst van `final_testfragment` en `testdocent.mp3`).

---

## 2. Inventaris ground truth en bijbehorende audio

Map: `Data-analysis/Experiments/diarization/hyperparameter_tuning/`. Audio: `Data-analysis/src/test-files/`. Duur via `ffprobe`/transcript. **[GELEZEN/BEREKEND]**

| Ground truth | Git | Audio | Duur | Rijen | Sprekers | Rol-kolom | Overlap `ja` | Eerdere uitvoer in `Data-local` |
|---|---|---|---|---|---|---|---|---|
| `ground_truth_testaudio1_fragment.csv` | ja | `testaudio1_fragment.mp3` | 29,99 s | 12 | A (leerling), B (docent), `GEEN` (applaus) | ja | 1 | transcript, diarized, turns, docent_roles |
| `ground_truth_testaudio2_fragment.csv` | ja | `testaudio2_fragment.mp3` | 30,01 s | 19 | A (docent), B (leerling) | ja | 2 | idem |
| `ground_truth_testaudio2_fragment_raster.csv` | **nee** | idem | 30,01 s | 19 | A, B | **nee** (en geen `intelligible`) | 6 | idem |
| `ground_truth_testaudio4_fragment.csv` | ja | `testaudio4_fragment.mp3` | 120,03 s | 87 | A–D | **leeg** | 11 | transcript, diarized (geen turns/docent) |
| `ground_truth_testaudio5_fragment.csv` | ja | `testaudio5_fragment.mp3` | 46,00 s | 20 | A (docent), B, C (leerlingen), `ONBEKEND` | ja (3 leeg) | 4 | transcript, diarized, turns, docent_roles |
| `ground_truth_testaudio7_fragment.csv` | ja | `testaudio7_fragment.mp3` | 64,03 s | 38 | A (docent), B, C (leerlingen) | ja | 5 | idem |
| `ground_truth_final_testfragment.csv` | ja | **mp3 ontbreekt**; wel `Data-local/processed/diarization/final_testfragment_16k_mono.wav` (312,5 s) | 312,5 s | 137 | **geen** | leeg | leeg | transcript, diarized |
| `ground_truth_template.csv` | ja | — | — | 4 `VOORBEELD_`-rijen | — | — | — | niet inlezen |

Aanvullende referenties: `Data-local/raw/testaudio{1,2,5}_manual.txt` (handmatige transcriptie met `Docent:`/`Leerling:`, **zonder tijden**; 54/146/174 woorden) en de chunk-gebonden `manual_labels` in `Notebooks/04-diarization.ipynb` (rol-labels op Whisper-chunkindex). Zonder referentie: `testaudio3` (68,9 s), `testaudio6_fragment` (83 s), `testaudio8_fragment` (48 s), de volledige `testaudio1/2/4/5.mp3`, `testdocent.mp3` (23 s, referentiestem).

Kolombetekenis in de nieuwe CSV's (uit de bestanden afgeleid, **niet bevestigd**): `speaker_role` ∈ {docent, leerling, GEEN, leeg}; `overlap` ∈ {ja, nee, leeg}; `intelligible` ∈ {ja, nee, leeg}. De waarde `intelligible=ja` staat precies bij rijen met notities als "spreker zit verder weg" en "meerdere mensen spreken door elkaar" (testaudio5), dus waarschijnlijk betekent `ja` hier *"moeilijk verstaanbaar"*. Dat moet jij bevestigen voordat de kolom wordt gebruikt.

---

## 3. Wat is bruikbaar per soort meting

| Meting | Eis | testaudio1 | testaudio2 (tracked) | testaudio2 (raster) | testaudio4 | testaudio5 | testaudio7 | final |
|---|---|---|---|---|---|---|---|---|
| **WER/CER** (onafhankelijke tekst) | tekst ≠ Whisper | deels¹ | ❌ identiek | ✅ 3/19 rijen verschillen | ❌ identiek | deels¹ | ❌ 35/38 identiek | ❌ |
| **Segmentgebaseerd** sprekerlabel | label per segment/rij | ✅ | ✅ | ✅ | ✅ | ✅ (zonder `ONBEKEND`) | ✅ | ❌ |
| **Ruwe DER** | referentietijdlijn + ruwe beurten | ⚠️ tijden/overlap rommelig | ⚠️ gehele seconden | ✅ 0,1 s | ✅ grof | ⚠️ | ⚠️ gehele seconden | ❌ |
| **Overlap** | tweede spreker aanwezig | ❌ alleen boolean | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Docentrol** | spreker→rol | ✅ | ✅ | ❌ (kolom ontbreekt, wel te koppelen via tracked) | ❌ rolkolom leeg | ✅ | ✅ | ❌ |

¹ Zie §4: testaudio1 en testaudio5 wijken wel van Whisper af, maar de referentie is gedeeltelijk gelijk aan Whisper en voor testaudio1 verschilt de CSV ook van de eigen `testaudio1_manual.txt` (WER 0,197 tussen beide; **[AFGELEID]** uit validatiecontrole V06).

Wat geldt voor alle bestanden:
- **Overlap**: alleen een vlag per rij, zonder identiteit van de tweede spreker. Strikte overlap-DER en overlap-detectie (precisie/recall op gelijktijdige spraak) zijn dus niet te scoren; alleen `skip_overlap=True` of een per-rij-overlapvlag.
- **Eén label per rij**: een sprekerwissel binnen een segment kan in de referentie niet bestaan. Fouten van het type "twee sprekers in één turn" worden daardoor onderschat (bekend uit audit F1/F3).
- **Stilte** is vrijwel nergens als niet-spraak gelabeld (testaudio7 en testaudio2-tracked hebben 0 gaten). Een ruwe DER telt dan ook stilte als spraak en geeft een **vertekend false-alarm-deel**; de UEM/niet-spraakregel moet vooraf worden vastgelegd (§5).

---

## 4. Overzicht per audiobestand

Legenda: ✅ bruikbaar · ⚠️ eerst controleren · ❌ niet verantwoord · 🔍 alleen exploratief.

### 4.1 `testaudio1_fragment` (30 s; A leerling, B docent; applaus)
- **Al bruikbaar:** ✅ rollen, ✅ tekst wijkt aantoonbaar af van Whisper (62 vs 63 woorden, gelijkenis 0,99, het meeste handmatig gecorrigeerd), ✅ `testaudio1_manual.txt`, ✅ rol-chunks in notebook 04.
- **Nog controleren:**
  - Dubbele `turn_index` (3, 5 en 6 komen twee keer voor): sorteer/koppel op tijd + spreker, niet op index.
  - Rij `Nee.` (A, 14,8–20,3 s) beslaat 5,5 s voor één woord en overlapt 5,1 s met B; waarschijnlijk is dit het gehele overlapvenster. Rij 6 (A, 22,1–24,5) overlapt 0,1 s met B.
  - Laatste rij eindigt op 30,6 s terwijl de audio 29,99 s duurt (overshoot overgenomen uit Whisper).
  - `GEEN`/`APPLAUS` heeft lege overlap/intelligible; beslis hoe dit in de UEM wordt behandeld.
  - Tekst in CSV vs `testaudio1_manual.txt` verschilt (WER ≈ 0,20); welke is de referentie?
  - Slechts 54 woorden: één woord ≈ 2 % WER.
- **Verantwoord:** segmentlabel (met optimale 1-op-1-koppeling), docentrol op rolniveau, WER tegen één benoemde referentie met vermelding van de spreiding.
- **Exploratief:** DER (overlapzone 5 s), overlap, alles op spreker-niveau (n = 2).
- **Ontwikkeldata:** ja (docentdrempel 0,35 is hierop mede gekozen).

### 4.2 `testaudio2_fragment` (30 s; A docent, B leerling)
- **Al bruikbaar:** ✅ twee varianten.
  - *Tracked:* sprekers + rollen + `intelligible`; tijden in hele seconden, aaneengesloten, tekst = Whisper.
  - *Raster (ongecommit):* tijden op 0,1 s, tekst handmatig gecorrigeerd (3/19 rijen anders dan Whisper), geen rollen, gaten gelaten (14 stuks, samen 6,4 s), overlap op 6 rijen, B totaal 4,0 s i.p.v. 7,0 s in de tracked variant.
- **Nog controleren:** (a) welke variant is *de* referentie, of beide (tracked voor rollen, raster voor tijd/tekst) met een expliciete koppeling per rij; (b) raster rij 13 ("Dat staat hier, echt waar.") duurt 0,3 s en rij 7 ("Met zijn vrouw") 0,4 s: plausibel bij gedeeltelijke overlap, maar controleren; (c) rij 12/13 overlappen 0,1 s terwijl alleen rij 13 `ja` heeft; (d) `testaudio2_manual.txt` bevat "Nee, dat kan niet." dat in beide CSV's ontbreekt, en het raster eindigt op 29,0 s van 30,0 s; (e) raster mist `speaker_role`.
- **Verantwoord:** WER/CER tegen raster-`transcript` en `testaudio2_manual.txt` (twee referenties, spreiding rapporteren), segmentlabel, ruwe DER met raster-tijden, docentrol.
- **Exploratief:** alles over spreker B (4–7 s), overlap.
- **Ontwikkeldata:** ja (tuning van `min_cluster_size` en `threshold`, docentdrempel).

### 4.3 `testaudio4_fragment` (120 s; 4 sprekers, A–D)
- **Al bruikbaar:** ✅ sprekerlabels en overlapvlag (11 rijen, 9,2 s), fijne rijen (mediaan 1,1 s; 10 rijen < 0,6 s), 9 notities.
- **Nog controleren:** `speaker_role` en `intelligible` zijn leeg (welke spreker is docent?); `transcript` is 87/87 gelijk aan Whisper; rijgrenzen ≈ Whisper (±0,02 s); notitie "docent praat erdoorheen" bij een B-rij; 8 rijen "rumoer" aan het eind; spreker C 7,3 s, D 0,8 s (één zin).
- **Verantwoord:** segmentlabel, ruwe DER (met collar, zie §5), aantal ontdekte sprekers t.o.v. 4.
- **Niet verantwoord:** WER/CER (circulair: 0,000 per constructie). 🔍 C en D.
- **Ontwikkeldata:** ja, zwaar gebruikt (alle `results_*`).

### 4.4 `testaudio5_fragment` (46 s; docent A, leerlingen B, C; rumoer)
- **Al bruikbaar:** ✅ tekst echt handmatig herwerkt (gelijkenis met Whisper 0,95), rollen, 5 notities, `testaudio5_manual.txt`.
- **Nog controleren:** 3 rijen `ONBEKEND` zonder rol/overlap (2 daarvan met tekst, "rumoer"); laatste rij "fragment knipt hier af, niet meenemen" eindigt op 46,1 s > 46,0 s en moet uit de UEM; `intelligible=ja` op 4 rijen; **Whisper-uitvoer zelf is hier niet stabiel** (9/21 segmenten verschillen tussen twee bestaande runs, vooral vanaf ± 28 s), dus segmentindex-koppeling is riskant; koppel op tijd; de manual-txt heeft twee leerlingen, de CSV drie sprekers (B/C leerlingen + onbekend).
- **Verantwoord:** WER/CER met genormaliseerde regels, docentrol, segmentlabel op de eerste ~28 s. Daarna 🔍.
- **Exploratief:** het rumoerige deel (≥ 28 s), overlap, `ONBEKEND`.
- **Ontwikkeldata:** ja (docentdrempel; rol-labels in notebook 04).

### 4.5 `testaudio7_fragment` (64 s; docent A, leerlingen B, C; "constant rumoer")
- **Al bruikbaar:** ✅ rollen; drie tekstcorrecties t.o.v. Whisper (rijen 0, 15, 37); 5 overlaprijen; 28 notities (alle "constant rumoer").
- **Nog controleren:** tijden zijn hele seconden en aaneengesloten (0–62 s van 64 s; laatste 2 s niet gelabeld) → stilte telt als spraak; `intelligible` is overal `nee` ondanks "constant rumoer"; 35/38 rijen tekstueel gelijk aan Whisper; spreker C 4 s.
- **Verantwoord:** docentrol, segmentlabel, WER alleen met de aantekening dat het 92 % Whisper-afgeleid is (niet als nauwkeurigheid rapporteren).
- **Exploratief:** ruwe DER (ASR-raster), overlap, spreker C.
- **Ontwikkeldata:** ja, **bekeken** (overlapregel/docentrol is mede hierop bijgesteld, audit T10 is in-sample).

### 4.6 `final_testfragment` (312,5 s)
- **Bruikbaar:** ❌ als referentie. Geen speaker-, overlap-, rol- of notitie-annotatie; `transcript` = Whisper (137/137); 97 % van de rijen is exact 2,0 s en start op `x,1` s (mechanisch raster); tekst als "Abonneer, like en share." en "Iedereen lacht." wijst op Whisper-hallucinaties of ondertitelpatronen.
- **Nog controleren:** herkomst/toestemming, ontbrekende mp3, domein (lijkt geen workshop).
- 🔍 Alleen als robuustheidsfragment (aantal ontdekte sprekers, hallucinatiecontrole), niet in de baseline-scores.

### 4.7 Zonder referentie: `testaudio3`, `testaudio6_fragment`, `testaudio8_fragment`, volledige `testaudio1/2/4/5.mp3`, `testdocent.mp3`
- Geen annotatie. 🔍 uitsluitend exploratief.
- `testaudio3` is het enige bestand zonder enige cache-uitvoer in `Data-local`. `testaudio6/8` zijn al diarized en visueel bekeken (commit `73885f3`; `testaudio6` heeft een `_BEFORE`-variant).
- `testdocent.mp3`: herkomst onbekend; **niet vastgesteld** of dezelfde stem ook in een testfragment zit (lek-risico voor docentherkenning).

---

## 5. Voorgestelde meetdefinities (vooraf vastleggen)

**Verantwoord op de bestaande referenties**
1. **WER/CER** (`jiwer`, nog niet geïnstalleerd): kleine letters, interpunctie weg, apostrof behouden, `Docent:`/`Leerling:` weg, `(…)`-opmerkingen weg, `APPLAUS`/`GEEN` weg; vooraf bepalen of `uh/eh/ehm` meetellen. Alleen testaudio1, 2 (raster + manual), 5. Telt per referentie apart; geen gemiddelde over fragmenten; altijd absolute woordtellers erbij.
2. **Segmentgebaseerd sprekerlabel**: `speaker_raw` per Whisper-segment tegen het referentielabel op **tijd** (maximale overlap), optimale 1-op-1-koppeling; ook aantal ontdekte vs. echte sprekers.
3. **Ruwe DER** met `pyannote.metrics` (v4.1 aanwezig), collar 0 en 0,25 s, `skip_overlap` aan en uit; UEM = gelabelde spraakregio (dus `GEEN`, `ONBEKEND`, knip-staart uit). Vermelden: *"referentie heeft ASR-gebaseerde grenzen"*; DER telt ruwe pyannote-beurten (nieuw uit te voeren), niet de segmentversie.
4. **Docentrol** (rolniveau): confusiematrix DOCENT / OTHER / ONZEKER per referentierol, in seconden. Drempel 0,35 en `min_clip_duration_seconds=1,0` ongewijzigd.

**Voorlopig alleen exploratief:** overlap-detectie, spreker-niveau scores voor sprekers met < 10 s, `final_testfragment`, `testaudio3/6/8`, het rumoerige staartdeel van testaudio5, elk vergelijk met sortformer/community-1/WhisperX.

---

## 6. Technische uitvoerbaarheid met de bestaande code

### 6.1 Beschikbaar **[GELEZEN, niet uitgevoerd]**
| Onderdeel | Status |
|---|---|
| Venv `Data-analysis/src/.venv` | Python 3.14.8 |
| faster-whisper / ctranslate2 | 1.2.1 / 4.8.2 |
| torch / torchaudio | 2.14.0+cpu / 2.11.0 |
| pyannote.audio / core / metrics | 4.0.7 / 6.0.1 / 4.1 |
| speechbrain, numpy, scipy, pandas, pydantic, python-dotenv, huggingface-hub | 1.1.1, 2.5.3, 1.18.1, 3.0.5, 2.13.5, 1.2.3, 1.30.0 (numpy/torch/pyannote komen overeen met `requirements.txt`) |
| `jiwer`, `pytest` | **niet geïnstalleerd** in de venv |
| ffmpeg 7.1.1 | op PATH |
| `.env` met `HF_TOKEN` | aanwezig (waarde niet gelezen of getoond); **geldigheid niet getest** (netwerkaanroep) |
| Whisper `Systran/faster-whisper-medium` | snapshot `08e178d4…`, `model.bin` aanwezig |
| `pyannote/speaker-diarization-3.1` | snapshot `84fd2591…`; YAML: wespeaker-embedding, `segmentation-3.0`, `method=centroid`, `min_cluster_size=12`, `threshold=0.7046`, `min_duration_off=0.0` |
| `pyannote/segmentation-3.0` / `wespeaker-voxceleb-resnet34-LM` | `e66f3d3b…` / `837717dd…`, `pytorch_model.bin` aanwezig |
| Machine | 12 CPU-threads, ± 88 GB vrij, CPU-only |

Alle modelgewichten staan in de HF-cache, dus een run in `HF_HUB_OFFLINE=1` lijkt mogelijk. **[NIET GETEST]**

Let op: de twee eerdere audits liepen op een andere installatie (Python 3.11.5, andere numpy, geen token/gewichten) en hebben stap 2–4 daar niet kunnen uitvoeren. Hun getallen (o.a. DER 0,18–0,42 op segmentniveau) zijn dus **geen baseline voor deze omgeving**.

### 6.2 Per stap
| Stap | Kan draaien | Randvoorwaarden en risico's |
|---|---|---|
| Whisper `transcription.py` | ja | **Geen `--out`**; schrijft naar `Data-local/processed/<stem>.json`. Zonder `--force` stopt het stil met exit 0 als dat bestand bestaat, met `--force` wordt de bestaande cache **overschreven**. Cache-sleutel = bestandsnaam, niet model of config (audit F8). Gebruik een wrapper rond `TranscriptionEngine` met eigen uitvoerpad. |
| pyannote `diarization.py` | ja | Heeft `--out`. Wav-conversie gaat altijd naar `Data-local/processed/diarization/<stem>_16k_mono.wav` en wordt hergebruikt als die bestaat. Bewaart **geen ruwe beurten**. Zonder `--min/--max-speakers` loopt het met priors `None`. De bestaande caches zijn met wisselende priors gemaakt (testaudio4: 1–3; testaudio6: 1–2; testaudio2: geen) en dus niet vergelijkbaar. |
| `preprocessing.py` | ja | Heeft `--out`, geen `--force`; schrijft altijd. |
| `docent_recognition.py` | ja | `--out`, `--force`; deelt de wav-cache met stap 2 en schrijft de referentie-wav naar `…/docent_recognition/`. `--reference` verplicht, geen standaard in de code. |
| `run_docent_pipeline.py` | ja | Geeft **geen** `--out` en geen speakerpriors door en schrijft naar de bestaande paden. **Niet gebruiken voor de baseline.** |
| Unit-tests in `src/tests` | `pytest` ontbreekt | Mocken subprocess/embedding; geen kwaliteitsbewijs. |

Gevolgen: (1) hergebruik de bestaande caches **niet** als baseline (verschillende runtimes en instellingen, en niet te herleiden naar één codeversie); (2) alle nieuwe uitvoer moet via wrappers met eigen uitvoerroot, waarbij `src/` ongemoeid blijft.

---

## 7. Vooraf vast te leggen (run-manifest per run)

- **Code/data:** git `HEAD` + `git status`; SHA-256 van elke `src/*.py` (werkkopie heeft CRLF; leg ook de git-blob-hash vast), elke ground-truth-CSV, elk audiobestand, elke `*_manual.txt`, `testdocent.mp3`. Baseline moet op een gecommitte staat draaien (nu is de raster-CSV ongecommit).
- **Omgeving:** `pip freeze` van de venv, Python 3.14.8, OS, `torch.get_num_threads()`, CPU-model, `HF_HUB_OFFLINE`-waarde, HF-snapshot-hashes (§6.1), SHA-256 van `model.bin` en de `.bin`-gewichten.
- **Whisper (`TranscriptionConfig`, niet wijzigen):** model `medium`, `nl`, `cpu`/`int8`, `beam_size=5`, `condition_on_previous_text=True`, `vad_filter=True`, `vad_parameters=None`, `word_timestamps=False`, `log_prob_threshold=-1,0`, `no_speech_threshold=0,6`, `compression_ratio_threshold=2,4`, `use_batching=False`. Opmerking: de CLI-standaard in `config.py` is `base`; de pipeline-standaard is `medium` (`run_docent_pipeline.py`). **Vastleggen welke ‘baseline’ is bedoeld: `medium`.**
- **pyannote (`DiarizationConfig`):** `speaker-diarization-3.1`, `device=cpu`, **`min_speakers=None`, `max_speakers=None`** (hoofdconditie); `overlap_min_ratio=0,15`, `uncertain_coverage_below=0,60`, `uncertain_margin_below=0,15`, `main_speaker_min_share=0,0`.
- **Preprocessing:** `max_gap_within_turn_seconds=1,5`, `large_context_gap_seconds=3,0`.
- **Docentherkenning:** `wespeaker-voxceleb-resnet34-LM`, `similarity_threshold=0,35`, `min_clip_duration_seconds=1,0`, referentie `testdocent.mp3`.
- **Evaluatie:** normalisatieregels (§5), collar(s), UEM-regel, `skip_overlap`, koppelingsmethode, aantal herhalingen, seed-situatie (er wordt geen seed gezet; Whisper-fallback met temperatuur kan niet-deterministisch zijn).
- **Uitvoer per run:** starttijd, runtime per stap, exitcode, stdout/stderr.

Niets hiervan verandert instellingen of drempels; het legt alleen vast wat de bestaande code al gebruikt.

---

## 8. Opslag zonder iets te overschrijven

Aparte uitvoerroot, buiten alle bestaande cachepaden en met `Data-local/`-conventie (gitignored; mapnaam met hoofdletter, zie audit F12):

```
Data-local/evaluation/baseline_v1/
  run_manifest.json                # §7, één per runreeks
  <fragment>/run1/ transcript.json, diarized.json, raw_turns.rttm, turns.json, docent_roles.json, log.txt
  <fragment>/run2/ …               # onafhankelijke herhaling
  scores/                          # per metriek, per referentie, met ruwe tellers
```

Regels: elk script weigert te schrijven als het doelbestand bestaat (geen `--force`); bestaande `Data-local/processed/` en alle CSV's blijven read-only (leg hun hashes vast); een eigen wav-map in de nieuwe root (de `to_wav`-functie accepteert een eigen `out_dir`); wrappers staan in `Experiments/baseline_evaluation/`, importeren `TranscriptionEngine` en `PyannoteBackend` zonder ze te wijzigen en bewaren de ruwe `SpeakerTurn`s als RTTM. Referentiebestanden worden niet gekopieerd of herschreven, alleen gehasht.

---

## 9. Ontwikkel- en testdata gescheiden houden

**Reeds gebruikt (dus ontwikkeldata, uitkomsten zijn optimistisch):**

| Fragment | Waarvoor al gebruikt |
|---|---|
| testaudio2, testaudio4 | tuning `min_cluster_size`/`threshold`, README-conclusies |
| testaudio1, 2, 5 | keuze docentdrempel 0,35 (49 chunks), `manual_labels` |
| testaudio6, 7, 8 | overlapregel en rol-aanpassing, "laatste check"; testaudio7 ook de in-sample docentrolcontrole in de audit |
| final_testfragment | diarisatievoorbeeld |

**Voorstel:**
- **Dev** = testaudio1, 2, 4, 5 en (met label "bekeken") 7. Dit is de enige set waarop de baseline in stap 4B mag draaien.
- **Achtergehouden test** = bestaat nog niet. Kandidaten die niet in de bovenstaande lijst staan: `testaudio3` en de niet-fragment-delen van de volledige `testaudio1/2/4/5.mp3` (offset van de `_fragment`-bestanden is niet vastgelegd; eerst bepalen om overlap in tijd uit te sluiten). Die moeten later door jou **zonder Whisper-voorinvulling** worden geannoteerd (dus geen `transcript_hint`-methode), in een aparte map.
- Regels: annoteren vóór de eerste modelrun; SHA-256 + datum van de testset vastleggen; één keer scoren nadat protocol en normalisatie bevroren zijn; geen parameter- of drempelwijziging na het zien van testscores; splitsen per opnamesessie, niet per fragment, zodat dezelfde stemmen/zaal niet in beide sets zitten; elke dev-uitkomst met label "optimistisch" rapporteren.
- Hoeveelheid bepaalt de claim: bij enkele minuten en weinig sessies is alleen "consistent/inconsistent met dev" te zeggen, geen puntschatting met betrouwbaarheidsinterval.

---

## 10. Aannames en tegenvoorbeelden

| # | Aanname | Tegenvoorbeeld/controle | Gevolg |
|---|---|---|---|
| A1 | "Handmatig gecontroleerd" betekent onafhankelijke tekst | `transcript` = Whisper bij testaudio4 (87/87), testaudio2-tracked (19/19), testaudio7 (35/38), final (137/137) | WER daar niet rapporteren |
| A2 | Rijgrenzen zijn onafhankelijke tijden | hele seconden (testaudio2-tracked, testaudio7); ±0,02 s van Whisper (testaudio4) | DER = consistentie met ASR-raster; collar nodig |
| A3 | Eén label per rij volstaat | sprekerwissel binnen een segment kan niet voorkomen | fouten onderschat |
| A4 | `overlap=ja` identificeert gelijktijdige spraak | geen tweede spreker genoteerd; in testaudio1 beslaat één woord 5 s overlap | geen overlap-DER |
| A5 | Bestaande cache = baseline | wisselende priors, verschillende datums, geen codeversie in de output, testaudio5 niet reproduceerbaar | nieuwe runs, eigen map |
| A6 | Whisper is deterministisch | testaudio5: 9/21 segmenten verschillen tussen twee runs; andere vier identiek | twee runs per fragment en verschil rapporteren |
| A7 | Koppeling op chunkindex blijft geldig | segmentatie verschilt per run (testaudio5) | koppelen op tijd |
| A8 | Rollen per spreker zijn consistent | in de CSV's wel (A→docent enz.), maar testaudio4 heeft geen rollen | docentmapping nodig vóór role-eval |
| A9 | Resultaten generaliseren | alle fragmenten zijn kort en van waarschijnlijk dezelfde opnameserie; sprekers < 10 s | alleen beschrijvend |
| A10 | De audit-DER is een baseline | segmentversie, andere installatie, circulaire referentie | niet overnemen |

---

## 11. Voorstel voor de volgende stap (4B): eerste reproduceerbare dev-baseline

Doel: één gedocumenteerde, herhaalbare basismeting met zichtbare onzekerheid. Geen tuning, geen modelwissels, geen nauwkeurigheidsclaim.

1. **Bevriezen, zonder modelrun** (kan direct): referentiekeuzes vastleggen (§12); `PROTOCOL.md` met normalisatie, UEM, collar, koppelingsregel en falsificatiecriteria; het `run_manifest.json`-schema; hashes van alle referenties en audiobestanden berekenen.
2. **Kleine, gerichte aanvulling door jou** (geen nieuwe annotatie van audio): docentspreker per fragment voor testaudio4; bevestig `intelligible`; kies de testaudio2-referentie; los de kleine punten uit §4 op (dubbele `turn_index`, overshoot > audioduur, gaten).
3. **Gereedschap (nieuwe code, `src/` onaangeroerd):** transcriptiewrapper met eigen uitvoerpad; diarisatierunner die `PyannoteBackend.diarize` aanroept en ruwe beurten als RTTM bewaart; scorer voor WER/CER, segmentlabel en DER; unit-tests met handgemaakte voorbeelden, inclusief **bewust foute** voorbeelden waarop de scorer aantoonbaar slechter scoort (anders is de scorer niet falsifieerbaar).
4. **Installatie:** `jiwer` (en `pytest`) in een aparte eval-venv, niet in de productie-venv (jouw akkoord nodig; netwerk).
5. **Eerste runs, alleen dev:** testaudio1, 2, 4, 5 (7 gelabeld "bekeken"), `min/max_speakers=None`, **twee onafhankelijke runs** per fragment, offline indien mogelijk.
6. **Falsificatiecriteria vooraf:**
   - Baseline = instabiel als twee runs verschillen in aantal segmenten, tekst of aantal ontdekte sprekers (verwacht al voor testaudio5).
   - Scorer = ongeldig als de opzettelijk foute voorbeelden niet slechter scoren.
   - Twee referenties van hetzelfde fragment die onderling meer dan 5 % WER verschillen worden niet tot één getal samengevoegd (nu vastleggen: testaudio1 zit rond 20 %).
   - Een metriek zonder onafhankelijke referentie (testaudio4/7 WER) wordt niet berekend of expliciet als "circulair" gelabeld.
7. **Rapporteren:** per fragment en per metriek met ruwe tellers (woorden, seconden, sprekers), geen gemiddelde over fragmenten van 30 en 120 s, elk getal "dev, optimistisch", ruwe DER met collar-variant en met de vermelding dat de referentie ASR-gebaseerde grenzen heeft.
8. **Pas daarna (4C):** definitie en annotatie van de achtergehouden test (§9) en eenmalige scoring.

---

## 12. Open vragen (blokkeren 4B)

1. Welke testaudio2-variant is de referentie (tracked, raster, of beide met koppeling per rij)? Wat betekent "raster"? Mag de raster-CSV gecommit worden? Zijn rijen 7, 11, 13 correct?
2. Betekent `intelligible=ja` "moeilijk verstaanbaar"? En wat is de bedoeling van lege `overlap` bij `GEEN`/`ONBEKEND`?
3. Welke spreker (A–D) is de docent in testaudio4, en hoe ga je om met `ONBEKEND` in testaudio5?
4. Is `testaudio1_manual.txt` of de CSV-`transcript` de leidende tekstreferentie voor testaudio1 (ze verschillen ≈ 20 % WER)?
5. Herkomst, toestemming en gebruiksdoel van `final_testfragment` (mp3 ontbreekt)? Zo niet te gebruiken, uit de baseline laten.
6. Uit welke opname komt `testdocent.mp3`, en komt die stem voor in een testfragment? En welke offsets hebben de `_fragment`-bestanden in de volledige opnames?
7. Akkoord met `jiwer` en `pytest` in een aparte eval-venv (netwerk nodig)? Akkoord met het draaien in `HF_HUB_OFFLINE=1`?
8. Privacy: 13 mp3's met (mogelijk minderjarige) leerlingen staan in git (`src/test-files/`); `.gitignore` bevat `data-local/` maar de map heet `Data-local` (audit F12/F13). Niet door mij gewijzigd; wel relevant zodra er nieuwe uitvoer met persoonsgegevens (transcripten) in de repo-boom komt.

---

## 13. Beperkingen van dit rapport

- Alles is statisch gecontroleerd; **er is geen model, test of script uit de pipeline uitgevoerd**. "Kan draaien" volgt uit code, cache-inhoud en packageversies, niet uit een geslaagde run.
- De HF-token is niet gevalideerd; offline-gedrag van pyannote is niet getest.
- De vergelijking "gelijk aan Whisper" is op genormaliseerde tekst gedaan tegen de bestaande cache en tegen de auditrun; het sluit niet uit dat je de tekst nagelopen en ongewijzigd goed hebt bevonden. Het toont wel dat zulke rijen geen verschil bevatten dat een WER kan meten.
- De testaudio5-afwijking vergelijkt twee bestaande runs op mogelijk verschillende Python-/machineversies; de oorzaak (nondeterminisme, versie, hardware) is niet vastgesteld.
- Bestandstellingen (sprekers, seconden, rijen) zijn zelf berekend en niet door een tweede persoon gecontroleerd.
