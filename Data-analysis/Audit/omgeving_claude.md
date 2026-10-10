# Omgevingscontrole bij de fase‑1‑audit — Claude (Claude Code, Windows)

**Bronmarkering.** `[DESTIJDS]` = destijds in het gesprek waargenomen en in de tool‑uitvoer vastgelegd. `[NU]` = zojuist gemeten in de huidige omgeving; dit is een reconstructie en bewijst niet dat de toestand tijdens de audit identiek was. Er bestaan van mijn audit geen aparte logbestanden of manifests uit die tijd; alleen de toolresultaten in het gesprek en de resultaatbestanden in `Data-analysis/Audit/` (`edge_results.json`, `wer_results.json`, `synth_results.json`). Er is geen nieuwe modeltest uitgevoerd. De map `Audit_fase1_2026-10-09/` in de repo-root is niet door mij gemaakt; ik heb die niet gelezen en niet gebruikt (onafhankelijkheid). Haar manifest kan dus niet door mij vergeleken worden.

## 1. Repository
| Item | Waarde | Bron |
|---|---|---|
| Locatie | `C:\Users\School\Projects\StudieStap_WorkshopTool` | DESTIJDS + NU (zelfde) |
| Branch / commit | `main` / `33cc8a10eb2aea0a161b387f08ce0192b46e89bc` | DESTIJDS (git status bij start: branch `main`, laatste commit 33cc8a1) + NU bevestigd |
| Remote | `git@github.com:EdgarSabi/StudieStap_WorkshopTool.git` | NU |
| Gewijzigd (tracked) | `ground_truth_final_testfragment.csv`, `ground_truth_template.csv`, `ground_truth_testaudio2_fragment.csv`, `ground_truth_testaudio4_fragment.csv` (alle in `Data-analysis/Experiments/diarization/hyperparameter_tuning/`), `Data-analysis/Notebooks/03-transcription-evaluation.ipynb` | DESTIJDS (startstatus) + NU gelijk |
| Untracked | `ground_truth_testaudio1/5/7_fragment.csv` | DESTIJDS + NU |
| Nieuw sinds de start | `Data-analysis/Audit/` (door mij gemaakt, tijdens de audit), `Audit_fase1_2026-10-09/` (niet door mij; aangemaakt 13:35) | NU |
| `.idea/` | aanwezig maar door `.gitignore` genegeerd (komt niet in `git status` voor); in het manifest staat hij als `untracked` omdat het manifest alleen tracked/niet‑tracked onderscheidt | NU |

De gewijzigde bestanden verschillen volgens `git diff --stat` voor de 4 CSV's over de hele inhoud (251 regels per kant; consistent met regeleinde‑/BOM‑wijziging, niet nader onderzocht); voor notebook 03 1 regel. Hashes van de werkkopieën staan in het manifest.

## 2. Aanwezige bestanden (NU; tracked/untracked‑status uit git; zonder `.git`, `__pycache__`, `.ipynb_checkpoints`, `Audit_fase1_2026-10-09/`)
Totaal 117 bestanden. Zie `manifest_claude.csv` (pad, bytes, SHA‑256, git‑status).
- **Audio:** 13 mp3 in `Data-analysis/src/test-files/` (testaudio1/2/3/4/5, testaudio1/2/4/5/6/7/8_fragment, testdocent). Geen wav/m4a.
- **Python:** 35 `.py` (o.a. `src/` met config, transcription, diarization, preprocessing, docent_recognition, models, run_docent_pipeline, evaluation/wer, tests; Experiments; Afgeronde_experimenten; mijn `Audit/scripts`).
- **Notebooks:** 6 (`01`–`06`); `.ipynb_checkpoints` met kopieën van 02 en 03 (niet in manifest).
- **JSON:** 11, waaronder 5 `results_*` (tuning), classificatie-fixtures, mijn 3 resultaatbestanden. **Geen pipeline‑uitvoer** (`transcript`/`diarized`/`turns`/`docent_roles`‑JSON).
- **CSV:** 7 ground‑truth-bestanden (incl. template en `final_testfragment`).
- **Config:** `src/requirements.txt`, `whisperx/requirements-whisperx.txt`, `.gitignore`, `.idea/*`. Geen `.env`, geen `pyproject`/`environment.yml`, geen notebook‑requirements.
- **Overig:** 6 docx, 3 png, pdf, `Data-local/raw/testaudio1_manual.txt` (388 B, het enige bestand in `Data-local`), 4 `.ckpt`‑stubs + `hyperparams.yaml` in `src/None/speechbrain/` (tracked).

## 3. Ontbrekend ten opzichte van de auditopdracht
[DESTIJDS vastgesteld via `ls`/`find`; NU opnieuw bevestigd voor `Data-local`]
- Scraper/downloader‑code: bestaat niet in de repo.
- `Data-local/processed/**` (alle pipeline‑JSON's, benchmark‑JSON's, WAV‑cache) en `Data-local/raw/` behalve `testaudio1_manual.txt`.
- `testaudio2_manual.txt`, `testaudio5_manual.txt`, `Breinschade_Uitleg_Sara.txt`, `pyannote_teacher_similarity.csv`, `speechbrain_teacher_similarity.csv` (door notebooks gebruikt).
- Ruwe diarizatie‑turns, RTTM‑bestanden, en audio van `final_testfragment` (GT bestaat, geen mp3 met die naam).
- `.env`/HF‑token, `.venv`, pyannote‑ en wespeaker‑modelgewichten.
- NLP/CountVectorizer/tokenizationcode: niet aanwezig (grep leverde niets).

## 4. Modellen
- **Lokaal beschikbaar [DESTIJDS: `pip list` + `ls ~/.cache/huggingface/hub`]:** alleen `Systran/faster-whisper-medium` (snapshot `08e178d4…`, ≈1,5 GB; `config.json`, `model.bin`, `tokenizer.json`, `vocabulary.txt`). Geen pyannote, wespeaker, speechbrain‑ of Whisper‑large/small/base‑cache. [NU] zelfde inhoud.
- **Herkomst/timing [NU]:** de cachemap is aangemaakt 2026‑10‑09 12:45, `model.bin` 12:47 (lokale tijd). Wanneer en door wie hij gedownload is, kan ik niet vaststellen; ik heb niets gedownload. Ik trof hem al aan bij mijn eerste controle.
- **Daadwerkelijk uitgevoerd [DESTIJDS]:** uitsluitend faster‑whisper `medium`, device cpu, compute_type int8, via `TranscriptionEngine` met `TranscriptionConfig(model_size="medium")` (vad_filter aan, beam 5, nl, geen word timestamps). Fragmenten: testaudio2/1/5/7/4_fragment en 6 synthetische wav's (stilte, witte ruis, 2× roze ruis, 8 kHz, 15 s stilte+spraak).
- **Niet uitgevoerd:** pyannote diarizatie, wespeaker‑embedding, speechbrain, WhisperX, large‑v3/small. Alle diarizatie‑/rolcijfers komen uit opgeslagen notebook‑uitvoer.

## 5. Hugging Face‑token
**Nee.** [DESTIJDS: `.env` bestond niet] [NU: `HF_TOKEN` en `HUGGINGFACE_TOKEN` niet gezet in de shell; geen `~/.cache/huggingface/token`, geen `~/.huggingface/token`.] Er is geen waarde uitgelezen of weergegeven. Beperking: omgevingsvariabelen van andere processen/gebruikers of een wachtwoordmanager heb ik niet kunnen inzien.

## 6. Interpreter, versies, hardware
[NU gemeten; de interpreter is dezelfde als in de audit gebruikt — DESTIJDS: `python` = Python311, `pip list` identiek aan nu voor de genoemde pakketten.]
- Python 3.11.5 (MSC v.1936, 64‑bit), `C:\Users\School\AppData\Local\Programs\Python\Python311\python.exe`; geen venv (systeem-/gebruikersinstallatie). Windows 11 Pro Education 10.0.26200.
- Pakketten: faster‑whisper 1.2.1, ctranslate2 4.8.2, pydantic 2.13.5, numpy **2.4.6** (requirements: 2.5.3), python‑dotenv **1.1.1** (requirements: 1.2.3), torch `2.14.0+cpu` volgens `torch.__version__` (`pip list` toont 2.14.0), torchaudio 2.11.0, pyannote.audio 4.0.7, pyannote.metrics 4.1, pyannote.core 6.0.1, jiwer 4.0.0, pandas 2.2.3, scikit‑learn 1.9.0, scipy 1.17.1, matplotlib 3.10.3, nbformat 5.10.4, openai‑whisper 20231117, torchcodec 0.16.0. `pytest` niet geïnstalleerd (tests draaien met `unittest`). Geen speechbrain/whisperx in `pip list`. ffmpeg 2025‑07‑12 (gyan.dev full build) in `C:\Users\School\Downloads\ffmpeg\bin`.
- **Correctie op het eerste rapport:** daar stond dat torch geïnstalleerd is "zonder `+cpu`". `torch.__version__` meldt wel `+cpu`; alleen `pip list` toont de lokale tag niet. De afwijkingen die wél kloppen: numpy en python‑dotenv.
- Hardware: Intel Core i7‑8700K (6 kernen/12 threads), 15,9 GB RAM, NVIDIA GeForce RTX 4060 aanwezig maar torch is CPU‑only en `cuda.is_available()` = False; alle runs op CPU. De hardware is NU gemeten; DESTIJDS vastgelegd is alleen dat device `cpu` was en dat 120 s audio ≈143 s duurde.

## 7. Tests
**Uitgevoerd [DESTIJDS]:**
- `unittest` `Data-analysis/src/tests` (17, OK) en `Experiments/classification/tests` (51, OK). `test_run_docent_pipeline` mockt `subprocess`; geen echte pipeline-stappen (de geprinte "Klaar"-regels kwamen uit de mock).
- ASR-baseline en WER/CER op 5 fragmenten; DER op segmentniveau uit notebook‑HTML-uitvoer (4 fragmenten); overlapvlag‑ en docentrolevaluatie tegen GT; 6 synthetische ASR‑robuustheidstests; 22 randgevalstests (functies uit `diarization.py`, `models.py`, `preprocessing.py`, `to_wav`); JSON‑validatie van mijn eigen ASR‑uitvoer en de 5 `results_*.json`.
**Niet uitvoerbaar:** `diarization.py`/`docent_recognition.py`/`run_docent_pipeline.py` echt (geen token/modellen); `evaluate_min_cluster_size.py` (pyannote + `Data-local/processed/diarization/*.wav`); notebooks opnieuw uitvoeren (ontbrekende data); `evaluation/wer.py` via CLI; scraper; Linux/macOS‑gedrag van `.gitignore`; fragmenten 3/6/8 en `testdocent`; hardware‑/GPU‑tests. De JSON‑fixtures van de classificatie zijn alleen via hun unit tests gecontroleerd.

## 8. Gevolgen voor het eerste auditrapport
1. Alle uitspraken over diarizatie en docentrol berusten op door jou opgeslagen notebook‑uitvoer, die ik niet kon herleiden tot bronbestanden; DER, overlap‑ en rolcijfers (T4, T9, T10) zijn daarmee afgeleide secundaire gegevens op segmentniveau, niet op ruwe pyannote‑turns.
2. Geen enkele pyannote‑ of wespeaker‑uitspraak is door een eigen run bevestigd; code‑inspectie en synthetische functietests tonen de logica, niet het modelgedrag.
3. De WER‑ en robuustheidsuitkomsten gelden voor één model (medium, int8, CPU), één machine en één set van 5 + 6 bestanden; de herhaalbaarheid over machines is niet getest, wel dat mijn run overeenkwam met de eerdere notebookrun.
4. Het bestaan van de ASR-modelcache is niet herleidbaar; zo kan in een andere omgeving een andere modelrevisie gebruikt zijn (revisie `08e178d4…` hier; in jouw eerdere runs onbekend).
5. De correctie over `+cpu` (§6) vervangt de overeenkomstige zin in het eerste rapport (M‑ en §2‑tekst); de overige conclusies veranderen niet.
6. De niet‑gecommitte CSV's en notebook 03 zijn gebruikt zoals ze op schijf stonden (werkkopie, niet `HEAD`); hun hashes staan in het manifest. Uitkomsten kunnen afwijken als de andere omgeving de gecommitte versies gebruikt.
7. Vergelijk tussen beide auditomgevingen op `manifest_claude.csv` (SHA‑256 per bestand); de modelcache en pakketversies zijn niet in het manifest opgenomen.

**Manifest:** `Data-analysis/Audit/manifest_claude.csv` — 117 bestanden, relatieve paden vanaf de repo-root, uitgezonderd `.git`, caches en `Audit_fase1_2026-10-09/`; hashes zijn van de huidige werkkopie (NU). Inclusief mijn eigen auditbestanden (status `untracked`); het rapport zelf en dit manifest zijn niet in een bevroren staat gehasht (`omgeving_claude.md` en `manifest_claude.csv` ontbreken in het manifest).
