"""E3: Mini-detector - folk markers vs TF-IDF baselines.

Classifier families x matched training pairs:
  families: folk (9 hand-crafted markers, logreg) | tfidf (word 1-2grams)
            | char (char_wb 3-5grams)
  pairs:    W = wiki_ai vs wiki_human | H = hc3_ai vs hc3_human

Reports in-domain AUC, cross-pair transfer AUC, FPR on human test
corpora at 95%/99% in-domain TPR thresholds, FPR by Gutenberg author,
top folk weights and top TF-IDF terms.
Output: analysis/e3_detector.json, figures/e3_fpr_by_author.png
"""
import collections
import json
import time

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from .. import corpora, paths
from .detectors import fit_folk, threshold_for_tpr, fpr_at, matrix

TEST_SETS = ["gutenberg", "hn_pre", "arxiv_pre", "arxiv_post"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def fit_text(ai_texts, hu_texts, kind):
    spec = {
        "tfidf": dict(analyzer="word", ngram_range=(1, 2), min_df=5,
                      sublinear_tf=True),
        "char": dict(analyzer="char_wb", ngram_range=(3, 5), min_df=5,
                     max_features=100000, sublinear_tf=True),
    }[kind]
    texts = ai_texts + hu_texts
    y = np.array([1] * len(ai_texts) + [0] * len(hu_texts))
    idx = np.arange(len(texts))
    idx_tr, idx_te = train_test_split(
        idx, test_size=0.2, random_state=13, stratify=y)
    vec = TfidfVectorizer(**spec)
    X_tr = vec.fit_transform([texts[i] for i in idx_tr])
    clf = LogisticRegression(max_iter=500, C=1.0)
    clf.fit(X_tr, y[idx_tr])
    X_te = vec.transform([texts[i] for i in idx_te])
    probs_te = clf.predict_proba(X_te)[:, 1]
    model = {
        "kind": kind, "vec": vec, "clf": clf,
        "y_te": y[idx_te], "probs_te": probs_te,
        "score_texts": lambda ts: clf.predict_proba(vec.transform(ts))[:, 1],
    }
    if kind == "tfidf":
        names = np.array(vec.get_feature_names_out())
        coefs = clf.coef_[0]
        model["terms"] = {
            "top_ai_terms": [str(t) for t in names[np.argsort(coefs)[-25:]][::-1]],
            "top_human_terms": [str(t) for t in names[np.argsort(coefs)[:25]]],
        }
    return model


def main():
    pairs = {}
    for tag, ai_name, hu_name in [("W", "wiki_ai", "wiki_human"),
                                  ("H", "hc3_ai", "hc3_human")]:
        log(f"loading {tag} pair")
        pairs[tag] = (corpora.feat_rows(ai_name), corpora.feat_rows(hu_name),
                      corpora.raw_texts(ai_name), corpora.raw_texts(hu_name))
    test_rows = {n: corpora.feat_rows(n) for n in TEST_SETS}
    test_texts = {n: corpora.raw_texts(n) for n in TEST_SETS}
    log("test corpora loaded")

    result = {}
    for tag in ["W", "H"]:
        ai_rows, hu_rows, ai_texts, hu_texts = pairs[tag]
        other = "H" if tag == "W" else "W"
        entry = {}

        log(f"{tag}: fitting folk")
        m = fit_folk(ai_rows, hu_rows)
        auc = roc_auc_score(m["y_te"], m["probs_te"])
        thr95 = threshold_for_tpr(m["y_te"], m["probs_te"], 0.95)
        thr99 = threshold_for_tpr(m["y_te"], m["probs_te"], 0.99)
        in_fpr95 = fpr_at(m["probs_te"][m["y_te"] == 0], thr95)
        in_fpr99 = fpr_at(m["probs_te"][m["y_te"] == 0], thr99)

        def score_rows(rows):
            return m["clf"].predict_proba(m["scaler"].transform(matrix(rows)))[:, 1]

        tests = {n: {
            "n": len(test_rows[n]),
            "fpr@95": fpr_at(score_rows(test_rows[n]), thr95),
            "fpr@99": fpr_at(score_rows(test_rows[n]), thr99),
        } for n in TEST_SETS}
        o_ai_s = score_rows(pairs[other][0])
        o_hu_s = score_rows(pairs[other][1])
        transfer_auc = roc_auc_score(
            np.array([1] * len(o_ai_s) + [0] * len(o_hu_s)),
            np.concatenate([o_ai_s, o_hu_s]))
        gut_s = score_rows(test_rows["gutenberg"])
        by_author = collections.defaultdict(list)
        for r, sv in zip(test_rows["gutenberg"], gut_s):
            by_author[r["meta"].split("|")[0]].append(sv >= thr95)
        entry["folk"] = {
            "in_domain_auc": float(auc),
            "in_domain_fpr@95": in_fpr95,
            "in_domain_fpr@99": in_fpr99,
            "transfer_auc": float(transfer_auc),
            "tests": tests,
            "weights": dict(sorted(m["weights"].items(),
                                   key=lambda kv: -abs(kv[1]))),
            "gutenberg_by_author": {
                a: {"n": len(v), "fpr@95": float(np.mean(v))}
                for a, v in sorted(by_author.items(),
                                   key=lambda kv: -np.mean(kv[1]))},
        }
        log(f"{tag}: folk done AUC={auc:.3f}")

        for kind in ["tfidf", "char"]:
            log(f"{tag}: fitting {kind}")
            m = fit_text(ai_texts, hu_texts, kind)
            auc = roc_auc_score(m["y_te"], m["probs_te"])
            thr95 = threshold_for_tpr(m["y_te"], m["probs_te"], 0.95)
            thr99 = threshold_for_tpr(m["y_te"], m["probs_te"], 0.99)
            in_fpr95 = fpr_at(m["probs_te"][m["y_te"] == 0], thr95)
            in_fpr99 = fpr_at(m["probs_te"][m["y_te"] == 0], thr99)
            tests = {n: {
                "n": len(test_texts[n]),
                "fpr@95": fpr_at(m["score_texts"](test_texts[n]), thr95),
                "fpr@99": fpr_at(m["score_texts"](test_texts[n]), thr99),
            } for n in TEST_SETS}
            o_ai_s = m["score_texts"](pairs[other][2])
            o_hu_s = m["score_texts"](pairs[other][3])
            transfer_auc = roc_auc_score(
                np.array([1] * len(o_ai_s) + [0] * len(o_hu_s)),
                np.concatenate([o_ai_s, o_hu_s]))
            entry[kind] = {
                "in_domain_auc": float(auc),
                "in_domain_fpr@95": in_fpr95,
                "in_domain_fpr@99": in_fpr99,
                "transfer_auc": float(transfer_auc),
                "tests": tests,
            }
            if kind == "tfidf":
                entry[kind]["terms"] = m["terms"]
            log(f"{tag}: {kind} done AUC={auc:.3f}")
        result[tag] = entry
        with open(paths.E3_DETECTOR, "w") as f:
            json.dump(result, f, indent=1)
        log(f"{tag}: written partial results")

    for tag in ["W", "H"]:
        print(f"##### {tag}-pair")
        for kind in ["folk", "tfidf", "char"]:
            r = result[tag][kind]
            print(f"  [{kind:5s}] AUC {r['in_domain_auc']:.3f} | "
                  f"transfer {r['transfer_auc']:.3f} | "
                  + " ".join(f"{n}: {t['fpr@95']:.2f}@95"
                             for n, t in r["tests"].items()))
        print("  folk weights:",
              {k: round(v, 2)
               for k, v in list(result[tag]["folk"]["weights"].items())[:5]})
        print("  top AI terms:",
              result[tag]["tfidf"]["terms"]["top_ai_terms"][:12])
        print("  top human terms:",
              result[tag]["tfidf"]["terms"]["top_human_terms"][:12])

    plt.rcParams.update({
        "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
        "figure.dpi": 200, "savefig.bbox": "tight",
    })
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    wa = result["W"]["folk"]["gutenberg_by_author"]
    ha = result["H"]["folk"]["gutenberg_by_author"]
    authors = list(wa.keys())
    w_fpr = [wa[a]["fpr@95"] for a in authors]
    h_fpr = [ha[a]["fpr@95"] for a in authors]
    order = sorted(range(len(authors)), key=lambda i: -w_fpr[i])
    xs = np.arange(len(authors))
    ax.bar(xs - 0.2, [w_fpr[i] for i in order], 0.4, color="#0072B2",
           label="W-classifier (wiki pair)")
    ax.bar(xs + 0.2, [h_fpr[i] for i in order], 0.4, color="#D55E00",
           label="H-classifier (chat pair)")
    ax.set_xticks(xs)
    ax.set_xticklabels([authors[i].split()[-1] for i in order],
                       rotation=60, ha="right", fontsize=7)
    ax.set_ylabel("false-positive rate @ 95% TPR", fontsize=8)
    ax.axhline(0.05, color="#888888", ls="--", lw=1)
    ax.text(len(authors) - 0.5, 0.055, "in-domain FPR target (5%)",
            color="#888888", fontsize=7, ha="right")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(paths.figure_path("e3_fpr_by_author.png"))
    fig.savefig(paths.figure_path("e3_fpr_by_author.pdf"))
    log("figure saved")


if __name__ == "__main__":
    main()
