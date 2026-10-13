"""Mijlpaal D: de lege classificatie-interface en het sjabloon voor een eigen indicator.

Er is GEEN didactische classifier: deze tests bewaken vooral dat er niets verzonnen wordt en
dat een eigen indicator (hier een nep-indicator uit de test zelf) correct door de interface past.
"""
import importlib.util
import json
from pathlib import Path

import pytest

from conftest import make_wav, needs_ffmpeg
from studiestap.classification import indicators as registry
from studiestap.classification.base import (ConversationContext, Evidence, Indicator, IndicatorResult,
                                            IndicatorStatus, Utterance)
from studiestap.classification.indicators import run_indicators
from studiestap.models import to_dict

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "mijn_indicator.py"


def ctx(*texts, review="ASSESSABLE"):
    return ConversationContext([Utterance(i, i, i + 1, t, ["A"], ["docent"], review) for i, t in enumerate(texts)])


def load_example():
    spec = importlib.util.spec_from_file_location("mijn_indicator", EXAMPLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.MijnIndicator()


def test_het_register_is_standaard_leeg_en_meldt_dat_eerlijk():
    assert registry.INDICATORS == []
    out = run_indicators(ctx("wat denk jij?"))
    assert out["status"] == "NOT_IMPLEMENTED" and out["indicators"] == []


def test_basisindicator_zonder_implementatie_verzint_niets():
    r = Indicator().classify(ctx("wat denk jij?"))
    assert r.status == IndicatorStatus.NOT_IMPLEMENTED and r.evidence == []


def test_sjabloon_is_standaard_niet_geimplementeerd():
    r = load_example().classify(ctx("een zin", "nog een zin"))
    assert r.status == IndicatorStatus.NOT_IMPLEMENTED


def test_sjabloon_gedrag_zodra_student_het_invult():
    # Een leerling-implementatie simuleren: zoek_fragment vindt een vraagteken.
    ind = load_example()
    ind.geimplementeerd = True
    ind.zoek_fragment = lambda u: u.text if "?" in u.text else None

    r = ind.classify(ctx("Wat denk jij?", "Ik denk niks."))
    assert r.status == IndicatorStatus.DETECTED
    assert [(e.segment_id, e.quote) for e in r.evidence] == [(0, "Wat denk jij?")]     # bewijs bij detectie

    assert ind.classify(ctx("Geen vraag hier.")).status == IndicatorStatus.NOT_DETECTED
    # niets gevonden maar kwaliteit onzeker -> UNKNOWN, geen stellig 'nee'
    assert ind.classify(ctx("Geen vraag hier.", review="REVIEW_REQUIRED")).status == IndicatorStatus.UNKNOWN
    # alleen onbruikbare tekst -> NOT_ASSESSABLE
    assert ind.classify(ctx("", review="NOT_ASSESSABLE")).status == IndicatorStatus.NOT_ASSESSABLE
    # geen uitingen -> NOT_ASSESSABLE
    assert ind.classify(ConversationContext([])).status == IndicatorStatus.NOT_ASSESSABLE


def test_kapotte_indicator_wordt_UNKNOWN_en_andere_indicatoren_draaien_door():
    class Kapot(Indicator):
        name = "kapot"
        def classify(self, context):
            raise ValueError("bug")

    class Goed(Indicator):
        name = "goed"
        def classify(self, context):
            return IndicatorResult("goed", IndicatorStatus.DETECTED, [Evidence(0, "x")])

    out = run_indicators(ctx("x"), [Kapot(), Goed()])
    statuses = {r.indicator: r.status for r in out["indicators"]}
    assert statuses == {"kapot": IndicatorStatus.UNKNOWN, "goed": IndicatorStatus.DETECTED}
    json.dumps(to_dict(out))   # resultaatstructuur is JSON-baar


@needs_ffmpeg
def test_pipeline_geeft_indicator_de_context_met_tekst_rollen_en_kwaliteit(tmp_path, monkeypatch):
    from test_pipeline import make_backends, Counter   # hergebruik de nep-modellen
    from studiestap.pipeline import run_pipeline
    from studiestap.settings import Settings

    gezien = {}

    class Spion(Indicator):
        name = "spion"
        def classify(self, context):
            gezien["ctx"] = context
            return IndicatorResult(self.name, IndicatorStatus.UNKNOWN, explanation="alleen kijken")

    monkeypatch.setattr(registry, "INDICATORS", [Spion()])
    audio = make_wav(tmp_path / "a.wav", seconds=4.0, rate=16000, channels=1)
    settings = Settings()
    settings.output.directory = str(tmp_path / "out")
    r = run_pipeline(audio, settings, backends=make_backends(Counter()))

    utter = gezien["ctx"].utterances
    assert [u.text for u in utter] == ["welkom allemaal", "vragen jullie dat"]
    assert utter[0].roles == ["onbekend"]               # zonder referentie nooit 'docent'
    assert utter[1].speakers == ["SPEAKER_01"] or "SPEAKER_00" in utter[1].speakers
    assert utter[0].review_status in ("ASSESSABLE", "REVIEW_REQUIRED")
    result = json.loads((r.run_dir / "07_result.json").read_text(encoding="utf-8"))
    assert result["classification"]["status"] == "RAN"
    assert result["classification"]["indicators"][0]["status"] == "UNKNOWN"
