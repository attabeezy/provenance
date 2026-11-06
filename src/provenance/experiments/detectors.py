"""Shared detector utilities: folk-classifier fitting and threshold ops.

Used by experiments/e3_detector.py and experiments/meta_audit.py.
"""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from ..features import FEATURE_KEYS


def matrix(rows):
    return np.array([[float(r[k]) for k in FEATURE_KEYS] for r in rows])


def stack_folk(ai_rows, hu_rows):
    """Stack folk-feature matrices and labels for a matched pair."""
    X = np.vstack([matrix(ai_rows), matrix(hu_rows)])
    y = np.array([1] * len(ai_rows) + [0] * len(hu_rows))
    return X, y


def fit_folk(ai_rows, hu_rows):
    """Fit the 9-feature logistic-regression 'folk' classifier.

    Deterministic split (test_size=0.2, random_state=13, stratified).
    Returns scaler, classifier, and the held-out test tensors.
    """
    X, y = stack_folk(ai_rows, hu_rows)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=13, stratify=y)
    scaler = StandardScaler().fit(X_tr)
    clf = LogisticRegression(max_iter=2000, C=1.0)
    clf.fit(scaler.transform(X_tr), y_tr)
    probs_te = clf.predict_proba(scaler.transform(X_te))[:, 1]
    return {
        "scaler": scaler, "clf": clf,
        "X_te": X_te, "y_te": y_te, "probs_te": probs_te,
        "weights": {k: float(c) for k, c in zip(FEATURE_KEYS, clf.coef_[0])},
    }


def threshold_for_tpr(y_te, probs, tpr_target):
    """Probability threshold achieving a target TPR on positive test rows."""
    pos = sorted(probs[y_te == 1])
    k = int(np.ceil(tpr_target * len(pos)))
    return pos[-k] if k > 0 else pos[0]


def fpr_at(scores, thr):
    """Fraction of scores at or above the threshold (scores of negatives)."""
    return float(np.mean(scores >= thr))
