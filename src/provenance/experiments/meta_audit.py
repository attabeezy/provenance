"""Meta-audit: run the paper's own instruments over the paper itself.

Scores two texts with the Section 3.4 folk classifiers (W and H pairs,
in-domain 95%-TPR thresholds): the pre-revision prose draft
(paper/draft.md) and the compiled revision (the body of paper/paper.tex).
Reports Section 3.1 marker rates and per-100-word-window flag rates
for each text.
"""
import json
import re

import numpy as np

from .. import corpora, features, paths
from .detectors import fit_folk, threshold_for_tpr

FEATURE_KEYS = features.FEATURE_KEYS

DROP_TEX_LINES = (
    "\\begin{table", "\\end{table", "\\begin{tabular", "\\end{tabular",
    "\\begin{figure", "\\end{figure", "\\caption", "\\centering",
    "\\Description", "\\includegraphics", "\\input", "\\toprule",
    "\\midrule", "\\bottomrule", "\\label", "\\hline", "\\rowcolor",
)

TEX_SKIP_RE = re.compile(
    r"^\\(section|subsection|paragraph|title|author|affiliations?"
    r"|abstract|keywords|maketitle|bibliography|bibliographystyle|booktitle|thanks)"
)


def markdown_body(text: str) -> str:
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith(("#", "|", "-", "*", ">", "[", "---")):
            continue
        if re.match(r"^\d+\.\s", s):
            continue
        lines.append(s)
    return " ".join(lines)


def tex_body(text: str) -> str:
    m = re.search(r"\\begin\{document\}", text)
    if m:
        text = text[m.end():]
    end = text.find("\\begin{thebibliography}")
    if end != -1:
        text = text[:end]
    kept = []
    opener_re = re.compile(
        r"^\\(?:emph|textbf|textit)\{([^{}]+)\}\s*(.*)$"
    )
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("%"):
            continue
        if s.startswith("\\noindent"):
            s = s[len("\\noindent"):].strip()
        op = opener_re.match(s)
        if op:
            s = f"{op.group(1)} {op.group(2)}"
        if s.startswith("\\"):
            continue
        if re.search(r"(?<!\\)&", s):
            continue
        if not re.search(r"\w", s):
            continue
        kept.append(s)
    body = " ".join(kept)
    body = re.sub(r"\\footnote\{[^{}]*\}", " ", body)
    body = re.sub(r"\\cite\{[^}]*\}", " ", body)
    body = re.sub(r"\\(?:ref|eqref|label)\{[^{}]*\}", " ", body)
    body = re.sub(
        r"\\(?:emph|textit|textbf|texttt|textsc|textnormal)\{([^{}]*)\}",
        r"\1", body)
    body = re.sub(r"\\[A-Za-z]+\*?", " ", body)
    body = re.sub(r"~", " ", body)
    body = body.replace("\\%", "%").replace("\\&", "&")
    body = body.replace("``", '"').replace("''", '"')
    return body


def windows_of(body: str, size: int = 100):
    wds = body.split()
    return [" ".join(wds[i:i + size])
            for i in range(0, len(wds) - size + 1, size)]


def folk_models():
    models = {}
    for tag, ai_name, hu_name in [("W", "wiki_ai", "wiki_human"),
                                  ("H", "hc3_ai", "hc3_human")]:
        m = fit_folk(corpora.feat_rows(ai_name), corpora.feat_rows(hu_name))
        thr = threshold_for_tpr(m["y_te"], m["probs_te"], 0.95)
        models[tag] = (m, thr)
    return models


def scan(body: str, models) -> dict:
    rate = features.full(body)
    chunks = windows_of(body)
    X = np.array([[float(features.full(c)[k]) for k in FEATURE_KEYS]
                  for c in chunks])
    out = {
        "n_windows": len(chunks),
        "emdash_per_1k": rate["emdash_per_1k"],
        "triad_per_1k": rate["triad_per_1k"],
    }
    for tag, (m, thr) in models.items():
        s = m["clf"].predict_proba(m["scaler"].transform(X))[:, 1]
        out[tag] = {
            "flag_rate": float(np.mean(s >= thr)),
            "thr": float(thr),
            "mean_prob": float(np.mean(s)),
        }
    return out


def main():
    texts = {
        "draft": markdown_body(open(paths.DRAFT, encoding="utf-8").read()),
        "revision": tex_body(open(paths.PAPER_TEX, encoding="utf-8").read()),
    }
    models = folk_models()
    out = {name: scan(body, models) for name, body in texts.items()}
    paths.META_AUDIT.write_text(json.dumps(out, indent=1))
    for name, r in out.items():
        print(name)
        print(f"  windows {r['n_windows']}  "
              f"em-dash/1K {r['emdash_per_1k']:.2f}  "
              f"triads/1K {r['triad_per_1k']:.2f}")
        for tag in ("W", "H"):
            print(f"  {tag} flagged {r[tag]['flag_rate'] * 100:.1f}%  "
                  f"mean p {r[tag]['mean_prob']:.2f}")


if __name__ == "__main__":
    main()
