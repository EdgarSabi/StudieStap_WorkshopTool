"""Evaluatierunner voor de fase-1-pipeline. Draait de ORIGINELE main()-functies uit Data-analysis/src in-process, met
omgeleide uitvoerpaden naar een NIEUWE map. Wijzigt niets in src, gebruikt geen bestaande caches als resultaat,
overschrijft nooit.

    # alleen controleren (geen modellen laden, schrijft niets):
    python run_baseline.py --fragment testaudio2_fragment --preflight
    # modellen laden zonder audio te verwerken (smoke test):
    python run_baseline.py --fragment testaudio2_fragment --preflight --load-models
    # echte run:
    python run_baseline.py --fragment testaudio2_fragment --run-id 20261013_dev1_run1

Draai met Data-analysis/src/.venv/Scripts/python.exe. Standaard HF_HUB_OFFLINE=1 (geen netwerk); --online heft dat op.
"""
import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from baseline_eval import settings as S                                   # noqa: E402
from baseline_eval import refs as R                                        # noqa: E402
from baseline_eval import runlib as L                                      # noqa: E402
from baseline_eval import diar as D                                        # noqa: E402

PROTOCOL_VERSION = "v1"


def token_present() -> bool:
    """Alleen ja/nee. De waarde wordt nooit ingelezen in een variabele die wordt geprint of gelogd."""
    if os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN"):
        return True
    env = S.REPO / ".env"
    if env.is_file():
        return any(line.strip().startswith(("HF_TOKEN=", "HUGGINGFACE_TOKEN=")) and len(line.split("=", 1)[1].strip()) > 0
                   for line in env.read_text(encoding="utf-8").splitlines())
    return False


def resolve_inputs(fragment: str) -> dict:
    if fragment not in S.FRAGMENTS:
        raise SystemExit(f"Onbekend fragment '{fragment}'. Keuze: {sorted(S.FRAGMENTS)}")
    spec = S.FRAGMENTS[fragment]
    audio = S.TEST_FILES / spec["audio"]
    dur = L.probe_audio(audio)
    ref = R.load_reference(S.GT_DIR / spec["ref"], fragment)
    roles_src = None
    if spec["role_source"]:
        rs = R.load_reference(S.GT_DIR / spec["role_source"], fragment)
        roles_src = {"path": str(rs.path), "sha256": rs.sha256}
    manual = None
    if spec["manual_txt"]:
        mp = S.RAW_DIR / spec["manual_txt"]
        R.manual_txt_text(mp)
        manual = {"path": str(mp), "sha256": L.sha256(mp)}
    L.probe_audio(S.DOCENT_REFERENCE_AUDIO)
    return {"fragment": fragment, "audio_path": str(audio), "audio_sha256": L.sha256(audio), "audio_duration_s": dur,
            "reference_path": str(ref.path), "reference_sha256": ref.sha256, "reference_rows": len(ref.rows),
            "reference_speakers": ref.speakers(), "role_source": roles_src, "manual_txt": manual,
            "docent_reference_audio": str(S.DOCENT_REFERENCE_AUDIO),
            "docent_reference_sha256": L.sha256(S.DOCENT_REFERENCE_AUDIO)}


def pipeline_settings(src_cfg) -> dict:
    from dataclasses import asdict
    return {"transcription": asdict(src_cfg.TranscriptionConfig(model_size="medium")),
            "diarization": asdict(src_cfg.DiarizationConfig()),
            "preprocessing": asdict(src_cfg.PreprocessingConfig()),
            "docent_recognition": asdict(src_cfg.DocentRecognitionConfig(reference_audio=str(S.DOCENT_REFERENCE_AUDIO))),
            "note": "Identiek aan wat run_docent_pipeline.py doorgeeft: --model medium, geen min/max-speakers, geen --threshold."}


def load_models_smoke() -> dict:
    """Laadt de drie modellen zonder audio te verwerken (alleen de referentieclip van de docent wordt ingebed)."""
    import config as src_cfg
    import transcription, diarization, docent_recognition
    res = {}
    t0 = time.time()
    try:
        transcription.TranscriptionEngine(src_cfg.TranscriptionConfig(model_size="medium"))
        res["whisper_medium"] = {"ok": True, "seconds": round(time.time() - t0, 1)}
    except Exception as e:                                           # noqa: BLE001
        res["whisper_medium"] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}"}
    t0 = time.time()
    try:
        diarization.PyannoteBackend(src_cfg.DiarizationConfig())
        res["pyannote_diarization_3.1"] = {"ok": True, "seconds": round(time.time() - t0, 1)}
    except Exception as e:                                           # noqa: BLE001
        res["pyannote_diarization_3.1"] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}"}
    t0 = time.time()
    try:
        with tempfile.TemporaryDirectory() as td:
            wav = diarization.to_wav(S.DOCENT_REFERENCE_AUDIO, Path(td), False)
            docent_recognition.DocentReferenceRecognizer(wav, src_cfg.DocentRecognitionConfig(
                reference_audio=str(S.DOCENT_REFERENCE_AUDIO)).embedding_model)
        res["wespeaker_docent"] = {"ok": True, "seconds": round(time.time() - t0, 1)}
    except BaseException as e:                                       # noqa: BLE001 (to_wav kan sys.exit doen)
        res["wespeaker_docent"] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}"}
    return res


def run(fragment: str, eval_root: Path, run_id: str) -> int:
    inputs = resolve_inputs(fragment)
    fdir = L.new_dir(eval_root / "runs" / run_id / fragment)          # weigert als de map al bestaat
    import config as src_cfg
    import transcription, diarization, preprocessing, docent_recognition
    processed_before = L.tree_snapshot(S.REPO / "Data-local" / "processed")
    src_before = {p.name: L.sha256(p) for p in sorted(S.SRC.glob("*.py"))}
    refs_before = {p.name: L.sha256(p) for p in sorted(S.GT_DIR.glob("ground_truth_*.csv"))}

    manifest = {"protocol": PROTOCOL_VERSION, "fragment": fragment, "run_id": run_id,
                "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "command": sys.argv, "inputs": inputs, "pipeline_settings": pipeline_settings(src_cfg),
                "git": L.git_state(S.REPO), "environment": L.environment(S.SRC, token_present()),
                "seeds": "geen (de pipeline zet geen seed; Whisper-temperatuurfallback kan niet-deterministisch zijn)",
                "output_dir": str(fdir)}
    L.write_json_new(fdir / "run_manifest.json", manifest)
    (fdir / "logs").mkdir()
    stem = Path(inputs["audio_path"]).stem
    stages, ok = [], True

    def stage(name, module, argv, patches, outputs):
        nonlocal ok
        if not ok:
            stages.append({"stage": name, "status": "skipped_after_failure"})
            return
        r = L.run_original_main(module, argv, patches, fdir / "logs" / f"{name}.log")
        r.pop("stdout")
        r["name"] = name
        r["outputs"] = {k: (L.sha256(v) if v.exists() else None) for k, v in outputs.items()}
        if r["status"] == "ok" and any(h is None for h in r["outputs"].values()):
            r["status"] = "missing_output"
        stages.append(r)
        ok = r["status"] == "ok"

    t_json = fdir / "01_transcript" / f"{stem}.json"
    stage("01_transcribe", transcription, [Path(inputs["audio_path"]).name, "--dir", "test", "--model", "medium"],
          {"PROCESSED_DATA_DIR": fdir / "01_transcript"}, {"transcript": t_json})

    # ruwe pyannote-beurten vastleggen: wrapper om de methode, direct opgeslagen zodra het model klaar is
    orig = diarization.PyannoteBackend.diarize
    raw_json = fdir / "02_diarization" / "raw_turns.json"

    def capture(self, *a, **k):
        res = orig(self, *a, **k)
        (fdir / "02_diarization").mkdir(exist_ok=True)
        D.write_rttm(res.turns, stem, fdir / "02_diarization" / "raw_turns.rttm")
        L.write_json_new(raw_json, {"backend": res.backend, "model": res.model, "settings": res.settings,
                                    "runtime_seconds": res.runtime_seconds,
                                    "turns": [{"start": t.start, "end": t.end, "speaker": t.speaker} for t in res.turns]})
        return res
    diarization.PyannoteBackend.diarize = capture
    try:
        d_json = fdir / "02_diarization" / f"{stem}_diarized.json"
        (fdir / "02_diarization").mkdir(exist_ok=True)
        stage("02_diarize", diarization, ["--transcript", t_json, "--out", d_json, "--dir", "test"],
              {"DIARIZATION_OUTPUT_DIR": fdir / "wav"},
              {"diarized": d_json, "raw_turns_rttm": fdir / "02_diarization" / "raw_turns.rttm"})
    finally:
        diarization.PyannoteBackend.diarize = orig

    p_json = fdir / "03_preprocessing" / f"{stem}_diarized_turns.json"
    (fdir / "03_preprocessing").mkdir(exist_ok=True)
    stage("03_preprocess", preprocessing, ["--diarized", d_json, "--out", p_json],
          {"PREPROCESSING_OUTPUT_DIR": fdir / "03_preprocessing"}, {"turns": p_json})

    r_json = fdir / "04_docent" / f"{stem}_diarized_turns_docent_roles.json"
    (fdir / "04_docent").mkdir(exist_ok=True)
    stage("04_docent", docent_recognition,
          ["--processed", p_json, "--reference", S.DOCENT_REFERENCE_AUDIO, "--out", r_json],
          {"DIARIZATION_OUTPUT_DIR": fdir / "wav", "DOCENT_RECOGNITION_OUTPUT_DIR": fdir / "wav_ref"},
          {"docent_roles": r_json})

    processed_after = L.tree_snapshot(S.REPO / "Data-local" / "processed")
    src_after = {p.name: L.sha256(p) for p in sorted(S.SRC.glob("*.py"))}
    refs_after = {p.name: L.sha256(p) for p in sorted(S.GT_DIR.glob("ground_truth_*.csv"))}
    result = {"fragment": fragment, "run_id": run_id, "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "all_stages_ok": all(s.get("status") == "ok" for s in stages), "stages": stages,
              "no_touch_check": {"data_local_processed_diff": L.diff_snapshots(processed_before, processed_after),
                                 "src_py_unchanged": src_before == src_after,
                                 "reference_csv_unchanged": refs_before == refs_after}}
    L.write_json_new(fdir / "run_result.json", result)
    print(json.dumps({k: result[k] for k in ("fragment", "all_stages_ok")}, ensure_ascii=False))
    for s in stages:
        print(f"  {s.get('name', s.get('stage'))}: {s['status']} ({s.get('seconds', '-')} s)" + (f" -> {s['detail'][:200]}" if s.get("detail") else ""))
    print("no_touch_check:", json.dumps(result["no_touch_check"], ensure_ascii=False)[:400])
    return 0 if result["all_stages_ok"] else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fragment", required=True, choices=sorted(S.FRAGMENTS))
    ap.add_argument("--eval-root", default=str(S.EVAL_ROOT_DEFAULT))
    ap.add_argument("--run-id", default=None, help="verplicht voor een echte run")
    ap.add_argument("--preflight", action="store_true", help="controleer alleen; schrijft niets")
    ap.add_argument("--load-models", action="store_true", help="met --preflight: laad de modellen (geen audioverwerking)")
    ap.add_argument("--online", action="store_true", help="staat netwerktoegang tot Hugging Face toe (standaard offline)")
    a = ap.parse_args()
    if not a.online:
        os.environ["HF_HUB_OFFLINE"] = "1"
    sys.path.insert(0, str(S.SRC))
    if a.preflight:
        info = resolve_inputs(a.fragment)
        rep = {"inputs": info, "hf_token_present": token_present(), "hf_hub_offline": os.environ.get("HF_HUB_OFFLINE"),
               "environment": L.environment(S.SRC, token_present())}
        rd = Path(a.eval_root) / "runs"
        rep["eval_root_exists"] = Path(a.eval_root).exists()
        rep["run_dir_would_collide"] = bool(a.run_id and (rd / a.run_id / a.fragment).exists())
        if a.load_models:
            rep["model_load_smoke"] = load_models_smoke()
        print(json.dumps(rep, indent=2, ensure_ascii=False, default=str))
        return
    if not a.run_id:
        sys.exit("--run-id is verplicht voor een echte run (zo kan een run nooit per ongeluk een andere overschrijven).")
    sys.exit(run(a.fragment, Path(a.eval_root), a.run_id))


if __name__ == "__main__":
    main()
