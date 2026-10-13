# Evaluatieprotocol — baseline fase 1 (versie v1)

Status: **bevroren vóór de eerste echte run**. Wijzigingen na het zien van resultaten alleen als nieuwe versie (v2) met reden en datum onderaan
(§15); oude scores blijven staan en worden niet herberekend onder een nieuw protocol zonder dat te vermelden.

Doel: een reproduceerbare *ontwikkelbaseline* van de ongewijzigde fase-1-pipeline (Whisper → pyannote → sprekerkoppeling → preprocessing → docentherkenning),
met zichtbare onzekerheid. Geen tuning, geen modelvergelijking, geen nauwkeurigheidsclaim buiten de ontwikkeldata.

---

## 1. Broncode en referenties (hashes vastgelegd op 2026-10-12)

Repository: `main` @ `0a4ab99d811c945a39ff11d4c6a74a83a1540609`. Ongetrackt op dit moment: `…/ground_truth_testaudio2_fragment_raster.csv`
(primaire referentie voor audio 2), `Experiments/diarization/sortformer/`, `Docs/Interview_Melle.docx` en deze map. `Data-analysis/src/*.py` is onveranderd ten opzichte van `5b6f856`.
Elke run schrijft de actuele hashes opnieuw in zijn `run_manifest.json`; `score_run.py` weigert te scoren als de referentiehash sinds de run is veranderd.

| Bestand | SHA-256 |
|---|---|
| `src/config.py` | `de727ea69a6f9f5f370a270c9a795894fa3462154912a80cf3b3e7067c62fa4a` |
| `src/transcription.py` | `153b7fa38afb5d83c28c4d0d1e082057baac8d24168b058719369137d52da97d` |
| `src/diarization.py` | `cfa384c53dfc53821ee8470110fad4a1ca5e20464ef2043efa7e2136b0dc246b` |
| `src/preprocessing.py` | `4ba85fc3730fc563f8c4fa46ae4b405b7c79b74ab8fc97f6b771ddf9eafd9b6a` |
| `src/docent_recognition.py` | `af63ff656399c8c8bfe4db50f69e16e00e2f243773cbc004c3afb5adb35809b0` |
| `src/models.py` | `dcbb063bebcb56656d1f0d84fc1d5419ea095adef7b1b93299285cdc9832832f` |
| `src/run_docent_pipeline.py` | `74ae0f6ae238c6b673735628ccbea17e9213f92424d7c9034e6a56faf6da095e` |
| `ground_truth_testaudio1_fragment.csv` | `bce4069a5156970e57df495a652c21199bb7e8cf44601647b0334e2c0c9978fa` |
| `ground_truth_testaudio2_fragment_raster.csv` (**primair, audio 2**) | `4b2a99321c0e81648c35a3af901461abc649ffb96a6af3c6cc09dc53f7abbf4b` |
| `ground_truth_testaudio2_fragment.csv` (alleen rolbron voor audio 2) | `8e622635c4a125232610959813fd9988276c2ca48774381d298d1d9f1e1d7f03` |
| `ground_truth_testaudio4_fragment.csv` | `83417b95d88d1a0ba476b6e86f792f7beb287d0a2b74eef9ba310a48d8f12a4c` |
| `ground_truth_testaudio5_fragment.csv` | `e629ddecc383f4d413060e67ce42d1a49e725baa121ad61640008cbcdbdae1f6` |
| `ground_truth_testaudio7_fragment.csv` | `35c296f8f2e7bbef2e4ddc4644117d0d72bf58abd7b81220683ca71d46c4cef2` |
| `ground_truth_final_testfragment.csv` (niet gebruikt, leeg sjabloon) | `8894a2bb5d7b0adcb541630de00c50910faa1675fed518626489354f2cc04e7c` |
| `testaudio1_fragment.mp3` | `9b77c0fd4409d3addcaf3432d8786225198d9b8194432abff11a8a66cb097010` |
| `testaudio2_fragment.mp3` | `3f5aaf74b54a76280bededdcc51ea90434c0896be3257cd2c9c1a3fc4c845f7a` |
| `testaudio4_fragment.mp3` | `c42516ed660a2f3c74591fcd8103a86f72f9ec56ac5a1f0f7996f0275ecb61d6` |
| `testaudio5_fragment.mp3` | `72a7802554c93624aaac116a38b92ec719bd7322e076d4fcbc053ed7846150ad` |
| `testaudio7_fragment.mp3` | `85e625e12334c13a3acfc2e50194e43394f41dc0ee072a44a4b34008741ca389` |
| `testdocent.mp3` (docentreferentie) | `2ac7ef3b3b690f86cf731d795aa22a0a429746f38488ec25b37831638e65f81e` |
| `Data-local/raw/testaudio1_manual.txt` | `f5f2d12c51a67797dcc88a3a8b457b5a8150ccc81514b582d03c0bf36335264a` |
| `Data-local/raw/testaudio2_manual.txt` | `96cbf8548c70521dc0e87c3cc8fde388e2f1d5120658580030c4bd0277b7d21e` |
| `Data-local/raw/testaudio5_manual.txt` | `a26684359bf2492b01c8daeaa0626ecb86eae4425c694b228d9fa6d75ecb9743` |

Modelrevisies (lokale HF-cache): `Systran/faster-whisper-medium` `08e178d4…`, `pyannote/speaker-diarization-3.1` `84fd2591…`,
`pyannote/segmentation-3.0` `e66f3d3b…`, `pyannote/wespeaker-voxceleb-resnet34-LM` `837717dd…` (volledig in `run_manifest.json`).
Omgeving: `Data-analysis/src/.venv` (Python 3.14.8; faster-whisper 1.2.1, pyannote.audio 4.0.7, torch 2.14.0+cpu, pyannote.metrics 4.1, numpy 2.5.3). Er wordt niets in die omgeving geïnstalleerd.

## 2. Vaste keuze van fragmenten (alle = ontwikkeldata)

| Fragment | Audio | Referentie | Rolbron | Tweede tekstreferentie |
|---|---|---|---|---|
| `testaudio2_fragment` | 30,0 s | **`…_raster.csv` (primair)** | rollen A=docent, B=leerling uit `ground_truth_testaudio2_fragment.csv` (`speaker_id` → `speaker_role`; alleen die twee kolommen) | `testaudio2_manual.txt` |
| `testaudio1_fragment` | 30,0 s | eigen CSV | eigen CSV | `testaudio1_manual.txt` |
| `testaudio4_fragment` | 120,0 s | eigen CSV | **geen** (rolkolom leeg) → geen rolscore | — |
| `testaudio5_fragment` | 46,0 s | eigen CSV | eigen CSV | `testaudio5_manual.txt` |
| `testaudio7_fragment` | 64,0 s | eigen CSV | eigen CSV | — |

Niet in de baseline: `final_testfragment` (geen sprekerannotatie, mp3 ontbreekt), `testaudio3/6/8` en de volledige opnames (geen referentie).
Eerste run: alleen `testaudio2_fragment`. De overige vier pas na beoordeling van die run.

## 3. Betekenis van de kolommen (gebruikersbevestiging 2026-10-12)

- `intelligible`: **`ja` = spraak is moeilijk of niet verstaanbaar, `nee` = verstaanbaar.** (De kolomnaam is dus misleidend.) De originele CSV's worden niet gewijzigd. In het harnas is een afgeleide
  eigenschap `unintelligible` met dezelfde waarden (`ja/nee/leeg`). **Uitsluitend kwaliteitswaarschuwing**: rijen met `unintelligible=ja` blijven in tekst, UEM en DER; aantal rijen en seconden worden per fragment in de scores gerapporteerd.
- `overlap`: `ja` = in dit stuk spreken meerdere mensen tegelijk. Er is geen tweede spreker genoteerd → overlapannotatie is **onvolledig** (zie §10).
- `speaker_role`: `docent` / `leerling` / `GEEN` / leeg.
- `transcript` (of oudere naam `transcript_hint`): zie §6. De tekst is voor sommige bestanden gelijk aan de Whisper-uitvoer (zie §10).

## 4. Rijtypen en maskering

Elke referentierij krijgt precies één type (in `baseline_eval/refs.py`):

| Type | Regel | Gedrag |
|---|---|---|
| `speech` | `speaker_id` is een sprekerlabel (`SPREKER_x`) | bekende spreker; in referentieannotatie, tekst, UEM |
| `nonspeech` | `speaker_id = GEEN` (bijv. APPLAUS) | **stilte/niet-spraak**: gemaskeerd uit UEM, niet in tekst, nooit een spreker |
| `unknown` | `speaker_id = ONBEKEND` | **spraak met onbekende identiteit**: gemaskeerd uit DER/segmentscore, nooit een spreker; tekst blijft in WER |
| `cut` | notitie bevat "niet meenemen" | afgekapt/onbruikbaar: overal gemaskeerd (DER, tekst, segmenten) |
| `unlabelled` | lege `speaker_id` | bestand heeft geen sprekerannotatie → geen DER/segment/rolscore |

Niet-gelabelde gebieden (gaten tussen rijen) hebben twee mogelijke betekenissen (stilte of niet geannoteerd). Daarom worden **altijd beide UEM-varianten** gerapporteerd (§7). Referentietijden voorbij de audioduur worden afgekapt.

## 5. Koppeling

Alles koppelt op **tijd**. Nergens wordt een rij-, segment- of chunkindex gebruikt (indexen verschillen per Whisper-run; `turn_index` is in de CSV's niet uniek).

## 6. WER/CER

- Referentietekst: rijen van type `speech`/`unknown`/`unlabelled`, gesorteerd op (begin, eind), samengevoegd. `nonspeech` en `cut` vallen weg. Rijen met `unintelligible=ja` blijven.
- Hypothese: Whisper-segmenten gesorteerd op begin; segmenten waarvan het midden in een `nonspeech`- of `cut`-gebied valt worden weggelaten (aantal wordt gerapporteerd).
- Normalisatie (identiek voor referentie en hypothese): NFKC, kleine letters; `’‘` → `'`; tekst tussen `(…)` en `[…]` weg; `-` en `_` → spatie; alle overige leestekens → spatie, apostrof blijft binnen woorden (`z'n`); losse apostrofs weg; cijfers blijven zoals ze zijn (geen cijfer/woord-omzetting).
- Tussenwerpsels: **primair** worden aarzelgeluiden verwijderd: `uh, uhh, uhm, euh, euhm, eh, ehh, ehm, hm, hmm, hmmm, mm, mmm, mhm`. Lexicale tussenwerpsels (`ja, nee, oh, ah, hè, wow, …`) blijven. De variant met aarzelgeluiden erin wordt altijd ook gerapporteerd.
- WER = (S + D + I) / aantal referentiewoorden; CER op de genormaliseerde tekenreeks (spaties tellen mee). Lege referentie → `rate = null` met reden, nooit 0.
- Tweede referentie (`*_manual.txt`, labels `Docent:`/`Leerling n:` en aanhalingstekens verwijderd): alleen voor audio 1, 2, 5, **los** gerapporteerd; plus de WER tussen de twee referenties onderling. Referenties die onderling > 5 % WER verschillen worden niet tot één getal samengevoegd.
- Circulariteitstoets: aandeel referentierijen waarvan de genormaliseerde tekst gelijk is aan het in tijd best overlappende Whisper-segment. **≥ 0,90 ⇒ `circular`: de WER wordt wel berekend maar gemarkeerd "niet rapporteren".**
- Implementatie zonder externe dependency; gecontroleerd tegen `jiwer 4.0.0` in een geïsoleerde venv (`crosscheck_jiwer.py`).

## 7. Sprekers: ruwe DER

Hypothese = ruwe pyannote-beurten (RTTM, vóór koppeling aan Whisper-segmenten). Een tweede, aparte hypothese = `speaker_raw` per Whisper-segment (zoals de pipeline het uitlevert), met dezelfde grid.
Referentie = alleen `speech`-rijen; gelijktijdige sprekers blijven gelijktijdig. Optimale 1-op-1-labelkoppeling (`pyannote.metrics`). Componenten (gemist / vals alarm / verwisseling) in seconden én als fractie.

Vooraf vastgelegde raster (alle 8 combinaties worden altijd gerapporteerd, niets wordt achteraf geselecteerd):

| Dimensie | Waarden |
|---|---|
| Collar | **0 s** en **0,25 s per kant** van elke referentiegrens (NIST/DIHARD-conventie; pyannote-parameter = 2 × 0,25). De eerdere audits gebruikten pyannote-parameter 0,25 (= ±0,125 s): niet vergelijkbaar. |
| UEM | `labelled` (alleen in gelabelde bekende-sprekerrijen; vals alarm in gaten onzichtbaar) en `strict` (hele audio min maskers; gaten tellen als stilte) |
| Overlap | `keep` (alles scoren) en `exclude` (rijen met `overlap=ja` én alle tijd met ≥ 2 gelijktijdige referentiesprekers uit de UEM) |

Kopcijfer voor onderlinge vergelijking van runs (vooraf gekozen, niet achteraf te wijzigen): `uem=labelled | overlap=exclude | collar=0,25`. Dit is een vergelijkingsgetal, geen kwaliteitsclaim.
`skip_overlap` van pyannote wordt niet gebruikt: overlap wordt expliciet via de UEM behandeld.
Een lege UEM of 0 s referentiespraak geeft `der = null` met reden.

## 8. Segmentgebaseerde evaluatie

Voor elk Whisper-segment (tijdsvenster) wordt de referentiespraak erin berekend. Status (evaluatieontwerp, **geen pipelinedrempels**):
`masked` (≥ 50 % gemaskeerd/onbekend) → `no_ref_speech` (< 30 % bekende spraak) → `mixed` (tweede referentiespreker ≥ 15 % van het segment) → anders `single`.
Alleen `single` telt voor de nauwkeurigheid in seconden (optimale koppeling `speaker_raw` → referentiespreker; niet-toegewezen segment = fout). `mixed`, `masked`, `no_ref_speech` worden geteld en getoond, **nooit stil weggelaten**. Dit voorkomt dat twee sprekers binnen één ASR-segment als één spreker in de referentie verdwijnen: de referentie volgt de CSV, niet het ASR-segment.

## 9. Docentrol

Per preprocessing-turn wordt de referentierol bepaald uit de tijd (`docent`/`leerling`/`mixed`/`none`, zelfde 30 %/15 %-regel). Voorspelling: `DOCENT` / `OTHER` / `ONZEKER` / niet beoordeeld. Rapportage:
volledige tabel referentierol × voorspelling (turns én seconden); **`ONZEKER` altijd als eigen kolom**; `coverage` (aandeel beslissingen), `decided_accuracy` (alleen DOCENT/OTHER), `strict_accuracy` (ONZEKER telt als fout). `mixed`/`none` worden getoond, niet gescoord. Drempel 0,35 en alle pipelinewaarden ongewijzigd. Audio 4: geen rolreferentie → geen score.

## 10. Vooraf: wat is exploratief

Alle getallen zijn **ontwikkeldata, optimistisch** (zie §11). Daarbovenop gelden de volgende vooraf bekende beperkingen; `score_run.py` leidt de meeste daarvan automatisch uit de data af en zet ze in `evidence`:

| Meting | Status | Reden |
|---|---|---|
| WER/CER, alle fragmenten | **exploratief** | referenties zijn gemaakt met Whisper als voorinvulling (README `hyperparameter_tuning`) |
| WER/CER testaudio4, testaudio7 (en `final`) | **niet rapporteren** zodra circulair | transcript is (vrijwel) identiek aan Whisper (87/87, 35/38) |
| WER/CER audio 1 | exploratief+ | rijen overlappen in tijd (volgorde dubbelzinnig); twee tekstreferenties verschillen ≈ 20 % |
| WER/CER audio 5 | exploratief+ | ruis; eerdere runs verschilden (9 van 21 segmenten); `ONBEKEND`-tekst |
| DER met `overlap=keep` | **exploratief** | overlap is alleen als boolean geannoteerd, zonder tweede spreker |
| DER audio 4, 7 (en 2-tracked) | **exploratief** | referentiegrenzen op ASR-raster/hele seconden → meet deels consistentie met Whisper |
| DER audio 1, 5 | **exploratief** | lange overlapzones, `ONBEKEND`-gebieden |
| DER audio 2 raster, `overlap=exclude` | indicatief (alleen onder de dev-reserve) | 0,1 s-grenzen, tekst deels onafhankelijk |
| Segmentscore | indicatief waar de grenzen niet op het ASR-raster liggen, anders exploratief | idem |
| Docentrol | exploratief | drempel 0,35 is in-sample gekozen op audio 1/2/5; één docent, één referentieclip |
| Alles per spreker < 10 s (o.a. B in audio 2, C/D in audio 4) | exploratief | te weinig data |

`intelligible` wordt niet gebruikt om iets uit te sluiten. `unintelligible=ja` wordt alleen als waarschuwing naast de scores gemeld.

## 11. Ontwikkeldata en achtergehouden testdata

- **Ontwikkeldata** = alle fragmenten in §2. Ze zijn al gebruikt voor tuning (`min_cluster_size`, `threshold`), de docentdrempel, de overlapregel en eerdere audits. Elk getal wordt gemarkeerd "dev, optimistisch".
- **Achtergehouden testdata bestaat nog niet.** Kandidaten: `testaudio3` en de niet-fragmentdelen van de volledige `testaudio1/2/4/5.mp3` (offset van de fragmenten is niet vastgelegd; eerst bepalen). Die zouden door de gebruiker **zonder Whisper-voorinvulling** geannoteerd moeten worden, per opnamesessie gescheiden, met hash en datum vastgelegd vóór de eerste modelrun, en slechts één keer gescoord na bevriezing van dit protocol.
- Geen enkele parameter, drempel of normalisatieregel wordt gewijzigd op basis van scores. De testset wordt niet gebruikt om protocolkeuzes te maken.

## 12. Hypothesen en falsificatiecriteria (vooraf)

| # | Hypothese | Verworpen als |
|---|---|---|
| H1 | De scorers rekenen correct | een van de 52 tests of de jiwer-kruiscontrole faalt, of een opzettelijk kapotte scorer door alle tests komt (mutatietests) |
| H2 | Het harnas laat bestaande caches, `src/` en referenties onaangeroerd | `no_touch_check` in `run_result.json` toont toegevoegde/gewijzigde bestanden in `Data-local/processed`, een andere hash van `src/*.py` of een CSV |
| H3 | Dezelfde pipeline geeft op hetzelfde fragment dezelfde uitvoer | twee runs verschillen in segmentaantal, tekst, segmenttijden of RTTM. Voor audio 5 wordt dit **verwacht** (eerdere runs verschilden). |
| H4 | De raster-referentie van audio 2 is niet circulair, die van audio 4 en 7 wel | `circularity.ratio` van audio 2 ≥ 0,90, of van audio 4 < 0,90 |
| H5 | Een WER van exact 0,000 op echte klasaudio duidt op een circulaire referentie, niet op perfecte transcriptie | een WER 0 bij een referentie die niet circulair is (dan is de aanname onjuist of de toets te grof) |
| H6 | Ruwe-beurten-DER laat fouten zien die in de segmentversie verdwijnen (twee sprekers binnen één segment) | segment- en ruwe DER vrijwel gelijk én geen `mixed` segmenten op audio 2 |

H3–H6 worden pas na de runs getoetst; de uitkomst (ook "verworpen") wordt rapporteerd.

## 13. Uitvoer en reproduceerbaarheid

- Nieuwe root: `Data-local/evaluation/baseline_v1/runs/<run_id>/<fragment>/` (gitignored). Elke run maakt een **nieuwe** map; bestaat die al dan stopt de runner. Bestanden worden met modus `x` geschreven. Bestaande caches (`Data-local/processed/**`) worden niet gelezen als resultaat en niet geschreven.
- Per fragment: `run_manifest.json` (vooraf: invoerhashes, instellingen, omgeving, git), `01_transcript/`, `02_diarization/` (`raw_turns.rttm`, `raw_turns.json`, `*_diarized.json`), `03_preprocessing/`, `04_docent/`, `wav/`, `wav_ref/`, `logs/<stap>.log`, `run_result.json` (status en foutmeldingen per stap, hashes van uitvoer, `no_touch_check`), later `scores_v1.json`.
- De runner roept de **originele** `main()` van `transcription.py`, `diarization.py`, `preprocessing.py` en `docent_recognition.py` aan met dezelfde argumenten als `run_docent_pipeline.py` (model `medium`, geen speakerpriors, geen drempeloverride). Alleen de uitvoerpaden (module-variabelen) worden in het draaiende proces omgezet en na afloop hersteld; `PyannoteBackend.diarize` wordt ingepakt om de ruwe beurten te bewaren. Er is geen netwerk nodig (`HF_HUB_OFFLINE=1`).
- Fouten (afsluitcode, uitzondering met traceback) worden bewaard; een mislukte stap stopt de volgende stappen en wordt niet verborgen.
- Seeds: de pipeline zet er geen; dit blijft zo (instellingen niet wijzigen). Daarom H3 met twee runs.
- Tokens: alleen "aanwezig ja/nee" wordt gelogd; waarden worden nooit gelezen in logs of manifest.

## 14. Wat dit protocol niet doet

Geen tuning, geen modelvergelijking, geen classificatie, geen nieuwe annotatie, geen uitspraken over generalisatie of over productiekwaliteit. Geen controle van `testdocent.mp3` op stemlek naar testfragmenten (herkomst onbekend).

## 15. Versielog

- v1 — 2026-10-12 — eerste vastlegging; `intelligible`-betekenis gecorrigeerd door de gebruiker (ja = moeilijk/niet verstaanbaar), raster-CSV als primaire referentie voor audio 2.
