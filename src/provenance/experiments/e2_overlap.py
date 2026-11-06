"""E2: Human/AI overlap, pooled-rate comparison + per-doc continuous stats.

Pooled rates (per 1K/100K words) with 95% Poisson CIs for each corpus;
per-doc distributions for length-robust features (sentence length, TTR).
Output: analysis/e2_overlap.json + figures/e2_overlap.png/.pdf
"""
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .. import corpora, paths
from ..features import extract

CORPORA = ["wiki_ai", "hc3_ai", "wiki_human", "hc3_human", "gutenberg",
           "hn_pre", "arxiv_pre", "arxiv_post"]
LABELS = {
    "wiki_ai": "AI: GPT-3.5 completions (wiki style)",
    "hc3_ai": "AI: ChatGPT 3.5-turbo (Q&A chat)",
    "wiki_human": "Human: Wikipedia intros",
    "hc3_human": "Human: pre-ChatGPT Q&A answers",
    "gutenberg": "Human: pre-LLM classics (Gutenberg)",
    "hn_pre": "Human: HN comments 2015-19",
    "arxiv_pre": "Human: arXiv cs.CL 2010-19",
    "arxiv_post": "Human(+AI?): arXiv cs.CL 2023-26",
}

POOLED = [
    ("emdash", "n_emdash", 1000, "em-dashes / 1K words"),
    ("core", "n_core", 1000, "slop lexicon / 1K words"),
    ("triad", "n_triad", 1000, "rule-of-three / 1K words"),
    ("notxbut", "n_notxbut", 10000, "not-X-but-Y / 10K words"),
    ("notonly", "n_notonly", 10000, "not-only-but-also / 10K words"),
    ("moreover", None, 100000, "moreover / 100K words"),
    ("delve", None, 100000, "delve family / 100K words"),
]


def corpus_texts():
    """Raw text lists for all eight corpora."""
    tx = {name: [] for name in CORPORA}
    with open(paths.WIKI_PAIRS, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            tx["wiki_ai"].append(r["ai"])
            tx["wiki_human"].append(r["human"])
    with open(paths.GUTENBERG_SEGMENTS, encoding="utf-8") as f:
        for line in f:
            tx["gutenberg"].append(json.loads(line)["text"])
    with open(paths.HN_COMMENTS, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if 2015 <= r["year"] <= 2019:
                tx["hn_pre"].append(r["text"])
    with open(paths.HC3_PAIRS, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            tx["hc3_human"].append(r["human"])
            tx["hc3_ai"].append(r["ai"])
    with open(paths.ARXIV_ABSTRACTS, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if 2010 <= r["year"] <= 2019:
                tx["arxiv_pre"].append(r["text"])
            elif 2023 <= r["year"] <= 2026:
                tx["arxiv_post"].append(r["text"])
    return tx


def main():
    cache = {name: corpora.feat_rows(name) for name in CORPORA}
    texts = corpus_texts()

    result = {"pooled": {}, "per_doc": {}}
    for name in CORPORA:
        tx = texts[name]
        agg = {"n_words": 0}
        for key in ["n_emdash", "n_triad", "n_notxbut", "n_notonly", "n_core"]:
            agg[key] = 0
        delve_keys = ["delve", "delves", "delving", "delved"]
        agg["delve"] = 0
        agg["moreover"] = 0
        for t in tx:
            f = extract(t)
            agg["n_words"] += f["n_words"]
            for key in ["n_emdash", "n_triad", "n_notxbut", "n_notonly", "n_core"]:
                agg[key] += f[key]
            agg["delve"] += sum(f["n_lexicon"].get(k, 0) for k in delve_keys)
            agg["moreover"] += f["n_lexicon"].get("moreover", 0)
        n = agg["n_words"]
        entry = {"n_docs": len(tx), "n_words": n}
        for pname, key, scale, label in POOLED:
            k = agg[key] if key else agg[pname]
            rate = k / n * scale
            ci = 1.96 * math.sqrt(k) / n * scale if k > 0 else 3.0 / n * scale
            entry[pname] = {"rate": rate, "ci": ci, "count": k, "label": label}
        result["pooled"][name] = entry

        # per-doc continuous stats (length-robust)
        rows = cache[name]
        sl = [r["mean_sent_len"] for r in rows]
        tt = [r["ttr"] for r in rows]
        mw = [r["mean_word_len"] for r in rows]
        st = [r["std_sent_len"] for r in rows]
        entry_doc = {
            "mean_sent_len": {"mean": sum(sl) / len(sl), "n": len(sl)},
            "ttr": {"mean": sum(tt) / len(tt)},
            "mean_word_len": {"mean": sum(mw) / len(mw)},
            "std_sent_len": {"mean": sum(st) / len(st)},
        }
        result["per_doc"][name] = entry_doc

    with open(paths.E2_OVERLAP, "w") as fo:
        json.dump(result, fo, indent=1)

    # report
    print(f"{'corpus':>11} {'words':>9} " + " ".join(f"{p:>13}" for p, _, _, _ in POOLED))
    for name in CORPORA:
        e = result["pooled"][name]
        row = f"{name:>11} {e['n_words']:>9,} "
        for pname, _, _, _ in POOLED:
            row += f"{e[pname]['rate']:>13.2f}"
        print(row)
    print()
    for name in CORPORA:
        d = result["per_doc"][name]
        print(f"{name:>11}: mean_sent={d['mean_sent_len']['mean']:.1f} "
              f"std_sent={d['std_sent_len']['mean']:.1f} "
              f"ttr={d['ttr']['mean']:.3f} word_len={d['mean_word_len']['mean']:.2f}")

    # figure: pooled rates with CI, grouped bars (log scale)
    plt.rcParams.update({
        "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
        "figure.dpi": 200, "savefig.bbox": "tight",
    })
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    feats = ["emdash", "core", "triad", "notxbut", "moreover", "delve"]
    width = 0.12
    colors = {
        "wiki_ai": "#D55E00", "hc3_ai": "#E69F00", "wiki_human": "#009E73",
        "hc3_human": "#F0E442", "gutenberg": "#0072B2", "hn_pre": "#56B4E9",
        "arxiv_pre": "#CC79A7", "arxiv_post": "#999999",
    }
    for ci_, name in enumerate(CORPORA):
        xs, ys, es = [], [], []
        for fi, feat in enumerate(feats):
            e = result["pooled"][name][feat]
            xs.append(fi + (ci_ - (len(CORPORA) - 1) / 2) * width)
            ys.append(max(e["rate"], 1e-3))
            es.append(e["ci"])
        ax.bar(xs, ys, width=width, yerr=es, color=colors[name],
               label=LABELS[name], capsize=1.5, error_kw={"lw": 0.8})
    ax.set_yscale("log")
    ax.set_xticks(range(len(feats)))
    ax.set_xticklabels(["em-dash\n/1K", "slop lexicon\n/1K", "triads\n/1K",
                        "not-X-but-Y\n/10K", "moreover\n/100K", "delve\n/100K"],
                       fontsize=8)
    ax.set_ylabel("pooled rate (log scale)", fontsize=8)
    ax.legend(frameon=False, fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(paths.figure_path("e2_overlap.png"))
    fig.savefig(paths.figure_path("e2_overlap.pdf"))
    print("saved", paths.figure_path("e2_overlap.png"))


if __name__ == "__main__":
    main()
