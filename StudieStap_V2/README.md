# StudieStap 2.0

Een schone, modulaire audiopipeline voor workshopreflectie:
opname -> tekst -> sprekers -> woordtijden -> sprekerkoppeling -> docentherkenning -> kwaliteitssignalen -> JSON.

> **Doel: reflectie, geen beoordeling.** De tool beoordeelt geen docent of StudieStapper en meldt
> expliciet wanneer gegevens te onzeker zijn. Didactische classificatie is bewust nog leeg
> (zie `docs/HOW_IT_WORKS.md`, "Je eigen indicator toevoegen").

## Installeren (Windows)

Vereist: Python 3.12 en `ffmpeg` op je PATH (`winget install Gyan.FFmpeg`).

```bash
cd C:\Users\School\StudieStap\StudieStap_V2
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"            # lichte kern + tests
```

De zware modelpakketten staan los, zodat de kern en de tests licht blijven:

```bash
pip install -e ".[models]"         # faster-whisper + pyannote.audio (haalt o.a. torch binnen: groot)
pip install -e ".[align]"          # WhisperX voor woorduitlijning (optioneel)
```

Controleer wat je computer heeft (toont nooit je token):

```bash
studiestap check
```

## Een eigen opname testen

```bash
studiestap analyze "C:\Audio\voorbeeld.mp3"
studiestap analyze "C:\Audio\voorbeeld.mp3" --teacher-reference "C:\Audio\docent_referentie.mp3"
studiestap transcribe "C:\Audio\voorbeeld.mp3"
```

Je ziet per stap of die bezig is, geslaagd, gedeeltelijk geslaagd, niet beschikbaar of mislukt is.
De uitvoer komt in `output\<naam>_<8 tekens>\` (staat in `.gitignore`). Open `07_result.json` voor het geheel;
`run_manifest.json` bevat instellingen, versies, stapstatussen en hashes.

Handige opties: `--force` (alles opnieuw), `--no-align` (geen woorduitlijning), `--config pad\config.yaml`,
`--out map`, `--debug` (technische details bij fouten).

Dezelfde opname twee keer analyseren herhaalt de zware modelstappen niet, zolang audio en instellingen gelijk zijn.

## Instellingen en token

* Alle instellingen staan in `config.yaml` (model, device, compute type, taal, drempels...). Een typfout geeft een duidelijke fout.
* Kopieer `.env.example` naar `.env` en vul `HF_TOKEN=...` in als je gated modellen moet downloaden.
  `.env` staat in `.gitignore`. Heb je de modellen al lokaal in de cache staan, zet dan in `config.yaml`
  `huggingface: offline: true`; dan is geen token nodig.

## Tests draaien

```bash
pytest                           # alle unit- en integratietests (synthetisch, geen modellen nodig)
python tools/mutation_check.py   # bouwt bewust fouten in de code en controleert dat de tests ze afkeuren
```

## Privacy

Audio, transcripties, embeddings, caches, `.env` en `output\` blijven buiten Git. Er wordt niets geupload;
alles draait lokaal. De tijdelijke 16 kHz-werkkopie van je audio wordt na een run verwijderd
(`output.keep_audio: true` bewaart haar). Lokale rungegevens verwijderen:

```bash
studiestap clean output\voorbeeld_ab12cd34
```

## Meer lezen

`docs/ARCHITECTURE.md` (pipeline), `docs/HOW_IT_WORKS.md` (elke module), `docs/DECISIONS.md` (keuzes),
`IMPLEMENTATION_REPORT.md` (wat is gebouwd en getest, en wat nog niet).
