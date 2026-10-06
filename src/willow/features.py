"""Prediction windows and features (proposal: System/Analysis Plan, 01 Prediction setup + 02 Features).

A window is anchored at round t for one person:
    t-1 -> t : observed history (status at t + change since t-1)
    t+1      : outcome, newly receiving help from another person with mobility or self-care

At risk = living in the community at t-1 and t AND no help with any of the 7 activities at t.
Nothing from round t+1 is ever used as a feature.

Feature sets
    status    status-now core items + demographics             (baseline, "one-time snapshot")
    snapshot  status + extra measures                          (best snapshot; Q2 comparison)
    change    snapshot + change since last year                (main model)
The app's ~30-feature set lives in app_model.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .schema import (ACTIVITY_GROUPS, BINARY_ITEMS, CHANGE_GROUPS, CORE_ITEMS, DEMOGRAPHICS, HELP_COLS,
                     HIGHER_IS_BETTER, MOBILITY, NO_DIRECTION, ORDINAL_ITEMS, SELFCARE, STATIC,
                     STATUS_COMMUNITY, TRACKED_ITEMS)

AUDIT_COLS = ["race_eth", "low_income", "income", "weight", "stratum", "psu", "cohort", "source"]


def _any_help(df, acts=None):
    cols = HELP_COLS if acts is None else [f"{a}_help" for a in acts]
    return (df[cols].fillna(0).sum(axis=1) > 0).astype(int)


def build_windows(panel: pd.DataFrame) -> pd.DataFrame:
    """One row per at-risk (person, t), with item__prev / item__cur columns, follow-up status and outcomes.

    followup: 'community' (outcome observed), 'deceased', 'care' (nursing home / residential care) or
    'lost' (no interview at t+1). Outcomes are NaN unless followup == 'community'.
    """
    p = panel.copy()
    for c in TRACKED_ITEMS + STATIC:
        if c not in p.columns:
            p[c] = np.nan
    keep = ["person_id", "round", "status"] + TRACKED_ITEMS + HELP_COLS
    extra = [c for c in DEMOGRAPHICS + STATIC + AUDIT_COLS if c in p.columns and c not in keep]
    cur = p[keep + extra]
    prev = p[keep].assign(round=p["round"] + 1)
    nxt = p[["person_id", "round", "status"] + HELP_COLS].assign(round=p["round"] - 1)

    w = cur.merge(prev, on=["person_id", "round"], suffixes=("__cur", "__prev"))
    w = w.merge(nxt.rename(columns={c: f"{c}__next" for c in nxt.columns if c not in ("person_id", "round")}),
                on=["person_id", "round"], how="left")
    cur_help = w[[f"{h}__cur" for h in HELP_COLS]]
    at_risk = ((w["status__cur"] == STATUS_COMMUNITY) & (w["status__prev"] == STATUS_COMMUNITY)
               & cur_help.notna().all(axis=1) & (cur_help.sum(axis=1) == 0))
    w = w[at_risk].copy()

    nstat = w["status__next"]
    w["followup"] = np.select(
        [nstat == STATUS_COMMUNITY, nstat == "deceased", nstat.isin(["nursing_home", "residential_care"])],
        ["community", "deceased", "care"], default="lost")
    nxt_help = w[[f"{h}__next" for h in HELP_COLS]].rename(columns=lambda c: c.replace("__next", ""))
    obs = (w["followup"] == "community").values
    w["y_any"] = np.where(obs, _any_help(nxt_help), np.nan)
    w["y_mobility"] = np.where(obs, _any_help(nxt_help, MOBILITY), np.nan)
    w["y_selfcare"] = np.where(obs, _any_help(nxt_help, SELFCARE), np.nan)
    # competing exits: new help OR moved to care OR died (sensitivity analysis)
    w["y_composite"] = np.where(obs, w["y_any"], np.where(w["followup"].isin(["deceased", "care"]), 1.0, np.nan))
    # calendar flags (known in advance, not leakage): NHATS round 10 = 2020, 11 = 2021
    w["covid_change"] = w["round"].isin([10, 11]).astype(int)
    w["covid_outcome"] = w["round"].isin([9, 10]).astype(int)
    w["prev_any_help"] = (w[[f"{h}__prev" for h in HELP_COLS]].fillna(0).sum(axis=1) > 0).astype(int)
    w = w.drop(columns=[c for c in w.columns if c.endswith("__next")])
    for c in DEMOGRAPHICS + STATIC + AUDIT_COLS:
        if f"{c}__cur" in w.columns:
            w = w.rename(columns={f"{c}__cur": c})
        w = w.drop(columns=[f"{c}__prev"], errors="ignore")
    return w.reset_index(drop=True)


def analytic_windows(windows: pd.DataFrame, outcome: str = "y_any") -> pd.DataFrame:
    a = windows[windows[outcome].notna()].copy()
    a[outcome] = a[outcome].astype(int)
    return a


# ------------------------------------------------------------------ feature builders
def _base(w, items, static):
    c = {f"cur_{it}": w[f"{it}__cur"].values for it in items}
    for d in DEMOGRAPHICS + list(static):
        if d in w.columns:
            c[d] = w[d].values
    c["covid_change"] = w["covid_change"].values
    c["covid_outcome"] = w["covid_outcome"].values
    return c


def worse(it, a, b):
    """Elementwise 'a is worse than b', respecting each item's direction."""
    if it in NO_DIRECTION:
        return np.zeros(len(a), dtype=bool)
    return (a < b) if it in HIGHER_IS_BETTER else (a > b)


def direction(w, items):
    """+1 if any item got worse, -1 if only improvements, 0 if no change."""
    up = np.zeros(len(w), dtype=bool)
    down = np.zeros(len(w), dtype=bool)
    for it in items:
        if it in NO_DIRECTION:
            continue
        a, b = w[f"{it}__cur"].values.astype(float), w[f"{it}__prev"].values.astype(float)
        ok = ~np.isnan(a) & ~np.isnan(b)
        up |= ok & worse(it, a, b)
        down |= ok & worse(it, b, a)
    return np.where(up, 1, np.where(down, -1, 0))


def n_declined(w, groups=ACTIVITY_GROUPS) -> np.ndarray:
    """Number of everyday-activity areas that got worse between t-1 and t."""
    return sum((direction(w, CHANGE_GROUPS[g]) == 1).astype(int) for g in groups)


def _new(c, p):
    v = ((c == 1) & (p == 0)).astype(float)
    v[np.isnan(c) | np.isnan(p)] = np.nan
    return v


def status_features(w, items=CORE_ITEMS, static=()):
    return pd.DataFrame(_base(w, items, static), index=w.index)


def change_features(w, ordinal=ORDINAL_ITEMS, binary=BINARY_ITEMS, static=STATIC):
    c = _base(w, list(ordinal) + list(binary), static)
    cur = {it: w[f"{it}__cur"].values.astype(float) for it in list(ordinal) + list(binary)}
    prv = {it: w[f"{it}__prev"].values.astype(float) for it in list(ordinal) + list(binary)}
    for it in ordinal:
        c[f"d_{it}"] = cur[it] - prv[it]
    for it in binary:
        c[f"new_{it}"] = _new(cur[it], prv[it])
    nansum = lambda keys: np.nansum(np.vstack([c[k] for k in keys]), axis=0) if keys else np.zeros(len(w))
    c["n_worse_difficulty"] = sum((np.nan_to_num(c[k]) > 0).astype(int)
                                  for k in c if k.startswith("d_") and k.endswith("_diff"))
    c["n_new_devices"] = nansum([k for k in c if k.startswith("new_") and k.endswith("_device")])
    c["n_new_doing_less"] = nansum([k for k in c if k.startswith("new_") and k.endswith("_less")])
    c["n_new_went_without"] = nansum([k for k in c if k.startswith("new_") and k.endswith("_wout")])
    c["n_areas_declined"] = sum(worse(it, cur[it], prv[it]).astype(int) for it in list(ordinal) + list(binary))
    c["prev_any_help"] = w["prev_any_help"].values
    return pd.DataFrame(c, index=w.index)


FEATURE_SETS = {
    "status": lambda w: status_features(w),
    "snapshot": lambda w: status_features(w, ORDINAL_ITEMS + BINARY_ITEMS, STATIC),
    "change": lambda w: change_features(w),
    # fairness mitigation only: add economic status (income) as a predictor. Race is never a predictor.
    "change_ses": lambda w: change_features(w).assign(
        log_income=np.log1p(w["income"].clip(lower=0)).values if "income" in w else np.nan,
        low_income=w["low_income"].values if "low_income" in w else np.nan),
}


def make_X(w: pd.DataFrame, feature_set: str = "change") -> pd.DataFrame:
    if feature_set == "app":
        from .app_model import app_features
        return app_features(w)
    return FEATURE_SETS[feature_set](w).astype(float)


def counterfactual(w: pd.DataFrame, items: list[str]) -> pd.DataFrame:
    """Copy of windows in which the given items did NOT change between t-1 and t."""
    cf = w.copy()
    for it in items:
        cf[f"{it}__cur"] = cf[f"{it}__prev"]
    return cf

