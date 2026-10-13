"""Maak examples/example_result.json met SYNTHETISCHE gegevens (nep-modellen, sinustoon als audio).

Het voorbeeld laat de vorm van het eindresultaat zien; de inhoud is verzonnen en zegt niets over
echte opnames of modellen.   Gebruik:  python tools/make_example.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "src"))

from conftest import make_wav                       # noqa: E402
from test_pipeline import Counter, make_backends    # noqa: E402
from studiestap.pipeline import run_pipeline        # noqa: E402
from studiestap.settings import Settings            # noqa: E402


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        audio = make_wav(tmp / "voorbeeld.wav", seconds=4.0, rate=16000, channels=1)
        reference = make_wav(tmp / "docent_referentie.wav", seconds=2.0, rate=16000, channels=1)
        settings = Settings()
        settings.output.directory = str(tmp / "out")
        report = run_pipeline(audio, settings, backends=make_backends(Counter()), teacher_reference=reference)
        result = json.loads((report.run_dir / "07_result.json").read_text(encoding="utf-8"))
    result["audio"]["source_path"] = "voorbeeld.wav"
    result["provenance"]["settings"]["output"]["directory"] = "output"   # geen lokaal pad in het voorbeeld
    result["_let_op"] = "SYNTHETISCH VOORBEELD: nep-modellen en verzonnen tekst; alleen bedoeld om de structuur te tonen."
    target = ROOT / "examples" / "example_result.json"
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Geschreven: {target}")


if __name__ == "__main__":
    main()
