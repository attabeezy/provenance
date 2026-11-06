"""E1: Marker time-series in HN comments and arXiv abstracts.

Pools text per year per corpus, computes marker rates with 95% Poisson
CIs, writes analysis/e1_timeseries.json and figures/e1_*.png.

Rates: per 100K words for word-level markers (delve, core slop,
moreover), per 1K words for em-dash and triads.
"""
import collections
import json
import math

from .. import corpora, paths
from ..features import extract


def pooled_year_rates(texts):
    """Pool all texts, return rates + Poisson 95% CI half-widths."""
    n_words = 0
    counts = collections.Counter()
    for t in texts:
        f = extract(t)
        n_words += f["n_words"]
        counts["emdash"] += f["n_emdash"]
        counts["notxbut"] += f["n_notxbut"]
        counts["notonly"] += f["n_notonly"]
        counts["triad"] += f["n_triad"]
        counts["core"] += f["n_core"]
        counts["lex"] += f["n_lex"]
        counts["moreover"] += f["n_lexicon"].get("moreover", 0)
        counts["delve"] += (
            f["n_lexicon"].get("delve", 0) + f["n_lexicon"].get("delves", 0)
            + f["n_lexicon"].get("delving", 0) + f["n_lexicon"].get("delved", 0)
        )
    n = max(n_words, 1)

    def rate_ci(k, scale):
        r = k / n * scale
        ci = 1.96 * math.sqrt(k) / n * scale if k > 0 else 1.96 * 1.0 / n * scale
        return {"rate": r, "ci": ci, "count": k}

    return {
        "n_docs": len(texts),
        "n_words": n_words,
        "emdash_per_1k": rate_ci(counts["emdash"], 1000),
        "triad_per_1k": rate_ci(counts["triad"], 1000),
        "core_per_100k": rate_ci(counts["core"], 100000),
        "delve_per_100k": rate_ci(counts["delve"], 100000),
        "moreover_per_100k": rate_ci(counts["moreover"], 100000),
        "notxbut_per_100k": rate_ci(counts["notxbut"], 100000),
        "notonly_per_100k": rate_ci(counts["notonly"], 100000),
    }


def main():
    result = {}
    for name, path in [("hn", paths.HN_COMMENTS), ("arxiv", paths.ARXIV_ABSTRACTS)]:
        rows = corpora.read_jsonl(path)
        by_year = collections.defaultdict(list)
        for r in rows:
            by_year[r["year"]].append(r["text"])
        result[name] = {
            str(y): pooled_year_rates(texts)
            for y, texts in sorted(by_year.items())
        }
        # sanity: total words
        tw = sum(v["n_words"] for v in result[name].values())
        print(f"{name}: {len(rows)} docs, {tw:,} words, "
              f"years {min(by_year)}-{max(by_year)}")
    with open(paths.E1_TIMESERIES, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
    print("wrote", paths.E1_TIMESERIES)


if __name__ == "__main__":
    main()
