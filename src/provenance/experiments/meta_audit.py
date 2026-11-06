"""Meta-audit: score our own draft through the E3 folk detectors.

Chunks the draft's prose into ~100-word windows, scores with both
folk classifiers (W and H pairs) at their in-domain 95%-TPR thresholds,
and reports flag rates.
"""
import json
import re

import numpy as np

from .. import corpora, paths
from ..features import full as feat_full, FEATURE_KEYS
from .detectors import fit_folk, matrix, threshold_for_tpr


def prose_windows(target=100):
    text = open(paths.DRAFT, encoding="utf-8").read()
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith(("#", "|", "-", "*", ">", "[")) or s.startswith("---"):
            continue
        if re.match(r"^\d+\.\s", s):
            continue
        lines.append(s)
    body = " ".join(lines)
    words = body.split()
    chunks = []
    for i in range(0, len(words) - target + 1, target):
        chunks.append(" ".join(words[i:i + target]))
    return chunks


def main():
    chunks = prose_windows()
    print(f"windows: {len(chunks)} (~100 words each)")
    feats = [feat_full(c) for c in chunks]
    X = np.array([[float(r[k]) for k in FEATURE_KEYS] for r in feats])

    out = {}
    for tag, ai_name, hu_name in [("W", "wiki_ai", "wiki_human"),
                                  ("H", "hc3_ai", "hc3_human")]:
        ai_rows = corpora.feat_rows(ai_name)
        hu_rows = corpora.feat_rows(hu_name)
        m = fit_folk(ai_rows, hu_rows)
        s = m["clf"].predict_proba(m["scaler"].transform(X))[:, 1]
        thr = threshold_for_tpr(m["y_te"], m["probs_te"], 0.95)
        flagged = s >= thr
        out[tag] = {"flag_rate": float(np.mean(flagged)), "thr": float(thr)}
        print(f"{tag} folk model: flagged {np.mean(flagged)*100:.1f}% of "
              f"{len(chunks)} window-mentioned draft chunks "
              f"(mean AI-probability {np.mean(s):.2f})")
    with open(paths.META_AUDIT, "w") as f:
        json.dump({"n_windows": len(chunks), **out}, f, indent=1)


if __name__ == "__main__":
    main()
