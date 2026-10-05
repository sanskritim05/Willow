"""Load real NHATS round files into the canonical long panel.

Runs ONLY on your own computer. NHATS conditions of use forbid uploading the data to
public AI tools, so never paste these files (or row-level outputs) into a chatbot.

Every variable name comes from config/variables.yaml, which must be verified against
the NHATS codebooks first (`python -m willow inspect --nhats-dir ...`).
"""
from __future__ import annotations

import glob
import os
import warnings

import numpy as np
import pandas as pd
import yaml

from . import dementia, nhats_extra
from .schema import EXTRA_ITEMS

HERE = os.path.dirname(__file__)
DEFAULT_CONFIG = os.path.abspath(os.path.join(HERE, "..", "..", "config", "variables.yaml"))


def load_config(path: str | None = None) -> dict:
    with open(path or DEFAULT_CONFIG) as f:
        return yaml.safe_load(f)


def _header(path: str) -> list[str]:
    """Variable names only (no respondent rows)."""
    if path.lower().endswith(".dta"):
        with pd.io.stata.StataReader(path) as rd:
            return [c.lower() for c in rd.variable_labels()]
    return list(_read_any(path).columns)


def _read_any(path: str, columns=None) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".dta":
        if columns is not None:
            with pd.io.stata.StataReader(path) as rd:
                hdr = {c.lower(): c for c in rd.variable_labels()}
            columns = list(dict.fromkeys(hdr[c] for c in columns if c in hdr))
        df = pd.read_stata(path, convert_categoricals=False, columns=columns)
    elif ext == ".sas7bdat":
        df = pd.read_sas(path)
    elif ext == ".csv":
        df = pd.read_csv(path, low_memory=False)
    else:
        raise ValueError(f"Unsupported file type: {path}")
    df.columns = [c.lower() for c in df.columns]
    return df


def _find(nhats_dir: str, pattern, r: int):
    """First file matching `pattern` (or any of a list of patterns) for round r, searched recursively,
    so files may sit in round subfolders (data/raw/round_01/...). Anything under _archive/ is ignored."""
    nhats_dir = os.path.expanduser(nhats_dir)
    hits = []
    for pat in ([pattern] if isinstance(pattern, str) else pattern):
        hits += glob.glob(os.path.join(nhats_dir, "**", pat.format(r=r)), recursive=True)
    hits = sorted(h for h in set(hits) if os.path.splitext(h)[1].lower() in (".dta", ".sas7bdat", ".csv")
                  and "_archive" not in os.path.relpath(h, nhats_dir).split(os.sep))
    if len(hits) > 1:
        warnings.warn(f"Round {r}: {len(hits)} files match {pattern!r}; using {os.path.basename(hits[0])}")
    return hits[0] if hits else None


FILE_KINDS = {"sp": "sp_file", "tracker": "tracker_file", "income": "income_file", "covid": "covid_file"}


def file_inventory(nhats_dir: str, cfg: dict | None = None, rounds=range(1, 15)) -> pd.DataFrame:
    """One row per round: the file name found for each kind (SP, tracker, imputed income, COVID), or None."""
    cfg = cfg or load_config()
    rows = []
    for r in rounds:
        row = {"round": r}
        for kind, key in FILE_KINDS.items():
            pat = cfg["files"].get(key)
            hit = _find(nhats_dir, pat, r) if pat else None
            if kind == "covid" and "{r}" not in str(pat) and r != 10:
                hit = None  # the COVID-19 supplement only exists for Round 10
            row[kind] = os.path.basename(hit) if hit else None
        rows.append(row)
    return pd.DataFrame(rows)


def _recode(series: pd.Series, rule):
    num = pd.to_numeric(series, errors="coerce")
    if rule is None:  # identity: keep valid codes, negative NHATS missing codes -> NaN
        return num.where(num >= 0)
    rule = dict(rule)
    default = rule.pop("_default", None)
    out = num.map(rule)
    if default is not None:
        out = out.where(out.notna() | ~(num >= 0), default)
    return out


def rounds_available(nhats_dir: str, cfg: dict):
    return [r for r in range(1, 30) if _find(nhats_dir, cfg["files"]["sp_file"], r)]


def inspect(nhats_dir: str, cfg: dict | None = None) -> pd.DataFrame:
    """Report which configured variables are missing from each round's SP file."""
    cfg = cfg or load_config()
    rows = []
    for r in rounds_available(nhats_dir, cfg):
        cols = set(_header(_find(nhats_dir, cfg["files"]["sp_file"], r)))
        for name, spec in cfg["items"].items():
            if "nhats" in spec:
                v = spec["nhats"].format(r=r)
                rows.append({"round": r, "canonical": name, "nhats_var": v, "found": v in cols})
        for v in cfg["derived"]["phq2"]["items"]:
            rows.append({"round": r, "canonical": "phq2", "nhats_var": v.format(r=r),
                         "found": v.format(r=r) in cols})
        # imputed-income file (not every round has one): check its key variables when present
        inc = _find(nhats_dir, cfg["files"]["income_file"], r) if "income_file" in cfg["files"] else None
        if inc:
            icols = set(_header(inc))
            for v in cfg.get("income", {}).get("check_vars", []):
                rows.append({"round": r, "canonical": "income_imputed", "nhats_var": v.format(r=r),
                             "found": v.format(r=r) in icols})
    return pd.DataFrame(rows)


def load_income(nhats_dir: str, cfg: dict | None = None) -> pd.DataFrame:
    """person_id, round, income: mean of NHATS's 20 imputed total-income draws (rounds with an income file)."""
    cfg = cfg or load_config()
    spec, frames = cfg["income"], []
    for r in rounds_available(nhats_dir, cfg):
        path = _find(nhats_dir, cfg["files"]["income_file"], r)
        if not path:
            continue
        draws = [spec["draw"].format(r=r, k=k) for k in range(1, spec["n_draws"] + 1)]
        raw = _read_any(path, columns=[cfg["id"]] + draws)
        vals = raw[[d for d in draws if d in raw.columns]].apply(pd.to_numeric, errors="coerce")
        vals = vals.where(vals >= 0)
        frames.append(pd.DataFrame({"person_id": raw[cfg["id"]].values, "round": r,
                                    "income": vals.mean(axis=1).values}))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["person_id", "round", "income"])


def add_income(panel: pd.DataFrame, income: pd.DataFrame) -> pd.DataFrame:
    """Attach income (carried forward to rounds without an income file) and low_income = bottom
    quartile among community residents in that round. Audit variable only, never a predictor."""
    p = panel.drop(columns=[c for c in ("income", "low_income") if c in panel.columns])
    p = p.merge(income, on=["person_id", "round"], how="left").sort_values(["person_id", "round"])
    p["income"] = p.groupby("person_id")["income"].ffill()
    comm = p["status"] == "community"
    q1 = p[comm].groupby("round")["income"].quantile(0.25)
    p["low_income"] = np.where(p["income"].isna(), np.nan, (p["income"] <= p["round"].map(q1)).astype(float))
    return p.reset_index(drop=True)


def raw_columns(cfg: dict, r: int, extra=()) -> list[str]:
    """Every SP-file column the loader needs for round r (lower case), plus `extra` ({r} allowed)."""
    wanted = [cfg["id"]] + [s["nhats"].format(r=r) for s in cfg["items"].values() if "nhats" in s]
    wanted += [i.format(r=r) for i in cfg["derived"]["phq2"]["items"]]
    wanted += dementia.source_columns(r)
    wanted += nhats_extra.source_columns(r)
    wanted += [e.format(r=r) for e in extra]
    return list(dict.fromkeys(wanted))


def load_raw_round(nhats_dir: str, r: int, cfg: dict | None = None, extra=()) -> pd.DataFrame:
    """Raw (un-recoded) SP-file columns for one round. Stays on your machine: never print its rows."""
    cfg = cfg or load_config()
    return _read_any(_find(nhats_dir, cfg["files"]["sp_file"], r), columns=raw_columns(cfg, r, extra))


def load_panel(nhats_dir: str, cfg: dict | None = None, raw: dict | None = None) -> pd.DataFrame:
    """Canonical long panel. `raw` ({round: frame from load_raw_round}) skips re-reading the SP files."""
    cfg = cfg or load_config()
    if not cfg.get("verified"):
        warnings.warn("config/variables.yaml is not marked verified: results are NOT trustworthy until every "
                      "variable name and code has been checked against the NHATS codebooks.")
    idcol = cfg["id"]
    frames = []
    seen: set = set()
    for r in (sorted(raw) if raw is not None else rounds_available(nhats_dir, cfg)):
        raw_r = raw[r] if raw is not None else load_raw_round(nhats_dir, r, cfg)
        df = pd.DataFrame({"person_id": raw_r[idcol].values, "round": r})
        for name, spec in cfg["items"].items():
            if "nhats" not in spec:
                continue
            v = spec["nhats"].format(r=r)
            rule = cfg["recodes"].get(spec["recode"]) if spec["recode"] != "identity" else None
            df[name] = _recode(raw_r[v], rule).values if v in raw_r.columns else np.nan
        # derived
        ph = cfg["derived"]["phq2"]
        parts = [_recode(raw_r[i.format(r=r)], ph["recode"]) for i in ph["items"] if i.format(r=r) in raw_r.columns]
        df["phq2"] = sum(parts).values if len(parts) == len(ph["items"]) else np.nan
        # official NHATS dementia classification (Technical Paper #5 algorithm, ported in dementia.py);
        # falls back to the reported-diagnosis item from the config if the cognition items are absent
        dc = dementia.to_canonical(dementia.classify(raw_r, r))
        if dc.notna().any():
            df["dementia_class"] = dc.values
        dm = cfg["derived"].get("dementia")  # optional: override with a precomputed column
        if dm:
            dcol = dm["column"].format(r=r)
            if dcol in raw_r.columns:
                df["dementia_class"] = _recode(raw_r[dcol], dm["recode"]).values
        # expanded measures (IADLs, physical capacity/performance, symptoms, conditions, Medicaid)
        ext = nhats_extra.derive(raw_r, r)
        for c in ext.columns:
            df[c] = ext[c].values
        # age & status
        df["age"] = df.pop("age_cat").map(cfg["age_cat_midpoints"])
        df["status"] = df.pop("residence").fillna("nonresponse")
        df["cohort"] = np.where(df["person_id"].isin(seen), np.nan, r)
        seen |= set(df["person_id"])
        frames.append(df)
    panel = pd.concat(frames, ignore_index=True)
    panel["cohort"] = panel.groupby("person_id")["cohort"].transform("min")
    if raw is None:
        panel = add_income(panel, load_income(nhats_dir, cfg))
    # persons missing from a round after entry (and not known to have exited) are nonresponse rows
    items = [c for c in panel.columns if c.endswith(("_help", "_diff", "_device", "_less", "_wout"))]
    items = list(dict.fromkeys(items + [c for c in EXTRA_ITEMS if c in panel.columns]))
    panel.loc[panel["status"] != "community", items] = np.nan
    for c in ["female", "race_eth"]:  # time-invariant: carry forward/back
        panel[c] = panel.groupby("person_id")[c].transform(lambda s: s.ffill().bfill())
    panel["source"] = "nhats"
    return panel.sort_values(["person_id", "round"]).reset_index(drop=True)
