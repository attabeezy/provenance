"""JSONL IO and corpus loaders shared across collectors and experiments."""
import json
from functools import lru_cache

from . import paths


def read_jsonl(path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def write_jsonl(path, rows) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def feat_rows(name: str) -> list[dict]:
    """Load a derived feature cache  analysis/feat_{name}.jsonl."""
    return read_jsonl(paths.feat_path(name))


def raw_texts(name: str) -> list[str]:
    """Raw text lists for the eight comparison corpora.

    Names: wiki_ai | wiki_human | hc3_ai | hc3_human | gutenberg |
    hn_pre | arxiv_pre | arxiv_post
    """
    if name in ("wiki_ai", "wiki_human"):
        key = "ai" if name == "wiki_ai" else "human"
        return [r[key] for r in read_jsonl(paths.WIKI_PAIRS)]
    if name in ("hc3_ai", "hc3_human"):
        key = "ai" if name == "hc3_ai" else "human"
        return [r[key] for r in read_jsonl(paths.HC3_PAIRS)]
    if name == "gutenberg":
        return [r["text"] for r in read_jsonl(paths.GUTENBERG_SEGMENTS)]
    if name == "hn_pre":
        return [r["text"] for r in read_jsonl(paths.HN_COMMENTS)
                if 2015 <= r["year"] <= 2019]
    if name in ("arxiv_pre", "arxiv_post"):
        lo, hi = (2010, 2019) if name == "arxiv_pre" else (2023, 2026)
        return [r["text"] for r in read_jsonl(paths.ARXIV_ABSTRACTS)
                if lo <= r["year"] <= hi]
    raise KeyError(name)
