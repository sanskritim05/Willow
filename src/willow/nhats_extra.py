"""Expanded NHATS measures: household activities (IADLs), physical capacity and performance,
symptoms, weight, chronic conditions, sensory, social network, Medicaid.

Codes verified against the Round 5 SP frequency codebook (NHATS public use files, R1-14).
Physical performance tests were not administered in Round 10 (2020, telephone), so those
measures are missing that round by design.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .schema import IADL_TASKS

IADL_VARS = {"laundry": ("ha", "laun"), "shopping": ("ha", "shop"), "meals": ("ha", "meal"),
             "banking": ("ha", "bank"), "meds": ("mc", "meds")}
PC_ITEMS = ["walk6blks", "walk3blks", "up20stair", "up10stair", "car20pnds", "car10pnds", "geonknees",
            "bendover", "rechovrhd", "opnjarwhd"]
CHRONIC = [1, 2, 3, 4, 5, 6, 7, 8, 10]   # heart attack, heart dz, HBP, arthritis, osteoporosis, diabetes, lung, stroke, cancer


def source_columns(r: int) -> list[str]:
    cols = []
    for x, (sec, stem) in IADL_VARS.items():
        cols += [f"{sec}{r}d{stem}sfdf", f"{sec}{r}d{stem}reas"]
    cols += [f"pc{r}{i}" for i in PC_ITEMS]
    cols += [f"ss{r}{v}" for v in ("lowenergy", "prbbalcrd", "lwrbodstr", "probbreat", "seewellst", "hearphone")]
    cols += [f"hw{r}{v}" for v in ("lst10pnds", "currweigh", "howtallft", "howtallin")]
    cols += [f"hc{r}disescn{i}" for i in CHRONIC]
    cols += [f"sn{r}dnumsn", f"ip{r}cmedicaid"]
    cols += [f"wa{r}{v}" for v in ("wlkc1rslt", "wlkc1secs", "wlk1hndr", "wlkc2rslt", "wlkc2secs", "wlk2hndr")]
    cols += [f"ch{r}{v}" for v in ("2chstrslt", "chstndsec", "chstdhndr")]
    cols += [f"gr{r}{v}" for v in ("grp1reslt", "grp1rdng", "grp2rdng")]
    cols += [f"ba{r}{v}" for v in ("sxsresult", "stdmreslt", "ftdmreslt")]
    cols += [f"cg{r}memcom1yr", f"cg{r}ratememry", f"cp{r}chgthink8", f"cp{r}memrygood"]
    return cols


def _num(raw, col):
    if col not in raw.columns:
        return np.full(len(raw), np.nan)
    return pd.to_numeric(raw[col], errors="coerce").astype(float).values


def _map(v, m):
    out = np.full(len(v), np.nan)
    for k, val in m.items():
        out[v == k] = val
    return out


def derive(raw: pd.DataFrame, r: int) -> pd.DataFrame:
    n = len(raw)
    o = {}
    # --- household activities: difficulty by self; someone else does it because of health
    for x, (sec, stem) in IADL_VARS.items():
        sfdf = _num(raw, f"{sec}{r}d{stem}sfdf")
        reas = _num(raw, f"{sec}{r}d{stem}reas")
        o[f"iadl_{x}_diff"] = _map(sfdf, {2: 0, 3: 1, 1: 0, 8: 0, 9: 0})
        o[f"iadl_{x}_hhelp"] = _map(reas, {1: 1, 3: 1, 2: 0, 4: 0, -1: 0})
    # --- self-reported physical capacity (1 able, 2 not able; -1 skipped because able at harder level)
    pc = {i: _map(_num(raw, f"pc{r}{i}"), {1: 0, 2: 1, -1: 0}) for i in PC_ITEMS}
    pc["walk6blks"] = _map(_num(raw, f"pc{r}walk6blks"), {1: 0, 2: 1})   # gateway item: -1 = not asked
    stack = np.vstack([pc[i] for i in PC_ITEMS])
    o["capacity_limits"] = np.where(np.isnan(pc["walk6blks"]), np.nan, np.nansum(stack, axis=0))
    o["cannot_walk_6blocks"] = pc["walk6blks"]
    o["cannot_climb_10stairs"] = pc["up10stair"]
    # --- symptoms
    yn = {1: 1, 2: 0}
    o["low_energy"] = _map(_num(raw, f"ss{r}lowenergy"), yn)
    o["balance_problem"] = _map(_num(raw, f"ss{r}prbbalcrd"), yn)
    o["lower_body_weak"] = _map(_num(raw, f"ss{r}lwrbodstr"), yn)
    o["breathing_problem"] = _map(_num(raw, f"ss{r}probbreat"), yn)
    o["poor_vision"] = _map(_num(raw, f"ss{r}seewellst"), {1: 0, 2: 1})
    o["poor_hearing"] = _map(_num(raw, f"ss{r}hearphone"), {1: 0, 2: 1})
    # --- weight
    o["weight_loss_10lb"] = _map(_num(raw, f"hw{r}lst10pnds"), yn)
    wt, ft, inch = _num(raw, f"hw{r}currweigh"), _num(raw, f"hw{r}howtallft"), _num(raw, f"hw{r}howtallin")
    ht = np.where((ft > 0) & (inch >= 0), ft * 12 + inch, np.nan)
    bmi = np.where((wt > 0) & (ht > 0), 703 * wt / ht ** 2, np.nan)
    o["bmi"] = np.where((bmi > 12) & (bmi < 70), bmi, np.nan)
    # --- chronic conditions (1 yes, 7 previously reported, 2 no)
    cc = np.vstack([_map(_num(raw, f"hc{r}disescn{i}"), {1: 1, 7: 1, 2: 0}) for i in CHRONIC])
    o["n_chronic"] = np.where(np.isnan(cc).all(axis=0), np.nan, np.nansum(cc, axis=0))
    o["stroke"] = cc[CHRONIC.index(8)]
    # --- social network, Medicaid
    net = _num(raw, f"sn{r}dnumsn")
    o["network_size"] = np.where(net >= 0, net, np.nan)
    o["medicaid"] = _map(_num(raw, f"ip{r}cmedicaid"), yn)
    # --- physical performance (1 completed, 2 attempted, 3 not attempted)
    t = []
    for k, (rs, sc, hn) in enumerate([("wlkc1rslt", "wlkc1secs", "wlk1hndr"), ("wlkc2rslt", "wlkc2secs", "wlk2hndr")]):
        res, s, h = _num(raw, f"wa{r}{rs}"), _num(raw, f"wa{r}{sc}"), _num(raw, f"wa{r}{hn}")
        t.append(np.where((res == 1) & (s >= 0), s + np.where(h >= 0, h, 0) / 100, np.nan))
    o["walk_time"] = np.fmin(t[0], t[1])
    cres, cs, ch = _num(raw, f"ch{r}2chstrslt"), _num(raw, f"ch{r}chstndsec"), _num(raw, f"ch{r}chstdhndr")
    o["chair_time"] = np.where((cres == 1) & (cs > 0), cs + np.where(ch >= 0, ch, 0) / 100, np.nan)
    g1, g2 = _num(raw, f"gr{r}grp1rdng"), _num(raw, f"gr{r}grp2rdng")
    o["grip_max"] = np.fmax(np.where(g1 > 0, g1, np.nan), np.where(g2 > 0, g2, np.nan))
    bal = np.vstack([_num(raw, f"ba{r}{v}") for v in ("sxsresult", "stdmreslt", "ftdmreslt")])
    administered = (bal > 0).any(axis=0)
    o["balance_score"] = np.where(administered, (bal == 1).sum(axis=0), np.nan)
    results = np.vstack([_num(raw, f"wa{r}wlkc1rslt"), cres, _num(raw, f"gr{r}grp1reslt"), bal[0]])
    any_admin = (results > 0).any(axis=0)
    o["perf_unable"] = np.where(any_admin, ((results == 2) | (results == 3)).sum(axis=0), np.nan)
    # --- self-reported memory (self-respondent items first, proxy items as fallback)
    worse_self = _map(_num(raw, f"cg{r}memcom1yr"), {1: 0, 2: 0, 3: 0, 4: 1, 5: 1})
    worse_proxy = _map(_num(raw, f"cp{r}chgthink8"), {1: 1, 3: 1, 2: 0})
    o["memory_worse"] = np.where(np.isnan(worse_self), worse_proxy, worse_self)
    fair_poor = {1: 0, 2: 0, 3: 0, 4: 1, 5: 1}
    poor_self = _map(_num(raw, f"cg{r}ratememry"), fair_poor)
    poor_proxy = _map(_num(raw, f"cp{r}memrygood"), fair_poor)
    o["memory_poor"] = np.where(np.isnan(poor_self), poor_proxy, poor_self)
    return pd.DataFrame(o, index=raw.index)
