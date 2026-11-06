"""Smoke tests for corpora IO + folk detector fitting, synthetic-only.

These must pass on a fresh clone without the (gitignored) raw data.
"""
import numpy as np
import pytest

from provenance import corpora
from provenance.experiments import detectors
from provenance.features import FEATURE_KEYS


def _synthetic_row(seed, ai=True):
    rng = np.random.default_rng(seed)
    r = {}
    for i, k in enumerate(FEATURE_KEYS):
        base = 2.0 if ai else 0.5
        r[k] = float(base + 0.5 * i + rng.normal(0, 0.3))
    r["n_words"] = 100
    return r


def test_jsonl_roundtrip(tmp_path):
    p = tmp_path / "x.jsonl"
    rows = [{"a": "one", "n": 1}, {"a": "two", "n": 2}]
    corpora.write_jsonl(p, rows)
    assert corpora.read_jsonl(p) == rows


def test_raw_texts_rejects_unknown():
    with pytest.raises(KeyError):
        corpora.raw_texts("nonexistent_corpus")


def test_fit_folk_scores_and_threshold():
    ai = [_synthetic_row(i, ai=True) for i in range(40)]
    hu = [_synthetic_row(1000 + i, ai=False) for i in range(40)]
    m = detectors.fit_folk(ai, hu)
    auc = (m["probs_te"][m["y_te"] == 1] > m["probs_te"][m["y_te"] == 0].mean())
    assert 0 <= m["probs_te"].min() and m["probs_te"].max() <= 1
    thr = detectors.threshold_for_tpr(m["y_te"], m["probs_te"], 0.95)
    assert 0 <= thr <= 1
    fpr = detectors.fpr_at(m["probs_te"][m["y_te"] == 0], thr)
    assert 0 <= fpr <= 1
    # separable synthetic data: trained threshold should catch most AI rows
    ai_scores = m["clf"].predict_proba(
        m["scaler"].transform(detectors.matrix(ai)))[:, 1]
    assert detectors.fpr_at(ai_scores, thr) > 0.8


def test_matrix_shape():
    rows = [_synthetic_row(i) for i in range(3)]
    X = detectors.matrix(rows)
    assert X.shape == (3, len(FEATURE_KEYS))
