# Voorregistratie — laatste ontwikkeltests (audio 4 en audio 5)

Vastgelegd vóór de runs (2026-10-13), branch `feature/lossless-speaker-intersections`, HEAD `afefb0a`. Nieuwe run-IDs: `20261013_final_dev_run1` (beide fragmenten, aparte mappen). Geen tuning, geen aanpassing van instellingen.

| # | Verwachting | Falsificatie |
|---|---|---|
| E1 | Elke combinatie (ruwe beurt, Whisper-segment) met positieve overlap staat precies één keer als intersection in dat segment, met kloppende begin/eind/duur | enige afwijking van de onafhankelijke berekening met exacte rationale getallen, in aantal, label of tijd |
| E2 | Segmenten met ≥ 2 ruwe labels hebben `multiple_raw_speakers=True` en dat blijft na preprocessing, docentstap en JSON-herladen zichtbaar (turnsamenvatting = som van bronsegmenten) | enig segment/turn waar het ontbreekt of niet klopt |
| E3 | Dominant label, overige segmentvelden, turngrenzen/flags en docentrollen zijn identiek aan wat de **oorspronkelijke** code (commit `0a4ab99`) op exact dezelfde nieuwe ruwe beurten en Whisper-segmenten oplevert (replay, geen oude cache) | enig verschil in een bestaand veld |
| E4 | Geen ruwe sprekers gaan stilzwijgend verloren *binnen* Whisper-segmenten: elk ruw label met activiteit binnen een segment komt in de intersections voor, ook bij korte stukjes (< 1 s) en rumoer. Ruwe activiteit **buiten** alle Whisper-segmenten staat per constructie niet in de segmentinformatie en wordt apart geteld en getoond | een ruwe beurt met positieve overlap met een segment die ontbreekt; of buiten-segment-activiteit die niet wordt gerapporteerd |

Vergelijkbaarheid met oude uitvoer: de oude caches in `Data-local/processed` zijn niet vergelijkbaar (ouder, andere speaker-priors bij audio 4: 1–3; code van vóór `0a4ab99`), en worden niet als meting gebruikt. Oude auditrun-Whisperuitvoer (`Validatie_fase1_stap2/zip_extract/asr`) wordt alleen als afzonderlijke diagnostische observatie vergeleken.

Rapportage van WER/DER/rollen alleen binnen de vooraf vastgelegde beperkingen (PROTOCOL v1 §10): audio 4 is circulair voor WER, audio 4/5 hebben `ONBEKEND`/rumoer-gebieden, overlap is onvolledig geannoteerd, audio 4 heeft geen rolreferentie. De Whisper-voorgevulde ground truths zijn geen onafhankelijke nauwkeurigheidswaarheid.
