"""Validation metrics (proposal: Validation). Aggregate numbers only.

    AUROC, AUPRC, Brier score, calibration (observed / expected, slope, intercept),
    sensitivity and precision when the top 20% of risk is flagged (threshold fixed on training data),
    with 95% CIs from a bootstrap that resamples people, not rows.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

# proposal targets (README: Validation Targets)
TARGETS = {"auroc": (0.75, None), "obs_exp": (0.9, 1.1)}


def alert_threshold(p_train: np.ndarray, flag_share: float = 0.2) -> float:
    """Risk above which the top `flag_share` of TRAINING predictions are flagged."""
    return float(np.quantile(p_train, 1 - flag_share))


def core_metrics(y: np.ndarray, p: np.ndarray, threshold: float) -> dict:
    y, p = np.asarray(y), np.asarray(p)
    logit = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    cal = LogisticRegression(C=1e6).fit(logit.reshape(-1, 1), y)
    flag = p >= threshold
    return {
        "auroc": roc_auc_score(y, p),
        "auprc": average_precision_score(y, p),
        "brier": brier_score_loss(y, p),
        "obs_exp": y.sum() / p.sum(),
        "cal_slope": cal.coef_[0, 0],
        "cal_intercept": cal.intercept_[0],
        "flagged_pct": 100 * flag.mean(),
        "sensitivity": flag[y == 1].mean(),
        "precision": y[flag].mean() if flag.any() else np.nan,
        "prevalence": y.mean(),
    }


def bootstrap_ci(y, p, groups, threshold: float, n: int = 1000, seed: int = 5600) -> pd.DataFrame:
    """Point estimate and 95% CI for every core metric, resampling people (all their windows together)."""
    y, p, groups = np.asarray(y), np.asarray(p), np.asarray(groups)
    point = core_metrics(y, p, threshold)
    ids, inv = np.unique(groups, return_inverse=True)
    rows_of = [np.flatnonzero(inv == i) for i in range(len(ids))]
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n):
        idx = np.concatenate([rows_of[i] for i in rng.integers(0, len(ids), len(ids))])
        if 0 < y[idx].sum() < len(idx):
            draws.append(core_metrics(y[idx], p[idx], threshold))
    d = pd.DataFrame(draws)
    return pd.DataFrame({"estimate": point, "ci_low": d.quantile(0.025), "ci_high": d.quantile(0.975)})


def calibration_table(y, p, bins: int = 10) -> pd.DataFrame:
    """Mean predicted vs observed risk by decile of predicted risk."""
    df = pd.DataFrame({"y": np.asarray(y), "p": np.asarray(p)})
    df["bin"] = pd.qcut(df["p"], bins, labels=False, duplicates="drop")
    return df.groupby("bin").agg(n=("y", "size"), predicted=("p", "mean"), observed=("y", "mean")).reset_index()


def check_targets(m: dict) -> pd.DataFrame:
    rows = []
    for k, (lo, hi) in TARGETS.items():
        ok = (lo is None or m[k] >= lo) and (hi is None or m[k] <= hi)
        target = f"≥ {lo}" if hi is None else f"{lo}–{hi}"
        rows.append({"metric": k, "value": m[k], "target": target, "met": "yes" if ok else "no"})
    return pd.DataFrame(rows)
