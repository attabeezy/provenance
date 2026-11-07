"""Synthetic tests for the vintage-corpus collection filter (E5).

These must pass on a fresh clone without the (gitignored) raw data.
"""
from provenance.collect import gpt2_filter_rows


def _long_doc(words=120, flag=True, token="tok"):
    d = {"text": " ".join([token] * words)}
    if flag is not None:
        d["ended"] = flag
    return d


def test_filter_drops_short_and_cut_rows():
    docs = [
        {"text": "one two three four five", "ended": True},   # < 60 words
        _long_doc(flag=False),                                # cut mid-sentence
        _long_doc(flag=True, token="alpha"),                  # keep
        _long_doc(flag=None, token="beta"),                   # keep (no flag)
        {"text": "", "ended": True},                          # empty
    ]
    kept = gpt2_filter_rows(docs)
    assert len(kept) == 2
    assert kept[0]["text"].split()[0] == "alpha"
    assert kept[1]["text"].split()[0] == "beta"
    assert kept[1]["ended"] is True


def test_filter_respects_cap_and_normalizes_whitespace():
    docs = [_long_doc(flag=True, token=f"tok{i}") for i in range(10)]
    docs.append({"text": "a\nwhole  bunch\n\nof   words " * 20, "ended": True})
    kept = gpt2_filter_rows(docs, cap=3)
    assert len(kept) == 3
    kept_all = gpt2_filter_rows(docs)
    normalized = [d["text"] for d in kept_all if d["text"].startswith("a")]
    assert len(normalized) == 1
    assert "\n" not in normalized[0] and "  " not in normalized[0]
