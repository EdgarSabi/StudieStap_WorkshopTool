# StudieStap — onafhankelijke testvalidatie

**Fase 1, stap 2 · 9 oktober 2026 · Reviewer: Codex.** Uitsluitend validatie van de oorspronkelijke audittests; geen verbetering of heraudit van de pipeline. Repositorycommit `33cc8a10eb2aea0a161b387f08ce0192b46e89bc` plus bestaande werkboomwijzigingen. Nieuwe bestanden staan uitsluitend in `Validatie_fase1_stap2_2026-10-09/`.

## 1. Samenvatting

Beide audits bevatten reproduceerbare technische observaties, maar hun geslaagd/mislukt-tellingen zijn **geen maat voor pipelinekwaliteit**. Alle 32 ChatGPT-proeven hebben bij herhaling dezelfde booleaanse uitkomst (9 True, 23 False). Alle 22 Claude-randgevallen zijn uitgevoerd; de oorspronkelijke telling is 10 True en 12 False. De 17 src- en 51 classificatie-unit-tests slagen opnieuw. Testvaliditeit moet per onderzoeksvraag worden beoordeeld: een verkeerde verwachting kan een correct werkende functie laten “falen”, en een te zwakke assertion kan fouten missen.

De teruggevonden Claude-baselines maken de vijf WER/CER-berekeningen en vier segment-/turn-DER-berekeningen rekenkundig reproduceerbaar. Dat maakt ze nog geen onafhankelijke kwaliteitsmetingen. WER/CER gebruiken onvoldoende onafhankelijk onderbouwde referentietekst; DER gebruikt verwerkte sprekerlabels in plaats van ruwe pyannote-turns en een onvolledige overlapreferentie. De claim dat deze DER een gegarandeerde ondergrens is, is met een onafhankelijk tegenvoorbeeld weerlegd. Synthetische/ruis-ASR-experimenten zijn door ontbrekende exacte audio en generatie niet te verifiëren als experiment.

De oorspronkelijke ChatGPT-audit zegt dat audio/docentreferentie ontbreken, maar de eigen oorspronkelijke manifesten bevatten alle 13 MP3’s met hashes. Dat is een aantoonbare rapportagefout. Geen ASR-run uitvoeren is op zichzelf toegestaan binnen een offline audit; “audio ontbrak” is hier geen houdbare verklaring. Claude E1, E11, E13 en E16 hebben geen geldige verwachting voor de bedoelde normale route. Andere proeven tonen bruikbare beperkingen, zonder een modelnauwkeurigheid of incidentfrequentie aan te tonen.

## 2. Gecontroleerde bewijsbestanden

### Beschikbaarheid en herkomst

| Gevraagd pad | Vastgesteld |
|---|---|
| `Audit_fase1_2026-10-09/` | Aanwezig en leesbaar; origineel rapport, 32-testscript, JSON-uitvoer, inventaris, manifest, twee unittestlogs, dependencylog, integriteitscontrole en test/inventarisbijlage onderzocht. |
| `Data-analysis/Audit/` | Aanwezig en leesbaar; origineel auditrapport, edge/wer/synth-resultaten, alle zeven scripts, manifest en aanvullend omgevingsdocument onderzocht. |
| `Audit_bewijs/bewijspakket_claude.zip` | **Ontbreekt.** Geen fictieve alternatieve locatie gebruikt. |
| `Data-analysis/Audit/bewijspakket_claude.zip` | Afzonderlijk aangetroffen pakket. Omdat het naast de oorspronkelijke audit staat, onderzocht als later samengesteld bewijs; niet gelijkgesteld aan het gevraagde ontbrekende pad. |

Het zip bevat 34 bestanden. De README verklaart dat ASR-JSON, nb_hyp, stdout, resultaat-JSON en taakoutputs tijdens de audit geschreven zijn; het pakket zelf, commando-overzicht, instellingen en referentiehashes zijn later samengesteld. Deze historische status is een **herkomstverklaring**, geen cryptografisch bewezen tijdstip. De reconstructie vermeldt overschreven eerdere nb_hyp/WER-versies en een aangepaste DER-scriptversie. Een originele DER-uitvoerlog en shell-history ontbreken.

**Hashcontrole:** alle 102 vermeldingen in ChatGPT `manifest.json` en alle 117 in Claude `manifest_claude.csv` komen overeen met de huidige bestanden (219 checks, nul afwijkingen of ontbrekende bestanden). Alle 33 checks in zip `SHA256SUMS.txt` slagen. Pakketkopieën van vijf referenties, zeven scripts en drie resultaten zijn bytegelijk aan de werkboom. Gemeenschappelijke bronbestanden hebben dezelfde hashes; verschil tussen manifests betreft audit/IDEbestanden en notebookcheckpoints, geen verschillende pipelineversie. De 13 MP3’s zijn ook opgenomen in het ChatGPT-manifest.

SHA-256 bewijst bytegelijkheid met het vastgelegde manifest, niet dat een bestand historisch daadwerkelijk is uitgevoerd, niet dat annotaties onafhankelijk zijn en niet dat het manifest authentiek gedateerd is. Claude beschrijft het manifest als na de audit berekend. De broncommit alleen is onvoldoende: CSV’s en notebook 03 zijn gewijzigd ten opzichte van HEAD. Hier zijn steeds de gemanifesteerde werkboomversies gebruikt.

### Bewijsregistratie

| Nieuwe registratie | Inhoud |
|---|---|
| `manifest_checks.json` | Elk origineel manifestpad, verwachte en actuele SHA-256 en status. |
| `zip_checks.json` | Hash van de zip, alle leden en interne checksumvergelijking. |
| `before_hashes.json`, `unchanged_originals.json` | Hashsnapshot van oorspronkelijke audits, bron/notebook/experimentbestanden en lokale data; oorspronkelijke bestanden gecontroleerd op wijzigingen. |
| `environment.json`, `commands.json` | Interpreter, versies, commit, werkboomstatus en uitgevoerde opdrachten. |
| `chatgpt_herhaling.json/.log`, `claude_herhaling/edge_results.json`, `claude_edge.log` | Nieuwe technische herhalingen, gescheiden van originelen. |
| `wer_herberekend.json`, `wer_herberekening.log`, `der_herberekening.log` | Nieuwe berekeningen op opgeslagen hypothesen; geen nieuwe ASR/diarizatie. |
| `falsification_results.json`, `supplemental_results.json`, `notebook_herhaling.json`, `json_herhaling.log` | Nieuwe tegenvoorbeelden, metriek-/extractiecontrole en notebook/schemaherhaling. |
| `teruggevonden_bewijs/` | Geselecteerde kopieën uit zip. Bronzip blijft onveranderd; originele resultaatkopieën na berekening bytegelijk hersteld. |

Een aanwezige andere validatiemap is niet gelezen. Er zijn geen nieuwe validatieconclusies van een andere reviewer gebruikt. Aanvullende omgevings-/pakketdocumenten zijn gelezen voor herkomst, niet als onafhankelijke bevestiging van hun conclusies. Oorspronkelijke pipeline/audittests/referentiedata zijn niet gewijzigd. Geen modelconstructie, modeldownload, installatie, audioupload of drempelwijziging uitgevoerd.

## 3. Testmatrix

Oordelen gelden voor de genoemde **onderzoeksclaim**, niet voor het resultaatlabel in het oude JSON. GELDIG betekent dus niet noodzakelijk “software correct”; ook een correct ontworpen tegenvoorbeeld dat een fout aantoont kan geldig zijn. GEDEELTELIJK GELDIG betekent dat een smallere uitspraak behouden kan worden. Sommige rijen vermelden expliciet een ongeldige bredere interpretatie.

| Audit | Test-ID | Onderzoeksvraag | Type bewijs | Oordeel | Onderbouwing | Beperking |
|---|---|---|---|---|---|---|
| ChatGPT Work | T01 | Wordt opeenvolgende spraak onderscheiden van simultane spraak? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Opeenvolgend A 0–8/B 8–10 geeft overlap=True. Bewijst dat vlag geen simultaniteit meet. | Verwachte False is een semantische eis; implementatie documenteert tweede-sprekerdekking. |
| ChatGPT Work | T02 | Wordt ontbrekende diarizatie onzeker? | script + origineel JSON + offline herhaling | GELDIG | Zonder turns: speaker=None en uncertain_assignment=True; exacte conditie opnieuw bevestigd. | Eén geometrisch scenario; geen modeluitval onderzocht. |
| ChatGPT Work | T03 | Wordt volledige gelijktijdige spraak onzeker? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Volledige A/B-overlap geeft uncertain=True en overlap=True in opgeslagen uitvoer. | Predicate controleert alleen uncertain; V02 weerlegt dekking van korte overlap. |
| ChatGPT Work | T04 | Kan een korte tweede spreker onzichtbaar blijven? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | A 0–9/B 9–10 eindigt met alleen A en beide vlaggen False. | Correct tegenvoorbeeld voor informatieverlies; waarschuwing is geen vastgelegd contract. |
| ChatGPT Work | T05 | Worden onlogische tijden en confidence geweigerd? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Negatieve/omgekeerde tijden en confidence=3 worden daadwerkelijk geaccepteerd. | bad_model retourneert altijd False; verwachte ValidationError zou als geblokkeerd worden geregistreerd. |
| ChatGPT Work | T06 | Wordt verplicht tekstveld gecontroleerd? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Ontbrekend text wordt afgewezen; herhaling bevestigt dit. | Elke Exception geldt als geslaagd; test controleert niet specifiek ValidationError/text-locatie. |
| ChatGPT Work | T07 | Blijven onzekere segmenten apart en bronsegmenten behouden? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Merge-aantallen [2,1,1] en brontelling 4 kloppen. | V08: duplicatie van bron 0 passeert dezelfde predicate; exact-eenmaal behoud onvoldoende getest. |
| ChatGPT Work | T08 | Is preprocessing bestand tegen ongeordende segmenten? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Ongeordende input 5–6,0–1 wordt turn 5–1; gedrag gereproduceerd. | Tijdvolgorde is impliciete invoervoorwaarde; geen bewijs dat echte upstreamdata ongeordend is. |
| ChatGPT Work | T09 | Wordt lange stilte in context gemarkeerd? | script + origineel JSON + offline herhaling | GELDIG | 9 s stilte geeft context-onzeker na/voor bij grens 3 s. | Test van ingestelde heuristiek, geen validatie van pedagogische context. |
| ChatGPT Work | T10 | Wordt NaN-similarity als onbruikbaar behandeld? | script + origineel JSON + offline herhaling | GELDIG | Mockscore NaN geeft OTHER in plaats van onzeker; onbruikbare getallen niet afgevangen. | Geen echte NaN-embedding of incidentfrequentie aangetoond. |
| ChatGPT Work | T11 | Is een nulvector bewijs voor OTHER? | script + origineel JSON + offline herhaling | GELDIG | Twee nulvectoren geven cosine 0 en vervolgens OTHER. | Toetst helper + mockbeslissing; geen echte embeddingmeting. |
| ChatGPT Work | T12 | Wordt werkelijke cliplengte gecontroleerd? | script + origineel JSON + offline herhaling | GELDIG | Turnspan 2 s met 0,25 s beschikbare audio roept mock aan met 4000 samples en geeft DOCENT. | Bewijst clipduurcontrole op metadata; mockscore bewijst geen werkelijke valse docentherkenning. |
| ChatGPT Work | T13 | Is docentrol onafhankelijk van MAIN_SPEAKER? | script + origineel JSON + offline herhaling | GELDIG | OTHER_SPEAKER_1 + mockscore 0,8 geeft DOCENT. | Rolbeslisregel is onafhankelijk van spreektijdlabel; geen accuracymeting. |
| ChatGPT Work | T14 | Blijven meerdere leerlingidentiteiten afzonderlijk? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Drie raw-ID’s leveren drie friendly labels. | Assert controleert slechts aantal; geen injectiviteit, permutatiestabiliteit of downstreamidentiteiten. |
| ChatGPT Work | T15 | Hebben verschillende bronnen verschillende cachepaden? | script + origineel JSON + offline herhaling | GELDIG | Verschillende bronpaden/extensies met gelijke stem geven hetzelfde JSON-cachepad. | Padbotsing aangetoond; feitelijke verkeerde transcriptinhoud niet gemeten. |
| ChatGPT Work | T16 | Komen batchinginstellingen overeen met opgeslagen config? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Fake batching-call bevat alleen language/batch_size; opgeslagen config vermeldt beam/VAD/words. | Predicate controleert beam/VAD, niet alle opties of werkelijk modelgedrag; testdouble wel passend. |
| ChatGPT Work | T17 | Wordt herhalende tekst gemarkeerd? | script + origineel JSON + offline herhaling | GELDIG | Vaste herhaling krijgt possible_repetition_hallucination. | Test heuristiek; bewijst niet dat herhaling hallucinatie is. |
| ChatGPT Work | T18 | Kan WAV met 24-bit samples via conversie worden verwerkt? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | 24-bit PCM passeert to_wav en loader geeft unsupported sample width. | Formaat incompatibel; duidelijke fout is geen bewijs van stille datacorruptie. |
| ChatGPT Work | T19 | Wordt onverwachte sample rate correct doorgegeven door WAV-loader? | script + origineel JSON + offline herhaling | GELDIG | 48 kHz stereo wordt gelezen als sr=48000, shape=[2,48000]. | Nul-audio en alleen loader; geen resampling/modelkwaliteit. |
| ChatGPT Work | T20 | Wordt een gedeeltelijke WAV gedetecteerd? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Afgekapt WAV met header 16000 frames levert 28 samples zonder fout. | Predicate is hardcoded False; verwachte fout zou als geblokkeerd worden geregistreerd. |
| ChatGPT Work | T21 | Bestraft de bestaande score false alarms en extra speakers? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Scorer geeft 100% ondanks 99 s extra spraak en extra spreker. | Dit is conform bewust milde scorer; weerlegt algemene accuracy/DER, niet het dekkingcontract. |
| ChatGPT Work | T22 | Kan lege referentie veilig worden gescoord? | script + origineel JSON + offline herhaling | GELDIG | Lege GT en hypothese geven ZeroDivisionError. | Concrete grensgevalfout; geen historische tuningrun met lege GT bewezen. |
| ChatGPT Work | T23 | Dwingt status OK een bruikbaar resultaat af? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | OK met detected/evidence=None wordt geaccepteerd, tegen beschreven bruikbaar-paar-semantiek. | Hardcoded False en uitzonderingsregistratie niet geschikt voor toekomstige regressiecontrole. |
| ChatGPT Work | T24 | Weigert schema niet-eindige tijdstempels? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | NaN/Inf worden geaccepteerd en als null geschreven. | Hardcoded False; ontbreken eindigheidscontrole is bewezen, type-afwijzing bij een fix wordt geblokkeerd genoemd. |
| ChatGPT Work | T25 | Blijft een onbekend extra bronveld behouden? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | extra_marker wordt weggegooid bij modelconstructie. | Pydantic extra-ignore is ontwerpkeuze; eis alles behouden niet afgeleid uit schema. |
| ChatGPT Work | T26 | Blijven ontbrekende kwaliteitsvelden onbekend? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Ontbrekende kwaliteitsvelden worden False/defaults. | Geen verplichte provenance-eis vastgelegd; bewijst defaultgedrag, niet dat schone segmenten fout zijn. |
| ChatGPT Work | T27 | Worden niet-spraak en onbekende identiteit apart gehouden in scoring? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | GEEN/ONBEKEND worden als gewone speaker-ID geladen. | Semantisch risico overtuigend, maar annotatiecodeboek en audioverificatie ontbreken. |
| ChatGPT Work | T28 | Wordt een corrupte transcriptcache afgewezen? | script + origineel JSON + offline herhaling | GELDIG | Bestand met alleen { geldt als aanwezige cache. | Bestaan-only helper/CLI bewezen; geen historische cachecorruptie. |
| ChatGPT Work | T29 | Blijven ongelabelde tekstregels van de bestaande handmatige referentie behouden? | script + origineel JSON + offline herhaling | GELDIG | Originele manual-parser bewaart 5 van 9 niet-lege regels en verliest vier vervolgregels. | Tekststructuur bewijst verlies; inhoud niet opnieuw beluisterd. |
| ChatGPT Work | T30 | Is agreement vrij van de aanname MAIN=docent? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | MAIN + recognition OTHER wordt conflict in experimentele helper. | Scenario MAIN=leerling is logisch, maar helper documenteert eigen MAIN=docentheuristiek; productie niet geraakt. |
| ChatGPT Work | T31 | Volgt refinement de gedocumenteerde overlapratio? | script + origineel JSON + offline herhaling | GELDIG | AST-extractie originele pure functie: overlap 1/1 op kortste versus 1/10 op nieuwe segmentduur geeft None. | Bewijst documentatie/codeverschil; volledige refinement niet uitgevoerd. |
| ChatGPT Work | T32 | Blokkeren slechte ASR-signalen een stellige docentrol? | script + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Hoge mockscore geeft DOCENT ondanks twee ASR-quality_flags. | Automatische blokkade niet vastgelegd; slechte tekst betekent niet automatisch onherkenbare stem. |
| Claude Code | E1 | Docent (S0) spreekt 10 s, leerling (S1) 30 s: wie wordt MAIN_SPEAKER? | edge_tests.py + origineel JSON + offline herhaling | ONGELDIG | Verwachting docent=MAIN strijdt met expliciet spreektijdcontract; V01 bevestigt juiste rangschikking. | Geen geldige test van docentidentiteit. |
| Claude Code | E2 | Gelijke spreektijd (10 s/10 s), turns in omgekeerde volgorde aangeleverd | edge_tests.py + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Gelijke spreektijd: invoervolgorde beïnvloedt tie-label. | Onzekerheid of stabiele tie-break is ontwerpeis, geen bewezen persoonsverwisseling. |
| Claude Code | E3 | 4 sprekers met 25% spreektijd elk, default-config: main_speaker_uncertain? | edge_tests.py + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Default min_share=0 maakt flag False bij 25% hoofdspreker. | True wordt door test geëist zonder geldend configuratiecontract; toont defaultwerking. |
| Claude Code | E4 | Sprekerwissel BINNEN een segment (S0 0-4 s, S1 4-5 s), niemand praat tegelijk: overlap? | edge_tests.py + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | A 0–4/B 4–5 geeft overlap=True zonder simultaniteit. | Geometrie geldig; vlagcontract is tweede-sprekerdekking. |
| Claude Code | E5 | Echt gelijktijdig praten (S1 3 s binnen S0) | edge_tests.py + origineel JSON + offline herhaling | GELDIG | 3 s echte overlap binnen 5 s geeft overlap=True. | Geen bewijs dat kortere overlap wordt gevonden (V02). |
| Claude Code | E6 | ASR-segment zonder enige diarization-spraak | edge_tests.py + origineel JSON + offline herhaling | GELDIG | Geen tijdsnijding geeft None en uncertain=True. | Pure Python-logica, geen diarizatiemodeltest. |
| Claude Code | E7 | Slechts 20% van segment door diarization gedekt (rest onbekend) | edge_tests.py + origineel JSON + offline herhaling | GELDIG | 20% dekking geeft confidence=1 maar uncertain=True. | Confidence is gedocumenteerde share; audit mag dit niet als onterechte zekere toewijzing framen. |
| Claude Code | E7b | 60/40 verdeling S0/S1 binnen een segment | edge_tests.py + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | 60/40 geeft confidence=0,6 en uncertain=False. | rec(..., True) bevat geen assertion; resultaat is observatie. |
| Claude Code | E8 | Segment met end < start | edge_tests.py + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Omgekeerde tijden geaccepteerd; numeriek gebrek bewezen. | Elke uitzondering zou als correcte afwijzing gelden. |
| Claude Code | E9 | JSON met typfout in veldnaam / onbekend veld | edge_tests.py + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Typfoutveld en extra top-levelveld worden genegeerd. | Extra-ignore is toegestaan schemaontwerp; generieke except kan verkeerde oorzaak maskeren. |
| Claude Code | E10 | Segment zonder text-veld | edge_tests.py + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Ontbrekende text afgewezen. | Vangt iedere Exception; test valideert niet de afwijzingsreden. |
| Claude Code | E11 | Segment met willekeurig speaker-label | edge_tests.py + origineel JSON + offline herhaling | ONGELDIG | Vrij string-speakerlabel wordt als fout gezien. | Raw labels/labels A zijn geldig in dit ontwerp; gesloten vocabulaire is niet het contract. |
| Claude Code | E12 | Segmenten A(0-2), A(1-3, overlapt in tijd), A(10-12): turns? | edge_tests.py + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Overlappende A-segmenten en grote gap leveren twee turns. | Aantal alleen; geen source- of spancontrole en geen echte simultane sprekers. |
| Claude Code | E13 | Zelfde friendly label, andere speaker_raw | edge_tests.py + origineel JSON + offline herhaling | ONGELDIG | Invoer gebruikt één friendly label voor twee verschillende raw-ID’s en eist splitsing. | Niet mogelijk via normale injectieve build_label_map; audit erkent dit zelf. |
| Claude Code | E14 | Merged turn: span vs. werkelijke spraak (docent_recognition min-duur check gebruikt end-start) | edge_tests.py + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Gemergde turn: span 2,5 s, segmentduursom 1,1 s. | rec(...,False) zonder embeddingaanroep; span is geen bewezen verkeerde rol, duur som telt stilte binnen segment mee. |
| Claude Code | E15-8000Hz-2ch-16bit | WAV-loader met afwijkend formaat | edge_tests.py + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Loader laadt 8 kHz stereo. | Elke Exception krijgt ok=True; duidelijke versus onverwachte fout niet onderscheiden. |
| Claude Code | E15-44100Hz-1ch-16bit | WAV-loader met afwijkend formaat | edge_tests.py + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | Loader laadt 44,1 kHz mono. | Gelijk permissief testontwerp als overige E15-formaten; geen amplitude/samples-inhoudcheck. |
| Claude Code | E15-16000Hz-1ch-24bit | WAV-loader met afwijkend formaat | edge_tests.py + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | 24-bit wordt expliciet geweigerd. | Passed betekent afwijzing acceptabel, niet dat formaat ondersteund wordt. |
| Claude Code | E15-16000Hz-1ch-8bit | WAV-loader met afwijkend formaat | edge_tests.py + origineel JSON + offline herhaling | GEDEELTELIJK GELDIG | 8-bit wordt expliciet geweigerd. | Passed betekent afwijzing acceptabel, niet dat formaat ondersteund wordt. |
| Claude Code | E16 | to_wav() met 8 kHz stereo WAV (docstring: 'convert non-wav inputs') | edge_tests.py + origineel JSON + offline herhaling | ONGELDIG | Test eist WAV-conversie, terwijl to_wav alleen non-WAV conversie belooft. | Geen backendrun; 8 kHz/stereo op zich geen bewezen pipelinefout. |
| Claude Code | E17 | Twee verschillende bestanden met dezelfde naam (map A: 1 s, map B: 2 s) -> WAV-cache | edge_tests.py + origineel JSON + offline herhaling | GELDIG | 1 s/2 s mp3 met dezelfde naam hergebruiken 1 s WAV; lokaal herhaald. | Geen controls op ffmpeg-returncodes in generatie; geslaagde output bevestigt hier invoerduur. |
| Claude Code | E18 | transcription.output_path_for: zelfde bestandsnaam in raw/ en test-files/ | edge_tests.py + origineel JSON + offline herhaling | GELDIG | raw/x en test/x geven gelijk transcriptpad. | Padbotsing, geen accuracymeting. |
| Beide | UNIT-SRC | Werken rolbeslisregels en runnerorkestratie? | originele tests/logs + herhaling 17/17 | GELDIG | Mocks passen bij unitniveau; metadata, onzekerheid, rolbeslissingen en force-doorvoer worden getest. | Geen echte subprocessketen/modelkwaliteit; oorspronkelijke verwachting is ontwerpregel. |
| Beide | UNIT-CLASS | Werken datamodellen, context, prompt en mockintegratie? | originele tests/logs + herhaling 51/51 | GELDIG | Technische verwachtingen bevestigd in juiste cwd. | Geen didactische validiteit; classifier is mock en fixtures zijn synthetisch. |
| ChatGPT Work | INVENTARIS-AUDIO | Ontbraken audio en docentreferentie? | manifest + inventory + inventarisbijlage | ONGELDIG | Eigen oorspronkelijke bewijs bevat 13 MP3’s inclusief testdocent; huidige hashes gelijk. | Rapportagefout; geen modelrun alsnog uitgevoerd. |
| ChatGPT Work | SYNTAX | Zijn 28 Python en 8 oorspronkelijke JSON syntactisch geldig? | inventory.json + broninspectie | GEDEELTELIJK GELDIG | Geldigheidsscan interpreteert parsing correct; schema en runtime zijn afzonderlijke vragen. | Geen uitgebreide nieuwe syntaxscan/modeluitvoering; telling heeft oorspronkelijk scope. |
| ChatGPT Work | DEPENDENCIES | Zijn dependencies consistent? | dependency_check + metadata | GEDEELTELIJK GELDIG | pip-check conflict en versiedrift zijn controleerbaar; geen bewijs dat alle modellen falen. | Geen volledige nieuwe import-/inferencecontrole; oorspronkelijke dependencies niet gewijzigd. |
| Claude Code | T2-ASR | Zijn vijf baselines uitgevoerd en identiek aan eerdere uitvoer? | teruggevonden asr/*.json + asr_log + notebooks | GEDEELTELIJK GELDIG | Opgeslagen outputs en kleine uitvoeringslog ondersteunen baseline; geen nieuwe ASR-run. | Modelrevisie/hash niet destijds vastgelegd; matching grenzen/tekst is smaller dan totale gelijkheid. |
| Claude Code | T3-WER/CER | Meten WER/CER transcriptienauwkeurigheid? | wer_eval.py + vijf ASR/CSV + V05 | GEDEELTELIJK GELDIG | Aritmetiek exact gerepliceerd, maar referentieonafhankelijkheid onvoldoende aangetoond. | Voor accuracyclaim ONGELDIG; als tekstafstand GELDIG. WER=0 bewijst op zichzelf geen circulariteit. |
| Claude Code | T4-DER | Meet gerapporteerde DER het diarizatiemodel? | der.py + nb_hyp + CSV + nieuw DER-log | GEDEELTELIJK GELDIG | Alle getallen reproduceerbaar voor gekozen segment-/turnhypothese en UEM. | Geen raw-DER; overlapreferentie onvolledig; ondergrensclaim ONGELDIG (V03), identieke intervals overschrijven (V04). |
| Claude Code | T6-SILENCE | Werkt VAD en is lege uitvoer correct afgehandeld? | synth_results + run_synth.py | NIET TE VERIFIËREN | Log meldt nul segmenten voor stilte/witte ruis; audio/generatie ontbreken. | Nul segmenten bewijst niet specifiek VAD-effect, geen VAD-uit ablatietest; leeg kan juist zijn. |
| Claude Code | T7-NOISE | Hoe verandert ASR bij twee roze-ruiscondities? | synth_results + run_synth.py | NIET TE VERIFIËREN | Historische WER-afstanden 0,229/0,441 opgeslagen; kwaliteitflags beschreven. | Geen wav/generatiescript/seed/RMS; SNR niet controleerbaar en schone ASR is geen onafhankelijke waarheid. |
| Claude Code | T8-8KHZ | Is lagere samplefrequentie robuust? | synth_results + run_synth.py | NIET TE VERIFIËREN | Eén historisch verschil 0,102 opgeslagen. | Invoeraudio/conversie ontbreekt; acceptabel heeft geen vooraf vastgelegd criterium. |
| Claude Code | SYNTH-SILENCE-PREFIX | Blijven tijden correct na 15 s stilte? | synth_results | NIET TE VERIFIËREN | Eerste start 14,8 s; WER tegen volledige t2-referentie 0,508. | Audio ontbreekt; waarschijnlijk verkort spraakfragment maar niet bewezen. Gelijke inhoud/duur niet vastgesteld. |
| Claude Code | T9-OVERLAP | Zijn 16 van 22 vlaggen fout? | nb_hyp + GT + aanvullende intervaltelling | GEDEELTELIJK GELDIG | TP/FP/FN opnieuw 1/4/1,1/2/3,4/10/1; dus 16/22 niet positief volgens rijproxy. | Geen definitieve simultaniteitswaarheid; testaudio7 is processed-turnniveau (26 turns), overige tabellen segmentniveau. |
| Claude Code | T10-ROL | Wat is docentrecall op testaudio7? | notebook05 + GT + nieuwe duursom | GEDEELTELIJK GELDIG | 31 s DOCENT,6 s OTHER,6 s ONZEKER op docent; leerling 6/2/5 s; sommen gerepliceerd. | 31/37 is secondenrecall onder besliste cases, geen 37 onafhankelijke beslissingen; in-sample/één fragment. |
| Claude Code | T11-JSON | Zijn baseline-JSON schema-valide en tijden consistent? | validate_json.py + vijf JSON + nieuwe log | GEDEELTELIJK GELDIG | Schema valide; eindovershoot en gehele seconden reproduceerbaar; 5 absolute paden, niet 4. | Geen diarization-blok hoort bij ASR-stadium; checker waarschuwt ook toegestane toestanden en mist NaN/negatieve start. |
| Claude Code | F5-QUALITY | Zijn qualitygetallen onafhankelijk per segment? | baseline-JSON + lokale faster-whisper-bron | GEDEELTELIJK GELDIG | Vensterwaarden worden hergebruikt in niet-batched bibliotheekpad; losse waarden zijn geen per-woordscore. | Weinig unieke waarden alleen is geen bewijs; tekstherhalingsflag is juist per segment en bibliotheekclaim niet universeel. |
| Beide | NB01 | Zijn notebookberekeningen herhaalbaar? | oorspronkelijke bron/output + nieuwe exec-herhaling | GEDEELTELIJK GELDIG | Huidige uitvoering: cel 5 FileNotFoundError. | Verse namespace, gedeeld proces; geen schone Jupyter-kernel. 06 leest historische tuningresultaten, genereert ze niet. |
| Beide | NB02 | Zijn notebookberekeningen herhaalbaar? | oorspronkelijke bron/output + nieuwe exec-herhaling | GEDEELTELIJK GELDIG | Huidige uitvoering: cel 6 IndexError. | Verse namespace, gedeeld proces; geen schone Jupyter-kernel. 06 leest historische tuningresultaten, genereert ze niet. |
| Beide | NB03 | Zijn notebookberekeningen herhaalbaar? | oorspronkelijke bron/output + nieuwe exec-herhaling | GEDEELTELIJK GELDIG | Huidige uitvoering: cel 12 FileNotFoundError. | Verse namespace, gedeeld proces; geen schone Jupyter-kernel. 06 leest historische tuningresultaten, genereert ze niet. |
| Beide | NB04 | Zijn notebookberekeningen herhaalbaar? | oorspronkelijke bron/output + nieuwe exec-herhaling | GEDEELTELIJK GELDIG | Huidige uitvoering: cel 7 FileNotFoundError. | Verse namespace, gedeeld proces; geen schone Jupyter-kernel. 06 leest historische tuningresultaten, genereert ze niet. |
| Beide | NB05 | Zijn notebookberekeningen herhaalbaar? | oorspronkelijke bron/output + nieuwe exec-herhaling | GEDEELTELIJK GELDIG | Huidige uitvoering: cel 3 FileNotFoundError. | Verse namespace, gedeeld proces; geen schone Jupyter-kernel. 06 leest historische tuningresultaten, genereert ze niet. |
| Beide | NB06 | Zijn notebookberekeningen herhaalbaar? | oorspronkelijke bron/output + nieuwe exec-herhaling | GEDEELTELIJK GELDIG | Huidige uitvoering: alle 10 niet-lege codecellen voltooid. | Verse namespace, gedeeld proces; geen schone Jupyter-kernel. 06 leest historische tuningresultaten, genereert ze niet. |

## 4. Geldige tests

Behoud de unit-tests als bewijs van de geteste regels onder mocks: onzekerheid/te korte turn/None-score, metadata, behoud van input en runner-force-doorvoer. De classifierproeven testen een mock; zij bewijzen geen inhoudelijke classificatiekwaliteit. Verwachtingen volgen hier uit beschreven regels en vaste fixtures, niet uit de gemeten uitvoer.

Sterke concrete observaties zijn T10–T13 (onbruikbare scores, clipduur en afzonderlijke rolbeslissing), T15/T28/E17/E18 (cachegedrag), T19 (WAV-loader sample rate/shape), T22 (lege referentie), T29 (parserverlies) en T31 (documentatie/codeverschil). Hun conclusies blijven begrensd tot de werkelijk uitgevoerde functie en invoer. Cacheproblemen zijn aangetoonde software-/provenanceproblemen; geen bewijs dat historische kwaliteitsmetingen daadwerkelijk uit een verkeerde cache kwamen.

T29 heeft onafhankelijke tekstuele grondslag: het inputbestand heeft negen niet-lege regels, vier zijn gesproken vervolgregels zonder prefix. De parser verwijdert die. Dit bewijs vereist geen nieuwe spraakherkenning. T31 gebruikt de oorspronkelijke functie via AST, waardoor een modelimport wordt vermeden; het is een correcte controle van de pure functie, geen volledige refinementtest.

## 5. Gedeeltelijk geldige tests

### Testimplementaties en gewenste eigenschappen

ChatGPT T05/T20/T23/T24 zijn krachtige eenmalige probes, maar onvoldoende als automatisch regressietestinstrument: zij retourneren altijd False nadat constructie/laden lukt. Bij een gewenste ValidationError of corrupte-audiofout registreert de algemene wrapper `geslaagd=None` en “Uitvoering geblokkeerd”, in plaats van een geslaagde afwijzing. T06 en Claude E8–E10 vangen juist iedere Exception: een onverwachte import-/I/O-/TypeError kan ten onrechte de verwachte schema-afwijzing bevestigen. De opgeslagen concrete uitkomsten blijven controleerbaar; de testharness is methodologisch te grof.

T03 controleert alleen uncertain, terwijl de beschreven verwachting ook overlap bevat. T14 controleert slechts de grootte van de mapping. T16 controleert beam/VAD en de opgeslagen call maakt de ontbrekende overige opties zichtbaar; “alle parameters getest” is breder dan de assertion. T07 controleert merges en totaal aantal bronnen; V08 toont dat duplicaten/verloren bronidentiteiten onopgemerkt blijven. Claude E7b is altijd True en E14 altijd False: dit zijn observaties, geen objectieve pass/fail-tests. E15 geeft iedere Exception True; formaatweigering en onverwachte fout zijn niet onderscheiden.

T08 bewijst falen van ongeordende invoer, maar preprocessing loopt expliciet in tijdvolgorde. Een upstream-sorteergarantie kan het scenario in de normale pipeline uitsluiten. De gepaste conclusie is een onbeschermde invoervoorwaarde; niet dat bestaande echte transcripties onjuist zijn. T25/T26/E9 tonen defaults/extra-ignore. Zonder schemaspecificatie zijn dit ontwerpkeuzes en provenance-risico’s. T32 maakt ontbrekende koppeling tussen ASR-flags en rolbeslissing zichtbaar, maar tekstonzekerheid impliceert niet automatisch onbruikbare stemidentiteit.

### WER/CER: correcte afstand, onvoldoende onafhankelijke accuracy

`wer_eval.py` gebruikt jiwer `process_words`/`process_characters`; normalisatie is lowercase, niet-woordtekens naar spatie, apostrof behouden, witruimte samenvoegen. Referentie is CSV-transcript in rijvolgorde (GEEN uitgesloten); hypothese is alle ASR-segmenttekst. Een onafhankelijk geschreven dynamisch edit-distance-algoritme geeft exact dezelfde WER/CER als jiwer. Dit bevestigt de rekenkern zonder verwachte waarden uit dezelfde te toetsen metriek te kopiëren.

| Fragment | Referentiewoorden | Woordedits | WER | CER |
|---|---:|---:|---:|---:|
| 1 | 62 | 2 | 0,032258 | 0,035256 |
| 2 | 118 | 0 | 0 | 0 |
| 4 | 420 | 0 | 0 | 0 |
| 5 | 154 | 19 | 0,123377 | 0,099719 |
| 7 | 196 | 6 | 0,030612 | 0,021516 |

Dit zijn **nieuwe herberekeningen op teruggevonden oude ASR**, geen nieuwe modelmetingen. Dezelfde normalisatie op beide kanten is consistent voor deze tekstafstand, maar verwijdert interpunctie/case en maakt bijvoorbeeld koppeltekens tot woordgrenzen; dit moet bij elke vergelijking expliciet blijven. ONBEKEND-tekst wordt voor WER niet gemaskeerd; `intelligible=nee` wordt genegeerd, ook bij alle rijen van audio2/7. De bedoeling daarvan is zonder annotatiecodeboek ambigu.

De tuning-README zegt expliciet: “startpunt voorgevuld uit de Whisper-segmenten, daarna handmatig gecontroleerd en aangepast”. Voorinvulling verhoogt het risico op anchoring en afhankelijkheid. Het bewijs toont **niet** dat de aangekondigde handmatige controle nooit plaatsvond. Zero-WER op twee fragmenten of gelijke segmentgrenzen bewijst op zichzelf geen ondeugdelijke ground truth. De verdedigbare conclusie is onvoldoende aangetoonde onafhankelijkheid, niet bewezen fraude/geen handmatige controle. Er ontbreken controleprotocollen, correctielogs, tweede annotator en luisterverificatie in deze validatie.

V05 vindt gelijke intervallen binnen 0,06 s: 6/12,19/19,87/87,12/20,38/38 voor 1/2/4/5/7. Audio1-referentie loopt tot 30,6 s versus audiometadata 29,9766; audio5 tot 46,1 versus 45,9896. Audio7-ref stopt op 62 s terwijl ASR-duur 64 s is. WER-script filtert niet op tijd/UEM: dit zijn additional intervalbeperkingen. Audiohashes zijn wel controleerbaar, maar de transcript-/annotatie-inhoud is niet tegen audio gevalideerd. Sprekerannotaties kunnen handmatig onafhankelijk zijn van tekst, ook als tijden/woorden vooringevuld waren; tekstafhankelijkheid maakt niet automatisch elk speakerlabel ongeldig.

### DER: correct op de opgegeven representatie, geen zuivere modelkwaliteit

Claude `der.py` gebruikt echte `DiarizationErrorRate` met optimale speaker-matching, collar 0/0,25 en `skip_overlap=False/True`. `NONE` wordt bij ontbrekend hypotheselabel een gewone hypothese-identiteit; dit kan confusion opleveren en is een expliciete keuze, geen “geen spraak”. GEEN/ONBEKEND/leeg worden uit referentie én UEM verwijderd. Daardoor wordt ook stilte/applaus met GEEN niet als false-alarmgebied geëvalueerd. Die uitsluiting is verdedigbaar voor een begrensde score, maar onderdrukt false alarms als men volledige audio-DER claimt. UEM is 0..laatste ref-einde, behalve audio1 4,1..24,5. Geen beperking tot audio-duur en geen validatie van lege referentie/total=0 aanwezig.

| Fragment | DER collar 0, overlap inbegrepen | DER collar 0,25, overlap inbegrepen | Componenten collar 0: miss / FA / confusion |
|---|---:|---:|---|
| 2 | 0,233 | 0,218 | 0 / 0 / 0,233 |
| 5 | 0,424 | 0,384 | 0,021 / 0,027 / 0,375 |
| 7 | 0,177 | 0,162 | 0 / 0 / 0,177 |
| 1, alleen slice | 0,354 | 0,320 | 0,244 / 0,007 / 0,103 |

Alle rapportcijfers zijn uit de aanwezige referentie/hypothese reproduceerbaar. Kleine afrondingsverschillen in de som van componenten komen door afronding. De hypothese is **vijf notebookrijen voor audio1, 19 ASR-segmentrijen voor audio2, 20 voor audio5, 26 processed turns voor audio7**. Audio7 is dus geen ruwe ASR-segmentset van 38 en zeker geen raw-pyannote-output. De labels zijn reeds door Pythonalignment/preprocessing gevormd. Modelleringseffect, ASR-grenzen en verwerking zijn vermengd.

Referentie `overlap=ja` wordt niet door `ref_ann` omgezet in twee sprekers. Alleen daadwerkelijk afzonderlijke overlappende CSV-intervallen vormen overlap; zonder tweede ID/tijdspan ontbreekt dat bewijs. V04 toont bovendien overschrijven van de eerste annotatie als twee sprekers exact hetzelfde interval krijgen (default track). Dit is een concrete fout in de evaluatie-implementatie voor dat randgeval; geen claim dat iedere huidige CSV daardoor getroffen is. `skip_overlap=True` maakt voor audio2/5/7 nu geen verschil omdat de geconstrueerde referentie daar geen multi-track-overlap levert. Voor audio1 verandert 0,25-collar-DER naar 0,172; er bestaat daar wel geconstrueerde overlap. Een veronderstelde biasrichting is zonder volledige onafhankelijke referentie onbekend.

### Overlap, confidence en rolpercentages

T01/E4 testen Pythonkoppeling, niet pyannote. Eén winnaar per tekstsegment en een runner-up-drempel verbergen korte tweede sprekers (T04) en verwarren opeenvolgende activiteit met simultaniteit. V02 toont ook gemiste echte overlap van 1 s op 10 s. `speaker_confidence` is volgens het broncommentaar een aandeel toegewezen spraaktijd, geen kans. E7 geeft confidence=1 bij 20% dekking **maar uncertain=True**. De claim dat deze test een zeker verkeerd label bewijst is niet gerechtvaardigd.

De onafhankelijke intervaltelling repliceert Claude T9 (t2 TP1/FP4/FN1, t5 TP1/FP2/FN3, t7 TP4/FP10/FN1). “16/22 vals” betekent hier: geen positieve tijdsnijding met een gehele GT-rij waarop overlap=ja staat. Dat is een grove proxy, niet beluisterde framewaarheid. Eén gelijktijdig moment maakt een hele rij positief; ongemarkeerde simultaniteit lijkt false positive. Ontbrekende gelijktijdige tweede tracks maken een nauwkeurige overlap-evaluatie onmogelijk. Gebruik deze cijfers niet als definitieve overlap-precisie.

T10-duursommen zijn gerepliceerd. Voor docent: 31 s DOCENT,6 s OTHER,6 s ONZEKER; voor leerling: 6 s OTHER,2 s DOCENT,5 s ONZEKER. `31/37=83,8%` is **docentrecall in seconden na uitsluiting van onzeker**, geen 37 onafhankelijke beslissingen/accuracy. Inclusief onzeker is correct herkende docenttijd 31/43=72,1%; beslisdekking voor docent is 37/43=86,0%. Dit zijn aanvullende afleidingen van dezelfde secundaire gegevens, geen onafhankelijke performance. Samples binnen één opname/personen zijn gecorreleerd. Drempel 0,35 is volgens experimentele bronbeschrijving op dezelfde beperkte chunkset bekeken; geen onafhankelijke testset of onafhankelijke drempelvalidatie. Docentidentiteit en diarizatie-ID blijven afzonderlijke vragen.

### Notebook- en JSON-controles

ChatGPT voerde cellen uit met `exec` en een nieuwe variabelenruimte per notebook. Dit is meer dan opgeslagen output lezen en ondersteunt de foutlocaties, maar is **geen schone Jupyter-kernel**: imports blijven in gedeeld proces, bare expressions/display-protocol en widgets zijn niet volledig uitgevoerd als notebook. Deze validatie herhaalt precies dat begrensde model. 01–05 stoppen zoals geregistreerd, 06 doorloopt 10 codecellen. 06 leest bestaande tuning-JSON; dit reproduceert tabellen, niet pyannote-tuning.

Claude las voor relevante modelcijfers opgeslagen HTML-uitvoer. V09 bevestigt exact dat `nb_hyp.json` uit de huidige notebooktabellen wordt gereconstrueerd. Dat bewijst extractie en snapshotkoppeling, niet onderliggende modelruns. Out-of-order execution counts (04/05/06) bewijzen historische uitvoering in andere volgorde, niet automatisch incorrecte uitkomsten: 06 loopt nu in bronvolgorde wel door. Door ontbrekende brondata blijft 04 niet volledig controleerbaar.

`validate_json.py` accepteert vijf baseline-JSON’s. Het signaleert overshoot in audio1 (30,56 >29,9766), gehele-seconden grenzen in audio2/7 en **vijf** absolute paden (rapport T11 zegt vier). Een absoluut pad is portabiliteitsrisico, geen schemafout. Het ontbrekende diarization-blok is normaal in ASR-stap 1. Een overlap tussen ASR-segmenten is niet automatisch onmogelijk; de checker markeert het zonder codeboek. Negative starts/eindigheid ontbreken in de checker, en model exceptions stoppen de gehele batch. De checklist is dus niet een complete schema-/semantische validator.

## 6. Ongeldige tests

**Claude E1:** verwacht dat minder sprekende docent MAIN blijft. `build_label_map` zegt expliciet langstsprekende identiteit en geen docentidentificatie; V01 toont correcte output. Geen softwarefout aangetoond.

**Claude E11:** verwacht gesloten speaker-vocabulaire. De modellen accepteren raw-ID’s en vrije strings; de verwerking gebruikt A/andere raw labels bij tests. Zonder expliciete schema-eis is afwijzing van “Docent” niet het onafhankelijke oracle.

**Claude E13:** construeert botsende friendly labels voor twee raw-ID’s, hoewel normale labelmapping injectief is. Dit kan een defensieve test voor handmatige beschadigde invoer zijn, maar is geen bewijs van verlies op de normale route. De oorspronkelijke audit erkent het onrealistische scenario; neem de FAIL niet als pipelinefout over.

**Claude E16:** verwacht omzetting van een reeds WAV-bestand terwijl de docstring zegt “convert non-wav inputs”. V06 bevestigt contractueel padgedrag. Het 24-bit formaatprobleem uit T18 is een afzonderlijke combinatie loader/to_wav; geen bewijs dat 8 kHz/stereo faalt bij pyannote.

**Ongeldige interpretaties:** WER/CER als echte onafhankelijke transcriptienauwkeurigheid; verwerkte DER als zuivere diarizatiemodelkwaliteit; DER als bewezen ondergrens; 31/37 als 37 onafhankelijke docentbeslissingen; T6 als causaal bewezen VAD-effect zonder ablatietest; “audio ontbreekt” in ChatGPT tegen eigen manifest. Twee audits die dezelfde interpretatie geven vormen geen onafhankelijk empirisch bewijs.

## 7. Niet-verifieerbare tests

De zes Claude-synthetische ASR-bestanden (stilte, witte ruis, twee roze-ruisbestanden, 8 kHz, stilteprefix) zitten niet in repo/zip. `run_synth.py` **leest** bestaande wav’s maar genereert ze niet. Originele generatieopdrachten, seed, amplitudes, exact spraakinterval, clippingcontrole en gemeten signaal-/ruis-RMS ontbreken. Er zijn geen nieuwe bestanden gereconstrueerd die dezelfde historische test zouden suggereren. SNR ≈+8/−5 dB is niet reproduceerbaar vastgesteld. Een signaal-ruisclaim vergt een precieze meetdefinitie en daadwerkelijk gebruikte signalen; die ontbreken.

Silence/white noise: opgeslagen nul-segment-uitvoer is plausibel maar bewijst geen correct functioneren op echte zwakke spraak. Er zijn geen bekende positieve spraakreferenties in die condities, geen VAD-uitcontrole en geen false-negative-analyse. “Geen spraak” kan een geldige uitkomst zijn; een ontbrekende expliciete status is een gewenst kwaliteitsontwerp, geen uit deze proeven bewezen misclassificatie.

Pink-noise/8kHz: script gebruikt de CSV-transcriptie van schone testaudio2 als ref; het rapport noemt afstand t.o.v. schone run. Voor t2 zijn genormaliseerde CSV en schone ASR byte-inhoudelijk equivalent qua tekst, zodat de tekstafstanden hetzelfde zijn. Onafhankelijke woordcorrectheid ontbreekt. De prefixvariant heeft 9 segmenten tegen 19 schoon en score 0,508; zonder generatie/audio kan niet worden bepaald of het hele fragment is meegenomen. Verwijderd of verkort spraakmateriaal zou de WER onterecht verhogen. Tijdstart 14,8 s bewijst niet dat alle latere woordgrenzen juist zijn.

Raw-diarizatie, echte embeddings, volledige originele processed-JSON’s, similarity-CSV’s en een onafhankelijke speakeractiviteitsreferentie ontbreken. Daarom kan deze validatie geen raw-DER, identificatie-accuracy, effect van ruis op pyannote of onafhankelijk modelvoordeel herhalen. Oorspronkelijke ASR-inference is evenmin opnieuw uitgevoerd: nieuwe grote modelruns zijn expliciet buiten scope. Teruggevonden ASR/taaklogs maken de bewering beter gedocumenteerd, maar bevestigen geen cross-machine-reproduceerbaarheid of historisch vaste modelrevisie.

## 8. Tegenvoorbeelden en falsificatie

### V01 — Is MAIN een docentlabel?

Hypothese: Claude E1 verwacht docent=MAIN, maar functiecontract is spreektijdrang.

Invoer: `[[0, 10, "docent"], [10, 40, "leerling"]]`. Onafhankelijke verwachting: `{"docent": "OTHER_SPEAKER_1", "leerling": "MAIN_SPEAKER"}`.

Gemeten uitvoer staat volledig in `falsification_results.json`, item V01. Conclusie: E1 toont de gedocumenteerde rangschikking; geen fout in rolherkenning. Beperking: Rollen in synthetische invoer bekend; geen embeddings.

### V02 — Verbergt alignment korte simultane spraak?

Hypothese: Ook echte overlap kan onder de vlagdrempel verdwijnen.

Invoer: `[[0, 10, "A"], [9, 10, "B"]]`. Onafhankelijke verwachting: `{"overlap": true, "second_speaker_activity_seconds": 1}`.

Gemeten uitvoer staat volledig in `falsification_results.json`, item V02. Conclusie: Werkelijke overlap is 1 s, maar vlag is False. T03/E5 generaliseren niet naar alle overlap. Beperking: Pure geometrie; geen modeltest.

### V03 — Is segment-DER altijd een ondergrens voor raw-DER?

Hypothese: Er is geen gegarandeerde ordening.

Invoer: `{"ref": "A 0–1; B 1–2", "raw_bad": "X+Y 0–1, daarna niets", "segment": "X 0–2"}`. Onafhankelijke verwachting: `{"raw_bad_der": 1.0, "raw_good_der": 0.0, "same_segment_der": 0.5}`.

Gemeten uitvoer staat volledig in `falsification_results.json`, item V03. Conclusie: Segmentrepresentatie kan DER verhogen of verlagen; ondergrensclaim weerlegd. Beperking: Synthetisch; toont geen richting van bias in echte fragmenten.

### V04 — Bewaart Claude DER twee identieke overlapintervallen?

Hypothese: Zonder track-ID wordt eerste spreker overschreven.

Invoer: `"A en B beide 0–1"`. Onafhankelijke verwachting: `{"labels": ["A", "B"], "tracks": 2}`.

Gemeten uitvoer staat volledig in `falsification_results.json`, item V04. Conclusie: ref_ann verliest een spreker bij identieke intervallen; overlap=ja alleen voegt evenmin een tweede track toe. Beperking: Dit tegenvoorbeeld bewijst niet dat alle huidige CSV-rijen identiek overlappen.

### V05 — Zijn opgeslagen WER/CER aritmetisch juist?

Hypothese: Onafhankelijke edit distance geeft dezelfde cijfers.

Invoer: `"5 teruggevonden ASR-JSON + huidige hashgelijke CSV"`. Onafhankelijke verwachting: `"WER afgerond 0.032/0/0/0.123/0.031; CER 0.035/0/0/0.100/0.022"`.

Gemeten uitvoer staat volledig in `falsification_results.json`, item V05. Conclusie: Rekenkundige replicatie; geen ASR-run en geen onafhankelijkheid van annotaties bewezen. Beperking: Normalisatie gelijk gehouden voor vergelijking; spreker- en tijdcorrectheid niet getoetst.

### V06 — Heeft to_wav contractuele plicht elke WAV te converteren?

Hypothese: Docstring belooft conversie van non-WAV; bestaand WAV blijft geldig pad.

Invoer: `"C:\\Users\\School\\Projects\\StudieStap_WorkshopTool\\Audit_fase1_2026-10-09\\synthetic_48_stereo.wav"`. Onafhankelijke verwachting: `"zelfde pad (gedocumenteerd non-WAV contract)"`.

Gemeten uitvoer staat volledig in `falsification_results.json`, item V06. Conclusie: Claude E16 is geen bewijs van contractbreuk; formaatcompatibiliteit is aparte vraag (T18). Beperking: Geen backendrun of interne resampling.

### V07 — Kan cache modelconfig beoordelen?

Hypothese: Helpers hebben geen modelconfigargument.

Invoer: `"x.json met base; aanvraag medium"`. Onafhankelijke verwachting: `"cache moet modelmismatch onderscheiden"`.

Gemeten uitvoer staat volledig in `falsification_results.json`, item V07. Conclusie: Helpers tonen bestaan-only cache; CLI-inspectie bevestigt check vóór modelconstructie. Beperking: Geen model aangeroepen; verzoek medium is scenario, niet CLI-inference.

### V08 — Bewijst T07 dat elk bronsegment exact eenmaal behouden is?

Hypothese: Een telling alleen kan duplicatie missen.

Invoer: `"Fake preprocessing levert [2,1,1] maar herhaalt alleen eerste bron"`. Onafhankelijke verwachting: `"T07 moet False geven bij gedupliceerde/ontbrekende bronnen"`.

Gemeten uitvoer staat volledig in `falsification_results.json`, item V08. Conclusie: T07 blijft True bij vier kopieën van bron 0; oorspronkelijke test is voor bronbehoud onvolledig. Beperking: Mutatie van afzonderlijke testdouble, geen originele bestanden gewijzigd.

### V09 — Komt teruggevonden nb_hyp overeen met huidige opgeslagen notebookuitvoer?

Hypothese: Parser herhaalt dezelfde tabellen.

Invoer: `"notebook 03/05 HTML + extract_nb.py"`. Onafhankelijke verwachting: `"inhoud gelijk"`.

Gemeten uitvoer staat volledig in `falsification_results.json`, item V09. Conclusie: Toetst extractie en koppeling aan huidige snapshot; geen notebookbrondata/modelrun. Beperking: Historische invoerhash bij oorspronkelijke run ontbreekt.

Belangrijkste meetuitkomsten: V01 map leerling→MAIN/docent→OTHER; V02 overlap=False bij 1 s echte simultaniteit; V03 raw-DER 1,0 of 0,0 versus dezelfde segment-DER 0,5; V04 slechts track B blijft over; V05 edit distances gelijk aan jiwer; V06 WAV-pad onveranderd volgens contract; V07 cache=True zonder modelargument; V08 oorspronkelijke T07-predicate True bij vier kopieën van bron 0; V09 volledige inhoudsgelijkheid van notebookextractie.

V03 gebruikt tijdlijn A 0–1/B 1–2. Bij raw X+Y 0–1 en daarna geen spraak produceert alignment op één ASR 0–2-segment één winnaar X: raw-DER=1,0 en segment-DER=0,5. Bij perfect raw X 0–1/Y 1–2 produceert dezelfde een-winnaarrepresentatie segment-DER=0,5 terwijl raw-DER=0. De “ondergrens”-claim faalt in beide richtingvergelijkingen. Dit is een tegenvoorbeeld voor een algemene methodologische garantie, geen schatting van bias in echte data.

## 9. Tegenstrijdigheden tussen audits

| Verschil | Onafhankelijke beoordeling |
|---|---|
| ChatGPT “geen audio”; Claude 13 MP3’s | Eigen ChatGPT-manifest/inventory vermeldt ze met hashes: ChatGPT beschikbaarheidsclaim onjuist. Niet verklaard door broncodehashverschil. |
| ChatGPT geen metriek; Claude wel WER/CER/DER | Verschil in uitgevoerd onderzoek: offline geometry versus oude ASR-/notebookmetingen. Geen inhoudelijke tegenstelling in modelkwaliteit; teruggevonden pakket maakt Claude-rekenstappen controleerbaar. |
| ChatGPT T18 FAIL versus Claude E15-24bit PASS | Zelfde RuntimeError, verschillende oracles: succesvolle verwerking versus geladen of expliciet afgewezen. Verschil zegt niets over betere codeversie. |
| MAIN-rolprobleem in Claude E1 versus ChatGPT T13 | Functiecontract rangschikt spreektijd, productieherkenning is afzonderlijk; E1 verwart identiteit/rang met rol. Experimentele agreement-helper gebruikt nog wel MAIN=docentheuristiek. |
| Overlap semantisch risico versus harde fout | Beide meten dezelfde geometrie. Gelijktijdige spraak is niet rechtstreeks gemeten door vlag; documented runner-up-share wordt wel uitgevoerd zoals geschreven. |
| DER “ondergrens” versus geen echte kwaliteitsschatting | Getallen repliceerbaar, ondergrens onjuist. Ontbrekende raw-output maakt modelclaim onmogelijk. |
| Voorinvulling volgens Claude bewijst circulair; README zegt handmatig aangepast | Voorinvulling bewezen, ongecontroleerde/nooit-gecorrigeerde annotatie niet bewezen. Onafhankelijkheid onvoldoende vastgelegd. |

## 10. Aanvullende controles

### Werkelijk uitgevoerd

1. Inventaris en SHA-256 van oorspronkelijke manifests, zip en geselecteerde referentie/scriptkopieën; controle oorspronkelijke bestanden voor/na.
2. ChatGPT `run_audit.py`-testgedeelte via AST uitgevoerd met alleen `OUT`/`ROOT` naar nieuwe outputlocatie. Geen assert/input/verwachting aangepast. Het gedeelte na `manifest=[]` is bewust niet uitgevoerd: dat zou originele auditartefacten schrijven en notebookloop dupliceren. Dit is een gecontroleerde herhaling van de 32 proeven, geen ongewijzigde volledige auditrun.
3. Claude `edge_tests.py` ongewijzigd met nieuwe outputmap; lokaal ffmpeg genereert alleen kleine tonen voor WAV-cachetest. Geen persoonsgegevens of modellen gebruikt.
4. Originele unittest-suites vanuit hun correcte werkmap, 17/17 en 51/51.
5. Originele WER- en DER-scriptberekeningen op teruggevonden oude input; resultaten/logs uitsluitend nieuwe map. WER-resultaatkopie apart bewaard en uitgepakte oorspronkelijke resultaatkopie opnieuw uit zip hersteld.
6. V01–V09, notebooknamespaceherhaling, overlap/rol-duursommen, librarybroninspectie en JSONchecker. Geen werkelijke ASR-, embedding- of pyannote-modelinference.

### Interpreter en opdrachten voor herhaling

Python `3.11.5`, `C:\Users\School\AppData\Local\Programs\Python\Python311\python.exe`; packages: pydantic 2.13.5, numpy 2.4.6, torch distribution 2.14.0, torchaudio 2.11.0, faster-whisper 1.2.1, pyannote.audio 4.0.7, pyannote.core 6.0.1, pyannote.metrics 4.1, jiwer 4.0.0, scipy 1.17.1, pandas 2.2.3, matplotlib 3.10.3, nbformat 5.10.4, nbclient 0.10.0. Volledige metadata in `environment.json`. Distributiontag van torch alleen bewijst geen GPU/CPU-capaciteit; geen nieuwe hardwaremeting gedaan.

Uitvoeren vanuit `C:\Users\School\Projects\StudieStap_WorkshopTool` met bestaande interpreter en dependencies:

```powershell
python -B Validatie_fase1_stap2_2026-10-09\validate.py
python -B Validatie_fase1_stap2_2026-10-09\falsification.py > Validatie_fase1_stap2_2026-10-09\falsification.log
python -B Validatie_fase1_stap2_2026-10-09\supplemental.py
python -B Data-analysis\Audit\scripts\validate_json.py 'Validatie_fase1_stap2_2026-10-09/teruggevonden_bewijs/asr/*.json' > Validatie_fase1_stap2_2026-10-09\json_herhaling.log
python -B Validatie_fase1_stap2_2026-10-09\build_report.py
```

De exacte subprocessopdrachten, werkmap, returncodes en lognamen staan in `commands.json`; extra top-level opdrachten staan hierboven en in `execution_record.json`. Herhaling overschrijft uitsluitend nieuwe validatie-uitvoer. Voor onafhankelijk archiveren: kopieer deze gehele validatiemap naar een eigen locatie vóór herhaling. Reproductiescripts gebruiken de oorspronkelijke repository als referentie, niet historische HEAD-CSV’s. Pakketchecksumverificatie en repo-manifestcontrole moeten opnieuw slagen; netwerk/modelconstructie is niet nodig. FFmpeg moet lokaal beschikbaar zijn voor E17.

### Uitsluitend statisch / niet uitgevoerd

ASR-CLI cachecheck vóór config/modelconstructie, model/schemadefaults, thresholds, local-library toekenning en methodologische herkomst zijn statisch beoordeeld waar geen experiment vermeld staat. Tuningmodellen, echte docentembeddings, volledige schone Jupyter-kernelruns en ruis-ASR zijn niet gestart. Lezen van oude resultaten is nergens als nieuwe inference geregistreerd.

## 11. Prioriteiten voor vervolgonderzoek

1. **Referenties eerst:** documenteer onafhankelijke woord-/speakerannotatie, exacte audiorevisies en intervallen, verstaanbaarheid, GEEN/ONBEKEND, volledige simultane tracks en handmatige verificatie. Maak expliciet welke voorgevulde tekst/grenzen zijn gecorrigeerd. Nieuwe annotatie/luistercontrole is vervolgwerk, niet hier uitgevoerd.
2. **Scheid metingen:** WER/CER op hetzelfde onafhankelijke spraakinterval; raw-DER en verwerkte-label-DER afzonderlijk, vaste UEM/collar/overlapregels en miss/FA/confusion. Geef geen ondergrensgarantie zonder bewijs.
3. **Bewaar experimentinput:** ruiswav’s, generator/seed, schoon referentieinterval, daadwerkelijke RMS/SNR en volledige ASR-output. VAD-effect alleen met passende aan/uitcontrole en known speech; een nul-segment-geval is geen bewijs van gemiste spraak.
4. **Herstel testmethoden in een volgende stap:** specifieke exception-assertions, echte assertions voor E7b/E14, exacte source-identiteitcheck voor T07, contractcorrecte E1/E11/E13/E16, expliciete not-tested/skipped/input-missing-status. Deze oorspronkelijke tests zijn hier niet gewijzigd.
5. **Rolonderzoek:** onafhankelijke docenten/opnames, testset gescheiden van drempelkeuze, coverage/abstention én score op alle cases, seconden versus chunks duidelijk apart. Geen confidence-interval op alsof onafhankelijke chunks uit dezelfde opname.
6. **Reproduceerbaarheid:** schone notebookkernel met volledige bestanden/omgeving, modelrevisies en inputhashes per run. Behoud bestaande technische bevindingen en succesvolle unit-tests onder hun beperkte scope; geen grote nieuwe runs nodig om die uitspraken te behouden.

Dit is een onderzoeksvolgorde, geen uitgevoerd verbeterplan. Pipeline, classifier, modelinstellingen, drempels en didactische indicatoren zijn onveranderd.

## 12. Conclusie voor het stageonderzoek

De onafhankelijke validatie bevestigt dat een belangrijk deel van de technische auditobservaties op de vastgelegde bronversies herhaalbaar is. De tests tonen onder meer kwetsbaar cachehergebruik, onvolledige numerieke/clipvalidatie, verlies van vervolgregels uit een handmatige tekstreferentie en beperkingen in sprekerinformatie na segmentkoppeling. Deze bevindingen betreffen Pythonverwerking en testontwerp; zij geven geen foutpercentage van de spraakmodellen.

De opgeslagen WER/CER- en verwerkte-DER-cijfers zijn rekenkundig reproduceerbaar, maar onvoldoende voor onafhankelijke modelkwaliteit. Referentieonafhankelijkheid en volledige overlapannotatie zijn niet aangetoond; ruwe diarizatie ontbreekt, ruisinput/generatie ontbreekt en de rolmeting gebruikt één in-sample fragment met gecorreleerde tijdsduur. Een segment-DER is geen gegarandeerde ondergrens. Een aantal oorspronkelijke FAIL/PASS-labels berust op te sterke verwachtingen of zwakke assertions. Daarom worden alleen begrensde, per-test onderbouwde uitspraken behouden en blijven echte nauwkeurigheidsclaims afhankelijk van nieuw onafhankelijk evaluatiebewijs.
