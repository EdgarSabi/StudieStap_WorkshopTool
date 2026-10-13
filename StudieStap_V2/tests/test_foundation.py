"""Mijlpaal A: datamodellen, instellingen, audio-invoer en JSON-export.

Verwachting vooraf (falsificeerbaar): zie de commentaarregels bij iedere test.
Dit zijn unit-tests met synthetische gegevens: ze bewijzen NIETS over modelnauwkeurigheid.
"""
import hashlib
import json
import os

import pytest
import yaml

from conftest import make_wav, needs_ffmpeg
from studiestap.audio.loader import prepare_audio, validate_audio_path, wav_duration_seconds
from studiestap.models import Segment, StepStatus, StudieStapError, to_dict
from studiestap.output.exporter import MANIFEST_NAME, delete_run, summary_for_database, write_json
from studiestap.settings import Settings, load_settings


# ------------------------------------------------------------ modellen
def test_to_dict_geneste_dataclass_en_enum_wordt_json():
    # Verwacht: Enum wordt zijn waarde, geneste dataclass een dict.
    d = to_dict({"seg": Segment(id=0, start=0.0, end=1.0, text="hoi"), "status": StepStatus.PARTIAL})
    assert d["status"] == "partial"
    assert d["seg"]["text"] == "hoi"
    json.dumps(d)  # mag niet falen


# ------------------------------------------------------------ instellingen
def test_standaardinstellingen_komen_overeen_met_oude_baseline():
    # Verwacht: whisper medium, nl, cpu, int8, beam 5, VAD aan (oude baseline).
    t = Settings().transcription
    assert (t.model_size, t.language, t.device, t.compute_type, t.beam_size, t.vad_filter) == \
        ("medium", "nl", "cpu", "int8", 5, True)


def test_config_yaml_in_de_repo_laadt_en_is_gelijk_aan_standaard():
    # Verwacht: config.yaml documenteert dezelfde waarden als de defaults (geen verborgen afwijking).
    from pathlib import Path
    repo_config = Path(__file__).resolve().parents[1] / "config.yaml"
    assert load_settings(repo_config).to_dict() == Settings().to_dict()


def test_yaml_overschrijft_standaard(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(yaml.safe_dump({"transcription": {"model_size": "small"}}), encoding="utf-8")
    s = load_settings(cfg)
    assert s.transcription.model_size == "small"
    assert s.transcription.language == "nl"  # rest blijft standaard


@pytest.mark.parametrize("inhoud", [
    {"transcription": {"model_sise": "small"}},   # typfout in sleutel
    {"transcriptie": {"model_size": "small"}},    # typfout in sectie
])
def test_onbekende_sleutel_of_sectie_wordt_afgekeurd(tmp_path, inhoud):
    # Tegenvoorbeeld: een typfout mag NIET stilletjes genegeerd worden.
    cfg = tmp_path / "c.yaml"
    cfg.write_text(yaml.safe_dump(inhoud), encoding="utf-8")
    with pytest.raises(StudieStapError):
        load_settings(cfg)


def test_ontbrekend_configbestand_geeft_vriendelijke_fout(tmp_path):
    with pytest.raises(StudieStapError) as e:
        load_settings(tmp_path / "bestaat_niet.yaml")
    assert "niet gevonden" in e.value.message


def test_token_komt_nooit_in_de_provenance(monkeypatch):
    # Verwacht: ook als HF_TOKEN gezet is, staat het niet in de instellingen-snapshot.
    monkeypatch.setenv("HF_TOKEN", "hf_GEHEIM_TESTWAARDE")
    assert "GEHEIM" not in json.dumps(Settings().to_dict())


# ------------------------------------------------------------ audio
def test_ontbrekend_bestand(tmp_path):
    with pytest.raises(StudieStapError) as e:
        validate_audio_path(tmp_path / "nergens.mp3")
    assert "niet gevonden" in e.value.message


def test_verkeerd_formaat_en_leeg_bestand(tmp_path):
    txt = tmp_path / "notitie.txt"
    txt.write_text("hallo")
    with pytest.raises(StudieStapError):
        validate_audio_path(txt)
    leeg = tmp_path / "leeg.wav"
    leeg.write_bytes(b"")
    with pytest.raises(StudieStapError):
        validate_audio_path(leeg)


@needs_ffmpeg
def test_kapotte_audio_geeft_vriendelijke_fout(tmp_path):
    # Tegenvoorbeeld: ruis met .mp3-extensie is geen audio.
    kapot = tmp_path / "kapot.mp3"
    kapot.write_bytes(os.urandom(2048))
    with pytest.raises(StudieStapError) as e:
        prepare_audio(kapot, tmp_path / "work")
    assert "ffmpeg kon dit bestand niet lezen" in e.value.message


@needs_ffmpeg
def test_prepare_audio_zet_om_naar_16k_mono_en_laat_origineel_ongemoeid(tmp_path):
    bron = make_wav(tmp_path / "bron.wav", seconds=2.0, rate=48000, channels=2)
    hash_voor, mtime_voor = hashlib.sha256(bron.read_bytes()).hexdigest(), bron.stat().st_mtime_ns
    info = prepare_audio(bron, tmp_path / "work")

    import wave
    with wave.open(info.working_wav, "rb") as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)
    assert abs(info.duration_seconds - 2.0) < 0.05
    assert info.sha256 == hash_voor
    # origineel: zelfde inhoud, zelfde plek, niet aangeraakt
    assert bron.exists()
    assert hashlib.sha256(bron.read_bytes()).hexdigest() == hash_voor
    assert bron.stat().st_mtime_ns == mtime_voor
    assert wav_duration_seconds(__import__("pathlib").Path(info.working_wav)) > 0


# ------------------------------------------------------------ export
def test_write_json_hash_komt_overeen_met_bestand(tmp_path):
    p = tmp_path / "sub" / "x.json"
    digest = write_json(p, {"a": [1, 2, 3], "tekst": "één"})
    assert digest == hashlib.sha256(p.read_bytes()).hexdigest()
    assert json.loads(p.read_text(encoding="utf-8"))["tekst"] == "één"
    assert not list(tmp_path.rglob("*.tmp"))


def test_delete_run_weigert_willekeurige_map(tmp_path):
    # Tegenvoorbeeld: een map zonder run_manifest.json mag NIET verwijderd worden.
    vreemd = tmp_path / "belangrijk"
    vreemd.mkdir()
    (vreemd / "foto.jpg").write_bytes(b"x")
    with pytest.raises(StudieStapError):
        delete_run(vreemd)
    assert (vreemd / "foto.jpg").exists()


def test_delete_run_verwijdert_echte_run(tmp_path):
    run = tmp_path / "run"
    write_json(run / MANIFEST_NAME, {"x": 1})
    (run / "01_transcript.json").write_text("{}")
    delete_run(run)
    assert not run.exists()


def test_database_samenvatting_bevat_geen_tekst_of_pad():
    result = {
        "audio": {"sha256": "abc", "duration_seconds": 10.0, "source_path": "C:/geheim/pad.mp3"},
        "raw_speakers": ["SPEAKER_00"],
        "segments": [{"text": "leerling zegt iets", "quality": {"status": "REVIEW_REQUIRED"},
                      "speakers": {"attribution": "MIXED"}}],
        "steps": {"word_alignment": {"status": "unavailable"}},
    }
    s = json.dumps(summary_for_database(result))
    assert "leerling" not in s and "geheim" not in s
