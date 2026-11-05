"""Train/test split, cross-validation and model fitting (proposal: 03 Models, 04 Avoiding overfitting).

    split      30% of people held out AND train on earlier years / test on later years
    tuning     5-fold cross-validation on the training set, grouped by person
    calibration Platt scaling fit on the training out-of-fold predictions (no oversampling)

The test set is touched once, by `predict` after everything is chosen on training data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 5600


# ------------------------------------------------------------------ splits
def person_time_split(a: pd.DataFrame, split_round: int, test_share: float = 0.3, seed: int = SEED):
    """Hold out `test_share` of people; train on their outcomes up to `split_round`, test on later windows.

    Train: training people, outcome round (t+1) <= split_round.
    Test:  held-out people, t >= split_round (so every test outcome comes after every training outcome).
    """
    people = np.sort(a["person_id"].unique())
    rng = np.random.default_rng(seed)
    test_people = set(rng.choice(people, size=int(round(test_share * len(people))), replace=False))
    is_test = a["person_id"].isin(test_people)
    train = a[~is_test & (a["round"] + 1 <= split_round)]
    test = a[is_test & (a["round"] >= split_round)]
    return train.copy(), test.copy()


def grouped_folds(train: pd.DataFrame, y_col: str, k: int = 5, seed: int = SEED):
    """k folds that keep each person in one fold and the outcome rate similar across folds."""
    cv = StratifiedGroupKFold(n_splits=k, shuffle=True, random_state=seed)
    return list(cv.split(train, train[y_col], groups=train["person_id"]))


# ------------------------------------------------------------------ logistic regression
def logistic(C: float):
    """Median imputation + missing indicators, standardised inputs, L2-penalised logistic regression."""
    return make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                         LogisticRegression(C=C, max_iter=2000))


def tune_logistic(X: pd.DataFrame, y: np.ndarray, folds, grid=(1e-4, 3e-4, 1e-3, 3e-3, 0.01, 0.1, 1.0)):
    """Cross-validated AUROC and log loss for each penalty C; returns (table, best C, out-of-fold predictions)."""
    rows, oof = [], {}
    for C in grid:
        p = np.zeros(len(y))
        for tr, va in folds:
            p[va] = logistic(C).fit(X.iloc[tr], y[tr]).predict_proba(X.iloc[va])[:, 1]
        oof[C] = p
        rows.append({"C": C, "cv_auroc": roc_auc_score(y, p), "cv_log_loss": log_loss(y, p)})
    table = pd.DataFrame(rows)
    best = float(table.loc[table["cv_auroc"].idxmax(), "C"])
    return table, best, oof[best]


def coefficients(model, columns) -> pd.DataFrame:
    """Odds ratio per 1 SD of each input (and per missing-value indicator), largest effects first."""
    imp = model.named_steps["simpleimputer"]
    names = list(columns) + [f"{columns[i]} (missing)" for i in imp.indicator_.features_] if imp.add_indicator else list(columns)
    coef = model.named_steps["logisticregression"].coef_[0]
    out = pd.DataFrame({"feature": names, "coef": coef, "odds_ratio_per_sd": np.exp(coef)})
    return out.reindex(out["coef"].abs().sort_values(ascending=False).index).reset_index(drop=True)


# ------------------------------------------------------------------ calibration
def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def platt_fit(p: np.ndarray, y: np.ndarray) -> LogisticRegression:
    """Platt scaling: a 1-feature logistic regression on the logit of the raw predictions."""
    return LogisticRegression(C=1e6).fit(_logit(p).reshape(-1, 1), y)


def platt_apply(platt: LogisticRegression, p: np.ndarray) -> np.ndarray:
    return platt.predict_proba(_logit(p).reshape(-1, 1))[:, 1]
