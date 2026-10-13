"""Onafhankelijke kruiscontrole van baseline_eval.text tegen jiwer. Draaien in de ISOLATIE-venv (alleen jiwer geïnstalleerd):

    Data-analysis/Experiments/baseline_evaluation/.venv-eval/Scripts/python.exe -B crosscheck_jiwer.py

Vergelijkt S/D/I-tellingen (WER) en foutaantallen (CER) op (a) willekeurige woordrijen en (b) echte tekstparen uit
bestaande bestanden (alleen gelezen). Normalisatie gebeurt eerst met onze functie; jiwer wordt alleen voor de afstandsberekening gebruikt.
"""
import json
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import jiwer                                                              # noqa: E402
from baseline_eval import text as T                                       # noqa: E402

REPO = HERE.parents[2]


def compare(ref: str, hyp: str, tag: str, bad: list) -> None:
    r, h = T.normalize(ref), T.normalize(hyp)
    if not r:
        return
    o = jiwer.process_words(r, h if h else "")
    ours = T.wer(ref, hyp)
    jw = (o.substitutions, o.deletions, o.insertions)
    ow = (ours["substitutions"], ours["deletions"], ours["insertions"])
    oc = jiwer.process_characters(r, h)
    jc = oc.substitutions + oc.deletions + oc.insertions
    cc = T.cer(ref, hyp)["errors"]
    # Bij gelijke minimale afstand kunnen S/D/I-verdelingen verschillen; de totale afstand moet altijd gelijk zijn.
    if sum(jw) != sum(ow) or jc != cc:
        bad.append((tag, jw, ow, jc, cc))


def main():
    bad, n = [], 0
    rnd = random.Random(12345)
    vocab = "de kat zit op mat hond ja nee dat is een klas docent leerling vier brommer probleem".split()
    for i in range(500):
        ref = " ".join(rnd.choice(vocab) for _ in range(rnd.randint(1, 15)))
        hyp = " ".join(rnd.choice(vocab) for _ in range(rnd.randint(0, 15)))
        compare(ref, hyp, f"random{i}", bad)
        n += 1
    proc = REPO / "Data-local" / "processed"
    for p in sorted(proc.glob("testaudio*_fragment.json")):
        segs = json.loads(p.read_text(encoding="utf-8"))["segments"]
        words = " ".join(s["text"] for s in segs)
        compare(words, words, f"{p.name}:identiek", bad); n += 1
        half = " ".join(s["text"] for s in segs[::2])
        compare(words, half, f"{p.name}:halve-tekst", bad); n += 1
        compare(words, " ".join(reversed(words.split())), f"{p.name}:omgekeerd", bad); n += 1
    for p in sorted((REPO / "Data-local" / "raw").glob("testaudio*_manual.txt")):
        t = p.read_text(encoding="utf-8")
        compare(t, t.replace("ja", "nee"), f"{p.name}:ja->nee", bad); n += 1
    print(f"jiwer {jiwer.__version__ if hasattr(jiwer, '__version__') else '4.0.0'}; paren vergeleken: {n}; afwijkingen: {len(bad)}")
    for b in bad[:10]:
        print("  AFWIJKING", b)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
