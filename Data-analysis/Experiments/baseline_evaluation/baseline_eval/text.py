"""WER/CER zonder externe dependencies (onafhankelijk gecontroleerd tegen jiwer in crosscheck_jiwer.py)."""
import re
import unicodedata

# Aarzelgeluiden (verwijderd in de primaire variant). Lexicale tussenwerpsels (ja, nee, oh, ah, hè, wow) blijven staan.
FILLERS = frozenset({"uh", "uhh", "uhm", "euh", "euhm", "eh", "ehh", "ehm", "hm", "hmm", "hmmm", "mm", "mmm", "mhm"})
_BRACKETS = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_PUNCT = re.compile(r"[^\w\s']", re.UNICODE)


def normalize_tokens(text: str, remove_fillers: bool = True) -> list:
    t = unicodedata.normalize("NFKC", text or "").casefold()
    t = t.replace("’", "'").replace("‘", "'").replace("`", "'")
    t = _BRACKETS.sub(" ", t)            # (moeilijk te volgen), [applaus], ...
    t = t.replace("-", " ").replace("_", " ")
    t = _PUNCT.sub(" ", t)
    toks = [w.strip("'") for w in t.split()]
    toks = [w for w in toks if w]
    if remove_fillers:
        toks = [w for w in toks if w not in FILLERS]
    return toks


def normalize(text: str, remove_fillers: bool = True) -> str:
    return " ".join(normalize_tokens(text, remove_fillers))


def edit_counts(ref: list, hyp: list) -> dict:
    """Levenshtein met teruglopen -> substituties/deleties/insertions (S+D+I = minimale afstand)."""
    n, m = len(ref), len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            c = 0 if ref[i - 1] == hyp[j - 1] else 1
            d[i][j] = min(d[i - 1][j - 1] + c, d[i - 1][j] + 1, d[i][j - 1] + 1)
    i, j, s, dl, ins = n, m, 0, 0, 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (0 if ref[i - 1] == hyp[j - 1] else 1):
            s += 0 if ref[i - 1] == hyp[j - 1] else 1
            i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            dl += 1
            i -= 1
        else:
            ins += 1
            j -= 1
    return {"errors": d[n][m], "substitutions": s, "deletions": dl, "insertions": ins}


def _result(counts: dict, ref_len: int, hyp_len: int, unit: str) -> dict:
    out = dict(counts, ref_len=ref_len, hyp_len=hyp_len, unit=unit)
    # Lege referentie: geen deling door nul; expliciet None met reden (nooit stil 0).
    out["rate"] = counts["errors"] / ref_len if ref_len else None
    if not ref_len:
        out["note"] = "lege referentie: percentage niet gedefinieerd"
    return out


def wer(reference: str, hypothesis: str, remove_fillers: bool = True) -> dict:
    r, h = normalize_tokens(reference, remove_fillers), normalize_tokens(hypothesis, remove_fillers)
    return _result(edit_counts(r, h), len(r), len(h), "words")


def cer(reference: str, hypothesis: str, remove_fillers: bool = True) -> dict:
    r, h = list(normalize(reference, remove_fillers)), list(normalize(hypothesis, remove_fillers))
    return _result(edit_counts(r, h), len(r), len(h), "chars")
