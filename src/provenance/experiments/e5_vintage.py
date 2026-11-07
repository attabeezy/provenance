"""E5: vintage test - how do 2023-era detectors score 2019-era text?

Refits the E3 detector families (folk | tfidf | char) on each 2023-era
training pair:

  W  wiki_ai vs wiki_human     (GPT-wiki-intro, davinci-003 era)
  H  hc3_ai vs hc3_human       (HC3, ChatGPT era)

then scores one pre-ChatGPT generation, taken from a single fixed archive
(OpenAI gpt-2-output-dataset v1, files frozen 2020-12-02):

  gpt2_ai        natural samples of the largest released GPT-2 (xl-1542M)
  webtext_human  human WebText documents shipped in the same release

For each pair x family, the in-domain 95%/99% TPR thresholds of the
2023-era model are computed as in E3, then reported on the vintage corpora:

  recall@95       fraction of gpt2_ai flagged at the 95% threshold
  recall@99       same at the 99% threshold
  fpr@95, fpr@99  fraction of webtext_human flagged at those thresholds
  vintage_auc     AUC of gpt2_ai (positives) vs webtext_human (negatives)

Mean folk-marker rates per corpus (vintage vs 2023 pairs) are included so
the marker movement between model generations reads like E1-E2.

Output: analysis/e5_vintage.json
"""
import json
import time

import numpy as np
from sklearn.metrics import roc_auc_score

from .. import corpora, paths
from . import e3_detector
from .detectors import fit_folk, fpr_at, matrix, threshold_for_tpr

VINTAGE_PAIRS = ["gpt2_ai", "webtext_human"]
MARKERS = ["emdash_per_1k", "core_per_1k", "triad_per_1k"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def marker_rates():
    rates = {}
    for name in ["wiki_ai", "wiki_human", "hc3_ai", "hc3_human",
                 "gpt2_ai", "webtext_human"]:
        rows = corpora.feat_rows(name)
        rates[name] = {m: float(np.mean([r[m] for r in rows]))
                       for m in MARKERS}
    return rates


def vintage_block(scores_g2, scores_wt, thr95, thr99, y):
    return {
        "recall@95": float(np.mean(scores_g2 >= thr95)),
        "recall@99": float(np.mean(scores_g2 >= thr99)),
        "fpr@95": fpr_at(scores_wt, thr95),
        "fpr@99": fpr_at(scores_wt, thr99),
        "vintage_auc": float(roc_auc_score(
            y, np.concatenate([scores_g2, scores_wt]))),
    }


def main():
    feat = {n: corpora.feat_rows(n) for n in VINTAGE_PAIRS}
    texts = {n: corpora.raw_texts(n) for n in VINTAGE_PAIRS}
    for n in VINTAGE_PAIRS:
        assert len(feat[n]) == len(texts[n]), f"{n}: cache/text mismatch"
    y = np.array([1] * len(feat["gpt2_ai"])
                 + [0] * len(feat["webtext_human"]))

    result = {
        "y_counts": {n: len(feat[n]) for n in VINTAGE_PAIRS},
        "marker_rates": marker_rates(),
    }

    pairs = {}
    for tag, ai_name, hu_name in [("W", "wiki_ai", "wiki_human"),
                                  ("H", "hc3_ai", "hc3_human")]:
        pairs[tag] = (corpora.feat_rows(ai_name), corpora.feat_rows(hu_name),
                      corpora.raw_texts(ai_name), corpora.raw_texts(hu_name))

    for tag in ["W", "H"]:
        ai_rows, hu_rows, ai_texts, hu_texts = pairs[tag]
        entry = {}

        log(f"{tag}: fitting folk")
        m = fit_folk(ai_rows, hu_rows)
        thr95 = threshold_for_tpr(m["y_te"], m["probs_te"], 0.95)
        thr99 = threshold_for_tpr(m["y_te"], m["probs_te"], 0.99)

        def score_folk(rows):
            return m["clf"].predict_proba(
                m["scaler"].transform(matrix(rows)))[:, 1]

        entry["folk"] = vintage_block(
            score_folk(feat["gpt2_ai"]), score_folk(feat["webtext_human"]),
            thr95, thr99, y)

        for kind in ["tfidf", "char"]:
            log(f"{tag}: fitting {kind}")
            m2 = e3_detector.fit_text(ai_texts, hu_texts, kind)
            thr95 = threshold_for_tpr(m2["y_te"], m2["probs_te"], 0.95)
            thr99 = threshold_for_tpr(m2["y_te"], m2["probs_te"], 0.99)
            entry[kind] = vintage_block(
                m2["score_texts"](texts["gpt2_ai"]),
                m2["score_texts"](texts["webtext_human"]),
                thr95, thr99, y)
            log(f"{tag}: {kind} done")

        result[tag] = entry
        with open(paths.E5_VINTAGE, "w") as f:
            json.dump(result, f, indent=1)
        log(f"{tag}: written partial results")

    print(f"corpus sizes: {result['y_counts']}")
    print("marker rates (per 1K words):")
    for name, rates in result["marker_rates"].items():
        print(f"  {name:15s} emdash {rates['emdash_per_1k']:.2f} | "
              f"core {rates['core_per_1k']:.2f} | "
              f"triad {rates['triad_per_1k']:.2f}")
    for tag in ["W", "H"]:
        for kind in ["folk", "tfidf", "char"]:
            r = result[tag][kind]
            print(f"##### {tag} [{kind:5s}] "
                  f"recall@95 {r['recall@95']:.3f} @99 {r['recall@99']:.3f} | "
                  f"webtext fpr@95 {r['fpr@95']:.3f} @99 {r['fpr@99']:.3f} | "
                  f"vintage AUC {r['vintage_auc']:.3f}")


if __name__ == "__main__":
    main()
