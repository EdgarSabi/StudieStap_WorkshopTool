# Omgevingscontrole — oorspronkelijke ChatGPT-audit StudieStap fase 1

Datum aanvullende controle: **9 oktober 2026**. Dit document corrigeert de feitelijke beschikbaarheidsclaims van de oorspronkelijke audit; het is geen nieuwe technische of modelaudit. Alleen dit rapport en `manifest_omgeving_chatgpt.json` zijn voor deze controle aangemaakt. Oorspronkelijke bestanden, auditlogs en manifests zijn niet aangepast. Er zijn geen nieuwe unitproeven, audiodecoderingen, transcripties, embeddings, diarizatie- of modeltests uitgevoerd. Het lezen en hashen van modelbestanden is geen modeluitvoering.

## Kernbevinding en noodzakelijke correctie

**De audio was tijdens de oorspronkelijke audit aantoonbaar beschikbaar.** Zowel `Audit_fase1_2026-10-09/manifest.json` als de ingebedde bestandslijst in `inventory.json` bevat alle **13 MP3-bestanden** onder `Data-analysis/src/test-files`, inclusief de docentreferentie `testdocent.mp3`, met groottes en SHA-256-hashes. De bestandslijst in de inventarisbijlage vermeldt ze ook.

De eerdere uitspraken dat `src/test-files`, audio en referentieaudio ontbraken, zijn daarmee **in strijd met de eigen oorspronkelijke auditregistratie**. Dat was een fout in de interpretatie en rapportage. Het ontbreken van audiometingen mag niet worden gerechtvaardigd met die vermeende afwezigheid. De latere ontdekking bevestigde hun zichtbaarheid, maar is niet het enige bewijs: de oorspronkelijke manifests leggen aanwezigheid al vast.

Bij de huidige controle zijn alle **102 oorspronkelijke manifestrecords** teruggevonden met identieke grootte en hash. Er is dus geen bestandsverandering tussen die snapshot en nu aangetoond. Een manifest is een momentopname tijdens de audit, geen continue registratie vanaf het eerste commando; de precieze beschikbaarheid vóór die snapshot wordt er niet seconde voor seconde door bewezen.

## 1. Bewijsklassen en gebruikte bronnen

- **Oorspronkelijk vastgelegd:** oorspronkelijke manifests, dependency-inventaris, testresultaten, baseline-testlogs, integriteitscontrole en bewaarde tooluitvoer uit dit gesprek.
- **Huidige waarneming:** nieuwe bestands-/hashcontrole, Git-status, package-metadata, tokenaanwezigheidscontrole, geselecteerde cache-inventaris en hardwarequeries.
- **Reconstructie achteraf:** vergelijking van die registraties met codevereisten. Deze wordt niet als destijds uitgevoerde preflight of meting gepresenteerd.

Gebruikte oorspronkelijke bewijsbestanden:

| Bestand in `Audit_fase1_2026-10-09/` | Betekenis |
|---|---|
| `manifest.json` | 102 pad/grootte/SHA-256-records, inclusief 13 MP3's |
| `inventory.json` | Interpreter, packageversies, JSON/CSV/syntaxinventaris, notebookceluitvoering, dezelfde bestandsregistratie |
| `baseline_src.txt` | Geslaagde oorspronkelijke 17 src-unitproeven |
| `baseline_classification.txt` | Geslaagde oorspronkelijke 51 classificatie-unitproeven |
| `test_results.json` | 32 aanvullende auditproeven en expliciete invoer/uitkomsten |
| `dependency_check.txt` | Toen waargenomen numba/numpy-conflict |
| `integriteitscontrole.json` | Toen vastgelegde 102 bestandschecks, geen hashverschillen |
| `run_audit.py` | Vastgelegde auditwerkwijze en gebruik van testdoubles; niet opnieuw gestart |

De teksten/conclusies van de andere reviewer onder `Data-analysis/Audit` zijn niet gebruikt. Hun bestanden staan uitsluitend als huidige audit-artifacts in het nieuwe manifest; aanwezigheid bewijst niet wat deze ChatGPT-audit destijds heeft uitgevoerd. De oorspronkelijke logs hebben geen volledige timestamp- en commandoreeks voor ieder afzonderlijk experiment. Het oorspronkelijke manifest is bovendien niet cryptografisch ondertekend of buiten deze omgeving verzegeld; vergelijking tussen omgevingen moet daarom ook deze bewijsbestanden zelf meenemen.

## 2. Repository, branch, commit en werkboom

**Exacte repositorylocatie:** `C:\Users\School\Projects\StudieStap_WorkshopTool`.

**Oorspronkelijke audit:** deze locatie en commit `33cc8a10eb2aea0a161b387f08ce0192b46e89bc` zijn vastgelegd in de gesprekstooluitvoer en het auditrapport. Een expliciete oorspronkelijke branchmeting ontbreekt. De branchnaam van toen kan dus niet met zekerheid uit de commit worden afgeleid.

**Huidige controle:** branch `main`; commit eveneens `33cc8a10eb2aea0a161b387f08ce0192b46e89bc`. Alle 13 MP3-paden zijn momenteel ook geregistreerd door `git ls-files`. Dat laatste is een huidige Git-waarneming.

De eerste oorspronkelijke `git status --short` in dit gesprek vermeldde:

```text
 M Data-analysis/Experiments/diarization/hyperparameter_tuning/ground_truth_final_testfragment.csv
 M Data-analysis/Experiments/diarization/hyperparameter_tuning/ground_truth_template.csv
 M Data-analysis/Experiments/diarization/hyperparameter_tuning/ground_truth_testaudio2_fragment.csv
 M Data-analysis/Experiments/diarization/hyperparameter_tuning/ground_truth_testaudio4_fragment.csv
 M Data-analysis/Notebooks/03-transcription-evaluation.ipynb
?? Data-analysis/Experiments/diarization/hyperparameter_tuning/ground_truth_testaudio1_fragment.csv
?? Data-analysis/Experiments/diarization/hyperparameter_tuning/ground_truth_testaudio5_fragment.csv
?? Data-analysis/Experiments/diarization/hyperparameter_tuning/ground_truth_testaudio7_fragment.csv
```

Dit zijn reeds aanwezige gebruikerswijzigingen. De audit onderzocht de werkboom inclusief deze bestanden, niet uitsluitend de gecommitte toestand. Bij afronding kwam de nieuwe `Audit_fase1_2026-10-09/`-map erbij. Bij de huidige controle staat tevens `Data-analysis/Audit/` als untracked vermeld. Dit aanvullende rapport en manifest zijn ook nieuwe, niet-gecommitte artifacts. De commit alleen identificeert dus niet de gehele onderzochte omgeving. Voor de volledige huidige status zie `current_git` in het aanvullende manifest.

## 3. Aanwezige bestanden tijdens de oorspronkelijke audit

Onderstaande tellingen komen uit het oorspronkelijke manifest, niet uit een nieuw testresultaat.

| Categorie | Vastgelegd aantal | Betekenis |
|---|---:|---|
| Audio | 13 | MP3, inclusief volledige opnamen, fragmenten en docentreferentie |
| Python | 28 | Pipeline, experimenten, helpers en bestaande tests |
| Notebookbestanden | 8 | 6 actieve notebooks plus 2 `.ipynb_checkpoints`-kopieën |
| JSON | 8 | 3 synthetische classificatiefixtures en 5 samengevatte tuningresultaten |
| CSV | 7 | Ground-truth-/templatebestanden |
| YAML | 1 | Klein tekstbestand met verwijzing naar SpeechBrain-cache |
| Requirements | 2 | Hoofdroute en afzonderlijk WhisperX-experiment |

Daarnaast zijn documenten, afbeeldingen, README's en placeholders opgenomen. In totaal omvat de oorspronkelijke snapshot 102 bestanden. Bytecode, Git-interne bestanden, IDE-bestanden en de eigen auditmap waren destijds door de manifestschrijver uitgesloten. Afwezigheid uit een manifest bewijst voor zulke uitgesloten groepen geen afwezigheid op de computer.

### Audio onder `Data-analysis/src/test-files`

| Bestandsnaam | Bytes |
|---|---:|

| testaudio1.mp3 | 2812546 |

| testaudio1_fragment.mp3 | 274853 |

| testaudio2.mp3 | 4735263 |

| testaudio2_fragment.mp3 | 298173 |

| testaudio3.mp3 | 1103141 |

| testaudio4.mp3 | 3068980 |

| testaudio4_fragment.mp3 | 1352281 |

| testaudio5.mp3 | 1727188 |

| testaudio5_fragment.mp3 | 417950 |

| testaudio6_fragment.mp3 | 1703373 |

| testaudio7_fragment.mp3 | 1399821 |

| testaudio8_fragment.mp3 | 1014381 |

| testdocent.mp3 | 919653 |

De originele en huidige SHA-256-hashes zijn identiek en staan in het aanvullende manifest. De oorspronkelijke audit heeft deze audio niet beluisterd, gedecodeerd of met een ASR-/diarizatiemodel verwerkt. Aanwezigheid met hash bewijst leesbaarheid van bytes op het manifestmoment; zij bewijst nog geen geldigheid van het audiocontainerformaat of verstaanbaarheid.

### Volledige lijsten van Python, notebooks, JSON en CSV

Alle paden hieronder zijn relatief aan de repositoryroot.

#### Python

- `Data-analysis/Afgeronde_experimenten/diarization/community1/community1_test.py`

- `Data-analysis/Experiments/classification/classification.py`

- `Data-analysis/Experiments/classification/classification_data.py`

- `Data-analysis/Experiments/classification/tests/__init__.py`

- `Data-analysis/Experiments/classification/tests/test_classification.py`

- `Data-analysis/Experiments/classification/tests/test_classification_data.py`

- `Data-analysis/Experiments/diarization/hyperparameter_tuning/evaluate_min_cluster_size.py`

- `Data-analysis/Experiments/diarization/whisperx/whisperx_test.py`

- `Data-analysis/Experiments/speaker_recognition/_common.py`

- `Data-analysis/Experiments/speaker_recognition/pyannote_embeddings/test_teacher_recognition.py`

- `Data-analysis/Experiments/speaker_recognition/speechbrain_ecapa/test_teacher_recognition.py`

- `Data-analysis/Experiments/word_level_speaker_attribution/01_word_timestamps/extract_word_timestamps.py`

- `Data-analysis/Experiments/word_level_speaker_attribution/02_word_level_attribution/attribute_words_to_speakers.py`

- `Data-analysis/Experiments/word_level_speaker_attribution/03_recognition_refinement/refine_with_speaker_recognition.py`

- `Data-analysis/Experiments/word_level_speaker_attribution/_common.py`

- `Data-analysis/src/config.py`

- `Data-analysis/src/diarization.py`

- `Data-analysis/src/docent_recognition.py`

- `Data-analysis/src/evaluation/__init__.py`

- `Data-analysis/src/evaluation/wer.py`

- `Data-analysis/src/models.py`

- `Data-analysis/src/OLD_benchmark_transcription.py`

- `Data-analysis/src/preprocessing.py`

- `Data-analysis/src/run_docent_pipeline.py`

- `Data-analysis/src/tests/__init__.py`

- `Data-analysis/src/tests/test_docent_recognition.py`

- `Data-analysis/src/tests/test_run_docent_pipeline.py`

- `Data-analysis/src/transcription.py`

#### Notebookbestanden

- `Data-analysis/Notebooks/.ipynb_checkpoints/02-benchmarking-checkpoint.ipynb`

- `Data-analysis/Notebooks/.ipynb_checkpoints/03-transcription-evaluation-checkpoint.ipynb`

- `Data-analysis/Notebooks/01-exploring_data.ipynb`

- `Data-analysis/Notebooks/02-benchmarking.ipynb`

- `Data-analysis/Notebooks/03-transcription-evaluation.ipynb`

- `Data-analysis/Notebooks/04-diarization.ipynb`

- `Data-analysis/Notebooks/05-fixing-diarization-problems.ipynb`

- `Data-analysis/Notebooks/06-diarization-hyperparameter-tuning.ipynb`

#### JSON

- `Data-analysis/Experiments/classification/tests/fixtures/tiny_manual.json`

- `Data-analysis/Experiments/classification/tests/fixtures/tiny_pipeline.json`

- `Data-analysis/Experiments/classification/tests/fixtures/tiny_pipeline_with_docent_role.json`

- `Data-analysis/Experiments/diarization/hyperparameter_tuning/results_min_cluster_size_testaudio2_fragment.json`

- `Data-analysis/Experiments/diarization/hyperparameter_tuning/results_min_cluster_size_testaudio4_fragment.json`

- `Data-analysis/Experiments/diarization/hyperparameter_tuning/results_min_cluster_size_testaudio4_fragment_run1_12-6-3.json`

- `Data-analysis/Experiments/diarization/hyperparameter_tuning/results_threshold_testaudio2_fragment.json`

- `Data-analysis/Experiments/diarization/hyperparameter_tuning/results_threshold_testaudio4_fragment.json`

#### CSV

- `Data-analysis/Experiments/diarization/hyperparameter_tuning/ground_truth_final_testfragment.csv`

- `Data-analysis/Experiments/diarization/hyperparameter_tuning/ground_truth_template.csv`

- `Data-analysis/Experiments/diarization/hyperparameter_tuning/ground_truth_testaudio1_fragment.csv`

- `Data-analysis/Experiments/diarization/hyperparameter_tuning/ground_truth_testaudio2_fragment.csv`

- `Data-analysis/Experiments/diarization/hyperparameter_tuning/ground_truth_testaudio4_fragment.csv`

- `Data-analysis/Experiments/diarization/hyperparameter_tuning/ground_truth_testaudio5_fragment.csv`

- `Data-analysis/Experiments/diarization/hyperparameter_tuning/ground_truth_testaudio7_fragment.csv`

### Relevante configuratie en overige invoer

- `.gitignore`
- `Data-analysis/src/config.py`
- `Data-analysis/src/requirements.txt`
- `Data-analysis/Experiments/diarization/whisperx/requirements-whisperx.txt`
- `Data-analysis/src/None/speechbrain/hyperparams.yaml`
- Notebook-kernelspecificaties en metadata in de 8 geregistreerde notebookbestanden.
- `Data-local/raw/testaudio1_manual.txt` — 388 bytes, oorspronkelijk aanwezig.

Een `.env` is niet in de oorspronkelijke snapshot geregistreerd. Dit zegt niets over een token in de toenmalige procesomgeving. Het oorspronkelijke rapport noemt vijf checkpointbestanden; het manifest bevat feitelijk **vier `.ckpt`-bestanden plus één YAML-bestand**.

## 4. Ontbrekende bestanden ten opzichte van de opdracht

De oorspronkelijke opdracht noemt geen verplichte volledige bestandslijst. Daarom betreft dit ontbrekende onderdelen waarnaar de code/notebooks verwijzen of die nodig zijn voor de gevraagde metingen.

| Onderdeel | Historische vastlegging | Huidige controle / beperking |
|---|---|---|
| Audio + docentreferentie | 13 MP3's in originele manifests | Alle aanwezig, identieke hashes; mogen niet als ontbrekend worden gerapporteerd |
| Echte ASR-/diarized-/processed-uitvoer onder `Data-local/processed` | Niet geregistreerd; notebook 03/05 stoppen op concrete ontbrekende uitvoerpaden | Geen oorspronkelijke productie-uitvoer in het huidige projectmanifest aangetroffen; andere audit-JSON is geen oorspronkelijke pipelinebaseline |
| Benchmark-JSON onder `Data-local/processed/benchmark` | Notebook 02 vindt geen resultaten en stopt op results[0] | De historische uitvoer was niet beschikbaar voor die notebookrun |
| `Data-local/raw/Breinschade_Uitleg_Sara.txt` | Notebook 01 geeft FileNotFoundError | Ook niet in huidige projectmanifest |
| `testaudio2_manual.txt` en `testaudio5_manual.txt` | Niet in originele manifest; notebook 03 verwees ernaar | Niet in huidige projectmanifest; voor die tekstvergelijkingen ontbreken ze |
| Similarity-CSV's voor WeSpeaker/SpeechBrain | Notebook 04 geeft FileNotFoundError op pyannote-CSV | Niet als oorspronkelijke projectdata aangetroffen |
| Docentrol BEFORE-snapshot | Notebook 05 geeft FileNotFoundError | Niet als oorspronkelijke projectdata aangetroffen |
| Scraper/downloader, bronmanifest, downloadlogs | Geen uitvoerbare verzamelcode/manifest geregistreerd | De originele bronselectie/downloadkwaliteit is niet gereconstrueerd |
| Volledige evaluatiereferenties | CSV's en één handmatige tekst aanwezig | Aanwezigheid is geen inhoudsvalidatie; final-reference heeft lege speaker-ID's, overlapreferenties zijn niet als volledige simultane activiteitsannotaties bewezen |
| Project-venv en complete modelsnapshot | Niet historisch geïnventariseerd; gebruikte interpreter was globale Python | Cache wordt uitsluitend nu apart bekeken; geen volledig historisch cachebewijs |

Deze reconstructie bewijst concrete notebookblokkades en afwezigheid in de geregistreerde projectinventaris. Ze bewijst niet dat dezelfde bestanden niet elders op de computer, in een niet-geïnspecteerde cache of in een andere auditomgeving stonden.

## 5. Modellen: codeverwijzing, lokale bestanden en daadwerkelijke uitvoering

| Model/functie | Oorspronkelijk bewijs | Huidige lokale waarneming | Door deze oorspronkelijke audit uitgevoerd? |
|---|---|---|---|
| faster-whisper / Whisper base, medium en andere benchmarkgroottes | Config/code en geïnstalleerde library; geen oorspronkelijke HF-cache-inventaris | `Systran/faster-whisper-medium` in gecontroleerde HF-cache | **Nee**, geen echte ASR-inference; wrapper met testdouble |
| `pyannote/speaker-diarization-3.1` | Codeconfig en pyannote-package; importcheck slaagde volgens gesprekstooluitvoer | Niet aangetroffen in gecontroleerde HF-cache | **Nee**, geen Pipeline/model geladen |
| `pyannote/wespeaker-voxceleb-resnet34-LM` | Codeconfig; roltests met fake recognizer | Niet aangetroffen in gecontroleerde HF-cache | **Nee**, geen echte embeddings |
| `speechbrain/spkrec-ecapa-voxceleb` | Vier kleine `.ckpt`-bestanden plus YAML geregistreerd; SpeechBrain-package ontbreekt | Alle vijf bestanden bevatten tekstverwijzingen naar cachepaden, geen echte weights; geen SpeechBrain-snapshot in gecontroleerde HF-cache | **Nee** |
| `pyannote/speaker-diarization-community-1` | Experimentele code aanwezig | Niet aangetroffen in gecontroleerde HF-cache | **Nee** |
| WhisperX + Nederlands wav2vec2-alignment | Code/requirements aanwezig; WhisperX-package ontbreekt | Geen bijbehorende modelsnapshot aangetroffen in gecontroleerde cache | **Nee** |
| MockClassifier | Bestaande unitproeven en mockclassificatieroute | Broncode aanwezig | **Ja**, vaste synthetische antwoorden; geen ML-/didactiekmodel |

Huidige Whisper-medium-snapshot: revision `08e178d48790749d25932bbc082711ddcfdfbc4f`, onder `C:\Users\School\.cache\huggingface\hub`. Bestanden: `model.bin` (1.527.906.378 bytes), `config.json`, `tokenizer.json` en `vocabulary.txt`. Deze bestanden zijn nu leesbaar en gehasht; niet geladen. Dit maakt een lokale offline ASR-proef plausibel uitvoerbaar, maar is **geen bewijs dat de cache destijds al aanwezig was, dat inference nu slaagt of dat die proef toen is uitgevoerd**.

De huidige cachecheck beperkt zich tot de standaard/voor dit proces ingestelde Hugging Face-cache. Er is geen gehele-schijfzoekactie gedaan. Niet aangetroffen betekent uitsluitend niet aangetroffen in die gecontroleerde cache. De oude `.ckpt`-groottes/hashes bewijzen historische aanwezigheid van de tekstverwijzingen; de vaststelling van hun tekstinhoud is een huidige inspectie.

## 6. Hugging Face-token

**Huidige tokenaanwezigheid in gecontroleerde locaties: nee.**

| Gecontroleerde locatie / ingang | Token aanwezig? |
|---|---|
| `HF_TOKEN` / `HUGGINGFACE_TOKEN` in deze procesomgeving | Nee |
| Deze variabelen in repository-`.env` | Nee |
| Standaard/ingestelde lokale Hugging Face-login-tokenfile | Nee |
| Via de gebruikte pipeline-tokenlookup bereikbare token | Nee |

**Tijdens de oorspronkelijke audit:** aanwezigheid is niet vastgelegd. Er is daarom geen onderbouwd historisch ja/nee-antwoord. Dit wordt bewust als ontbrekende vastlegging gerapporteerd, niet achteraf als “nee”. Er zijn geen tokenwaarden opgenomen en geen authenticatie- of netwerkproeven uitgevoerd. Andere processen/accounts/opslaglocaties vallen buiten deze controle.

## 7. Interpreter, dependencies, FFmpeg en hardware

Oorspronkelijk vastgelegd én momenteel bevestigd:

- Interpreter: `C:\Users\School\AppData\Local\Programs\Python\Python311\python.exe`.
- Python: `3.11.5`, 64-bit AMD64, MSC v.1936.
- Audit-shellcontext: PowerShell op Windows.
- De gedocumenteerde venv is niet de interpreter waarmee deze auditproeven zijn uitgevoerd.

| Dependency | Oorspronkelijke metadata | Huidige metadata |
|---|---|---|

| faster-whisper | 1.2.1 | 1.2.1 |

| pydantic | 2.13.5 | 2.13.5 |

| numpy | 2.4.6 | 2.4.6 |

| torch | 2.14.0 | 2.14.0 |

| torchaudio | 2.11.0 | 2.11.0 |

| pyannote.audio | 4.0.7 | 4.0.7 |

| python-dotenv | 1.1.1 | 1.1.1 |

| jiwer | 4.0.0 | 4.0.0 |

| scipy | 1.17.1 | 1.17.1 |

| pandas | 2.2.3 | 2.2.3 |

| matplotlib | 3.10.3 | 3.10.3 |

| scikit-learn | 1.9.0 | 1.9.0 |

| speechbrain | Niet geregistreerd als geïnstalleerd | Niet geregistreerd als geïnstalleerd |

| whisperx | Niet geregistreerd als geïnstalleerd | Niet geregistreerd als geïnstalleerd |

| nbclient | 0.10.0 | 0.10.0 |

| soundfile | Niet geregistreerd als geïnstalleerd | Niet geregistreerd als geïnstalleerd |

De hierboven gemeten versies zijn ongewijzigd. Extra metadata die **uitsluitend nu** is verzameld: numba 0.61.2, ctranslate2 4.8.2, av 18.1.0, huggingface-hub 1.30.0. De tabel betreft de gebruikte interpreter, niet iedere Python-installatie op de computer. Geen nieuw `pip check` uitgevoerd; het oorspronkelijke log meldt numba 0.61.2 met requirement numpy<2.3 tegenover geïnstalleerde numpy 2.4.6. Het requirementsbestand is niet opnieuw geïnstalleerd of getoetst.

FFmpeg-pad werd destijds in gesprekstooluitvoer gevonden: `C:\Users\School\Downloads\ffmpeg\bin\ffmpeg.exe`. De versie is uitsluitend nu uitgelezen: `2025-07-12-git-35a6de137a-full_build-www.gyan.dev`, statische full build. Een versiequery is geen audio- of modeltest.

**Hardware uitsluitend nu uitgelezen:**

| Onderdeel | Huidige waarneming |
|---|---|
| CPU | Intel Core i7-8700K @ 3,70 GHz |
| Cores / logische processors | 6 / 12 |
| Fysiek RAM | 17.029.754.880 bytes (circa 15,86 GiB) |
| GPU | NVIDIA GeForce RTX 4060 |
| GPU-geheugen via nvidia-smi | 8188 MiB |
| NVIDIA-driver | 617.42 |
| Geïntegreerde GPU | Intel UHD Graphics 630 |

De beperkte omgeving blokkeerde de eerste CIM-read; dezelfde uitsluitend lezende hardwarequery is daarna met goedkeuring uitgevoerd. `nvidia-smi` is alleen voor inventarisatie gebruikt. De oorspronkelijke audit bevat geen hardwaremeting, CUDA-bruikbaarheidscontrole of hardwarebenchmark. Hoewel de code standaard CPU configureert, kunnen huidige GPU-specificaties niet worden gepresenteerd als destijds gebruikte versneller. De synthetische proeven gebruikten CPU-waveforms; geen modelruntime is gemeten.

## 8. Uitgevoerde en niet-uitgevoerde controles

Dit overzicht leest bestaande logs; er zijn geen tests opnieuw gedraaid.

| Controle tijdens oorspronkelijke audit | Uitvoering aangetoond? | Historische conclusie / beperking |
|---|---|---|
| Src-unitproeven | Ja: 17/17, baseline_src.txt | Beslislogica/orkestratie; geen ML-accuracy |
| Classificatie-unitproeven | Ja: 51/51, baseline_classification.txt | Fixtures/context/schema/mock; geen echte indicatorherkenning |
| Synthetische auditproeven | Ja: 32, test_results.json | 9 bevestigingen, 23 weerleggingen van gekozen verwachtingen; niet 23 audiofouten |
| Python-syntax | Ja: 28 bestanden, inventory.json | Parsecontrole, geen garantie op alle runtimepaden |
| JSON-syntax | Ja: 8 projectbestanden | Geen controle van ontbrekende echte pipeline-uitvoer |
| Referentie-CSV-structuur | Ja, inventory/test_results | Niet beluisterd/gevalideerd tegen audio |
| Notebook 01–06 | Ja, codecellen in geheugen | 06 compleet; 01–05 stoppen op vastgelegde fouten; geen volledige Jupyter-kernelrun |
| 2 notebookcheckpointkopieën | Alleen in manifest | Niet als aparte notebooks uitgevoerd |
| Torchaudio-/pyannote-importcheck | Ja, oorspronkelijke gesprekstooluitvoer | Module-import, geen modellaad-/inferenceproef; niet als apart bestand gelogd |
| Dependencycontrole | Ja, oorspronkelijk pip-checklog | Inconsistentie numba/numpy |
| Audiobestandsbytes hashen | Ja, oorspronkelijke manifests | Aanwezigheid/byte-identiteit; geen decodeerkwaliteit |
| WAV-loader op synthetische PCM/truncated data | Ja, test_results | Formaat/sample-rate/integriteit; geen echte MP3- of verstaanbaarheidstest |
| Echte audio beluisteren/decodeerbaarheid controleren | Nee | Was niet bewezen onmogelijk; audio stond in de snapshot |
| ASR op oorspronkelijke MP3's | Nee | Historische lokale modelsnapshot/preflight niet vastgesteld; audiogebrek was onjuiste reden |
| Diarizatie/echte speakerembeddings | Nee | Token/cache historisch niet vastgesteld; uitvoerbaarheid dus niet vooraf bewezen of weerlegd |
| WER/CER | Nee | Geen vergelijking van echte ASR-hypothese en exact begrensde referentie; bestaande referentietekst aanwezig |
| DER / miss / false alarm / confusion | Nee | Geen ruwe modelhypothese; volledige gevalideerde annotatie niet aangetoond |
| Nieuwe classifier/training | Nee | Buiten scope |

### Wat kon en kon niet worden vastgesteld over uitvoerbaarheid?

De succesvolle unit-, schema-, geometry-, WAV- en notebookproeven waren daadwerkelijk uitvoerbaar. De oorspronkelijke root-discovery mislukte door imports; dezelfde suites slaagden vervolgens vanuit hun correcte werkmappen. De vijf notebookstops zijn concrete historische blokkades op bestaande ontbrekende uitvoerdata.

Voor echte ASR en diarizatie is destijds geen correcte beschikbaarheidspreflight vastgelegd. **Niet uitgevoerd** mag hier niet worden vervangen door **kon niet worden uitgevoerd**. Er was audio en een docentreferentie; historische aanwezigheid van passende weights en token werd niet gecontroleerd. De huidige medium-cache ondersteunt een mogelijke offline ASR-vervolgcontrole, maar zo'n controle is nu uitdrukkelijk niet uitgevoerd.

In de huidige interpreter ontbreken WhisperX en SpeechBrain als geregistreerde packages. In de gecontroleerde huidige HF-cache is alleen Whisper-medium gevonden en de huidige pipeline-tokenlookup vindt geen token. Dat zijn beperkingen van de huidige waarneming; ze worden niet automatisch teruggedateerd.

## 9. Gevolgen voor het oorspronkelijke auditrapport

1. **Intrekken:** de claim dat audio, `test-files` en docentreferentie ontbraken. Deze is weerlegd door oorspronkelijk vastgelegde manifests, niet alleen door de huidige controle.
2. **Nuanceren:** “volledige baseline kon niet worden gestart wegens ontbrekende audio/referentie”. Correct is: geen echte baseline uitgevoerd; model-/tokenbeschikbaarheid destijds onvoldoende vastgesteld.
3. **Behouden als uitvoeringsfeit:** geen WER, CER, DER of echte ML-inference gemeten. Afwezigheid van een meting is geen afwezigheid van alle benodigde input.
4. **Behouden met scope:** aantoonbare unit-/synthetische codebevindingen en notebookstops, voor zover ze steunen op de vastgelegde tests en ongewijzigde code. Ze zeggen niets rechtstreeks over foutenpercentages op de beschikbare MP3's.
5. **Nuanceren:** “alle notebooks onderzocht” betreft 6 actieve notebooks; 2 checkpointkopieën zijn geïnventariseerd maar niet apart uitgevoerd.
6. **Corrigeren:** de oude SpeechBrain-map bevatte 4 checkpointnamen plus YAML, niet 5 checkpointbestanden. Huidige inspectie toont tekstverwijzingen, geen standalone weights.
7. **Niet invullen achteraf:** oorspronkelijke branchnaam, hardware, tokenstatus en externe modelcachebeschikbaarheid zijn niet volledig geregistreerd. Huidige metingen lossen dat historische gebrek niet op.
8. **Voorlopig oordeel beperken:** de conclusie over geschiktheid als onderzoeksbasis kan op statische/synthetische bevindingen rusten, maar de echte ASR-/diarizatiebetrouwbaarheid is niet geëvalueerd. De audit was op dat punt onvolledig; de onjuiste audiobeschikbaarheidsclaim mag geen basis voor vervolgkeuzes zijn.

Het oorspronkelijke auditrapport blijft ongewijzigd voor traceerbaarheid. Dit aanvullende document is de expliciete correctie bij gebruik van dat rapport.

## 10. Manifest en vergelijking tussen omgevingen

`manifest_omgeving_chatgpt.json` bevat:

- `original_manifest_records`: de 102 oorspronkelijk geregistreerde relatieve paden, bytes en SHA-256's, behouden als historische snapshot.
- `files`: huidige relatieve paden, groottes en SHA-256's, met onderscheid tussen oorspronkelijke projectbestanden, audit-artifacts en uitsluitend huidige bestanden.
- `recorded_in_original_manifest` en `same_as_original`: rechtstreeks vergelijkbaar met de oude snapshot.
- `environment`: huidige interpreter/packages, cachebestanden met modelrevisie en SHA-256, tokenaanwezigheidsbooleans en hardware; geen tokenwaarde.
- `current_git`: huidige branch/commit en vastgelegde werkboomstatus.

Git-interne bestanden, bytecode, venv/node_modules, secretconfiguratie en dit rapport/manifest zelf zijn uitgesloten van de huidige filehashlijst. De actuele lijst is daarom niet een dump van de gehele computer. De externe modelcache heeft een afzonderlijke namespace met cache-root/model/revision, en wordt niet met repositoryrelatieve projectpaden verward.

Vergelijk eerst dezelfde relatieve oorspronkelijke projectpaden tussen omgevingen, daarna groottes/hashes. Vergelijk modelweights afzonderlijk per model/revisie. Gebruik packageversies naast hashes en commit: gelijk commitnummer betekent geen gelijke werkboom, modelcache, tokenstatus of interpreter. Audit-artifacts van de ene omgeving zijn geen ontbrekende brondata van de andere.

Deze controle leverde **geen ontbrekende of gewijzigde bestanden uit de oorspronkelijke 102-recordsnapshot** op. Zij levert wel een aantoonbare correctie van het oorspronkelijke verslag over de audiobeschikbaarheid.
