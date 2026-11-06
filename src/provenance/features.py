"""Marker-based feature extraction for AI-writing stylometry.

Transparent, count-based features (the folk list of "AI tells"),
plus classical measures (lexical diversity, sentence burstiness).
All rates are normalized downstream; this module returns raw counts
and text statistics per document.
"""
import re
import unicodedata

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")
SENT_RE = re.compile(r"[^.!?]+[.!?]+|[^.!?]+$")

AI_LEXICON = [
    "delve", "delves", "delving", "delved",
    "moreover", "furthermore", "additionally",
    "tapestry", "testament", "pivotal", "crucial", "underscore",
    "underscores", "underscoring", "myriad", "foster", "fosters",
    "fostering", "leverage", "leveraging", "robust", "intricate",
    "intricacies", "multifaceted", "realm", "embark", "journey",
    "landscape", "elevate", "elevating", "harness", "harnessing",
    "unlock", "unlocking", "seamless", "seamlessly", "holistic",
    "actionable", "streamline", "streamlining", "paramount",
    "instrumental", "navigate", "navigating", "navigates",
    "notably", "significantly", "comprehensive", "profound",
    "profoundly", "vital", "essential", "noteworthy", "commendable",
    "boast", "boasts", "thriving", "bustling", "gem", "treasure trove",
    "in conclusion", "in summary", "it is important to note",
    "it's important to note", "keep in mind", "when it comes to",
]

CORE_SLOP = [
    "delve", "delves", "delving", "delved",
    "tapestry", "testament", "pivotal", "underscore",
    "underscores", "underscoring", "myriad", "foster", "fosters",
    "fostering", "leverage", "leveraging", "robust", "intricate",
    "intricacies", "multifaceted", "realm", "embark", "elevate",
    "elevating", "harness", "harnessing", "unlock", "unlocking",
    "seamless", "seamlessly", "holistic", "streamline", "streamlining",
    "treasure trove", "bustling",
]

NOT_X_BUT_Y_RE = re.compile(
    r"\bnot\s+(?:just\s+|only\s+)?(?:\w+[\w\-]*\s+){0,4}?[\w\-]+,?\s+but\b",
    re.IGNORECASE,
)
NOT_ONLY_BUT_RE = re.compile(
    r"\bnot only\b[^.!?]{0,80}?\bbut\b[^.!?]{0,20}?\balso\b", re.IGNORECASE
)
TRIAD_RE = re.compile(
    r",\s+(?:and\s+)?[A-Za-z][A-Za-z\-]*\s*,\s+and\s+[A-Za-z][A-Za-z\-]*"
)
EMDASH_CHARS = ("\u2014", "\u2013")
EMDASH_ASCII_RE = re.compile(r"(?<=\w)\s*--\s*(?=\w)")

# Rate-normalized feature keys used by the folk classifier (E3 / meta-audit).
FEATURE_KEYS = [
    "emdash_per_1k", "core_per_1k", "triad_per_1k",
    "notxbut_per_10k", "notonly_per_10k",
    "mean_sent_len", "std_sent_len", "ttr", "mean_word_len",
]


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    return text


def words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT_RE.findall(text) if s.strip()]


def emdash_count(text: str) -> int:
    n = sum(text.count(c) for c in EMDASH_CHARS)
    n += len(EMDASH_ASCII_RE.findall(text))
    return n


def extract(text: str) -> dict:
    """Return raw counts + basic stats for one document."""
    text = normalize(text)
    wds = words(text)
    sents = sentences(text)
    n_words = len(wds)
    lowered = text.lower()
    lex_counts = {}
    for term in AI_LEXICON:
        if " " in term:
            lex_counts[term] = lowered.count(term)
        else:
            lex_counts[term] = len(re.findall(rf"\b{re.escape(term)}\b", lowered))
    sent_lens = [len(words(s)) for s in sents] if sents else [0]
    mean_sent = sum(sent_lens) / len(sent_lens)
    var_sent = (
        sum((x - mean_sent) ** 2 for x in sent_lens) / len(sent_lens)
        if len(sent_lens) > 1 else 0.0
    )
    return {
        "n_words": n_words,
        "n_sents": len(sents),
        "n_emdash": emdash_count(text),
        "n_notxbut": len(NOT_X_BUT_Y_RE.findall(text)),
        "n_notonly": len(NOT_ONLY_BUT_RE.findall(text)),
        "n_triad": len(TRIAD_RE.findall(text)),
        "n_lex": sum(lex_counts.values()),
        "n_lexicon": lex_counts,
        "n_core": sum(lex_counts.get(t, 0) for t in CORE_SLOP),
        "mean_sent_len": mean_sent,
        "std_sent_len": var_sent ** 0.5,
        "mean_word_len": (
            sum(len(w) for w in wds) / n_words if n_words else 0.0
        ),
        "ttr": (len(set(w.lower() for w in wds)) / n_words) if n_words else 0.0,
    }


def rates(f: dict) -> dict:
    """Convert raw counts to per-1K-word rates (rare items per 10K)."""
    n = max(f["n_words"], 1)
    return {
        "emdash_per_1k": f["n_emdash"] / n * 1000,
        "notxbut_per_10k": f["n_notxbut"] / n * 10000,
        "notonly_per_10k": f["n_notonly"] / n * 10000,
        "triad_per_1k": f["n_triad"] / n * 1000,
        "lex_per_1k": f["n_lex"] / n * 1000,
        "core_per_1k": f.get("n_core", 0) / n * 1000,
        "delve_per_100k": (
            f["n_lexicon"].get("delve", 0) + f["n_lexicon"].get("delves", 0)
            + f["n_lexicon"].get("delving", 0) + f["n_lexicon"].get("delved", 0)
        ) / n * 100000,
        "moreover_per_100k": f["n_lexicon"].get("moreover", 0) / n * 100000,
        "mean_sent_len": f["mean_sent_len"],
        "std_sent_len": f["std_sent_len"],
        "ttr": f["ttr"],
        "mean_word_len": f["mean_word_len"],
        "n_words": f["n_words"],
    }


def full(text: str) -> dict:
    return rates(extract(text))
