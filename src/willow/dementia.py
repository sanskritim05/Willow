"""NHATS dementia classification (probable / possible / none), ported to Python.

Faithful port of the official Stata program:
  "NHATS_Addendum_to_Technical_Paper_5_Stata_Programming_Statements_R1-14_July2026.do"
  (Kasper, Freedman & Spillman, NHATS Technical Paper #5, with follow-up-round addendum).
Validated against "NHATS R1-14 Dementia Classification Unweighted Frequencies October 2025"
(see tests / `python -m willow dementia-check`).

Stata semantics kept on purpose: missing (NaN) never satisfies `==`, `&` binds tighter than `|`,
and a sum with any missing term is missing.

Output codes (same as NHATS): 1 probable, 2 possible, 3 no dementia,
-1 deceased / nursing home in initial round, -9 missing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PREFIXES = ("r", "hc", "is", "cp", "cg")
NEEDED = (["dresid", "resptype", "disescn9", "dad8dem", "speaktosp", "quesremem", "dclkdraw", "dclkdlnn",
           "atdrwclck", "dwrdimmrc", "dwrdlstnm", "dwrddlyrc", "presidna1", "presidna3", "vpname1", "vpname3"]
          + [f"chgthink{i}" for i in range(1, 9)] + [f"todaydat{i}" for i in range(1, 6)])


def source_columns(r: int) -> list[str]:
    """NHATS column names (lower case) the classification needs for round r."""
    return [f"{p}{r}{v}" for p in PREFIXES for v in NEEDED]


def _strip(raw: pd.DataFrame, r: int) -> pd.DataFrame:
    out = {}
    for c in raw.columns:
        for p in PREFIXES:
            pre = f"{p}{r}"
            if c.startswith(pre) and c[len(pre):] in NEEDED:
                out[c[len(pre):]] = pd.to_numeric(raw[c], errors="coerce").astype(float).values
    return pd.DataFrame(out, index=raw.index)


def classify(raw: pd.DataFrame, r: int) -> pd.Series:
    """raw: one round's SP file (lower-case column names). Returns demclas per row."""
    d = _strip(raw, r)
    # clock score was renamed dclkdlnn (machine-scored) in later releases; the R version of the
    # official program uses it whenever dclkdraw is absent (needed for the R12 V4 release too)
    if "dclkdlnn" in d and "dclkdraw" not in d:
        d["dclkdraw"] = d["dclkdlnn"]
    for v in NEEDED:
        if v not in d:
            d[v] = np.nan
    g = {k: d[k].values.copy() for k in d.columns}
    n = len(d)
    eq = lambda k, v: g[k] == v  # NaN == v is False, like Stata
    miss = lambda a: np.isnan(a)
    dad8 = np.full(n, -1.0) if r == 1 else g["dad8dem"]

    if r == 2:  # round 2 coding error fix
        m = eq("dwrdimmrc", 10) & eq("dwrddlyrc", -3)
        g["dwrdimmrc"][m] = -3

    dem = np.full(n, np.nan)
    if r >= 2:
        dem[eq("dresid", 7) | eq("dresid", 3) | eq("dresid", 5)] = -9
        dem[eq("dresid", 6) | eq("dresid", 8)] = -1
    else:
        dem[eq("dresid", 3)] = -9
        dem[eq("dresid", 4)] = -1
        # Stata line `gen demclas=-9 if dresid==7 | dresid==3 | ...` also applies in R1 for codes 7/3
        dem[eq("dresid", 7)] = -9
        dem[eq("dresid", 6)] = -1  # `dresid==6 | (dresid==8 & round>=2)`
    resp12 = eq("resptype", 1) | eq("resptype", 2)
    dx = eq("disescn9", 1) if r == 1 else (eq("disescn9", 1) | eq("disescn9", 7))
    dem[dx & resp12] = 1

    # ---- AD8 (proxy reports)
    proxy_open = eq("resptype", 2) & miss(dem)
    ad8, ad8miss = [], []
    for i in range(1, 9):
        a = np.full(n, -1.0)
        a[proxy_open] = np.nan
        c = g[f"chgthink{i}"]
        a[proxy_open & ((c == 1) | (c == 3))] = 1
        a[proxy_open & (c == 2) & miss(a)] = 0
        m = np.full(n, -1.0)
        m[proxy_open & ((a == 0) | (a == 1))] = 0
        m[proxy_open & miss(a)] = 1
        a[proxy_open & miss(a)] = 0
        ad8.append(a)
        ad8miss.append(m)
    score = np.full(n, -1.0)
    score[proxy_open] = np.sum(ad8, axis=0)[proxy_open]
    if r >= 2:
        score[(dad8 == 1) & proxy_open] = 8
    if 4 <= r <= 9:
        score[proxy_open & (dad8 == -1) & eq("chgthink1", -1)] = 8
    ad8_miss = np.full(n, -1.0)
    ad8_miss[proxy_open] = np.sum(ad8miss, axis=0)[proxy_open]
    ad8_dem = np.full(n, np.nan)
    ad8_dem[score >= 2] = 1
    ad8_dem[((score == 0) | (score == 1) | (ad8_miss == 8)) & miss(ad8_dem)] = 2
    dem[(ad8_dem == 1) & miss(dem)] = 1
    dem[(ad8_dem == 2) & eq("speaktosp", 2) & miss(dem)] = 3

    # ---- orientation: date items
    items = []
    for i in range(1, 6):
        t = g[f"todaydat{i}"]
        x = np.where(t > 0, t, np.nan)
        x[(t == 2) | (t == -7)] = 0
        items.append(x)
    date_sum = items[0] + items[1] + items[2] + (items[4] if r == 4 else items[3])
    date_sum[miss(date_sum) & eq("speaktosp", 2)] = -2
    anymiss = miss(items[0]) | miss(items[1]) | miss(items[2]) | miss(items[3])
    date_sum[anymiss & eq("speaktosp", 1)] = -3
    date_sumr = date_sum.copy()
    date_sumr[date_sum == -2] = np.nan
    date_sumr[date_sum == -3] = 0

    # ---- orientation: president / vice president
    def yn(k):
        v = g[k]
        x = np.where(v > 0, v, np.nan)
        x[(v == -7) | (v == 2)] = 0
        return x
    pl, pf, vl, vf = yn("presidna1"), yn("presidna3"), yn("vpname1"), yn("vpname3")
    presvp = pl + pf + vl + vf
    presvp[miss(presvp) & eq("speaktosp", 2)] = -2
    presvp[miss(presvp) & eq("speaktosp", 1) & (miss(pl) | miss(pf) | miss(vl) | miss(vf))] = -3
    presvpr = presvp.copy()
    presvpr[presvp == -2] = np.nan
    presvpr[presvp == -3] = 0
    date_prvp = date_sumr + presvpr

    # ---- executive function: clock drawing
    clk = g["dclkdraw"]
    sp, qr = g["speaktosp"], g["quesremem"]
    qbad = (qr == 2) | (qr == -7) | (qr == -8)
    if r == 10:
        clk[(sp == 2) & (clk == -9)] = -2
        clk[(sp == 1) & qbad & (clk == -9)] = -3
        clk[eq("atdrwclck", 2) & (clk == -9)] = -4
        clk[eq("atdrwclck", 97) & (clk == -9)] = -7
    if r >= 11:
        clk[(sp == 2) & (clk == -9)] = -2
        clk[(sp == 1) & qbad & (clk == -9)] = -3
    cs = clk.copy()
    cs[(clk == -2) | (clk == -9)] = np.nan
    cs[(clk == -3) | (clk == -4) | (clk == -7)] = 0
    cs[(clk == -9) & (sp == 1)] = 2
    cs[(clk == -9) & (sp == -1)] = 3

    # ---- memory: word recall
    def rec(k):
        v = g[k]
        x = v.copy()
        x[(v == -2) | (v == -1)] = np.nan
        x[(v == -7) | (v == -3)] = 0
        if r == 5:
            x[v == -9] = np.nan
        return x
    word = rec("dwrdimmrc") + rec("dwrddlyrc")

    def dom(x, lo_ok_hi, bad_lo, bad_hi):
        o = np.full(n, np.nan)
        o[(x > bad_lo) & (x <= bad_hi)] = 0
        o[(x >= 0) & (x <= lo_ok_hi)] = 1
        return o
    clock65 = dom(cs, 1, 1, 5)
    word65 = dom(word, 3, 3, 20)
    datena65 = dom(date_prvp, 3, 3, 8)
    domain = clock65 + word65 + datena65

    if r == 5:
        dem[eq("dwrdlstnm", -9) & miss(dem)] = -9
    ok = (sp == 1) | (sp == -1)
    dem[miss(dem) & ok & ((domain == 2) | (domain == 3))] = 1
    dem[miss(dem) & ok & (domain == 1)] = 2
    dem[miss(dem) & ok & (domain == 0)] = 3
    return pd.Series(dem, index=raw.index, name="demclas")


# Official unweighted counts (NHATS R1-14 Dementia Classification Unweighted Frequencies, Oct 2025).
# code order: -9 missing, -1 deceased/NH, 1 probable, 2 possible, 3 none.
OFFICIAL = {
    1: {-9: 168, -1: 468, 1: 1038, 2: 996, 3: 5575},
    2: {-9: 190, -1: 829, 1: 844, 2: 672, 3: 4540},
    3: {-9: 179, -1: 736, 1: 718, 2: 478, 3: 3688},
    4: {-9: 156, -1: 544, 1: 616, 2: 405, 3: 3016},
    5: {-9: 188, -1: 579, 1: 965, 2: 779, 3: 5823},
    6: {-9: 177, -1: 689, 1: 863, 2: 572, 3: 4975},
    7: {-9: 158, -1: 588, 1: 771, 2: 526, 3: 4269},
    8: {-9: 112, -1: 489, 1: 685, 2: 438, 3: 3823},
    9: {-9: 88, -1: 429, 1: 648, 2: 366, 3: 3446},
    10: {-9: 77, -1: 351, 1: 613, 2: 329, 3: 3019},
    11: {-9: 64, -1: 365, 1: 458, 2: 264, 3: 2666},
    12: {-9: 75, -1: 352, 1: 671, 2: 567, 3: 4662},
    13: {-9: 105, -1: 484, 1: 997, 2: 796, 3: 6215},
    14: {-9: 98, -1: 618, 1: 872, 2: 679, 3: 5388},
}


def check(nhats_dir: str) -> pd.DataFrame:
    """Compare our counts with NHATS's published unweighted frequencies (aggregate output only)."""
    from .nhats import _find, _read_any, load_config, rounds_available
    cfg = load_config()
    rows = []
    for r in rounds_available(nhats_dir, cfg):
        raw = _read_any(_find(nhats_dir, cfg["files"]["sp_file"], r), columns=source_columns(r))
        ours = classify(raw, r).fillna(-99).astype(int).value_counts()
        for code in (-9, -1, 1, 2, 3):
            off = OFFICIAL.get(r, {}).get(code)
            rows.append({"round": r, "code": code, "ours": int(ours.get(code, 0)), "official": off,
                         "match": None if off is None else int(ours.get(code, 0)) == off})
        if ours.get(-99, 0):
            rows.append({"round": r, "code": "unclassified", "ours": int(ours[-99]), "official": 0,
                         "match": False})
    return pd.DataFrame(rows)


def to_canonical(demclas: pd.Series) -> pd.Series:
    """NHATS codes -> pipeline scale: 2 probable, 1 possible, 0 none, NaN otherwise."""
    return demclas.map({1: 2.0, 2: 1.0, 3: 0.0})
