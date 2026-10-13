# Baseline readiness — fase 1, stap 4B

Datum: 2026-10-12 · Repo `main` @ `0a4ab99` · Protocol: [PROTOCOL.md](PROTOCOL.md) (v1, bevroren)

Er is **geen enkele echte audio-run** uitgevoerd. Bewijslabels: **[GETEST]** uitgevoerd en uitvoer bewaard · **[STATISCH]** alleen inspectie · **[NIET GETEST]**.

## 1. Conclusie in drie regels

- Het harnas is gebouwd en de **scorers zijn aantoonbaar correct op synthetische voorbeelden** (52 tests, jiwer-kruiscontrole zonder afwijking, mutatietests bewijzen dat de tests kunnen falen).
- Alle drie de modellen laden offline vanuit de lokale cache; het invoerpad, de referenties en de omleiding van de uitvoer zijn gecontroleerd. De volledige keten met echte inferentie is **nog niet** gedraaid.
- **Eén eerste kleine run (`testaudio2_fragment`, 30 s) kan veilig worden uitgevoerd.** Het schrijft uitsluitend naar een nieuwe map, overschrijft niets en legt fouten vast.

## 2. Wat aantoonbaar slaagt

| # | Voorbereiding | Bewijs |
|---|---|---|
| 1 | Scorertests 1–10 uit de opdracht + extra's (52 tests, 0 fouten): WER 0 / 1 fout woord / lege referentie, DER 0 / verwisseling / gemist / vals alarm, collar per kant, gelijktijdige sprekers, ONBEKEND geen extra persoon, twee sprekers in één ASR-segment, ONZEKER blijft apart, ontbrekende referentie/onleesbare audio, geen overschrijven | [GETEST] [test_output_scorers.txt](test_output_scorers.txt) |
| 2 | Verwachte waarden zijn met de hand uit tijdsrekenkunde afgeleid, niet uit de software (bijv. verwisseling van 5 s op 10 s ⇒ DER 0,5; 4 s gemiste overlap op 14 s ⇒ 4/14) | [STATISCH] zie commentaar in `tests/test_scorers.py` |
| 3 | De tests kunnen falen: een opzettelijk kapotte WER-, DER-, rol- (ONZEKER wegfilteren) en segmentscorer laat de echte tests mislukken | [GETEST] klasse `MutationSensitivity` |
| 4 | Onze WER/CER stemt overeen met `jiwer 4.0.0` (524 paren: 500 willekeurig + echte tekstparen; totale afstand identiek) | [GETEST] [test_output_jiwer_crosscheck.txt](test_output_jiwer_crosscheck.txt) |
| 5 | De originele modules bevatten de variabelen die de runner omzet; omleiding van de originele `preprocessing.main()` schrijft alleen naar de tijdelijke map, herstelt de variabele, en laat `Data-local/processed` en `src/*.py` onaangeroerd | [GETEST] `tests/test_wiring_no_models.py` |
| 6 | Standaardinstellingen van de pipeline (medium, cpu/int8, beam 5, VAD aan, geen speakerpriors, drempel 0,35) komen overeen met wat `run_docent_pipeline.py` doorgeeft | [GETEST] idem |
| 7 | Alle 6 gebruikte referenties parsen zonder fout; ONBEKEND/GEEN/"niet meenemen" worden geen spreker; originele CSV's worden niet gewijzigd door het inlezen (hash voor/na gelijk) | [GETEST] `RealReferenceChecks` |
| 8 | `score_run.py` scoort alle onderdelen, schrijft één nieuw bestand, weigert te overschrijven, weigert bij gewijzigde referentiehash; de circulariteitstoets markeert testaudio4 als circulair en de raster niet (voorspelling H4) | [GETEST] `tests/test_score_run_mechanics.py` (op een nagebouwde fixture van oude cachebestanden; **geen baseline**, de getallen zijn niet bewaard) |
| 9 | Preflight voor `testaudio2_fragment`: audio leesbaar (30,01 s), referentie 19 rijen/2 sprekers, rolbron en handmatige tekst aanwezig, hashes, omgeving, modelrevisies, `HF_TOKEN` aanwezig (waarde nooit getoond), offline-modus aan | [GETEST] [preflight_output.txt](preflight_output.txt) |
| 10 | Modellen laden offline zonder audio te verwerken: Whisper medium 5,0 s, pyannote 3.1 12,6 s, WeSpeaker + docentreferentie 1,5 s | [GETEST] [preflight_model_load_output.txt](preflight_model_load_output.txt) |
| 11 | Geen bestaande bestanden gewijzigd: `git status` toont alleen ongetrackte bestanden (nieuwe map `baseline_evaluation/`, plus de reeds ongetrackte raster-CSV e.d.); hash van `src/*.py` gelijk aan PROTOCOL; `Data-local/evaluation/` is niet aangemaakt | [GETEST] |
| 12 | Isolatie: `jiwer` staat alleen in `baseline_evaluation/.venv-eval` (gitignored); in de projectomgeving is niets geïnstalleerd; tests draaien met `unittest` (geen `pytest` nodig) | [GETEST] |

## 3. Wat nog geblokkeerd of onbewezen is

| Onderdeel | Status | Gevolg |
|---|---|---|
| Echte inferentie via de runner (Whisper-transcriptie, pyannote-diarisatie, docentembedding op audio) | **[NIET GETEST]** | Dit is precies wat de eerste run toetst. Risico's: onvoorziene fout in een stap (wordt vastgelegd), de capture-wrapper om `PyannoteBackend.diarize`, het hergebruik van de wav in `wav/` door stap 4. |
| Validiteit van de HF-token | **[NIET GETEST]** | Offline modus heeft de token niet nodig (modellen staan in de cache). Pas relevant bij `--online`. |
| Determinisme van Whisper/pyannote | **[NIET GETEST]** | Hypothese H3 vraagt een tweede run (`…_run2`). Voor audio 5 wordt afwijking verwacht. |
| Raster-CSV is ongecommit | open | De hash staat vastgelegd, maar voor volledige reproduceerbaarheid moet je de CSV committen (jouw beslissing; niet door mij gedaan). `git status` komt in elk manifest. |
| Achtergehouden testset | bestaat niet | Alles blijft "dev, optimistisch". Aanmaken vraagt jouw annotatie zonder Whisper-voorinvulling (PROTOCOL §11). |
| Docentreferentie `testdocent.mp3` | herkomst onbekend | Niet nagegaan of die stem ook in een testfragment zit (stemlek-risico). |
| Audio 4 rollen, `final_testfragment` | ontbreekt | Geen rolscore voor audio 4; `final` valt buiten de baseline. |
| Audio 1 tekstreferenties | twee verschillende bronnen (≈ 20 % WER onderling) | Worden apart gerapporteerd, niet samengevoegd. |

## 4. Kan één eerste kleine run veilig worden uitgevoerd?

**Ja**, voor `testaudio2_fragment` (30,0 s; voorgaande ruwe runtimes in dit project: Whisper ≈ 35 s, totaal naar schatting 1–3 min op CPU, niet gemeten met dit harnas). Waarom veilig:

- schrijft naar `Data-local/evaluation/baseline_v1/runs/<run_id>/testaudio2_fragment/` en weigert als die map al bestaat; alle bestanden met modus `x`;
- gebruikt geen oude JSON als invoer of resultaat; leest alleen audio, referenties en de modelcache;
- offline (`HF_HUB_OFFLINE=1`), geen downloads; geen tokenwaarde in logs;
- een mislukte stap wordt met traceback bewaard en stopt de volgende stappen; `run_result.json` bevat een `no_touch_check` (bestaande caches, `src/*.py`, referenties).

**Resultaten die exploratief blijven** (PROTOCOL §10): alle WER/CER (Whisper-voorgevulde referenties; audio 4 en 7 circulair), DER met `overlap=keep`, DER voor audio 1/4/5/7 (ASR-raster of lange overlap/ONBEKEND), docentrol (drempel in-sample), alles per spreker < 10 s (o.a. B in audio 2). `unintelligible=ja` is alleen een waarschuwing, geen uitsluiting.

## 5. Exact commando voor de eerste run

Vanuit `C:\Users\School\StudieStap\StudieStap_WorkshopTool`. Stap 1, de run (Whisper → pyannote → preprocessing → docentherkenning):

```bash
Data-analysis/src/.venv/Scripts/python.exe -B Data-analysis/Experiments/baseline_evaluation/run_baseline.py --fragment testaudio2_fragment --run-id 20261012_dev_run1
```

Stap 2, scoren (pas als stap 1 `all_stages_ok: true` meldt):

```bash
Data-analysis/src/.venv/Scripts/python.exe -B Data-analysis/Experiments/baseline_evaluation/score_run.py --run-dir Data-local/evaluation/baseline_v1/runs/20261012_dev_run1/testaudio2_fragment
```

Stap 3 (aanbevolen, voor H3): dezelfde run met `--run-id 20261012_dev_run2`, daarna de twee uitvoermappen vergelijken (segmenten, tekst, RTTM). Gebruik een **nieuw** `run-id` per poging: een bestaand id wordt geweigerd.

Hertesten van het harnas zelf:

```bash
Data-analysis/src/.venv/Scripts/python.exe -B -m unittest discover -s Data-analysis/Experiments/baseline_evaluation/tests
```

## 6. Bestanden

| Bestand | Inhoud |
|---|---|
| [PROTOCOL.md](PROTOCOL.md) | bevroren protocol v1 |
| [run_manifest.template.json](run_manifest.template.json) | manifesttemplate (de runner schrijft het ingevulde manifest) |
| [run_baseline.py](run_baseline.py) | runner (+ `--preflight`, `--load-models`) |
| [score_run.py](score_run.py) | scoort een run (WER/CER, ruwe DER, segment, docentrol) |
| `baseline_eval/` | `text.py` (WER/CER), `refs.py` (referenties, maskers), `diar.py` (DER, segment, rol, circulariteit), `runlib.py` (veilige uitvoer, omgeving), `settings.py` |
| `tests/` | scorertests, wiring zonder modellen, scoremechaniek |
| [crosscheck_jiwer.py](crosscheck_jiwer.py) | kruiscontrole tegen jiwer (isolatie-venv) |
| [test_output_scorers.txt](test_output_scorers.txt), [test_output_jiwer_crosscheck.txt](test_output_jiwer_crosscheck.txt), [preflight_output.txt](preflight_output.txt), [preflight_model_load_output.txt](preflight_model_load_output.txt) | testuitvoer |
| [baseline_preflight_claude.md](baseline_preflight_claude.md) | rapport van stap 4A (ongewijzigd) |

## 7. Beperkingen van dit harnas

- De scorertests bewijzen dat de rekenregels kloppen, niet dat de keuzes (UEM-varianten, 15 %/30 %-regels, collar per kant) de beste zijn; die zijn vooraf vastgelegd en transparant.
- De segmentstatusdrempels (15 %, 30 %, 50 %) zijn evaluatieontwerp, geen gevalideerde grenzen.
- De omleiding van uitvoerpaden werkt door module-variabelen tijdelijk te zetten in het draaiende proces; een toekomstige wijziging in `src/` die paden anders bepaalt, zou de wiring-tests laten falen (ze controleren het bestaan van de variabelen) maar niet automatisch alle gevolgen afdekken.
- Het harnas meet de pipeline zoals die nu is; het zegt niets over verbetermogelijkheden en doet geen tuning.
