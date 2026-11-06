"""E1 figures: adaptation curves for arXiv + HN markers (+ summary stats)."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .. import paths

D = None
CHATGPT = 2022.9

plt.rcParams.update({
    "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 200, "savefig.bbox": "tight",
})
C_MARK, C_STRUCT, C_LINE = "#0072B2", "#D55E00", "#888888"


def series(corpus, key):
    years = sorted(D[corpus], key=int)
    xs = [float(y) for y in years]
    ys = [D[corpus][y][key]["rate"] for y in years]
    es = [D[corpus][y][key]["ci"] for y in years]
    return xs, ys, es


def panel(ax, xs, ys, es, label, color, scale_note):
    ax.errorbar(xs, ys, yerr=es, fmt="o-", color=color, ms=3.5,
                lw=1.2, capsize=2, label=label)
    ax.axvline(CHATGPT, color=C_LINE, ls="--", lw=1)
    ax.text(CHATGPT + 0.08, ax.get_ylim()[1] * 0.92, "ChatGPT",
            color=C_LINE, fontsize=8, va="top")
    ax.set_ylabel(scale_note, fontsize=8)
    ax.legend(frameon=False, fontsize=8, loc="upper left")


def main():
    global D
    D = json.load(open(paths.E1_TIMESERIES, encoding="utf-8"))

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.2))

    xs, ys, es = series("arxiv", "delve_per_100k")
    panel(axes[0, 0], xs, ys, es, '"delve" family', C_MARK,
          "arXiv cs.CL: per 100K words")
    axes[0, 0].set_title("(a) Lexical tell: delve", fontsize=9)

    xs, ys, es = series("arxiv", "core_per_100k")
    panel(axes[0, 1], xs, ys, es, "core slop lexicon (32 items)", C_MARK,
          "per 100K words")
    axes[0, 1].set_title("(b) Lexical tells: slop lexicon", fontsize=9)

    xs, ys, es = series("arxiv", "triad_per_1k")
    panel(axes[1, 0], xs, ys, es, "rule-of-three lists", C_STRUCT,
          "per 1K words")
    axes[1, 0].set_title("(c) Structural pattern: triads", fontsize=9)
    axes[1, 0].set_xlabel("year", fontsize=8)

    xs, ys, es = series("hn", "core_per_100k")
    panel(axes[1, 1], xs, ys, es, "core slop lexicon", C_MARK,
          "HN comments: per 100K words")
    axes[1, 1].set_title("(d) HN: slop lexicon (hybrid register)", fontsize=9)
    axes[1, 1].set_xlabel("year", fontsize=8)

    fig.tight_layout()
    fig.savefig(paths.figure_path("e1_adaptation.png"))
    fig.savefig(paths.figure_path("e1_adaptation.pdf"))
    print("saved e1_adaptation.png/.pdf")

    # summary stats for the paper text
    s = {}
    a = D["arxiv"]
    s["delve"] = {
        y: {"rate": a[y]["delve_per_100k"]["rate"],
            "count": a[y]["delve_per_100k"]["count"],
            "words": a[y]["n_words"]}
        for y in ["2021", "2023", "2024", "2025", "2026"]
    }
    s["core_2022_2026"] = {
        y: a[y]["core_per_100k"]["rate"] for y in ["2020", "2022", "2024", "2025", "2026"]
    }
    s["triad_pre_post"] = {
        "mean_2010_2019": sum(a[str(y)]["triad_per_1k"]["rate"] for y in range(2010, 2020)) / 10,
        "mean_2023_2026": sum(a[str(y)]["triad_per_1k"]["rate"] for y in range(2023, 2027)) / 4,
    }
    h = D["hn"]
    s["hn_core"] = {y: h[y]["core_per_100k"]["rate"]
                    for y in ["2015", "2020", "2024", "2025", "2026"]}
    with open(paths.E1_SUMMARY, "w") as f:
        json.dump(s, f, indent=1)
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    main()
