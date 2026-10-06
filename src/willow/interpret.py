"""Interpretation checks (proposal: Explainability and Interpretation -> Interpretation).

* data quality: missing values by round and variable; age moves forward by about one year per round
* data bias: people who leave the study (die, move to care, stop responding) vs people who stay
* error analysis: what missed cases (false negatives) and false alarms (false positives) have in common,
  and how many people get flagged vs how many real cases are caught at different alert levels

Everything here is aggregate. Cells with fewer than MIN_CELL people are suppressed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .schema import ACTIVITIES, ITEM_LABELS, TRACKED_ITEMS

MIN_CELL = 11


# ------------------------------------------------------------------ data quality
def missingness(panel: pd.DataFrame, cols=None) -> pd.DataFrame:
    """Percent missing per variable and round, among community residents (the people we model)."""
    comm = panel[panel["status"] == "community"]
    cols = [c for c in (cols or TRACKED_ITEMS + [f"{a}_help" for a in ACTIVITIES] + ["age", "female", "race_eth",
            "lives_alone", "proxy", "income", "medicaid"]) if c in comm.columns]
    out = comm.groupby("round")[cols].apply(lambda g: g.isna().mean() * 100).T
    out.index.name = "variable"
    return out.round(1)


def age_check(panel: pd.DataFrame) -> pd.DataFrame:
    """Public-use NHATS gives 5-year age groups, so 'age goes up by one each year' is checked as: between
    consecutive interviews the age group never goes down, and rises by at most one group per 5 years."""
    p = panel.dropna(subset=["age"]).sort_values(["person_id", "round"])
    d_age = p.groupby("person_id")["age"].diff()
    d_rnd = p.groupby("person_id")["round"].diff()
    ok = d_age.notna()
    max_allowed = 5 * np.ceil(d_rnd / 5)
    rows = {"consecutive interview pairs checked": int(ok.sum()),
            "age group went DOWN": int((d_age[ok] < 0).sum()),
            "age group jumped more than the gap allows": int((d_age[ok] > max_allowed[ok]).sum()),
            "share of pairs consistent (%)": round(100 * float(((d_age[ok] >= 0) & (d_age[ok] <= max_allowed[ok])).mean()), 2)}
    return pd.DataFrame({"check": list(rows), "value": list(rows.values())})


# ------------------------------------------------------------------ data bias (attrition)
BIAS_VARS = ["age", "female", "lives_alone", "proxy", "low_income", "medicaid", "self_rated_health__cur",
             "dementia_class__cur", "fell_last_year__cur", "hospital_stay__cur", "go_out_freq__cur",
             "n_any_difficulty", "n_any_device"]


def attrition(windows: pd.DataFrame) -> pd.DataFrame:
    """Characteristics at t of at-risk people by what happened at t+1. If people who leave are sicker,
    the analytic sample (outcome observed) looks healthier than reality."""
    w = windows.copy()
    w["n_any_difficulty"] = w[[f"{a}_diff__cur" for a in ACTIVITIES]].fillna(0).gt(0).sum(axis=1)
    w["n_any_device"] = w[[f"{a}_device__cur" for a in ACTIVITIES]].fillna(0).gt(0).sum(axis=1)
    w["group"] = w["followup"].map({"community": "stayed (outcome observed)", "deceased": "died",
                                    "care": "moved to care", "lost": "lost to follow-up"})
    rows = []
    for g, d in w.groupby("group"):
        r = {"group": g, "windows": len(d) if len(d) >= MIN_CELL else f"<{MIN_CELL}",
             "share_of_at_risk_%": round(100 * len(d) / len(w), 1)}
        for v in BIAS_VARS:
            if v in d:
                r[v] = round(float(d[v].mean()), 3)
        rows.append(r)
    out = pd.DataFrame(rows).set_index("group").T
    out.index.name = "measure (mean at t)"
    return out


# ------------------------------------------------------------------ error analysis
def _profile_vars(w):
    cols = {"age": w["age"], "female": w["female"], "lives alone": w["lives_alone"], "proxy report": w["proxy"],
            "lowest income quartile": w.get("low_income"), "Medicaid": w.get("medicaid"),
            "any activity difficulty at t": w[[f"{a}_diff__cur" for a in ACTIVITIES]].fillna(0).gt(0).any(axis=1).astype(int),
            "any device use at t": w[[f"{a}_device__cur" for a in ACTIVITIES]].fillna(0).gt(0).any(axis=1).astype(int),
            "any everyday-activity decline t-1 -> t": w["_n_declined"].gt(0).astype(int),
            "fell recently": w["fell_last_year__cur"], "hospital stay": w["hospital_stay__cur"],
            "possible/probable dementia": (w["dementia_class__cur"] >= 1).astype(float).where(w["dementia_class__cur"].notna()),
            "self-rated health fair/poor": (w["self_rated_health__cur"] >= 4).astype(float).where(w["self_rated_health__cur"].notna())}
    return pd.DataFrame({k: v for k, v in cols.items() if v is not None})


def error_profiles(test: pd.DataFrame, p: np.ndarray, y_col: str, thr: float, n_declined: np.ndarray) -> pd.DataFrame:
    """Mean of each characteristic among true positives, false negatives (missed), false positives
    (false alarms) and true negatives at the top-20% alert rule."""
    w = test.assign(_n_declined=n_declined)
    y, flag = w[y_col].values == 1, p >= thr
    groups = {"caught (TP)": y & flag, "missed (FN)": y & ~flag, "false alarm (FP)": ~y & flag, "correctly quiet (TN)": ~y & ~flag}
    prof = _profile_vars(w)
    out = {}
    for g, m in groups.items():
        out[g] = prof[m].mean().round(3) if m.sum() >= MIN_CELL else pd.Series(np.nan, index=prof.columns)
    df = pd.DataFrame(out)
    df.loc["n windows"] = [int(m.sum()) if m.sum() >= MIN_CELL else f"<{MIN_CELL}" for m in groups.values()]
    df.loc["mean predicted risk"] = [round(float(p[m].mean()), 3) if m.sum() >= MIN_CELL else np.nan for m in groups.values()]
    df.index.name = "characteristic"
    return df


def alert_levels(y, p, p_train, rates=(0.05, 0.10, 0.20, 0.30, 0.40), tiers: dict | None = None) -> pd.DataFrame:
    """Flagged vs caught at different alert levels (thresholds fixed on training predictions)."""
    y, p = np.asarray(y), np.asarray(p)
    rows = []
    levels = [(f"top {int(r * 100)}%", float(np.quantile(p_train, 1 - r))) for r in rates]
    for name, thr in (tiers or {}).items():
        levels.append((f"app tier: {name}", thr))
    for name, thr in levels:
        flag = p >= thr
        tp = int((flag & (y == 1)).sum())
        rows.append({"alert level": name, "threshold": round(thr, 4), "flagged per 100 people": round(100 * flag.mean(), 1),
                     "real cases caught (sensitivity)": round(tp / max(1, y.sum()), 3),
                     "flagged who needed help (precision)": round(tp / max(1, flag.sum()), 3),
                     "people flagged per case caught": round(flag.sum() / max(1, tp), 1)})
    return pd.DataFrame(rows)


def label(item: str) -> str:
    return ITEM_LABELS.get(item, item)


def attrition_weights(windows: pd.DataFrame, split_round: int, clip_pct: float = 99.0) -> pd.Series:
    """Inverse-probability-of-follow-up weights (sensitivity analysis for dropout bias).

    Among at-risk windows that did not end in death or a move to care, model P(interviewed at t+1 | status at t)
    with a logistic regression fit on training-era windows only (outcome round <= split_round). Observed windows
    get stabilized weight mean(observed) / p, clipped at the 99th percentile. Deaths and moves to care are
    competing events, handled by the composite outcome, not by these weights.
    """
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    from .features import make_X
    w = windows[windows["followup"].isin(["community", "lost"])]
    X = make_X(w, "status")
    obs = (w["followup"] == "community").values.astype(int)
    fit_rows = (w["round"] + 1 <= split_round).values
    m = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                      LogisticRegression(C=0.1, max_iter=2000)).fit(X[fit_rows], obs[fit_rows])
    p = m.predict_proba(X)[:, 1]
    wt = obs[fit_rows].mean() / np.clip(p, 1e-3, 1)
    wt = np.minimum(wt, np.percentile(wt[obs == 1], clip_pct))
    return pd.Series(np.where(obs == 1, wt, np.nan), index=w.index, name="ipw")
