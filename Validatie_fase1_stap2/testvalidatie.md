# Testvalidatie — StudieStap fase 1, stap 2

Datum: 9 oktober 2026. Reviewer: Claude (Sonnet 5.5), onafhankelijk. Onderwerp: zijn de **tests** uit de twee fase-1-audits (ChatGPT Work en Claude Code) methodologisch correct, betrouwbaar en reproduceerbaar? De pipeline zelf is niet opnieuw geaudit.

**Leeswijzer bewijstypen**

| Code | Betekenis |
|---|---|
| **HERUITGEVOERD** | Ik heb het originele script of de test zelf opnieuw gedraaid; uitvoer vergeleken met het oorspronkelijke resultaat |
| **HERBEREKEND** | Ik heb de uitkomst met eigen, onafhankelijke code uit opgeslagen invoer berekend |
| **EIGEN TEST** | Nieuwe controletest van mij (scripts `v01`–`v09` in `scripts/`) |
| **STATISCH** | Alleen code-inspectie of lezen van opgeslagen uitvoer |
| **ONTBREEKT** | Essentieel bewijs is niet aanwezig |

---

## 1. Samenvatting

**Beide audits zijn technisch eerlijk en grotendeels reproduceerbaar, maar ze beantwoorden verschillende vragen en bevatten elk een zwakte die hun conclusies beperkt.**

1. **Reproduceerbaarheid is goed.** Alle 102 hashes van het ChatGPT-manifest en alle 117 van het Claude-manifest kloppen met de huidige bestanden. Alle 33 regels in `SHA256SUMS.txt` van het zip kloppen. Het ChatGPT-script `run_audit.py` (32 tests) en het Claude-script `edge_tests.py` (22 tests) geven bij herhaling **identieke** uitkomsten. De bewaarde WER-, DER-, overlap- en docentrolcijfers heb ik met eigen code herberekend en ze komen overeen.
2. **De belangrijkste inhoudelijke bevinding van Claude houdt stand.** De WER-referentie is niet onafhankelijk van Whisper. Voor `testaudio4` zijn alle 87 GT-rijen tekstueel én qua tijdgrenzen identiek aan Whisper-segmenten. Voor `testaudio1` ligt de CSV-tekst op 1,7% WER van Whisper en op 19,7% van de aparte handmatige transcriptie (eigen test V06). **WER 0,000 mag niet als transcriptienauwkeurigheid worden gepresenteerd.** Dit geldt niet uniform: in de rumoerige staart van `testaudio5` is de GT aantoonbaar handmatig herwerkt, en de README zegt dat de voorinvulling "daarna handmatig gecontroleerd en aangepast" is. Dat tweede deel liet Claude weg.
3. **ChatGPT heeft een feitelijke fout in de dekking.** Het rapport zegt dat audio en referenties ontbraken, en leidt daaruit af dat WER/CER/DER niet gemeten konden worden. Het eigen `manifest.json` bevat 13 mp3's onder `Data-analysis/src/test-files` (V08). ChatGPT heeft de GT-CSV's niet als Whisper-afgeleid herkend; dit is de grootste methodologische misser. Wel zijn zijn 32 technische proeven zorgvuldig, eerlijk gelabeld en volledig reproduceerbaar.
4. **Beide audits noemen "weerlegde verwachtingen" soms bug-bewijs, terwijl de verwachting afwijkt van de gedocumenteerde ontwerpkeuze.** Voorbeelden: `overlap` (gedocumenteerd als "andere spreker beslaat een betekenisvol deel", niet "gelijktijdig"), `MAIN_SPEAKER` (gedocumenteerd als "spreekt het meest"), de tuningscore (gedocumenteerd als "bewust simpel, overlap mild"). De waarnemingen kloppen; de formulering "fout" of "weerlegd" is vaak te sterk. Het zijn ontwerpbeperkingen of naamgevingsrisico's.
5. **Testharnasdefecten.** Bij ChatGPT hebben T05, T20, T23 en T24 een hard-gecodeerde `False`, zodat de test nooit "geslaagd" kan opleveren. Bij Claude hebben E7b, E14 en E15 (4 deelgevallen) een hard-gecodeerde waarde of een verwachting die elke uitkomst dekt, waardoor "10 van 22 geslaagd" slechts 5 echte, falsifieerbare geslaagde toetsen bevat. De onderliggende feiten blijven wel kloppen.
6. **Wat de audits niet bewijzen.** Geen enkele test in beide audits meet de nauwkeurigheid van Whisper of pyannote op onafhankelijk geannoteerde echte audio. De DER's zijn segmentgebaseerd, zonder ruwe diarizatie, op een referentie die op hetzelfde ASR-raster staat. Docentherkenning is in-sample (één docent, één referentieclip, drempel op dezelfde data gekozen).

**Telling van de oordelen (zie §3):**

| Groep | GELDIG | GEDEELTELIJK | ONGELDIG | NIET TE VERIFIËREN |
|---|---:|---:|---:|---:|
| ChatGPT T01–T32 (32 proeven) | 21 | 11 | 0 | 0 |
| Claude T1–T12 (11 rijen; T5 verwijst naar de E-tests) | 2 | 7 | 0 | 2 |
| Claude E1–E18 (19 rijen: E7b erbij, E15 als één groep) | 10 | 7 | 2 | 0 |
| Notebook-controles (4 rijen) | 4 | 0 | 0 | 0 |

Claude's centrale conclusie F1 (circulaire referentie) is apart beoordeeld: GELDIG voor audio2/4, GEDEELTELIJK voor audio1/5/7.

---

## 2. Gecontroleerde bewijsbestanden

### 2.1 Paden (conform opdracht eerst gecontroleerd)

| Pad | Bestaat? | Opmerking |
|---|---|---|
| `Audit_fase1_2026-10-09/` | Ja | ChatGPT-audit, 16 bestanden (+ matplotlib-cache) |
| `Data-analysis/Audit/` | Ja | Claude-audit, 14 bestanden |
| `Audit_bewijs/bewijspakket_claude.zip` | **Nee** | Map `Audit_bewijs/` bestaat niet. Het zip staat op `Data-analysis/Audit/bewijspakket_claude.zip`. Ik heb dat gebruikt en geen andere locatie verzonnen |

Uitgepakt (kopie, alleen lezen) in `Validatie_fase1_stap2/zip_extract/`.

### 2.2 Bronversie en hashes

* Repository: `main`, commit `33cc8a10eb2aea0a161b387f08ce0192b46e89bc`. Werkboom bevat dezelfde vijf gewijzigde bestanden als bij de start (4 CSV's en `03-transcription-evaluation.ipynb`). Na al mijn runs is `git status` voor tracked bestanden ongewijzigd.
* De 4 gewijzigde CSV's verschillen van HEAD in **schema, niet in meetinhoud** (zelf gecontroleerd met een CSV-parser op `git show HEAD:…` tegen de werkkopie): de gecommitte kolom heet **`transcript_hint`**; in de werkkopie is die hernoemd naar `transcript` en zijn de kolommen `speaker_role` en `intelligible` toegevoegd, plus CRLF-regeleinden. Voor `testaudio2` (19 rijen) en `testaudio4` (87 rijen) zijn tekst, tijden, `speaker_id` en `overlap` rij voor rij **identiek** aan HEAD. De Claude-metingen hangen dus niet af van niet-gecommitte inhoud. (Een eerdere gedachte van mij dat het alleen om regeleinden ging, was onjuist en is hierdoor gecorrigeerd.) De gecommitte kolomnaam `transcript_hint` is zelf bewijs voor de voorinvulling (zie §8, rij 1).
* `03-transcription-evaluation.ipynb` verschilt van HEAD in **één regel**: `language_info.version` 3.12.6 → 3.11.5. Het notebook is dus opnieuw opgeslagen in de Python 3.11.5-omgeving. Claude's opmerking "andere omgeving dan 02/04–06" is hiermee correct maar herleidbaar tot dit opslaan, niet tot een afwijkende pipeline.

| Controle (V01, **HERUITGEVOERD**) | Resultaat |
|---|---|
| ChatGPT `manifest.json` (102 records) tegen huidige bestanden | 102 gelijk, 0 ontbrekend, 0 verschil |
| Claude `manifest_claude.csv` (117) tegen huidige bestanden | 117 gelijk |
| Zip `SHA256SUMS.txt` (33) tegen uitgepakte bestanden | 33 gelijk, geen opmaakfouten |
| Zip-scripts/resultaten/GT-CSV's tegen kopieën in repo | allemaal identiek |
| `hashes_referenties.md` (12 invoerbestanden) tegen repo | allemaal gelijk |

**Kanttekening bewijswaarde.** Het ChatGPT-manifest is tijdens de audit gemaakt (13:30) en na afronding vergeleken (13:35); dat is sterk bewijs dat de bronnen niet veranderden. De Claude-hashes zijn **achteraf** berekend op de werkkopie ("NU"), zodat ze alleen bewijzen dat de bestanden nu overeenkomen met de bewaarde kopieën, niet dat ze tijdens de audit identiek waren. Claude zegt dit zelf ook (`hashes_referenties.md`, `omgeving_claude.md`).

### 2.3 Onderscheid oorspronkelijk / later teruggevonden / nieuw

| Categorie | Bestanden |
|---|---|
| **Oorspronkelijk, tijdens audit gemaakt (ChatGPT)** | `run_audit.py`, `test_results.json`, `testbijlage.md`, `inventory.json`, `manifest.json`, `baseline_*.txt`, `integriteitscontrole.json`, `auditrapport.md` |
| **Oorspronkelijk (Claude)** | `auditrapport_fase1.md`, `edge_results.json`, `wer_results.json`, `synth_results.json`, `scripts/*` |
| **Later teruggevonden / samengesteld (Claude)** | `bewijspakket_claude.zip`: `asr/*.json`, `nb_hyp.json`, `asr_log.txt` (originelen, mtime 13:28–13:36); `commando_overzicht_RECONSTRUCTIE.md`, `hashes_referenties.md`, `instellingen.md`, `SHA256SUMS.txt` (reconstructies, door Claude zelf zo gemarkeerd). Ook `omgeving_claude.md` en `manifest_claude.csv` (achteraf) |
| **Later toegevoegd (ChatGPT)** | `omgeving_chatgpt.md`, `manifest_omgeving_chatgpt.json` (16:12, in de repo-root) |
| **Nieuw (mijn validatie)** | Alleen in `Validatie_fase1_stap2/`: `scripts/v01`–`v10`, `resultaten/*.json`, `herhaling_chatgpt/`, `herhaling_claude/`, `zip_extract/` |

**Onafhankelijkheid, transparantie.**
* Ik heb geen validatierapport van de andere reviewer gebruikt. Tijdens mijn werk verscheen een nieuwe, niet door mij gemaakte map `Validatie_fase1_stap2_2026-10-09/`. Ik heb die **niet geopend** (door een `ls` zijn drie bestandsnamen zichtbaar geworden: `before_hashes.json`, `cache_config`, `chatgpt_herhaling`; inhoud niet gelezen).
* `omgeving_chatgpt.md` is een omgevingscontrole van ChatGPT achteraf, geen testvalidatie. Ik heb er de eerste ~80 regels van gelezen voordat ik de aard ervan doorhad. Geen enkele conclusie in dit rapport steunt erop; het feit dat de audio aanwezig was heb ik onafhankelijk uit `manifest.json` gehaald (V08).
* Beide audits liepen **gelijktijdig** op dezelfde werkboom (resultaatbestanden 13:28–13:36). Beide beweren niets te hebben gewijzigd en de hashvergelijkingen bevestigen dat voor tracked bestanden.

### 2.4 Mijn omgeving

Python 3.11.5 (`C:\Users\School\AppData\Local\Programs\Python\Python311\python.exe`), Windows 11. Libraries: numpy 2.4.6, scipy 1.17.1, pydantic 2.13.5, pyannote.metrics 4.1, pyannote.core 6.0.1, jiwer 4.0.0 (alleen in de heruitgevoerde Claude-scripts), faster-whisper 1.2.1, nbformat 5.10.4, torch 2.14.0 (`torch.__version__` = `2.14.0+cpu`). Dit is dezelfde interpreter en dezelfde versies als in beide audits (ChatGPT `inventory.json`, Claude `omgeving_claude.md`).

### 2.5 Wat ik niet gedaan heb (conform §11)

Geen model geladen of gedownload, geen Whisper/pyannote-run, geen audio of data geüpload, niets in de pipeline of audittests gewijzigd. De bestaande unit-suites heb ik wel opnieuw gedraaid (17 + 51 OK; ze mocken subprocess en schrijven niets: `Data-local/` bleef ongewijzigd). **Consequentie:** ik kon niet zelf toetsen of Whisper op deze audio deterministisch is, en niet of de diarizatie-uitvoer uit de notebooks bij de huidige code hoort. Dat staat onder "niet-verifieerbaar".

---

## 3. Testmatrix

Afkortingen: CG = ChatGPT-audit, CL = Claude-audit.

### 3.1 ChatGPT: 32 technische proeven (`run_audit.py`, `test_results.json`)

**Herhaling:** het originele script, ongewijzigd behalve het rootpad (`ROOT = OUT.parent.parent`, anders kon het niet vanuit mijn map draaien), gaf voor alle 32 tests dezelfde `geslaagd`-waarde en dezelfde uitkomst (9 geslaagd / 23 niet; alleen T15 verschilt, uitsluitend door het uitvoerpad). Notebook-resultaten identiek (V07 en kopie). Alle rijen hieronder zijn dus minimaal **HERUITGEVOERD (via het script)**; bij "Type bewijs" noem ik daarnaast mijn eigen aanvullende controle.

| Audit | Test-ID | Onderzoeksvraag | Type bewijs | Oordeel | Onderbouwing | Beperking |
|---|---|---|---|---|---|---|
| CG | T01 | Wordt opeenvolgende ≠ simultane spraak onderscheiden? | HERUITGEVOERD + EIGEN (V05-2) | GEDEELTELIJK | Waarneming klopt: A 0–7/B 7–10 en A 0–10/B 7–10 geven identieke vlaggen (`overlap=True`, `uncertain=False`) | De verwachting `overlap=False` strookt niet met `models.py:41` ("another speaker also covers a meaningful part of the segment") en `config.py:92`. Dit is een **naamgevings-/semantisch risico**, geen softwarefout. CG zegt dat zelf in R02 |
| CG | T02 | Ontbrekende diarizatie → onzeker? | HERUITGEVOERD | GELDIG | Positieve controle; verwachting volgt uit de code-intentie | Triviaal |
| CG | T03 | Volledige gelijktijdigheid → overlap + onzeker? | HERUITGEVOERD | GELDIG | A en B 0–10: winner = runner → margin 0 < 0,15 → onzeker | Eén geval; garandeert geen detectie van korte overlap (CG zegt dat) |
| CG | T04 | Blijft een korte tweede spreker onzichtbaar? | HERUITGEVOERD + EIGEN (V05-1) | GELDIG | Mijn sweep (B = 0,5…5 s van 10 s) met verwachting **uit de documentatie** (0,15 / 0,60 / 0,15): 8/8 gelijk aan implementatie. B is onzichtbaar tot 1,4 s en verschijnt vanaf 1,5 s als `overlap`. CG noemt dit terecht "ontwerpbeperking, geen modelfout" | Synthetisch; zegt niets over of pyannote zulke sprekers vindt |
| CG | T05 | Worden negatieve tijden/confidence=3 geweigerd? | HERUITGEVOERD | GELDIG (feit) | `models.py` bevat geen validators; gedrag klopt | **Harnasdefect:** `bad_model` geeft hard-gecodeerd `False`; een correcte `ValidationError` zou als "geblokkeerd" worden geboekt. Ernst "hoog" (F03) niet onderbouwd: in de 5 echte ASR-uitvoeren komt dit 0× voor (V05-7) |
| CG | T06 | Verplicht `text`-veld? | HERUITGEVOERD | GELDIG | Positieve controle | — |
| CG | T07 | Onzekere segmenten apart, bronnen behouden? | HERUITGEVOERD | GELDIG | Merge-aantallen [2,1,1] en 4 bronsegmenten kloppen | Synthetisch |
| CG | T08 | Preprocessing bestand tegen ongeordende invoer? | HERUITGEVOERD + EIGEN (V05-7) | GEDEELTELIJK | Turn 5→1 s reproduceerbaar | Op de 174 echte segmenten (5 bestanden) komt geen `end≤start` of niet-monotone volgorde voor. Robuustheidsgebrek aangetoond, geen aangetoond probleem in de praktijk |
| CG | T09 | Lange stilte → context onzeker? | HERUITGEVOERD | GELDIG | Positieve controle | — |
| CG | T10 | NaN-similarity → ONZEKER? | HERUITGEVOERD | GEDEELTELIJK | Echte `assign_docent_roles` met nep-herkenner; NaN → OTHER klopt | De echte `_embed` geeft bij falen `None` (→ ONZEKER). NaN uit het echte model is niet aangetoond. Fake omzeilt `_embed` |
| CG | T11 | Nulvector-cosine → ONZEKER? | HERUITGEVOERD + STATISCH | GEDEELTELIJK | `_cosine_similarity` geeft bewust 0.0 bij norm 0 (`if denom == 0`); daarna OTHER | Voorkomen van een nulembedding niet aangetoond |
| CG | T12 | Wordt werkelijke cliplengte gecontroleerd? | HERUITGEVOERD + STATISCH | GEDEELTELIJK | Min-duurcontrole gebruikt `turn.end − turn.start` (code gelezen); 4000 samples gaan naar herkenner | Scenario vereist audio korter dan tijdlijn. Wel realistisch grensgeval: `testaudio1` ASR-einde 0,58 s voorbij audio (V05-7), maar dat haalt de clip niet onder 1 s |
| CG | T13 | Docentrol onafhankelijk van MAIN_SPEAKER? | HERUITGEVOERD | GELDIG | Positieve controle | — |
| CG | T14 | Meerdere leerlingidentiteiten apart? | HERUITGEVOERD | GELDIG | 3 labels, juiste volgorde op spreektijd | — |
| CG | T15 | Verschillende bronnen → verschillend cachepad? | HERUITGEVOERD + EIGEN (V05-4b) | GELDIG | `output_path_for` gebruikt alleen `stem` | Of dit in uw werkwijze (unieke bestandsnamen) schade geeft, is niet getoetst |
| CG | T16 | Komen batchinginstellingen overeen met opgeslagen config? | HERUITGEVOERD + STATISCH | GELDIG | `BatchedInferencePipeline.transcribe` accepteert `beam_size`, `vad_filter`, `word_timestamps` (signatuur gecontroleerd), maar de wrapper stuurt ze niet door terwijl de config ze opslaat | Alleen opt-in-pad (`use_batching=True`); standaardroute onaangetast. Nep-model |
| CG | T17 | Herhalende tekst gemarkeerd? | HERUITGEVOERD | GELDIG | Positieve controle | — |
| CG | T18 | 24-bit WAV via conversie verwerkt? | HERUITGEVOERD + STATISCH | GEDEELTELIJK | `to_wav` laat `.wav` ongewijzigd, loader weigert 24-bit | De docstring belooft conversie van "non-wav inputs". De fout is **luid en duidelijk**, geen stille corruptie. Verwachting "conversie of verwerking" is strenger dan het contract. Alle echte testbestanden zijn mp3 |
| CG | T19 | 48 kHz stereo correct doorgegeven? | HERUITGEVOERD | GELDIG | Positieve controle | Resampling door pyannote niet getest (CG zegt dat) |
| CG | T20 | Afgekapt WAV gedetecteerd? | HERUITGEVOERD + EIGEN (V05-6) | GELDIG | Zelf bevestigd: 100 bytes, header 16000 frames, 28 samples geladen zonder fout | Harnas hard-codeert `False`. Realisme (onderbroken conversie) niet getoetst |
| CG | T21 | Bestraft de tuningscore false alarms? | HERUITGEVOERD + STATISCH | GELDIG (als bewijs dat het geen DER is) | Docstring van `evaluate_min_cluster_size.py`: "bewust simpel… overlap mild… frames binnen gelabelde beurten". Score 100% is dus **ontwerpgedrag** | Het label "verwachting weerlegd" suggereert een fout. De conclusie R03 ("niet als DER interpreteren") is wel correct en voorzichtig |
| CG | T22 | Lege referentie veilig gescoord? | HERUITGEVOERD | GEDEELTELIJK | `ZeroDivisionError` klopt | Geen echt bestand dat gescoord is, is leeg; ernst "middel" (F10) overdreven. De 137-rijen-sjabloon (`final_testfragment`) is bevestigd leeg (V05-8) |
| CG | T23 | Dwingt `status=OK` een bruikbaar resultaat af? | HERUITGEVOERD | GEDEELTELIJK | Model accepteert `OK` met `detected=None` | Eis komt uit een beschrijving die ik niet heb teruggevonden bij de klasse (alleen `status`-validator). Mock-classifier; harnas hard-codeert `False` |
| CG | T24 | Niet-eindige tijdstempels geweigerd? | HERUITGEVOERD + EIGEN (V05-5) | GELDIG | NaN → JSON `null`; terugleggen faalt met `ValidationError` | Dus luide, geen stille fout bij herladen. CG's formulering ("niet meer… teruggelezen") is correct |
| CG | T25 | Blijft onbekend extra veld behouden? | HERUITGEVOERD | GELDIG | Pydantic-default `extra=ignore`, bevestigd | Verwachting is reviewerskeuze; CG noemt het terecht "toegestaan gedrag" |
| CG | T26 | Blijven ontbrekende kwaliteitsvelden "onbekend"? | HERUITGEVOERD | GEDEELTELIJK | Defaults zijn `False` | `models.py` zegt expliciet dat Phase 2+-velden defaults hebben zodat oude JSON laadt: bewuste compatibiliteit. Risico terecht, "falen" niet |
| CG | T27 | GEEN/ONBEKEND apart van sprekers in scoring? | HERUITGEVOERD + EIGEN (V05-8) | GEDEELTELIJK | `load_ground_truth` neemt elke niet-lege `speaker_id` mee: `GEEN` (audio1) en `ONBEKEND` (audio5) worden sprekers | **Geen bestaand tuningresultaat getroffen:** `results_*.json` zijn voor `testaudio2` en `testaudio4`, en die bevatten alleen SPREKER_A–D. F11 "hoog" is latent |
| CG | T28 | Corrupte cache afgewezen? | HERUITGEVOERD | GELDIG | `cached_result_exists` = `exists()` | Triviaal gedrag. De bewering "modelconfig speelt geen rol" is hier niet getest, maar wel door mij (V05-4) |
| CG | T29 | Ongelabelde regels van handmatige referentie behouden? | HERUITGEVOERD + HERBEREKEND | GELDIG | 9 niet-lege regels, 5 geladen, 4 weggelaten; bestand zelf gelezen: de weggelaten regels zijn echte gesproken tekst (bv. "Zit er ook nog in je karaktereigenschap…") | Treft alleen de tekstweergave in notebook 03; er wordt daar geen WER uit berekend |
| CG | T30 | `compute_agreement` vrij van MAIN=docent? | HERUITGEVOERD + EIGEN | GELDIG | Zelf gedraaid: `('conflict_diar_main_sim_low', True)` bij correct herkende leerling | Experimentele helper, niet productiecode (productie neemt MAIN≠docent niet aan) |
| CG | T31 | Volgt refinement de gedocumenteerde overlapratio? | HERUITGEVOERD + STATISCH | GELDIG | Commentaar (r. 98) zegt "fraction of the shorter"; code deelt door nieuwe segmentduur (r. 135) en `shorter` wordt alleen op ≤0 getoetst. Resultaat `None` bevestigd | Experimenteel, laag gewicht (CG: "laag") |
| CG | T32 | Blokkeren slechte ASR-signalen een stellige docentrol? | HERUITGEVOERD | GEDEELTELIJK | Gedrag klopt; de beslisregels in `docent_recognition.py` noemen ASR-flags niet | Eis is een ontwerpkeuze van de reviewer, geen specificatie; CG zegt "methodologisch risico, geen bewezen fout" |

**Niet-testmatige claims van CG (STATISCH):** dependency-tabel. De regel "torch gepind 2.14.0+cpu, aangetroffen 2.14.0" is een **artefact van `pip`-metadata**: `torch.__version__` is `2.14.0+cpu` (zelf gecontroleerd). Claude had dezelfde misvatting en corrigeerde die in `omgeving_claude.md` §6. Numpy- en python-dotenv-afwijkingen kloppen wel.

### 3.2 Claude: kerntests T1–T12 (`auditrapport_fase1.md` §5)

| Audit | Test-ID | Onderzoeksvraag | Type bewijs | Oordeel | Onderbouwing | Beperking |
|---|---|---|---|---|---|---|
| CL | T1 | Slagen de 68 bestaande unit-tests? | HERUITGEVOERD | GELDIG | 17 + 51 OK; ChatGPT's `baseline_*.txt` idem | Mocken subprocess/ML; testen geen kwaliteit (beide audits zeggen dat) |
| CL | T2 | Is de ASR-baseline (medium) reproduceerbaar? | HERBEREKEND (V08, V09) | GEDEELTELIJK | Zip bevat 5 ASR-JSON's, `asr_log.txt` en instellingen. Vs. opgeslagen notebookrun: `testaudio1` 5/5 tijden gelijk, `testaudio2` 19/19 tijden en 18 van 19 teksten gelijk (1 afgekapt in HTML). **`testaudio5` wijkt af vanaf ± 28 s** (andere segmentatie, "Kere!" vs "Kerel!") | Claude's claim "zelfde segmenten" is alleen voor `testaudio2` aangetoond. Verse Whisper-run door mij niet gedaan (§2.5). Originele commando's zijn een reconstructie; modelrevisie is achteraf uit de cache gelezen |
| CL | T3 | WER/CER van de verse run t.o.v. GT-`transcript` | HERBEREKEND (V02) | GEDEELTELIJK | **Rekenwerk is correct:** mijn eigen Levenshtein (geen jiwer) geeft exact 0,032 / 0,000 / 0,000 / 0,123 / 0,031 en CER 0,035 / 0 / 0 / 0,100 / 0,022 | Twee kleine biassen in de testopzet: (a) rijen met `GEEN` gaan uit de referentie maar het Whisper-woord "APPLAUS" blijft in de hypothese (audio1: WER 0,032 → 0,016 als symmetrisch); (b) een rij met noot "niet meenemen" zit wel in de referentie (audio5: 0,123 → 0,094). Kolom `intelligible` (overal `nee` bij audio2/7) niet toegelicht |
| CL | T3→F1 | Is de referentie onafhankelijk van Whisper? (conclusie uit T3) | HERBEREKEND (V02, V06, V09) | GELDIG voor audio2/4; GEDEELTELIJK voor audio1/5/7 | Zie §8. Sterkste bewijs: audio4 87/87 rijen identiek aan ASR; audio1 laatste GT-eind 30,6 s > audio-duur 29,98 s | README noemt ook "daarna handmatig gecontroleerd en aangepast" (weggelaten in het rapport). Audio5-staart is aantoonbaar herwerkt |
| CL | T4 | DER (pyannote.metrics) op segmentuitvoer | HERUITGEVOERD (`der.py`) + HERBEREKEND (V03) | GEDEELTELIJK | Rekenlogica correct: eigen 10 ms-frame-DER geeft 0,233 / 0,424 / 0,177 met identieke componenten. `testaudio1` 0,344 vs 0,354: verschil volledig verklaard door 0,4 s dat spreker B in de GT met zichzelf overlapt (rij 11,8–15,6 en 15,2–20,3) | (1) Hypothese = notebook-HTML van een oudere run, codeversie onbekend, geen ruwe turns. (2) GT staat op hetzelfde ASR-raster: bij audio2/7 is missed/FA nul **per constructie**. (3) Literal label `"None"` (audio7, 1 s) telt als eigen spreker: DER 0,177 → 0,194 als weggelaten. (4) "Ondergrens" is niet onderbouwd. (5) `testaudio1` UEM 4,1–24,5 handmatig gekozen. (6) Reproduceerbaar alleen via bewaarde `nb_hyp.json` |
| CL | T5 | 22 randgevalproeven (E1–E18) | HERUITGEVOERD (22/22 identiek) | zie §3.3 | Per proef beoordeeld | De telling "10 geslaagd" is misleidend (§3.3) |
| CL | T6 | 30 s stilte en witte ruis | STATISCH (opgeslagen `synth_results.json`) | NIET TE VERIFIËREN | Uitkomst (0 segmenten) is opgeslagen | De audiobestanden en het genereerscript staan **niet** in het pakket (`run_synth.py` leest alleen `synth/*.wav`). Gegenereerde WAV's kon ik niet reproduceren. Alleen deze 2 signalen |
| CL | T7 | Roze ruis ≈ +8 / −5 dB SNR | STATISCH | NIET TE VERIFIËREN | Resultaten opgeslagen | SNR "grove schatting", generator ontbreekt, 1 realisatie per conditie. Rapport zegt "referentie = schone Whisper-run", maar `run_synth.py` gebruikt de **GT-CSV van testaudio2** (circulair, V02). Onderbouwing van "F5" (venstergemiddelden) staat los en is wel geldig |
| CL | T8 | 8 kHz versie | STATISCH | GEDEELTELIJK | Resultaat opgeslagen (18 segmenten) | Resamplemethode onbekend, 1 bestand, referentie als T7 |
| CL | T9 | Overlapvlag vs GT-overlap | HERBEREKEND (V04) | GEDEELTELIJK | Alle tellingen kloppen exact: audio2 TP1/FP4/FN1; audio5 TP1/FP2/FN3; audio7 TP4/FP10/FN1 (16 van 22 gevlagd = vals alarm). Er is **geen script** in het pakket; mijn herberekening is dus geen reproductie | De GT-vlag betekent "twee mensen tegelijk", de code-vlag "tweede spreker ≥ 15% van het segment". Beide GT's hebben **nul** overlappende tijdintervallen bij audio2/5/7. Een "vals alarm" kan een echte sprekerwissel zijn die de GT (zelfde raster als ASR) niet kan representeren |
| CL | T10 | Docentrol vs GT-rol, testaudio7 | HERBEREKEND (V04) | GEDEELTELIJK | Seconden kloppen: docent: 31 DOCENT / 6 OTHER / 6 ONZEKER; leerling: 6 OTHER / 2 DOCENT / 5 ONZEKER. 43 van 45 docentseconden zitten in MAIN_SPEAKER | Geen script in het pakket. In-sample (drempel op testaudio6/7), 1 fragment, 1 docent. "84% recall" negeert 6 s ONZEKER (met ONZEKER 72%). Uitvoer is oude notebookuitvoer |
| CL | T11 | JSON-validatie van de eigen ASR-JSON's | HERBEREKEND (V05-7) | GEDEELTELIJK | Hele-seconde-grenzen (audio2 19/19, audio7 38/38) en einde voorbij audio (audio1 +0,58 s) kloppen | Rapport zegt "audio_file absoluut (4×)", maar het zijn **5 van 5**. Geen opgeslagen uitvoer van `validate_json.py` |
| CL | T12 | Zijn `results_*.json` geldige JSON? | STATISCH | GELDIG | ChatGPT's `inventory.json` bevestigt 8/8 | Triviaal |

### 3.3 Claude: randgevallen E1–E18 (`edge_tests.py`)

Alle 22 uitkomsten zijn bij herhaling identiek (inclusief E17 met ffmpeg). Oordelen over de **testopzet**, niet over of de waarneming klopt (die klopt overal).

| Audit | Test-ID | Onderzoeksvraag | Type bewijs | Oordeel | Onderbouwing | Beperking |
|---|---|---|---|---|---|---|
| CL | E1 | Docent 10 s vs leerling 30 s → wie is MAIN? | HERUITGEVOERD | GEDEELTELIJK | Uitkomst klopt (leerling = MAIN) | `build_label_map` documenteert: "whoever talks the most becomes MAIN… NOT speaker identification". "FAIL" is dus verwacht ontwerpgedrag. Als **risico** (M1) is het geldig |
| CL | E2 | Gelijke spreektijd, andere volgorde | HERUITGEVOERD | GELDIG | Toewijzing hangt van invoervolgorde (zelf bevestigd) | Klein effect (alleen bij exacte gelijkheid) |
| CL | E3 | Default `main_speaker_min_share` | HERUITGEVOERD | GEDEELTELIJK | Bij default 0,0 kan `main_speaker_uncertain` niet `True` worden: klopt | Verwachting arbitrair; de default schakelt de functie uit |
| CL | E4 | Wissel binnen segment: overlap? | HERUITGEVOERD | GEDEELTELIJK | Zelfde bevinding als CG T01 | Zelfde beperking: verwachting wijkt af van de gedocumenteerde definitie |
| CL | E5 | Echte overlap gevlagd? | HERUITGEVOERD | GELDIG | Positieve controle | Kan E4 niet van E5 onderscheiden: juist het punt van het rapport |
| CL | E6 | Segment zonder diarizatie-spraak | HERUITGEVOERD | GELDIG | Positieve controle | — |
| CL | E7 | 20% dekking → onzeker | HERUITGEVOERD | GELDIG | Klopt | `confidence=1,0` bij 20% dekking is het punt van F4 |
| CL | E7b | 60/40: wat betekent confidence? | HERUITGEVOERD | ONGELDIG (als toets) | `passed` is hard-gecodeerd `True`; geen falsifieerbare verwachting | Conclusie F4 ("share, geen kans") staat los hiervan al in `models.py` ("winning speaker's share") |
| CL | E8 | `end < start` | HERUITGEVOERD | GELDIG | Geaccepteerd, klopt (CG T05 idem) | Zie CG T05 |
| CL | E9 | Typfout-veld / onbekend veld | HERUITGEVOERD | GELDIG | Stil genegeerd, klopt (CG T25) | — |
| CL | E10 | Segment zonder `text` | HERUITGEVOERD | GELDIG | Positieve controle | — |
| CL | E11 | Willekeurig speaker-label | HERUITGEVOERD | GEDEELTELIJK | `speaker: Optional[str]` is vrije tekst | Verwachting "vocabulaire" is een wens |
| CL | E12 | Overlappend zelfde-spreker segment | HERUITGEVOERD | GELDIG | 2 turns, klopt | — |
| CL | E13 | Zelfde label, andere `speaker_raw` | HERUITGEVOERD | ONGELDIG | Scenario onmogelijk: label-map is injectief. Claude zegt dit zelf | Telt toch mee als "mislukt" in de 10/22 |
| CL | E14 | Min-duurcheck op span i.p.v. spraaktijd | HERUITGEVOERD + STATISCH | GEDEELTELIJK | Code (`duration = turn.end − turn.start`) bevestigt de waarneming | `passed` hard-gecodeerd `False`; nooit een echte toets |
| CL | E15 (×4) | WAV-loader met 8 kHz-stereo, 44,1 kHz, 24-bit, 8-bit | HERUITGEVOERD | GEDEELTELIJK | Uitvoer informatief en consistent met CG T18/T19 | `ok=True` voor elke uitkomst; verwachting "geladen of duidelijke fout" kan niet falen. Vier deelgevallen met dezelfde methode, daarom gegroepeerd |
| CL | E16 | 8 kHz-stereo WAV niet geconverteerd | HERUITGEVOERD + STATISCH | GEDEELTELIJK | Klopt (CG T18) | Docstring zegt "non-wav inputs"; de pipeline-invoer is mp3 |
| CL | E17 | Zelfde bestandsnaam in 2 mappen → WAV-cache | HERUITGEVOERD | GELDIG | Tweede bestand (2 s) krijgt WAV van 1 s; code (`{stem}_16k_mono.wav`, `exists and not force`) bevestigt het mechanisme | Geldt alleen voor zelfde `stem`; synthetische sinussen |
| CL | E18 | `output_path_for` voor `raw/x.mp3` vs `test/x.mp3` | HERUITGEVOERD + EIGEN (V05-4b) | GELDIG | Zelfde pad, bevestigd | Zie CG T15 |

**Eerlijke telling Claude E-tests.** Geslaagd gemeld: 10. Daarvan zijn E7b en de vier E15-gevallen niet-falsifieerbaar. Echte, falsifieerbare geslaagde toetsen: **5** (E5, E6, E7, E10, E12). Echte mislukkingen met een verwachting die uit een specificatie of documentatie volgt: E2, E3, E8, E9, E17, E18 (en E4, E16 met kanttekening). E1, E11, E13, E14 zijn reviewersmeningen of onrealistisch.

### 3.4 Notebook-controles (onderdeel G)

| Audit | Test-ID | Onderzoeksvraag | Type bewijs | Oordeel | Onderbouwing | Beperking |
|---|---|---|---|---|---|---|
| CG | NB-uitvoering (§7) | Draaien codecellen in een lege namespace? | HERUITGEVOERD (V07 + CG-script) | GELDIG | Identiek: 01 faalt in cel 5, 02 cel 6, 03 cel 12, 04 cel 7, 05 cel 3 (FileNotFound/IndexError door ontbrekende `Data-local`), 06 alle 10 cellen OK. Statisch: geen enkele cel schrijft bestanden of gebruikt magics, dus veilig | Geen Jupyter-kernel/nbclient-run; cellen in bestandsvolgorde. CG zegt dit |
| CL | NB-uitvoeringsvolgorde | Out-of-order uitvoering? | STATISCH + HERBEREKEND | GELDIG | Opgeslagen `execution_count`: nb04 [2,3,4,29,22,…], nb05 [1,3,4,6,5,9,10] niet monotoon (nb06 ook: [6,9,7,10,…]; Claude noemt 06 niet) | De cellen die Claude voor DER gebruikte (nb03 cel 14/21/28, nb05 cel 2/6/14) staan wel in oplopende volgorde |
| CL | NB-leesbaarheid / data | Zijn conclusies uit notebooks reproduceerbaar? | HERUITGEVOERD (V07) | GELDIG | Alle verwijzingen naar `Data-local/processed/**` ontbreken; bevestigd | Beide audits: opgeslagen notebookuitvoer is de enige bron voor diarizatie/rol |
| CL | nb03 handmatige referentie | Weggevallen regels? | HERUITGEVOERD (CG T29) | GELDIG | Zie CG T29 | — |

---

## 4. Geldige tests

Deze tests zijn correct opgezet, het bewijs is controleerbaar en de conclusie past. **Conclusies die behouden mogen blijven:**

* **Reproduceerbaarheid van de audits zelf** (hashes, scripts, resultaten): alles reproduceert.
* **Bestaande unit-tests slagen** (17 + 51); ze meten geen kwaliteit.
* **`assign_speakers` implementeert zijn gedocumenteerde drempels** (T02, T03, T04 + V05-1): een tweede spreker onder 15% van het segment, in de test tot 1,4 s van 10 s, wordt niet gesignaleerd; het segment krijgt één label. Dit is een representatiebeperking van de alignment, **geen fout in pyannote**.
* **De vlag `overlap` kan opeenvolgende sprekerwissel en gelijktijdigheid niet onderscheiden** (CG T01, CL E4/E5, V05-2). Houd vast aan: "de vlag betekent *tweede spreker beslaat ≥15% van het segment*".
* **Cache en WAV-cache sleutelen alleen op bestandsnaam** (CG T15, T28; CL E17, E18; V05-4: `transcription.main()` stopt met exitcode 0 en zonder model te laden als er een `base`-cache is en `--model medium` gevraagd wordt).
* **Batching registreert niet-doorgestuurde instellingen** (CG T16; de batched API accepteert ze wel).
* **Modellen valideren niet op onmogelijke tijden of onbekende velden** (CG T05, T24, T25; CL E8, E9). Dit is een feit; het is in de 5 echte uitvoeren niet voorgekomen.
* **Afgekapte WAV wordt niet gedetecteerd** (CG T20; V05-6).
* **Handmatige-transcriptieparser laat 4 van 9 regels vallen** (CG T29).
* **Whisper-kwaliteitsmaten gelden per venster** (CL F5): in de opgeslagen JSON's hebben de segmenten 2, 2, 5, 2, 3 unieke `avg_logprob`-waarden (audio 1, 2, 4, 5, 7); in `faster_whisper/transcribe.py` r. 1362–1364 krijgt elk segment de venstergemiddelden.
* **Tuningscore ≠ DER** (CG T21/R03; CL F2). Geen enkele gerapporteerde "% totaal juist" is een DER.
* **Hele-seconde-timestamps bij audio2 en audio7** (CL F7): 19/19 en 38/38 reproduceren uit de bewaarde JSON. Oorzaak onbekend.
* **WER/CER-rekenwerk** van Claude (T3) en het DER-rekenwerk (T4) zijn aritmetisch correct (onafhankelijk herberekend).
* **Experimentele helpers**: `compute_agreement` (T30) en `_best_matching_label` (T31) gedragen zich anders dan hun commentaar/naam suggereert.

---

## 5. Gedeeltelijk geldige tests

Nuttig, maar onvoldoende voor de oorspronkelijke claim:

| Test | Wat wel | Wat niet |
|---|---|---|
| CG T01, CL E4 (overlap) | Vlag is niet gelijk aan gelijktijdigheid | Geen softwarefout; contradicts niet de eigen docs |
| CG T08, T10, T11, T12 | Ontbrekende guards in synthetische situaties | Geen aangetoond voorkomen in echte data; nep-herkenner omzeilt `_embed` |
| CG T18, CL E16 | WAV-extensie ≠ bruikbaar formaat | Fout is luid; contract is "non-wav inputs"; alle echte invoer is mp3 |
| CG T22, T23, T26, T27, T32 | Gedrag klopt | Ernst of "norm" komt van de reviewer; geen bestaand resultaat getroffen (T27) |
| CL T2 | ASR-run met vastgelegde instellingen | "Reproduceerbaar" alleen voor audio1/2; audio5 wijkt af vanaf ± 28 s |
| CL T3 | Rekenwerk correct | Referentie niet onafhankelijk; GEEN/"niet meenemen"-asymmetrie |
| CL T4 | DER-rekenwerk correct | Geen DER van het diarizatiemodel (zie §8, §12) |
| CL T9, T10, T11 | Cijfers kloppen | Geen script in pakket; GT-vlag meet iets anders dan de code-vlag; in-sample |
| CL E1, E3, E11, E14, E15, E16 | Waarnemingen kloppen | Verwachtingen zijn meningen, of de test kan niet falen |

---

## 6. Ongeldige tests

| Test | Reden |
|---|---|
| CL E7b | Geen verwachting: `passed=True` hard-gecodeerd. Kan niets weerleggen of bevestigen |
| CL E13 | Onmogelijk scenario (label-map is injectief), door Claude zelf erkend; telt toch mee in "10/22" |

Er zijn geen CG-proeven die ik als **ongeldig** beoordeel. Wel zijn T05, T20, T23 en T24 **procedureel zwak** (hard-gecodeerd `False`): de uitkomst blijft juist omdat de onderliggende waarneming (object zonder uitzondering gebouwd) direct uit de uitvoer volgt, maar de test kan zo nooit een voldane verwachting registreren.

Tevens ongeldig als **bewering** (geen test): *"audio/test-files/docentreferentie ontbraken"* (CG, auditrapport §1, §5, §9 en testbijlage). Het eigen manifest (V08) toont 13 mp3's in `Data-analysis/src/test-files`. Het ontbrekende bewijs was dus niet *afwezig*, het is niet gebruikt.

---

## 7. Niet-verifieerbare tests

| Item | Wat ontbreekt |
|---|---|
| CL T6, T7, T8 (stilte/ruis/SNR/8 kHz) | Gegenereerde WAV's en het script dat ze genereerde zijn niet bewaard. SNR en resampling niet herleidbaar. Alleen `synth_results.json` bestaat |
| CL T4 (DER) | Ruwe pyannote-turns, de codeversie waarmee de notebookuitvoer werd gemaakt, en originele `der.py`-uitvoer (alleen in het gesprek; `der.py` is bovendien tijdens de audit aangepast). Wel herberekenbaar uit `nb_hyp.json` |
| CL T9, T10 | Geen script; wel herberekend (V04) |
| CL `nb_hyp.json` | Eerste (cp1252) versie is overschreven; tussenversies van `wer_results.json` ook |
| CL ASR-run | Origineel commando en shell-historie; modelrevisie niet destijds vastgelegd |
| Beide | Alle `Data-local/processed/**` (pipeline-JSON's, WAV-cache), `testaudio2_manual.txt`, `testaudio5_manual.txt`, `pyannote_teacher_similarity.csv`, HF-token, pyannote- en wespeaker-gewichten, audio van `final_testfragment` |
| Beide | De tuning-resultaten van de gebruiker (`results_*.json`: 81 → 83,2%) kunnen door geen van beiden worden herberekend |

---

## 8. Tegenvoorbeelden en falsificatie

Ik heb actief geprobeerd belangrijke claims te weerleggen. Resultaat per poging:

| # | Claim | Poging tot weerlegging | Resultaat |
|---|---|---|---|
| 1 | CL: GT is circulair met Whisper (F1) | Zoek tegenvoorbeeld in een **onafhankelijke** handmatige transcriptie (`testaudio1_manual.txt`), V06 | **Overleeft.** CSV-tekst vs verse Whisper: 1,7% WER; CSV vs handmatig: 19,7%; Whisper vs handmatig: 21,3%. De CSV deelt Whisper-keuzes die de handmatige tekst niet heeft ("iets met opruimen", het woord "bitter"). Aanvullend: `testaudio4` 87/87 GT-rijen identiek aan een ASR-segment in tekst en tijd (V02). In HEAD heet de tekstkolom `transcript_hint`, en de tekst van `testaudio2` (19/19) en `testaudio4` (87/87) is ongewijzigd van "hint" naar "transcript" gegaan |
| 1b | Idem | Is het uniform? V09 en V02 | **Genuanceerd.** `testaudio5` staart (≥ 27,9 s): 0/8 rijen komen met een Whisper-grens overeen; de GT is daar herwerkt. Audio1 heeft menselijke splitsingen ("Dit ben jij." / "Dit ben ik." als aparte rijen). Circulariteit is ernstig voor audio2/4/7, zwakker voor audio1/5 |
| 2 | CL: "README bevestigt voorinvulling" | Lees de README volledig | **Gedeeltelijk.** Er staat: "startpunt voorgevuld uit de Whisper-segmenten, **daarna handmatig gecontroleerd en aangepast**". Het rapport citeert alleen het eerste deel. Een voorgevulde en gecontroleerde GT is geen onafhankelijke GT, maar "niet gecontroleerd" is niet bewezen |
| 3 | CL: DER-getallen | Eigen frame-DER zonder pyannote.metrics (V03) | **Overleeft** (3 van 4 exact, audio1 binnen 0,01, verschil verklaard) |
| 4 | CL: DER is "ondergrens" voor de echte DER | Is dat afleidbaar? | **Niet onderbouwd.** Het label per ASR-segment kan fouten toevoegen of juist verbergen; relatie tot de ruwe pyannote-DER is niet vastgesteld |
| 5 | CL: overlapvlag is ruis (16/22 vals alarm) | Herbereken (V04) | **Cijfers kloppen**; maar de GT-vlag meet iets anders dan de codevlag en GT en ASR delen het raster; "vals alarm" kan een echte sprekerwissel zijn |
| 6 | CG: "audio ontbreekt, daarom geen WER/DER" | Zoek de mp3's in CG's eigen manifest (V08) | **Weerlegd.** 13 mp3's, alle in `Data-analysis/src/test-files` |
| 7 | CG: "cache negeert modelinstellingen" (code-inspectie) | End-to-end `transcription.main()` met omgeleide mappen (V05-4) | **Bevestigd.** Exit 0, geen model geladen, geen waarschuwing |
| 8 | CG/CL: korte tweede spreker onzichtbaar | Drempelsweep met verwachting uit docs (V05-1) | **Bevestigd** en nu gekwantificeerd: zichtbaar vanaf 15% van de segmentduur |
| 9 | CG F03/T08: ongeordende of onmogelijke tijden "gaan naar alignment" | Komen ze voor in echte uitvoer? (V05-7) | **Niet waargenomen** in 174 echte segmenten |
| 10 | CG F11/T27: GEEN/ONBEKEND vervuilen de score ("hoog") | Welke bestaande resultaten gebruiken die fragmenten? | **Latent.** De bestaande tuningresultaten zijn van audio2/4 zonder GEEN/ONBEKEND |
| 11 | CG: torch "2.14.0 ≠ 2.14.0+cpu" | `torch.__version__` | **Weerlegd.** `2.14.0+cpu` |
| 12 | CL: ASR reproduceert eerdere run | Vergelijk met opgeslagen nb-run (V08, V09) | **Deels weerlegd.** audio1 en audio2 gelijk; audio5 vanaf ± 28 s niet (oorzaak niet vastgesteld: temperatuurfallback-niet-determinisme, andere instelling of versie) |
| 13 | CL: `audio_file` absoluut (4×) | Tel in bewaarde JSON's (V05-7) | **5 van 5.** Klein getalsverschil |
| 14 | CG T29 / CL: parser laat regels vallen | Bekijk het bronbestand | **Bevestigd** en gecontroleerd dat de weggelaten regels echte tekst zijn |
| 15 | CG/CL: notebooks niet uitvoerbaar | Koude run (V07) | **Bevestigd**; alleen notebook 06 loopt door, wat past bij het ontbreken van `Data-local/processed` |

---

## 9. Tegenstrijdigheden tussen de audits

| Onderwerp | ChatGPT | Claude | Verklaring / wat het bewijs zegt |
|---|---|---|---|
| **Audio aanwezig?** | "audio… ontbreken" (§2, §5, §9) | Mp3's gebruikt, ASR gedraaid | **Claude heeft gelijk.** CG's manifest bevat de 13 mp3's. CG heeft de lijst niet teruggekoppeld aan zijn rapport. Mogelijke bijkomende reden (door CG gegeven): een modelconstructie zou een download kunnen starten; niet getoetst. Ik kan niet vaststellen wie de Whisper-modelcache (12:45) plaatste |
| **WER/CER/DER** | "niet berekend" | Berekend (5 fragmenten; DER 4 fragmenten) | Gevolg van bovenstaande. Claude's cijfers zijn rekenkundig juist maar niet als nauwkeurigheid te citeren |
| **GT-herkomst** | Behandelt GT als "handmatige referentie", structurele controle | Herkent voorinvulling (F1) | Claude heeft gelijk (V06, V02). CG's R04 (overlap zonder interval, `intelligible` onduidelijk) is een andere, ook geldige constatering die Claude niet maakt |
| **Ernst "kritiek"** | "Geen bevindingen met ernst kritiek" | F1 "Kritiek" | Beide kloppen binnen eigen bereik: CG had geen metingen, dus geen kritieke feitelijke fout; Claude's F1 is een evaluatieprobleem |
| **Overlap-vlag** | R02 "semantisch risico" | F3 "Hoog" | Eens over de waarneming. Claude kwantificeert (T9), maar dat is met een GT die niet goed past |
| **Whisper-flags per venster** | Niet vermeld | F5 (Claude) | Alleen Claude; bevestigd |
| **Batching-config** | F02 | Niet vermeld | Alleen CG; bevestigd |
| **Hele-seconde-timestamps / `.gitignore`-hoofdletter / privacy** | Niet vermeld | F7, F12, F13 | Alleen Claude; F7 bevestigd. `.gitignore` en privacy niet door mij getoetst |
| **Cache** | F01 (+ corrupt cachebestand) | F8, E17/E18 | Eens, aanvullend |
| **Notebooks** | Cellen koud uitgevoerd, 06 loopt | Alleen opgeslagen uitvoer gelezen + uitvoervolgorde | Complementair; beide bevestigd |
| **torch-versie** | Presenteert 2.14.0 vs 2.14.0+cpu als drift | Corrigeert dit in `omgeving_claude.md` | Claude heeft gelijk |
| **Python 3.11.5 bij nb03** | Niet vermeld | "andere omgeving" | Komt van opnieuw opslaan (uncommitted metadata-wijziging) |
| **Aantal geslaagde tests** | 9 geslaagd / 23 weerlegd van 32 | 10 / 22 | Beide "geslaagd"-tellingen zijn niet vergelijkbaar: CG's "weerlegd" bevat ontwerpbeperkingen; Claude's "geslaagd" bevat niet-falsifieerbare gevallen (§3.3) |

---

## 10. Aanvullende controles

Alles in `Validatie_fase1_stap2/`. Hashes van mijn scripts en resultaten staan in §13.

| ID | Onderzoeksvraag | Hypothese | Invoer | Onafhankelijk bepaalde verwachting | Gemeten | Conclusie | Beperking |
|---|---|---|---|---|---|---|---|
| V01 | Komen alle manifests/hashes overeen? | Ja | Beide manifests, zip, repo | Hashes gelijk | 102/102, 117/117, 33/33 | Bewijsbestanden zijn consistent | Claude-hashes achteraf berekend |
| V02 | Zijn Claude's WER/CER-cijfers correct? Hoe afhankelijk zijn GT en ASR? | Cijfers kloppen; GT circulair voor audio2/4 | 5 ASR-JSON's + 5 GT-CSV's | Eigen Levenshtein, dezelfde normalisatie | WER 0,032 / 0 / 0 / 0,123 / 0,031 (identiek); rijen exact gelijk aan ASR-segment: 6/12, 19/19, 87/87, 14/20, 35/38; variant zonder GEEN-asymmetrie: audio1 0,016; zonder "niet meenemen"-rij: audio5 0,094 | Rekenwerk juist; circulariteit sterk voor 2/4/7 | Normalisatie is die van Claude; ASR-run niet door mij gedraaid |
| V03 | Is Claude's DER-berekening correct? | Ja | `nb_hyp.json` + GT-CSV's | Eigen frame-DER (10 ms, collar 0, optimale koppeling) | 0,233 / 0,424 / 0,177 exact, 0,344 (audio1) vs 0,354; `"None"`-label: audio7 0,194 zonder; GT overlapt zichzelf 0,4 s (audio1) | Rekenlogica juist; DER meet label-per-segment, niet pyannote | Hypothese uit oude notebooks |
| V04 | Kloppen T9 (overlapvlag) en T10 (docentrol)? | Ja | `nb_hyp.json` + GT | Eigen tel-/seconde-logica | T9: TP/FP/FN exact gelijk; T10: 31/6/6 en 6/2/5 exact | Cijfers kloppen; interpretatie beperkt | Geen origineel script |
| V05 | Gedragen de productiefuncties zich zoals beide audits zeggen? | Ja | Productiecode (alleen importeren) | Drempels uit `config.py` | Zie §8 en §4 | Bevestigd | Synthetisch |
| V06 | Is de GT-tekst afgeleid van Whisper? | Ja (H1) | `testaudio1_manual.txt`, GT-CSV, verse ASR | Bij H0 zou CSV even ver van Whisper als van handmatig liggen | 1,7% vs 19,7% (en 21,3%) | H1 aanvaard voor audio1 | Handmatige tekst is zelf los (parafrase, "bitter" ontbreekt); alleen audio1 heeft zo'n bestand |
| V07 | Draaien notebooks koud? | Nee (behalve 06) | 6 notebooks, lege namespace | Volgens ontbrekende data | Zie §3.4 | Bevestigd | Geen kernel |
| V08 | Reproduceert de verse ASR de notebookrun? Bevat CG's manifest de mp3's? | Ja / Ja | `nb_hyp.json`, ASR-JSON's, manifest | — | audio1 5/5 tijden, audio2 19/19 tijden, audio5 deels; 13 mp3's | Audio5 niet reproduceerbaar; CG's audio-claim onjuist | Afgekapte nb-tekst |
| V09 | Waren de GT-tijden van audio5 uit de oudere run gevuld? | Ja | GT + nb-run + verse run | Overeenkomst binnen 0,12 s | 14/20 (nb) vs 12/20 (vers); staart 2/8 vs 0/8 | Staart is herwerkt door de annotator | Klein aantal |
| H1 | Reproduceren de scripts? | Ja | `run_audit.py` (kopie, alleen rootpad aangepast) en `edge_tests.py` | Identiek aan origineel | 32/32 en 22/22 identiek | Beide audits zijn technisch herhaalbaar | Zelfde machine/omgeving |

---

## 11. Prioriteiten voor vervolgonderzoek

**Opnieuw meten (hoge prioriteit)**

1. **Onafhankelijke referentie.** Annoteer opnieuw, eerst luisteren zonder Whisper-voorinvulling, bij voorkeur door twee annotatoren; leg grenzen los van ASR-segmenten vast; documenteer een codeboek (`speaker_id`, `GEEN`, `ONBEKEND`, `overlap` met tijdspan en identiteit, `intelligible`). Pas daarna WER/CER/DER rapporteren.
2. **DER op ruwe pyannote-turns** (bewaar ze in de JSON) met vastgelegde collar (0 en 0,25 s) en overlap, mét missed/FA/confusion apart. Rapporteer segmentgebaseerde DER alleen als "label-per-segment".
3. **ASR-determinisme.** Herhaal de ASR-run meermalen op `testaudio5` om te zien of de afwijking vanaf ± 28 s ruis is.
4. **Docentherkenning op onafhankelijke data**: meerdere docenten, referenties van andere opnames, drempel op een aparte set kiezen.
5. **Ruis/SNR-experimenten opnieuw** met een bewaard generatiescript, een exacte SNR-berekening, meerdere realisaties, en een referentie die niet de Whisper-voorinvulling is.

**Kunnen blijven staan**

* De ontwerp-/representatiebeperkingen: één label per ASR-segment, vlagdefinitie `overlap`, venster-niveau Whisper-maten, cache-sleutel op bestandsnaam, ontbrekende validatie van modellen, afgekapte WAV, handmatige-parseromissie, "tuningscore ≠ DER".
* De conclusie dat WER/CER-cijfers op de huidige GT geen transcriptienauwkeurigheid zijn.

**Opruimen in de audits zelf (laag)**

* Eén gedeelde tellingswijze voor "geslaagd/weerlegd"; verwijder E7b/E13; maak harnassen (T05, T20, T23, T24) correct falsifieerbaar.
* Corrigeer CG's audio-bewering en torch-regel, en Claude's "4×", "ondergrens" en gedeeltelijke README-citaat.

---

## 12. Conclusie voor mijn stageonderzoek

*(Voorgestelde tekst, methodologisch verdedigbaar.)*

> Voor het onderzoek zijn twee onafhankelijke technische audits van de pipeline uitgevoerd. Het scriptmatige deel van beide audits (32 en 22 technische proeven) bleek bij herhaling volledig reproduceerbaar, en de gerapporteerde bestandshashes kwamen overeen met de onderzochte bronversie. De proeven tonen aan dat de koppeling van sprekers aan ASR-segmenten één label per segment toekent, dat een korte tweede spreker onder 15% van de segmentduur niet gesignaleerd wordt, dat de vlag `overlap` geen gelijktijdige spraak maar de aanwezigheid van een tweede spreker meet, en dat cache, schemavalidatie en audio-integriteitscontroles beperkt zijn. Deze bevindingen betreffen de verwerkingslogica, niet de nauwkeurigheid van de modellen.
>
> De berekende WER (0,000–0,123), CER en DER (0,18–0,42) zijn **niet** bruikbaar als maat voor de nauwkeurigheid van Whisper of pyannote. De referentietranscripties zijn deels afgeleid van de Whisper-uitvoer die ermee wordt getoetst (onder meer bij `testaudio4`: alle 87 referentierijen gelijk aan een ASR-segment in tekst en tijd), de referentie staat op hetzelfde tijdsraster als de segmentgebaseerde hypothese, en de DER is berekend op opgeslagen notebookuitvoer in plaats van op ruwe diarizatie. De tuningscore "totaal juist %" is bewust een dekkingsmaat en geen DER. Docentherkenning is alleen in-sample getoetst (één docent, één referentieclip, drempel op dezelfde data gekozen).
>
> Wetenschappelijk verdedigbare uitspraken zijn daarom: (1) de pipeline heeft de genoemde, reproduceerbaar aangetoonde ontwerpbeperkingen; (2) de huidige referentiedata zijn niet geschikt voor een onafhankelijke nauwkeurigheidsmeting; (3) de werkelijke nauwkeurigheid van transcriptie, diarizatie en docentherkenning is nog niet vastgesteld en vereist een onafhankelijk geannoteerde set en DER op ruwe diarizatie.

---

## 13. Reproduceerbaarheid van deze validatie

Alle commando's vanuit `C:\Users\School\Projects\StudieStap_WorkshopTool`, Python 3.11.5:

```
python -I Validatie_fase1_stap2/scripts/v01_hashcheck.py
python -I Validatie_fase1_stap2/scripts/v02_wer_independent.py
python -I Validatie_fase1_stap2/scripts/v03_der_independent.py
python -I Validatie_fase1_stap2/scripts/v04_overlap_role_recheck.py
python -B Validatie_fase1_stap2/scripts/v05_code_behaviour_checks.py
python -I Validatie_fase1_stap2/scripts/v06_manual_vs_csv.py
python -B Validatie_fase1_stap2/scripts/v07_notebook_cold_exec.py
python -I Validatie_fase1_stap2/scripts/v08_repro_and_manifest.py
python -I Validatie_fase1_stap2/scripts/v09_gt_vs_notebook_run.py
python -I Validatie_fase1_stap2/scripts/v10_git_head_vs_worktree.py
python -B Validatie_fase1_stap2/zip_extract/scripts/der.py Validatie_fase1_stap2/zip_extract   # reproductie T4
cd Validatie_fase1_stap2/herhaling_chatgpt && python -B run_audit_kopie.py                        # 32 tests
python -B Validatie_fase1_stap2/zip_extract/scripts/edge_tests.py Validatie_fase1_stap2/herhaling_claude   # 22 tests
```

Het zip moet eerst naar `Validatie_fase1_stap2/zip_extract/` zijn uitgepakt (`Expand-Archive`). V05 maakt tijdelijk een map `tmp/` aan en ruimt die op.

| Bestand | SHA-256 |
|---|---|
| `scripts/v01_hashcheck.py` | c300b06c00c8ce4c765f9312f04747243dd1feb09da32e8747f5ea0f76e23d79 |
| `scripts/v02_wer_independent.py` | efecd35730cbec419388697d1cff2cb8df4d81db469c15028b537752f664d1ee |
| `scripts/v03_der_independent.py` | 78226b4d4a88ad2683356036650c514fd4d3c1db7d8ab7ec4bb709f47f2a20b1 |
| `scripts/v04_overlap_role_recheck.py` | 1aa40fc22c261da95dcf9eee28384d89f54dec617120c1388acdfae4ceee3dbf |
| `scripts/v05_code_behaviour_checks.py` | 07c1d7b08375f8454384b05b1d03bad72b73d0a15671f2980e1943684fc90b6e |
| `scripts/v06_manual_vs_csv.py` | 2bc1a9001232a605e4568382e8d242dcb4772f788b44e7884e768c6835add5d7 |
| `scripts/v07_notebook_cold_exec.py` | 8c67b1dbb5733793e726e67ac1c90d7d3acb763f8dea59b252c29390ca4bd20d |
| `scripts/v08_repro_and_manifest.py` | 5be3d7486904d991a0eff5ba8b2239bbe446d7ab96cf4ad648c52b5859be3718 |
| `scripts/v09_gt_vs_notebook_run.py` | ce63f5ea19598f4dd2b205dcf85bbbf4e4457a3acdc3fa40d72ba19b8e9cc642 |
| `scripts/v10_git_head_vs_worktree.py` | 30d5bf6db045d4144aa387b5dce70091b6f56a90f45b66d7d75e1b2eb63143ba |

De resultaatbestanden `resultaten/v0*.json` bevatten de ruwe uitvoer van de bovenstaande scripts.

**Eerlijke uitvoeringsstatus.** Statische inspectie alleen: de bewering over `.gitignore`-hoofdletters, privacy van de mp3's, `speaker_confidence`-semantiek (F4), `exclusive_speaker_diarization` (M7), `Data-analysis/src/None/speechbrain/`-stubs en alle HF-modelrevisie-opmerkingen; hier heb ik niets over gemeten. Niet uitgevoerd: elke run met Whisper, pyannote of wespeaker; alle audit-claims over hun modelgedrag zijn dus alleen via de opgeslagen uitvoer getoetst.
