# Onafhankelijke technische en methodologische audit — StudieStap, fase 1

**Datum:** 9 oktober 2026. **Onderzocht:** aanwezige werkboom van `StudieStap_WorkshopTool`, commit `33cc8a10eb2aea0a161b387f08ce0192b46e89bc`, inclusief reeds aanwezige lokale wijzigingen. Die wijzigingen zijn geen auditwijzigingen. **Werkwijze:** oorspronkelijke code en gegevens, geen overgenomen conclusies uit andere audits. Geen externe downloads, modelinference, uploads, installatie, nieuwe classifier of wijzigingen aan de oorspronkelijke bestanden.

Bewijsbestanden staan naast dit rapport: `inventory.json`, `manifest.json`, `test_results.json`, `baseline_src.txt`, `baseline_classification.txt`, `dependency_check.txt` en `run_audit.py`. De leesbare testbijlage bevat voor ieder tegenvoorbeeld vraag, invoer, verwachting, uitkomst, conclusie en beperking. Celnummers in dit rapport zijn **1-based over alle notebookcellen**, inclusief Markdown; zij verschillen dus van uitvoernummers.

## 1. Samenvatting en voorlopig oordeel

De bestaande code vormt een bruikbare **experimentele basis**, maar de automatische resultaten zijn nog niet voldoende onderbouwd voor betrouwbare didactische beoordeling. De audit toont fouten in invoervalidatie, cachehergebruik, kwaliteitsafhandeling en de handmatige vergelijking. Daarnaast kan de koppeling van één spreker aan een heel ASR-segment een korte andere spreker volledig verbergen, zelfs wanneer de diarizatie die spreker correct heeft gevonden.

De 17 oorspronkelijke tests voor docentherkenning en orkestratie en de 51 oorspronkelijke classificatietests slagen in de juiste werkmappen. De 32 aanvullende auditproeven bevestigen 9 verwachte eigenschappen en weerleggen 23 verwachtingen. Dit zijn bewust gekozen technische tegenvoorbeelden; **23/32 is geen schatting van de foutkans van echte audio**. Een deel van de weerlegde verwachtingen betreft een ontwerpbeperking of methodologisch risico, niet een programmeerfout.

Alle 8 aanwezige project-JSON-bestanden zijn syntactisch geldig; zij bestaan uit 3 synthetische classificatiefixtures en 5 samengevatte tuningresultaten. Alle 28 Python-bestanden zijn syntactisch geldig. Vijf notebooks stoppen bij uitvoering met een lege variabelenruimte; notebook 06 doorloopt zijn 10 niet-lege codecellen.

**Geen WER, CER of DER gemeten.** Er is één handmatige teksttranscriptie en er zijn sprekerannotatie-CSV's, maar in deze checkout ontbreken audio, echte ASR-hypothesen en ruwe diarizatietijdlijnen. Samengevatte historische scores en opgeslagen notebookuitvoer zijn geen opnieuw uitgevoerde modelmetingen. De audit bewijst daarom niet dat pyannote zelf sprekers samenvoegt of opsplitst, en kan de betrouwbaarheid van het ASR-model niet kwantificeren.

Belangrijkste prioriteit: maak de invoer, sprekerkoppeling, referenties en evaluatie controleerbaar voordat verdere modelkeuze of classificatie plaatsvindt. Het uitgangspunt dat een fragment **niet beoordeelbaar** mag zijn is methodologisch passend. De huidige code heeft bruikbare onzekerheidsvelden, maar nog geen sluitende kwaliteitsbeslissing.

## 2. Projectinventarisatie en werkelijke gegevensstroom

### Productiecode

| Bestand onder `Data-analysis/src` | Werkelijke taak |
|---|---|
| `run_docent_pipeline.py` | Start vier scripts achtereenvolgens via hetzelfde Python-programma; stopt bij een niet-nul exitcode |
| `transcription.py` | MP3/WAV/M4A → faster-whisper → `WorkshopTranscript` |
| `diarization.py` | Audio → pyannote-sprekerbeurten → toewijzing van één spreker per ASR-segment |
| `preprocessing.py` | Diarized transcript → samengevoegde `SpeakerTurn`-objecten met bronsegmenten en contextvelden |
| `docent_recognition.py` | Audio per turn + docentreferentie → embedding/cosine → `DOCENT`, `OTHER` of `ONZEKER` |
| `models.py` | Pydantic-modellen voor transcript, segment, turn en processed transcript |
| `config.py` | Projectpaden, dataclasses en lazy tokenlookup; optioneel `.env` |
| `OLD_benchmark_transcription.py` | Afzonderlijke benchmarkroute met meerdere ASR-modelgroottes |
| `evaluation/wer.py` | Optionele jiwer-WER van tekstbestanden tegen transcript-JSON |
| `tests/*` | Unitproeven voor docentrol en scriptorkestratie; geen modelkwaliteitstoets |

Werkelijke route:

```text
raw/ of src/test-files/ audio
  → transcription.py → Data-local/processed/<stem>.json
  → diarization.py → processed/diarization/<stem>_diarized.json
  → preprocessing.py → processed/preprocessing/<stem>_diarized_turns.json
  → docent_recognition.py + referentieaudio
      → processed/docent_recognition/<stem>_diarized_turns_docent_roles.json
```

De geïntegreerde runner kiest standaard ASR `medium`, terwijl de losse transcriptiescriptconfig standaard `base` kiest. Beide gebruiken Nederlands, CPU en `int8`; batching staat standaard uit. ASR-config: beam 5, VAD aan, previous-text conditioning aan, woordtijdstempels uit. Interne decodeerdrempels en afzonderlijke heuristische vlagdrempels zijn expliciet aanwezig.

Diarizatie gebruikt `pyannote/speaker-diarization-3.1`; geen minimum/maximum aantal sprekers tenzij ingesteld. Labels worden op spreektijd gerangschikt: `MAIN_SPEAKER` betekent de langst sprekende identiteit. Dit is in de productieroute **geen docentlabel**. Koppeldrempels zijn 0,15 voor een tweede spreker, 0,60 voor winnaardekking en 0,15 voor het verschil met de runner-up. De opgeslagen `speaker_confidence` is een verhouding van tijdsdekking, geen gekalibreerde modelkans.

Docentherkenning gebruikt `pyannote/wespeaker-voxceleb-resnet34-LM`, cosine-drempel 0,35 en minimale turnspan 1 seconde. De losse docentstap eist een expliciete referentie; de runner vult standaard `test-files/testdocent.mp3` in. `OTHER` betekent uitsluitend dat de stem onder deze experimentele drempel valt; dit bewijst niet dat de persoon een leerling is.

### Experimenten, notebooks en gegevens

Aanwezig zijn speaker-recognitionproeven voor WeSpeaker en SpeechBrain ECAPA (`speechbrain/spkrec-ecapa-voxceleb`), woordtijdstempels/toewijzing/refinement, een WhisperX-proef met Nederlands wav2vec2-alignment, een gearchiveerde community-1-proef, en clusteringtuning. Deze worden niet door de hoofdroute gestart. `Experiments/classification` bevat contextselectie, promptopbouw en een cyclische **mockclassifier** die inhoud negeert. Er is geen echte didactische classifier aangetroffen.

Alle zes notebooks zijn onderzocht: verkenning, ASR-benchmark, transcriptievergelijking, sprekerherkenningsvergelijking, voor/na-docentrollen en clusteringtuning. Ondanks de titel meet notebook 04 docentherkenning op chunks, geen DER. In de onderzochte Python- en notebookbroncode is geen CountVectorizer-, lemmatisatie- of uitgebreide NLP-normalisatiepipeline aangetroffen. Zulke onderdelen mogen hier niet worden verondersteld.

`Data-local` bevat alleen `raw/testaudio1_manual.txt`. `src/test-files`, echte processed-uitvoer, referentieaudio en de genoemde benchmark- en similarity-CSV's ontbreken. De 7 `ground_truth*.csv`-bestanden staan in de tuningmap. `ground_truth_final_testfragment.csv` heeft 137 rijen met lege speaker-ID; `ground_truth_template.csv` is een voorbeeld. De vijf overige bestanden hebben respectievelijk 12, 19, 87, 20 en 38 rijen voor audio 1, 2, 4, 5 en 7.

De map `src/None/speechbrain` bevat vijf `.ckpt`-bestanden en `hyperparams.yaml`. Het YAML-bestand bevat hier alleen een absolute cacheverwijzing naar deze Windows-gebruiker. De huidige SpeechBrain-proef verwijst naar een andere cache onder `Data-local`. Deze restbestanden zijn dus geen aangetoonde, zelfstandig bruikbare modelinstallatie. Ze zijn niet geladen of gewijzigd.

`App/Backend` en `App/Frontend` bevatten alleen placeholders. Er is geen uitvoerbare scraper/downloader aangetroffen. Herkomst-URL's, bronchecksums, downloadlogs en een gegevensverzamelingsmanifest ontbreken. Betrouwbaarheid, volledigheid, duplicaatdetectie en selectie van een eventuele oorspronkelijke scraper zijn daarom niet toetsbaar. Er is niets gedownload.

### Dependencies en configuratie

| Dependency | Gepind in hoofdrequirements | Aangetroffen in gebruikte Python |
|---|---:|---:|
| faster-whisper | 1.2.1 | 1.2.1 |
| pydantic | 2.13.5 | 2.13.5 |
| numpy | 2.5.3 | 2.4.6 |
| torch | 2.14.0+cpu | 2.14.0 |
| torchaudio | 2.11.0 | 2.11.0 |
| pyannote.audio | 4.0.7 | 4.0.7 |
| python-dotenv | 1.2.3 | 1.1.1 |

Audit uitgevoerd met Python 3.11. De in documentatie genoemde project-venv is niet aanwezig. Verder lokaal: jiwer 4.0.0, scipy 1.17.1, pandas 2.2.3, matplotlib 3.10.3 en scikit-learn 1.9.0. SpeechBrain en WhisperX zijn niet geïnstalleerd in deze interpreter. De metadata meldt geen soundfile-distributie; dit blokkeerde de daadwerkelijk uitgevoerde pyannote-import niet. Torchaudio en pyannote.audio importeren. `pip check` meldt een werkelijk conflict: numba 0.61.2 vereist numpy <2.3, terwijl numpy 2.4.6 aanwezig is. Dit bewijst een inconsistente omgeving, niet dat alle audio-inference faalt.

De WhisperX-proef heeft een afzonderlijk uitgebreid requirementsbestand. Hoofdrequirements dekken notebookdependencies, scipy en SpeechBrain niet volledig. ASR-modelgroottes en HF-modelnamen zijn vastgelegd, maar modelrevisies/checksums ontbreken. Het volledige bestandoverzicht met hashes staat in `manifest.json` en de inventarisbijlage.

## 3. Vastgestelde fouten en concrete validatiegebreken

Ernst betreft het potentiële gevolg voor het onderzoek. Een synthetisch bewezen codepad betekent niet dat die fout al in een bestaand audioresultaat is opgetreden. Er zijn geen bevindingen met ernst kritiek: daadwerkelijke uitkomsten op audio zijn niet beschikbaar.

| ID / ernst | Locatie | Fout en bewijs | Onderzoeksgevolg | Aanbevolen correctie, nog niet uitgevoerd |
|---|---|---|---|---|
| F01 — hoog | `transcription.py`, `output_path_for` (122), `cached_result_exists` (126) | T15: verschillende bronpaden/extensies met gelijke stem leveren hetzelfde JSON-pad. T28: ongeldig cachebestand `{` geldt als bruikbaar. Config/model speelt geen rol in de cachesleutel. | Verkeerde of verouderde transcriptie kan stil worden hergebruikt, ook na modelwijziging. | Cache koppelen aan bronhash, effectieve config/modelrevisie en geldig schema; atomisch opslaan. WAV-cache heeft hetzelfde stemrisico bij code-inspectie. |
| F02 — hoog | `transcription.py`, `TranscriptionEngine.transcribe` (88–116) | T16: batching geeft alleen language en batch_size door, maar slaat beam=2, VAD=False en words=True op alsof toegepast. | Vergelijking van instellingen en reproduceerbaarheid kunnen onjuist zijn. | Werkelijk gebruikte batchingconfig doorgeven en vastleggen, of niet-ondersteunde opties weigeren. Alleen opt-in batching geraakt; standaardroute batcht niet. |
| F03 — hoog | `models.py`, `TranscriptSegment` (23), overige tijdmodellen | T05/T24: negatieve/omgekeerde tijden, confidence=3, NaN/Infinity geaccepteerd. NaN/Infinity worden als `null` geserialiseerd. | Onmogelijke tijdlijnen gaan naar alignment/slicing; uitgegeven JSON kan niet meer in hetzelfde numerieke schema worden teruggelezen. | Eindigheid, 0≤start≤end≤duur, confidencebereik, ordening en cross-fieldconsistentie valideren. |
| F04 — hoog | `preprocessing.py`, `build_speaker_turns` (49,90) | T08: A 5–6 s gevolgd door A 0–1 s wordt een turn 5–1 s; negatieve gap wordt geaccepteerd. | Verkeerde context, duur en clipselectie bij ongeordende invoer. | Ordening expliciet controleren/weigeren; mergegrenzen en outer span bewaken. Niet bewezen dat Whisper zulke volgorde produceert. |
| F05 — hoog | `docent_recognition.py`, `_cosine_similarity` (40), `_embed` (86), `assign_docent_roles` (176) | T10: NaN → OTHER zonder waarschuwing; T11: twee nulvectoren → 0 → OTHER. | Onbruikbare embedding wordt bewijs tegen docentrol. | Dimensie, eindigheid en norm controleren; onbruikbaar als ONZEKER behandelen. Testdouble/nulvector; geen aangetoonde NaN uit echt model. |
| F06 — hoog | `docent_recognition.py`, turnduurcontrole en `_slice_waveform` (111) | T12: turnspan 2 s, beschikbare audio 0,25 s; recognizer wordt met 4000 samples aangeroepen en testscore geeft DOCENT. | Te korte of verkeerde clips omzeilen de 1-s-controle bij tijd-/audiomismatch. | Beschikbare sampleduur en tijdgrenzen controleren vóór embedding; tijdlijn koppelen aan exacte audiohash. |
| F07 — middel | `diarization.py`, `to_wav` (346), `_load_wav_waveform` (79) | T18: geldige 24-bit WAV passeert conversie ongewijzigd en wordt vervolgens door loader geweigerd. | Ondersteunde extensie garandeert geen bruikbaar WAV-formaat. | WAV-formaat inspecteren en zo nodig omzetten naar ondersteunde PCM; duidelijke preflight. 48-kHz PCM-samplerate wordt wel correct doorgegeven (T19). |
| F08 — hoog | `diarization.py`, `_load_wav_waveform` (79) | T20: header zegt 16000 frames, afgekapt bestand levert 28 samples zonder fout. | Gedeeltelijk opgeslagen audio kan als volledig worden verwerkt; suffix/exists is onvoldoende controle. | Gelezen bytes vergelijken met geclaimde frames, kanalen en samplebreedte; corruptie apart rapporteren. |
| F09 — hoog | Notebook 03, cel 5, `load_manual_transcript` | T29 op de werkelijke handmatige referentie: van 9 niet-lege tekstregels worden 5 geladen; 4 regels zonder `:` worden volledig overgeslagen. | De vergelijking verwijdert gesproken tekst uit de referentie en kan ten onrechte ontbrekende/extra ASR-tekst suggereren. | Vervolgregels bewaren en hun rol expliciet annoteren; geen impliciete rol aannemen bij ambiguïteit. |
| F10 — middel | Tuning `evaluate_min_cluster_size.py`, `score` (55,95) | T22: lege referentie geeft ZeroDivisionError. Bestaand final-testbestand heeft 137 lege speaker-ID's en loader houdt die niet over. | Lege/onafgewerkte referentie kan geen zinvolle score opleveren en crasht de scorer. | Referentie vooraf valideren en zonder score met duidelijke reden stoppen. |
| F11 — hoog | Tuning `load_ground_truth` (45) | T27: GEEN uit audio1 en ONBEKEND uit audio5 worden als gewone spreker-ID meegenomen. Overlap/intelligible/note worden niet ingelezen. | Applaus kan als gemiste spreker tellen; verschillende onbekende stemmen als één identiteit. | Annotatiecodeboek met aparte non-speech/unknown/maskersemantiek; onbekend niet matchen alsof persoon. |
| F12 — middel | `classification_data.py`, `ClassificationResult` (287) | T23: status OK accepteert detected=None en evidence=None, in strijd met de beschreven bruikbare antwoordcombinatie. | Later kan ongeldig antwoord als succesvol worden opgeslagen. | Samenhang van status/antwoord velden valideren. Geen echte classifier gebouwd. |
| F13 — middel | `speaker_recognition/_common.py`, `compute_agreement` (165,189) | T30: MAIN die correct als OTHER herkend wordt, heet conflict omdat de helper MAIN=docent aanneemt. | Experimentele conflictschatting verwart spreektijdrang met rol. Productieroltoewijzing is hiervan onafhankelijk. | Alleen identiteit en werkelijk geannoteerde rol vergelijken; MAIN-heuristiek niet als referentie gebruiken. |
| F14 — laag | Woord-refinement `refine_with_speaker_recognition.py`, `_best_matching_label` (121,134–135) | T31: documentatie belooft overlap / kortste segment; code gebruikt overlap / nieuw segment. Nieuw 0–10, baseline 0–1 krijgt None ondanks ratio 1 op kortste segment. Bovendien wordt `shorter` over alle baselines bepaald. | Experimentele baselinevergelijking kan matches missen en is anders dan beschreven. | Gewenste noemer expliciet bepalen voor gekozen match; documentatie en test ermee overeenstemmen. |
| F15 — middel | Notebook 02, cel 6 | Werkelijke uitvoering: ontbrekende benchmarkmap → files=[] → results[0] → IndexError. | Geen bruikbare melding dat benchmarkgegevens ontbreken. | Lege input expliciet controleren vóór tabellen/plots. |

T25 toont daarnaast dat onbekende extra velden standaard worden genegeerd door Pydantic. Dat is toegestaan gedrag van de gekozen modelschema's, maar maakt de commentaarclaim dat niets uit bronsegmenten verloren gaat te breed. T26 toont dat ontbrekende overlap-/onzekerheidsvelden automatisch False worden. Dit zijn compatibiliteitskeuzes met een kwaliteitsrisico, behandeld onder onderdeel 4.

## 4. Mogelijke problemen, ontwerpbeperkingen en methodologische risico's

**R01 — hoog, gereproduceerde ontwerpbeperking:** `assign_speakers` kent één winnaar toe aan het hele tekstsegment. T04 bevat correct gevonden A 0–9 en B 9–10: output alleen MAIN, confidence 0,9, overlap=False, uncertain=False. Eén seconde van B verdwijnt als sprekerinformatie. Dit bewijst een probleem in alignmentrepresentatie, niet een fout in het diarizatiemodel. Een later kwaliteitsbeleid mag een schone vlag dus niet als bewijs van één spreker behandelen.

**R02 — hoog, semantisch risico:** T01 met opeenvolgend A 0–8 en B 8–10 geeft overlap=True zonder simultane spraak. De berekening volgt de eigen definitie “tweede spreker dekt een deel van segment”, maar downstreamtekst spreekt over een tweede stem in dezelfde clip en dominante stem. Bewaar onderscheid tussen **meerdere sprekers binnen een segment** en **werkelijk gelijktijdige spraak**. Huidige overlapvlag meet die tweede eigenschap niet rechtstreeks. T03 markeert volledige simultane spraak wel, maar garandeert niet dat alle korte overlap wordt gevonden.

**R03 — hoog, evaluatierisico:** de tuningscore is een milde dekking op 0,1-s-punten in referentiebeurten, met optimale één-op-één speaker-matching. T21 scoort 100% bij hypothese X 0–100 s en extra Y 0–1 s tegenover GT A 0–1 s. De 99 s extra spraak en extra actieve spreker worden niet bestraft. Dit is conform de bewust milde scorer, maar `overall_correct_pct` mag daarom niet als DER, volledige accuracy of algemene betrouwbaarheid worden geïnterpreteerd.

**R04 — hoog, referentierisico:** een overlap=True in CSV zonder afzonderlijke tijdspan/identiteit van de tweede spreker levert geen volledige multi-speakerreferentie. In audio4 vermeldt een note bij een overlap=False rij dat de docent erdoorheen praat. Audio1 bevat overlappende intervallen waarvan niet alle betrokken rijen overlap=True hebben. `intelligible` staat bij alle 19 rijen audio2 en alle 38 rijen audio7 op nee, terwijl transcriptietekst ingevuld is. Zonder codeboek is niet duidelijk of dit “onverstaanbaar” of een omgekeerd ingevuld veld is. Geen van deze teksten/tijden is tegen audio gecontroleerd. Vraag betekenis na vóór metingen; herannotatie is nodig waar ambiguïteit blijft.

**R05 — hoog, ontbreken kwaliteitsbeslissing:** ASR-vlaggen worden opgeslagen, maar docentrol kijkt niet naar die vlaggen (T32 geeft DOCENT met een fake hoge score). `overlap=True` blokkeert de rol niet; alleen een note verschijnt. VAD kan audio overslaan; geen provenance van afgewezen intervallen wordt opgeslagen. Een leeg transcript heeft geen expliciete “niet beoordeelbaar”-reden. Geen schoolaudio is gebruikt om vast te stellen hoe vaak dit gebeurt.

**R06 — hoog, verlies van onbekendheid:** tijdmodellen geven bij ontbrekende overlap/assignmentvelden False (T26). De classificatieloader noemt die waarden dan bekende betrouwbaarheid. Een oudere of handmatig onvolledig ingevulde processed JSON kan daardoor schoon lijken zonder meting. Extra velden verdwijnen (T25). Dit bewijst geen fout in de aanwezige synthetische fixtures, die zulke velden bewust bevatten, maar vraagt schema-/provenancebewaking.

**R07 — hoog, niet-gevalideerde rolgrens:** 0,35 is expliciet experimenteel, geen gemeten kans. De audit heeft geen onafhankelijke rolvalidatieset. Verschillende microfoons, stemmen, rumoer, meerdere docenten en samengestelde turns kunnen similarity beïnvloeden. Een score net onder/over de drempel kent nu steeds OTHER/DOCENT toe, zonder onzekerheidsband. Rol wordt per turn bepaald; dezelfde diarizatie-ID kan wisselende rollen krijgen. Dat kan zowel herstel van verkeerde diarizatie als embeddinginstabiliteit betekenen; audio/referenties zijn nodig om dit te onderscheiden.

**R08 — middel, bron- en configtraceerbaarheid:** output bevat paden/modelnamen/config, maar geen audiohash, modelrevision, dependencysnapshot of ruwe diarizatieturns. `word_timestamps=True` in de productiewrapper bewaart geen seg.words. Preprocessing neemt de volledige top-level transcription-/diarizationmetadata niet mee; het bronpad blijft behouden, maar alleen zolang die bron bewaard en beschikbaar is. Identiteiten zijn lokale fragmentlabels; spreektijdrang kan tussen fragmenten veranderen en is geen persoonsidentificatie over opnamen.

**R09 — middel, overschrijven/herstarten:** preprocessing en OLD-benchmark schrijven bestaande output onvoorwaardelijk. De runner kan na cache-succes van ASR stoppen doordat diarized JSON al bestaat. Er is geen veilige, configgebonden hervatstrategie. Dit gedrag is vastgesteld door code-inspectie, niet door oorspronkelijke data te overschrijven.

**Waarschijnlijke audioproblemen waarvoor bewijs ontbreekt:** pyannote kan korte tussenkomsten missen, vergelijkbare stemmen samenvoegen, één stem opsplitsen of rumoer verwarren met spraak; ASR kan zachte spraak missen of tekst hallucineren. Geen hiervan is in deze audit met echte audio aangetoond. Threshold- of modelwisseling zonder die controle kan een alignmentfout maskeren.

## 5. Uitgevoerde tests, meetresultaten en beperkingen

| Controle | Resultaat | Wat hiermee niet is bewezen |
|---|---|---|
| Bestaande src-unitproeven | 17/17 slagen | ASR-, diarizatie- of embeddingkwaliteit |
| Bestaande mockclassificatieproeven | 51/51 slagen | Herkenning van didactische indicatoren |
| Aanvullende technische proeven | 32 uitgevoerd: 9 bevestigingen, 23 weerleggingen | Populatiefoutpercentage |
| Python syntax | 28/28 geldig | Runtimecorrectheid op alle dependencies/data |
| Oorspronkelijke JSON syntax | 8/8 geldig | Geldigheid van ontbrekende echte pipeline-uitvoer |
| Notebookcellen, nieuw namespace per notebook | 06 compleet; 01–05 stoppen | Volledige Jupyter-kernel/widget/rendercontrole |
| Dependencycontrole | numba/numpy-conflict; versiedrift | Onmogelijkheid om ieder model uit te voeren |
| Torchaudio/pyannote-import | Beide slagen | Model geladen of inference uitgevoerd |
| WER / CER | Niet berekend | ASR-accuracy |
| DER, missed speech, false alarm, confusion | Niet berekend | Diarizatie-accuracy |

De eerste test-discovery vanuit de repositoryroot gaf importfouten voor projectmodules/tests. Vervolgens zijn de originele suites uitgevoerd vanuit respectievelijk `Data-analysis/src` en `Experiments/classification` met `-t .`; daar slagen ze. Dat was een uitvoercontextprobleem, geen bewijs van 68 falende tests. Logbestanden bevatten de succesvolle baseline.

De auditproeven laden geen modellen. Voor wrapper-/rolbeslissingen zijn testdoubles gebruikt; overige geometry/schema/WAV-proeven draaien de oorspronkelijke functies. Test T31 voert de oorspronkelijke pure functie via AST-extractie uit. Synthetische audio bestaat uit nulwaarden, dus is bruikbaar voor formaat/duurcontroles, niet voor verstaanbaarheid of speakerkwaliteit. Aanwezige annotaties zijn gelezen en structureel gecontroleerd, niet opnieuw beluisterd.

Een volledige ongewijzigde audiobaseline kon niet worden gestart: daarvoor ontbreken audio en referentie. Een modelconstructie zou bovendien mogelijk een download starten. Er zijn geen fictieve modelmetingen toegevoegd. Het WER-hulpscript leest de hele handmatige tekst onbewerkt, inclusief sprekerprefixen; voordat deze werkelijke referentie ermee wordt gebruikt, moeten gesproken woorden van annotatietekst worden gescheiden en exact hetzelfde fragment worden gekozen.

### Reproduceren van deze audit

Vanuit de projectroot met de aanwezige dependencies:

```powershell
python -B Audit_fase1_2026-10-09/run_audit.py
```

Het script zet HF/Transformers offline, schrijft uitsluitend in zijn eigen auditmap, bewaart originele notebookbestanden en genereert testresultaten/inventaris/baselinetestlogs. De scriptuitvoering maakt synthetische bestanden opnieuw; het is geen productiepipeline. `test_results.json` bevat strikt JSON; onbruikbare floats zijn daarin als tekst `nan`/`inf` vastgelegd. Hashes in `manifest.json` leggen de onderzochte bestanden vast. De afzonderlijke importcheck en handmatige code-inspectie zijn aanvullende auditstappen; de scriptuitvoering claimt die niet als modeltests.

De afsluitende hashvergelijking vond geen verschillen met de vastgelegde oorspronkelijke bestanden (`integriteitscontrole.json`). De Git-status bevat naast de nieuwe auditmap dezelfde vooraf bestaande lokale wijzigingen. De leesbare aanvullingen staan in `testbijlage.md` en `inventarisbijlage.md`.

## 6. Diarizatieanalyse: eerst oorzaken lokaliseren

De belangrijkste **aangetoonde** oorzaak van verkeerd toegeschreven tekst is de representatie ná diarizatie. Eén ASR-segment kan meerdere speakerbeurten omvatten; die worden tot één label gereduceerd. Bij 10% tweede sprekertijd verschijnen zelfs geen overlap- of assignmentwaarschuwingen. Bij 20% tweede sprekertijd verschijnt de overlapvlag ook als stemmen nooit tegelijk actief zijn. Wijzigingen in clustering kunnen deze representatiebeperking niet oplossen.

Ruwe pyannoteturns worden in de hoofd-JSON niet opgeslagen; alleen aantallen, speakerinventory en segmenttoewijzing. Daardoor kan een onderzoeker uit die JSON niet achterhalen of de tweede spreker oorspronkelijk wel gevonden was. De woordtoewijzingsproef draait diarizatie opnieuw; dat is geen exacte replay van de oorspronkelijke tijdlijn. Het woordexperiment kan bestaande grenzen benutten, maar kan een door diarizatie gemiste spreker niet reconstrueren. Er is geen nieuwe word-level oplossing geïmplementeerd.

De clusteringtuning verandert `clustering.min_cluster_size` of `threshold` op een geladen pipeline. Aantal sprekers wordt in de hoofdroute niet gefixeerd. De samengevatte JSON's hebben aantallen en dekkingspercentages, maar geen ruwe hypothesetijdlijnen of referentiehash. Ze kunnen worden ingelezen (notebook 06), maar hun historische scores kunnen hier niet onafhankelijk worden herberekend.

Voor een volgende echte vergelijking moeten referenties eerst speakeractiviteit per identiteit, stilte en simultane spraak beschrijven. Leg evaluatiegebied, grenscollar en overlapbehandeling vooraf vast. Kansrijk is een primaire score zonder collar met overlap inbegrepen, plus een afzonderlijke gevoeligheidsanalyse met bijvoorbeeld 0,25 s collar en expliciet uitgesloten overlap; dit zijn voorstellen, **geen toegepaste instellingen**. Rapporteer DER met gemiste spraak, false alarm en speakerconfusion afzonderlijk. Onbekende/niet-beoordeelbare referentiegebieden krijgen expliciete maskers, geen verzonnen persoon-ID.

Prioriteitsvolgorde: (1) ruwe tijdlijnen terugvinden/bewaren, (2) annotaties controleren, (3) ASR/alignmentfouten onderscheiden van clusteringfouten, (4) pas daarna parameters vergelijken op onafhankelijk evaluatiemateriaal. Geen ander model als bewezen oplossing aanbevolen.

## 7. Jupyter Notebook-audit en NLP/classificatie

| Notebook | Werkelijk uitgevoerde controle | Overige bevindingen uit inspectie |
|---|---|---|
| 01-exploring_data | Cel 3 uitgevoerd; cel 5 FileNotFoundError | Verwacht ontbrekende `Breinschade_Uitleg_Sara.txt`. Woorden via split en vraagtekens via count zijn beschrijvende tellingen, geen indicatorherkenning. |
| 02-benchmarking | Cellen 2,3,5 uitgevoerd; cel 6 IndexError | `get_result` kan None geven; cel 15 dereference heeft geen guard. RTF=tijd/duur is correct voor positieve duur; nulduur niet gecontroleerd. Gemiddelde looptijd per model is alleen eerlijk bij dezelfde audiolijst/hardware en vergelijkbare instellingen. |
| 03-transcription-evaluation | Definities in 5,7,9 uitgevoerd; 12 FileNotFoundError | T29 bewijst referentietekstverlies. Handmatige tekst is niet tijdgefilterd, ASR wel; selectie kan segmenten voorbij venstergrenzen meenemen. Geen WER/CER/DER. HTML-tekst wordt escaped; titel rechtstreeks ingevoegd, lokaal laag risico. |
| 04-diarization | Cel 6 uitgevoerd; 7 FileNotFoundError | Aantal chunks gelijk garandeert geen gelijke (fragment,index,tijd)-set. IGNORE/onbekende labels worden uitgesloten: rapporteer uitgesloten aandeel en reden. FN telt alleen prediction OTHER; ontbrekende predictions vallen buiten TP/TN/FP/FN terwijl n ze kan bevatten. Bij n=0 ontbreekt expliciete guard. |
| 05-fixing-diarization-problems | Cel 3 FileNotFoundError | Voor/na-aantallen rollen bewijzen geen kwaliteitsverbetering zonder dezelfde turns en referentielabels. Verwacht ontbrekende BEFORE-snapshot. |
| 06-diarization-hyperparameter-tuning | Alle 10 niet-lege codecellen uitgevoerd | Dubbele functie-definitie en onregelmatige historische uitvoernummers blokkeren schone uitvoering hier niet. Samenvoegen `{**run1, **run2}` overschrijft dezelfde parameterkeys indien die voorkomen; huidige sets zijn disjunct. Tuning/dekking is geen DER. |

Uitvoering gebeurde in geheugen, met een lege variabelenruimte per notebook en de notebookmap als werkmap. Geen opgeslagen uitvoer is als nieuwe meting gepresenteerd. Dit is een controle van uitvoerbare Python-cellen, geen volledige nbclient-kernelrun. Er zijn geen originele notebooks opnieuw opgeslagen. Werkmappen blijven relevant: paden zijn relatief aan de procesmap, niet intrinsiek aan de notebooklocatie.

De aangetroffen mockclassifier is technisch geschikt voor laden → context → prompt → resultaatschema. Onzekerheidsvelden en docentrollen worden doorgegeven en identiteiten van verschillende OTHER-sprekers blijven apart. De classifier geeft echter cyclisch True/False/Unknown onafhankelijk van inhoud of kwaliteit; dit is expliciet een mock. Status UNKNOWN is geen geïmplementeerde audio-abstentionbeslissing. Structurele contextvelden en ASR-signalen worden niet volledig in `ClassificationTurn` opgenomen. Geen nieuwe classifier of didactische indicator ontworpen.

## 8. Onbetrouwbare audio en toekomstig niet-beoordeelbaar

Aanwezige signalen in de huidige code: ASR avg_logprob, no_speech_prob, compression_ratio en herhalingsvlaggen; coverage/margin-heuristieken voor sprekertoewijzing; overlap/uncertain_assignment; contextgaps; cosine-score en embeddingwaarschuwingen. Woordexperiment bewaart bovendien woordprobability en controleert woordtijdstempels. Deze signalen hebben verschillende betekenissen. No-speech is geen algemeen rumoercijfer; similarity is geen kans; geometrische confidence meet geen verstaanbaarheid. De audit heeft geen aanvullende model-API's bevraagd of kwaliteitsgrenzen gekalibreerd.

Voor een volgende fase zijn deze controles kansrijk:

1. **Technische integriteit:** decodeerbaarheid, verwachte samplecount, eindige/ordelijke tijden, bronhash en overeenkomende audio/transcriptduur. Technische fouten krijgen een concrete reden; zij zijn geen negatieve didactische beoordeling.
2. **Gesproken inhoud:** lege transcriptie onderscheiden van stilte en mislukte ASR; waarschuwingen verzamelen en tegen handmatig gecontroleerde moeilijke audio valideren. Eventuele clipping/energie-/ruiskenmerken zijn kandidaten, geen al bewezen afkapregels.
3. **Sprekerbetrouwbaarheid:** simultane overlap en speakerwisseling afzonderlijk behandelen; onbekende identiteit, lage dekking en onbruikbare embedding bewaren. Werkelijke cliplengte gebruiken.
4. **Rol en context:** onbekende rol of onvoldoende context kan beoordeling blokkeren zonder tekst te verwijderen. OTHER mag niet automatisch LEERLING worden.
5. **Beslisbaarheid per tijdsinterval:** conceptuele status `beoordeelbaar`, `niet_beoordeelbaar` of `nog_onbekend`, met reasoncodes en begin/eind. Hervat bij een later interval waarvan ook relevante context betrouwbaar is. Sla oorspronkelijke resultaten en uitsluitingsreden op.

Beoordeel toekomstige abstention met zowel foutmaten op behouden fragmenten als het percentage uitgesloten tijd/turns en verschillen tussen docent/leerlingen. Anders kan een systeem schijnbaar beter worden door vooral stille of moeilijk hoorbare leerlingen weg te laten. Ook een niet-beoordeelbare zone is een onderzoeksuitkomst en moet traceerbaar blijven. **Geen status of kwaliteitsgate geïmplementeerd.**

## 9. Reproduceerbaarheid en ontbrekende onderdelen

Een andere onderzoeker kan met deze bestanden enkele unitproeven en de tuningtabellen reproduceren. De volledige bron→JSON-route en oorspronkelijke kwaliteitsmetingen kunnen **niet** zelfstandig worden gereproduceerd.

Ontbrekend: audio/test-files/docentreferentie; echte transcript-/diarization-/processed-JSON; similarity-CSV's; volledige handmatige referenties; bronmetadata/downloadmanifest; zelfstandig aanwezige projectomgeving; complete dependencies voor notebooks/experimenten; modelcommit/checksums; hardware-/threadinstellingen; exacte ruwe speakeractiviteiten en revisies van gebruikte annotaties. Seeds/deterministische instellingen zijn niet vastgelegd. Geen modelspecificatie wordt als historische versiezekerheid aangenomen op basis van alleen een naam.

Aanwezige sterke punten: centrale projectrootpaden in scripts, configsnapshots, bronsegmenten in turns, bronpaden, expliciete experimentele roldrempel, redelijk onderscheid tussen identiteit en rol in productie, foutstop tussen scripts en unitproeven. Notebookpaden blijven cwd-afhankelijk. Persistente paden in JSON zijn niet automatisch overdraagbaar; docentstap biedt audiooverride. De runnerrelatieve docentreferentie wordt vanuit src geïnterpreteerd; documenteer dat bij gebruik vanaf een andere map.

Runtime wordt met wall-clock gemeten; model-loadtijd ligt bij ASR/diarizatie buiten de opgeslagen inference-runtime. Vergelijk geen verschillende soorten runtime alsof beide inclusief laden zijn. CPU-uitvoering is geconfigureerd; er is geen hardwarebenchmark uitgevoerd. FFmpeg staat op PATH in deze auditomgeving, maar er is geen model- of end-to-endconversiebenchmark gedaan.

`pip check`-conflict en afwijkende NumPy/dotenv-versies moeten eerst verklaard worden. Een herinstallatie/compatibiliteitstest van het requirementsbestand is niet uitgevoerd. Commentaar over CPU-wheelselectie en API-compatibiliteit is niet als onafhankelijk gevalideerd installatiebewijs gebruikt. Versies in requirements bewijzen geen werkelijk opgeloste environment.

## 10. Geprioriteerd verbeterplan

### Nu oplossen, voordat betrouwbare vervolgresultaten worden geclaimd

1. Referenties herstellen: T29-tekstverlies, GEEN/ONBEKEND-semantiek, overlapannotatie, lege finalreferentie en het `intelligible`-codeboek. Resultaat: ondubbelzinnige, versievaste annotaties op exacte audiofragmenten.
2. Audio/JSON-validatie: F03–F08 en F10. Resultaat: corruptie, onmogelijke tijden en onbruikbare embeddings geven expliciet onbekend/fout, zonder stellige rol.
3. Bron/configgebonden cache en effectieve batchingconfig (F01/F02). Resultaat: herhaalde run verwijst aantoonbaar naar dezelfde bron/modelinstellingen.
4. Sprekerinformatie en evaluatie: R01–R03/F11/F13. Bewaar ruwe modeltijdlijn en maak speakerwisseling/overlap onderscheid controleerbaar; presenteer de dekking alleen als dekking. Meet later echte DER/WER op geschikte referenties.
5. Herstel notebookpreflight, lever een gecontroleerde gegevensmanifest/omgeving en herstartcontrole. Verbeter mockresultaatvalidatie voordat een echte classifier erop wordt aangesloten.

### Later aanpakken, na herstel en een echte audiobaseline

Valideer roldrempel en clipduur op apart materiaal; controleer meerdere leerlingen, vergelijkbare stemmen, microfoonafstand, stilte en rumoer. Kalibreer kwaliteits- en abstentionbeleid met retentiegraad en foutmaten. Onderzoek eerst per fout of ASR, diarizatie, alignment of roltoewijzing verantwoordelijk is. Pas daarna wordt parameter-/modelvergelijking informatief.

### Optioneel

Schema-versienummers, atomische writes, expliciete manifests met relatieve paden, aanvullende CLI-preflight en geautomatiseerde notebookstartcontrole kunnen onderhoud en traceerbaarheid verbeteren. Zij vereisen geen herbouw van de architectuur. F14 heeft lagere prioriteit dan de hoofdroute.

**Buiten fase 1:** echte abstentionfunctionaliteit bouwen, nieuwe classificatiemethoden/indicatoren, modeltraining en volledige architectuurvernieuwing. Dit rapport adviseert onderzoek daarvoor; het voert dit niet uit.

## 11. Concepttekst voor het stageverslag

### Onderzoeksmethode

In fase 1 is een onafhankelijke technische en methodologische audit uitgevoerd op de aanwezige StudieStap-projectbestanden. Eerst is de gegevensstroom uit de code gereconstrueerd. Vervolgens zijn oorspronkelijke unitproeven uitgevoerd en zijn synthetische tegenvoorbeelden opgesteld om aannames over tijdstempels, sprekerkoppeling, cachehergebruik, audiobestandsintegriteit en roltoewijzing actief te weerleggen. Uitvoering en code-inspectie zijn afzonderlijk gerapporteerd. De oorspronkelijke bestanden zijn niet gewijzigd en er zijn geen externe modellen of audio gedownload.

### Gebruikte tests en resultaten

De 17 oorspronkelijke tests voor docentherkenning en orkestratie en de 51 tests voor de mockclassificatie slaagden. Van 32 aanvullende auditproeven bevestigden 9 de onderzochte eigenschap en weerlegden 23 een verwachte controle of aanname. Deze proeven zijn doelgericht geselecteerd en vormen geen representatieve schatting van de modelaccuracy. Alle 28 Python-bestanden en 8 aanwezige JSON-bestanden waren syntactisch geldig. Bij uitvoering van notebookcellen met een lege variabelenruimte kon één van zes notebooks volledig worden doorlopen; de overige notebooks stopten door ontbrekende gegevens of onvoldoende afhandeling daarvan.

De audit toonde onder andere aan dat verschillende audiobronnen dezelfde transcriptcache kunnen gebruiken, dat niet-eindige tijdstempels worden geaccepteerd, dat onbruikbare embeddings als OTHER kunnen worden geclassificeerd en dat een afgekapt WAV-bestand niet expliciet wordt afgewezen. De parser van een handmatige transcriptie verwijderde bovendien ongelabelde tekstregels. Een korte tweede spreker kon in de segmentkoppeling verdwijnen zonder onzekerheidswaarschuwing, hoewel de synthetische diarizatietijdlijn deze spreker wel bevatte. De gebruikte tuningmaat bleek een dekkingsmaat die false alarms buiten de referentiebeurten niet bestraft.

### Beperkingen

In de onderzochte checkout ontbraken audiobestanden, docentreferentieopnamen, echte ASR-hypothesen en ruwe diarizatietijdlijnen. Daarom zijn geen WER-, CER- of DER-metingen uitgevoerd en zijn opgeslagen historische scores niet opnieuw bevestigd. De stemherkenningsproeven gebruikten testdoubles om beslislogica te toetsen; zij bewijzen geen foutenpercentage van de embeddingmodellen. Sprekerannotaties zijn structureel gecontroleerd maar konden niet tegen audio worden geverifieerd.

### Aanbevolen vervolgstappen

De bestaande pipeline is geschikt om als experimentele basis verder te onderzoeken, mits validatie, referenties, cacheidentiteit en traceerbaarheid eerst worden hersteld. Daarna kan met een afzonderlijke, gecontroleerde audiovalidatieset worden vastgesteld welk deel van de fouten ontstaat in ASR, diarizatie, alignment of roltoewijzing. In een volgende fase kan een expliciete niet-beoordeelbaarstatus worden onderzocht. Daarbij moeten zowel fouten op behouden fragmenten als het aandeel uitgesloten fragmenten worden gerapporteerd, zodat kwaliteitswinst niet uitsluitend berust op het wegfilteren van moeilijke leerlingenspraak.
