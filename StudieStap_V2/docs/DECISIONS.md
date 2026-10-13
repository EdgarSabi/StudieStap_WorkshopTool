# Technische keuzes

| Keuze | Motivatie |
|---|---|
| **Python 3.12** in eigen `.venv` | De WhisperX-stack draaide in het eerdere experiment op 3.12; 3.14 (oude hoofdomgeving) had er geen wheels voor. De oude omgeving is niet aangeraakt. |
| **Dataclasses i.p.v. pydantic** | Eenvoudiger te lezen en een afhankelijkheid minder; validatie van de belangrijkste invoer (audio, config) gebeurt expliciet. |
| **`argparse` i.p.v. een CLI-framework** | Standaardbibliotheek is genoeg voor vier commando's. |
| **Zware pakketten als extras** (`[models]`, `[align]`) | Kern en tests blijven licht en snel; je ziet precies wat zwaar is. |
| **Eigen WAV-lezer en altijd naar 16 kHz mono** | Pyannote krijgt een waveform i.p.v. een pad, zodat torchcodec/FFmpeg-DLL's niet nodig zijn (bekend probleem uit de oude pipeline). |
| **Whisper medium, nl, cpu, int8, beam 5, VAD aan** | Overgenomen uit de oude baseline voor een vergelijkbare start. Alles aanpasbaar in `config.yaml`. |
| **Geen eigen herhalingsdetectie ("hallucinaties")** | De oude heuristiek was niet gevalideerd; kwaliteitsregels volgen in onderzoeksfases 3-4. Alleen de ruwe Whisper-cijfers en de Whisper-standaarddrempels worden gebruikt. |
| **Ruwe en afgeleide uitvoer in aparte bestanden** | Terug te herleiden; latere stappen kunnen ruwe gegevens niet beschadigen. |
| **Alle intersecties bewaren; dominante spreker alleen als samenvatting; geen keuze bij gelijkspel** | Les van `feature/lossless-speaker-intersections`. Een vergelijking met opgeslagen oude runs liet zien dat bij exact gelijke dekking de oude code willekeurig koos. |
| **Segmentstatus `MIXED` zodra >= 2 ruwe labels overlappen, zonder minimale overlap** | Geen nieuwe ongevalideerde drempel. Gevolg: ook zeer kleine randoverlap telt (zie beperkingen); `seconds_per_speaker`/`simultaneous_seconds` zijn beschikbaar om later te drempelen. |
| **`min_single_speaker_coverage` 0.60 en WeSpeaker-drempel 0.35** | Experimenteel, overgenomen uit eerder werk, expliciet als niet-gevalideerd gemarkeerd in `config.yaml`. |
| **Woord met >= 2 overlappende sprekers = `AMBIGUOUS`, geen keuze** | Geen woordtoewijzing verzinnen bij tegenstrijdige informatie. |
| **Docentherkenning per ruwe spreker, op stukken zonder andere sprekers** | Stabieler dan per beurt en voorkomt dat mengstem wordt vergeleken. Gevolg: een spreker die altijd overlapt wordt `UNKNOWN`. |
| **Rol "docent" alleen bij `MATCH`; anders "onbekend"** | `NO_MATCH` bewijst niet dat iemand een leerling is. |
| **Kwaliteit: alleen `kind: observed`-signalen** | Onderscheid tussen waargenomen en bewezen onbetrouwbaar. `ASSESSABLE` is geen betrouwbaarheidsclaim. |
| **Cache op `sha256(audio) + instellingen` per stap** | Voorkomt dubbele modeluitvoering (ook WhisperX hergebruikt de bestaande transcriptie). |
| **Werkaudio wordt na de run verwijderd** | Privacy-by-design; `output.keep_audio` is een bewuste keuze. |
| **Geen database; wel `summary_for_database`** | Reservering: alleen geaggregeerde, privacyveilige getallen. |
| **`studiestap clean` weigert mappen zonder `run_manifest.json`** | Voorkomt dat een typfout in het pad iets anders verwijdert. |
| **Aparte git-repo in `StudieStap_V2`** | De oude repository blijft onaangeroerd. |
