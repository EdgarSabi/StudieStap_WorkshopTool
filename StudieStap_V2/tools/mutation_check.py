"""Bewust fouten inbouwen om te controleren dat de tests ze afkeuren.

Voor elke "mutatie" wordt een stukje broncode tijdelijk vervangen door een foutieve
versie. Daarna draaien de tests: ze MOETEN dan falen. Slaagt de testset toch, dan
is die zwak op dat punt ("overleefde mutatie"). Het bronbestand wordt altijd hersteld.

Gebruik:   python tools/mutation_check.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "studiestap"

# (bestand, originele tekst, foutieve tekst, wat gaat er mis)
MUTATIONS = [
    ("alignment/speakers.py", "if end > start:\n            out.append(Intersection",
     "if end > start + 100:\n            out.append(Intersection", "intersecties worden weggegooid"),
    ("alignment/speakers.py", "if not tie:", "if True:", "bij gelijkspel toch een dominante spreker kiezen"),
    ("alignment/speakers.py", "status=\"AMBIGUOUS\", speaker=None, candidates=candidates)",
     "status=\"AMBIGUOUS\", speaker=candidates[0], candidates=candidates)", "twijfelwoord toch aan eerste spreker geven"),
    ("alignment/speakers.py", "return WordSpeaker(index, text, start, end, status=\"NO_TIMING\")",
     "return WordSpeaker(index, text, start, end, status=\"SINGLE\", speaker=\"SPEAKER_00\")", "woord zonder tijd toch toewijzen"),
    ("alignment/speakers.py", "per_speaker_spans = {k: _merge(v) for k, v in sorted(per_speaker_spans.items())}",
     "per_speaker_spans = {k: v for k, v in sorted(per_speaker_spans.items())}", "zelfde spreker dubbel tellen"),
    ("pipeline.py", "if prev.get(\"fingerprint\") != fingerprint or", "if False or",
     "cache negeert gewijzigde instellingen"),
    ("pipeline.py", "if self.force or fingerprint is None", "if fingerprint is None", "--force werkt niet"),
    ("pipeline.py", "shutil.rmtree(work_dir, ignore_errors=True)  # privacy", "pass  # privacy",
     "audiokopie blijft staan"),
    ("output/exporter.py", "if not (run_dir / MANIFEST_NAME).exists():", "if False:", "elke map mag verwijderd worden"),
    ("output/exporter.py", "tmp.write_bytes(data)", "tmp.write_text(data.decode('utf-8'), encoding='utf-8')",
     "hash klopt niet meer met bestand (Windows regeleinden)"),
    ("recognition/teacher.py", "roles.append(SpeakerRole(speaker, \"NO_MATCH\", \"onbekend\"",
     "roles.append(SpeakerRole(speaker, \"NO_MATCH\", \"leerling\"", "niet-docent automatisch leerling noemen"),
    ("recognition/teacher.py", "if sim >= settings.similarity_threshold:", "if True:", "iedereen is docent"),
    ("recognition/teacher.py", "if other.speaker == target.speaker:\n            continue",
     "if False:\n            continue", "eigen interval van het fragment aftrekken"),
    ("quality/checks.py", "if any(s.code == \"EMPTY_TEXT\" for s in sigs):", "if False:", "lege tekst wel beoordeelbaar"),
    ("quality/checks.py", "elif sigs:\n            status = ReviewStatus.REVIEW_REQUIRED",
     "elif False:\n            status = ReviewStatus.REVIEW_REQUIRED", "signalen leiden niet tot review"),
    ("settings.py", "if key not in allowed:", "if False:", "typfout in config.yaml wordt genegeerd"),
    ("diarization/pyannote.py", "for seg, _track, label in annotation.itertracks(yield_label=True)",
     "for seg, _track, label in list(annotation.itertracks(yield_label=True))[:1]", "ruwe intervallen weggooien"),
    ("alignment/words.py", "key=lambda s: min(a1, s.end) - max(a0, s.start))", "key=lambda s: -s.id)",
     "woorden aan verkeerd segment hangen"),
    ("classification/indicators.py", "\"status\": \"NOT_IMPLEMENTED\" if not indicators else \"RAN\"",
     "\"status\": \"DETECTED\"", "lege classificatie meldt een detectie"),
]


def main() -> int:
    survivors = []
    for rel, old, new, what in MUTATIONS:
        path = SRC / rel
        original = path.read_text(encoding="utf-8")
        if old not in original:
            print(f"[SKIP ] {rel}: te vervangen tekst niet gevonden ({what})")
            survivors.append((rel, what + " [niet toegepast]"))
            continue
        try:
            path.write_text(original.replace(old, new, 1), encoding="utf-8")
            r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "--no-header", "-p", "no:cacheprovider"],
                               cwd=ROOT, capture_output=True, text=True)
        finally:
            path.write_text(original, encoding="utf-8")
        killed = r.returncode != 0
        print(f"[{'GEDOOD' if killed else 'OVERLEEFD'}] {rel}: {what}")
        if not killed:
            survivors.append((rel, what))
    print()
    print(f"{len(MUTATIONS) - len(survivors)} van {len(MUTATIONS)} bewuste fouten werden door de tests afgekeurd.")
    for rel, what in survivors:
        print(f"  ZWAK PUNT: {rel}: {what}")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
