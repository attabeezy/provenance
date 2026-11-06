"""E4: The arithmetic of accusation - base rates, scale, error concentration.

Closed-form computations:
  1. Expected daily false accusations under vendor-claimed FPR at scale.
  2. Bayesian posteriors under average vs. concentrated (subpopulation) FPR.
  3. Likelihood ratios per Gutenberg author from E3 folk-classifier FPRs.
Output: analysis/e4_math.json, figures/e4_lr_by_author.png
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .. import paths


def posterior(p, tpr, fpr):
    return tpr * p / (tpr * p + fpr * (1 - p))


def main():
    E3 = json.load(open(paths.E3_DETECTOR, encoding="utf-8"))
    tpr = 0.95          # operating point used in E3
    vendor_fpr = 1e-4   # Pangram-claimed population-average FPR

    # 1. scale math: docs scanned per day, share human
    scale = {}
    for n_docs in [1_000_000, 5_000_000]:
        for human_share in [0.5, 0.2, 0.1]:
            human_docs = n_docs * human_share
            scale[f"{n_docs/1e6:.0f}M_docs_{int(human_share*100)}pct_human"] = {
                "human_docs_per_day": human_docs,
                "false_accusations_per_day": human_docs * vendor_fpr,
                "false_accusations_per_year": human_docs * vendor_fpr * 250,
            }
    # per-writer career risk
    for n_submissions in [100, 500]:
        scale[f"writer_{n_submissions}_submissions"] = {
            "p_at_least_one_flag": 1 - (1 - vendor_fpr) ** n_submissions,
        }

    # 2. posteriors: average writer vs. concentrated-outcome writer
    posterior_table = {}
    for prior in [0.5, 0.2, 0.05]:
        posterior_table[f"prior_{prior}"] = {
            "avg_writer_fpr_1e-4": posterior(prior, tpr, vendor_fpr),
            "outlier_writer_fpr_0.30": posterior(prior, tpr, 0.30),
            "outlier_writer_fpr_0.56": posterior(prior, tpr, 0.56),
        }

    # likelihood ratios
    lrs = {}
    for tag in ["W", "H"]:
        by_author = E3[tag]["folk"]["gutenberg_by_author"]
        lrs[tag] = {
            a: {"fpr": v["fpr@95"], "lr": tpr / v["fpr@95"] if v["fpr@95"] > 0 else float("inf")}
            for a, v in by_author.items()
        }

    result = {
        "tpr": tpr, "vendor_fpr": vendor_fpr,
        "scale": scale, "posteriors": posterior_table,
        "likelihood_ratios": lrs,
    }
    with open(paths.E4_MATH, "w") as f:
        json.dump(result, f, indent=1)

    print("== expected false accusations (vendor FPR 1e-4) ==")
    for k, v in scale.items():
        if "p_at_least" in v:
            print(f"  {k}: {v['p_at_least_one_flag']:.3f}")
        elif "human_docs_per_day" in v:
            print(f"  {k}: {v['false_accusations_per_day']:.0f}/day, "
                  f"{v['false_accusations_per_year']:.0f}/yr")
    print("== posteriors P(AI | flagged) ==")
    for prior, row in posterior_table.items():
        print(f"  {prior}: avg {row['avg_writer_fpr_1e-4']:.4f} | "
              f"outlier30% {row['outlier_writer_fpr_0.30']:.3f} | "
              f"outlier56% {row['outlier_writer_fpr_0.56']:.3f}")
    print("== LR range across Gutenberg authors ==")
    for tag in ["W", "H"]:
        vals = [v["lr"] for v in lrs[tag].values() if v["lr"] != float("inf")]
        lo, hi = min(vals), max(vals)
        inf_authors = [a for a, v in lrs[tag].items() if v["lr"] == float("inf")]
        print(f"  {tag}: min LR {lo:.1f}, max LR {hi:.0f}, "
              f"inf-FPR authors: {inf_authors}")

    # figure: LR by author with evidentiary thresholds
    plt.rcParams.update({
        "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
        "figure.dpi": 200, "savefig.bbox": "tight",
    })
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    authors = list(lrs["W"].keys())
    order = sorted(authors, key=lambda a: lrs["W"][a]["lr"])
    xs = range(len(order))
    w_lr = [min(lrs["W"][a]["lr"], 500) for a in order]
    h_lr = [min(lrs["H"][a]["lr"], 500) for a in order]
    ax.bar([x - 0.2 for x in xs], w_lr, 0.4, color="#0072B2",
           label="W-classifier")
    ax.bar([x + 0.2 for x in xs], h_lr, 0.4, color="#D55E00",
           label="H-classifier")
    ax.axhline(19, color="#888888", ls="--", lw=1)
    ax.text(len(order) - 0.5, 21, "LR 19: 'strong' legal evidence",
            color="#888888", fontsize=7, ha="right")
    ax.axhline(1, color="#333333", ls=":", lw=1)
    ax.text(len(order) - 0.5, 3, "LR 1: no evidence",
            color="#333333", fontsize=7, ha="right")
    ax.set_yscale("log")
    ax.set_xticks(xs)
    ax.set_xticklabels([a.split()[-1] for a in order],
                       rotation=60, ha="right", fontsize=7)
    ax.set_ylabel("likelihood ratio of a flag\n(TPR 0.95 / author FPR)", fontsize=8)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(paths.figure_path("e4_lr_by_author.png"))
    fig.savefig(paths.figure_path("e4_lr_by_author.pdf"))
    print("saved", paths.figure_path("e4_lr_by_author.png"))


if __name__ == "__main__":
    main()
