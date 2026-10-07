# Sortformer als alternatief voor pyannote

Uit de hyperparameter-tuning bleek dat pyannote niet beter te krijgen is met instellingen. Korte tussenkomsten van leerlingen worden bij de docent geplakt en een derde stem (Emma) verdwijnt helemaal. Dat ligt aan hoe pyannote werkt: het knipt de audio eerst in stukjes en clustert daarna stemkenmerken. Een uitroep van een halve seconde geeft te weinig stemkenmerk om een eigen cluster te vormen, dus die belandt bij de dominante spreker.

NVIDIA Sortformer werkt anders. Het is één model zonder aparte clusteringstap, dat per 80 ms voor elk van maximaal vier sprekers voorspelt of die op dat moment praat. Overlap en korte tussenkomsten zijn daardoor precies waar het voor gebouwd is.

## Waarom Sortformer en niet DiariZen

Beide waren opties. Sortformer is gekozen om twee redenen. De eerste is de licentie: de gewichten van `nvidia/diar_streaming_sortformer_4spk-v2.1` vallen onder de NVIDIA Open Model License, die commercieel gebruik toestaat. De DiariZen-modellen zijn CC BY-NC 4.0, dus alleen voor onderzoek en niet in een stageproduct. Let op: de oudere `nvidia/diar_sortformer_4spk-v1` is ook CC BY-NC, gebruik die dus niet. De tweede reden is de installatie: DiariZen draait op een eigen, oudere fork van pyannote met torch 2.1, wat botst met onze pyannote 4.0.7. NeMo kan gewoon in dezelfde venv naast pyannote.

## Wat er in de code veranderd is

In `src/diarization.py` staat nu naast `PyannoteBackend` een `SortformerBackend` met precies dezelfde interface. Die zet de uitvoer van NeMo om naar dezelfde `SpeakerTurn`s (met ids als `SPEAKER_00`), dus `build_label_map()`, `assign_speakers()`, preprocessing en docentherkenning werken ongewijzigd. De standaard blijft pyannote, tot de evaluatie hieronder laat zien dat Sortformer echt beter is. Kiezen gaat zo:

```
.venv\Scripts\python.exe diarization.py --transcript <json> --backend sortformer
.venv\Scripts\python.exe run_docent_pipeline.py testaudio6_fragment.mp3 --diarization-backend sortformer
```

of permanent met `backend = "sortformer"` in `DiarizationConfig` in `config.py`. Daar staan ook het model, de streaming-instellingen en drie postprocessing-presets (`default`, `dihard3`, `callhome`). De presets zijn door NVIDIA zelf geoptimaliseerd; `dihard3` houdt heel korte spraakstukjes over en past waarschijnlijk het best bij een rumoerige klas.

## Installeren

In de bestaande venv in `Data-analysis/src`:

```
.venv\Scripts\pip install "nemo_toolkit[asr]==3.0.0"
```

Er is geen HuggingFace-token nodig; het model (ongeveer 500 MB) wordt bij de eerste run vanzelf gedownload. NeMo wordt officieel niet ondersteund op Windows. Als de installatie daar vastloopt, maak dan eerst een kopie van de venv (`.venv-sortformer`, staat al in `.gitignore`) zodat de werkende pyannote-omgeving heel blijft, en probeer anders WSL2. Op Linux is de combinatie getest zonder conflicten.

## Evalueren

Draai vanuit `Data-analysis/src`:

```
.venv\Scripts\python.exe ..\Experiments\diarization\sortformer\evaluate_sortformer.py testaudio4_fragment testaudio2_fragment --presets default dihard3 callhome --with-pyannote
```

Dit gebruikt dezelfde handmatige ground truth en dezelfde score als het tuning-experiment, zodat de getallen direct naast de oude tabel passen. `--with-pyannote` draait pyannote opnieuw mee voor een eerlijke vergelijking op alle kolommen (daarvoor is wel het HF-token nodig). De uitkomst komt in `results_sortformer.json`, inclusief alle turns zodat je verdachte stukken kunt terugluisteren.

Het script geeft naast de oude score ook een strenge variant. De oude score telt een blokje als goed zodra de juiste spreker ergens tussen de actieve sprekers zit. Bij het testen bleek dat een model dat overal iedereen actief zet daarmee 100% haalt. Omdat Sortformer van nature vaker overlap aangeeft dan pyannote, zou de oude score Sortformer dus te gunstig laten uitkomen. In de strenge score telt een blokje alleen als goed als de juiste spreker als enige actief is, behalve waar in de ground truth `overlap = ja` staat. Verder rapporteert het script dezelfde scores alleen voor korte beurten (onder 1,5 s) en hoe vaak het model overlap geeft waar er geen is.

Een redelijk criterium om over te stappen, in lijn met het tuning-experiment: op beide fragmenten minstens 3 procentpunt beter op de strenge score, zonder dat de onterechte overlap flink stijgt. Controleer daarna op `testaudio6_fragment` of het daar ook klopt, zonder op dat fragment nog iets te kiezen.

## Wat al getest is en wat niet

De code is getest met het echte NeMo-pakket (3.0.0) op een Sortformer-model met dezelfde architectuur maar willekeurige gewichten, omdat HuggingFace vanuit de testomgeving niet bereikbaar was. Daarmee is bevestigd dat de hele keten werkt: laden, diarize, omzetten naar turns, `assign_speakers()`, de JSON-uitvoer, preprocessing en het evaluatiescript. Ook de bestaande unittests en de nieuwe tests in `src/tests/test_diarization_sortformer.py` slagen. Wat nog niet bekend is, is hoe goed het echte model het doet op Nederlandse klasaudio. Dat moet blijken uit de evaluatie hierboven.

Een bruikbare bijvangst: de rekentijd hangt niet af van de gewichten. Het model deed op twee CPU-kernen ongeveer 5 seconden over het fragment van 120 s, tegen 74 tot 92 seconden voor pyannote. Voor een hele les scheelt dat veel.

## Beperkingen

Sortformer kan maximaal vier sprekers tegelijk onderscheiden. In een klas met meer sprekers worden stemmen in die vier plekken samengevoegd. Voor het onderscheid docent tegenover de rest is dat minder erg dan het klinkt, maar het is geen volledige diarisatie van een hele klas. Verder is het model vooral op Engels getraind en niet door NVIDIA op Nederlands getest, en geldt `min_speakers`/`max_speakers` niet voor Sortformer.
