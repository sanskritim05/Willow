"""Aggregate-only helpers for the exploration and cleaning notebooks.

NHATS conditions of use: share only aggregate results, never individual records. Every helper here returns
counts, percentages or summary statistics, and counts of 1-10 people are shown as "<11". In the notebooks,
never display raw rows (no df.head(), df.sample(), or printing a person's records).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MIN_CELL = 11
YEAR = {r: 2010 + r for r in range(1, 30)}


def suppress(df):
    """Replace counts of 1..MIN_CELL-1 with '<11' (zeros stay 0). Works on a Series or DataFrame of counts."""
    def f(v):
        return f"<{MIN_CELL}" if isinstance(v, (int, np.integer, float, np.floating)) and 0 < v < MIN_CELL else v
    return df.map(f) if isinstance(df, pd.DataFrame) else df.map(f)


def counts(df: pd.DataFrame, row: str, col: str | None = None) -> pd.DataFrame:
    """Suppressed counts of `row` (by `col`, if given)."""
    t = df.groupby([row, col]).size().unstack(fill_value=0) if col else df[row].value_counts(dropna=False).to_frame("n")
    return suppress(t)


def share_by(df: pd.DataFrame, col: str, by: str = "round", weight: str | None = None) -> pd.Series:
    """% of non-missing `col` equal to 1, per level of `by` (optionally survey-weighted)."""
    d = df[df[col].notna()]
    if weight:
        d = d[d[weight].notna()]
        return d.groupby(by).apply(lambda g: 100 * np.average(g[col], weights=g[weight]), include_groups=False).round(1)
    return (100 * d.groupby(by)[col].mean()).round(1)


def table_by(df: pd.DataFrame, cols, by: str = "round", weight: str | None = None) -> pd.DataFrame:
    """share_by for several binary columns: one row per column, one column per level of `by`."""
    return pd.DataFrame({c: share_by(df, c, by, weight) for c in cols}).T


def plot_lines(table: pd.DataFrame, title: str, ylabel: str = "%", labels: dict | None = None, figsize=(8, 4)):
    """Line plot for a variable x round table."""
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=figsize)
    for name, row in table.iterrows():
        ax.plot([YEAR.get(r, r) for r in row.index], row.values, marker="o", ms=3,
                label=(labels or {}).get(name, name))
    ax.axvspan(2019.5, 2021.5, color="grey", alpha=0.12, lw=0)
    ax.set_title(title, loc="left")
    ax.set_ylabel(ylabel)
    ax.legend(fontsize=8, frameon=False, bbox_to_anchor=(1, 1), loc="upper left")
    plt.tight_layout()
    return ax


def transition_table(panel: pd.DataFrame) -> pd.DataFrame:
    """Next-round status for people living in the community at round t."""
    p = panel[["person_id", "round", "status"]]
    nxt = p.assign(round=p["round"] - 1).rename(columns={"status": "next"})
    t = p[p.status == "community"].merge(nxt, on=["person_id", "round"], how="left")
    t["next"] = t["next"].fillna("not interviewed")
    out = (100 * pd.crosstab(t["round"], t["next"], normalize="index")).round(1)
    return out[out.index < panel["round"].max()]


def latest_activity_table(panel: pd.DataFrame, activities, suffixes=("help", "diff", "device", "less", "wout"),
                          weight: str = "weight") -> pd.DataFrame:
    """Most recent-round weighted percentages for activity status items."""
    comm = panel[panel.status == "community"]
    last = comm[comm["round"] == comm["round"].max()]
    rows = {}
    for a in activities:
        rows[a.replace("_", " ")] = {
            f"{suf} %": (share_by(last, f"{a}_{suf}", by="round", weight=weight).iloc[0]
                         if f"{a}_{suf}" in last else np.nan)
            for suf in suffixes
        }
    return pd.DataFrame.from_dict(rows, orient="index")


def outcome_table(windows: pd.DataFrame) -> pd.DataFrame:
    """New-help outcome rates among windows with observed community follow-up."""
    obs = windows[windows.followup == "community"]
    out = pd.DataFrame({
        "any of 7 (%)": (100 * obs.groupby("round")["y_any"].mean()).round(1),
        "mobility (%)": (100 * obs.groupby("round")["y_mobility"].mean()).round(1),
        "self-care (%)": (100 * obs.groupby("round")["y_selfcare"].mean()).round(1),
        "windows": suppress(obs.groupby("round").size()),
    })
    out.index = [f"t={r} ({YEAR[r]}) -> help in {YEAR[r + 1]}" for r in out.index]
    return out


def change_risk_table(windows: pd.DataFrame, groups: list[str]) -> pd.DataFrame:
    """Outcome rates for people whose status worsened from t-1 to t vs everyone else."""
    from .features import direction
    from .schema import CHANGE_GROUPS
    obs = windows[windows.followup == "community"]
    rows = []
    for g in groups:
        worse = direction(obs, CHANGE_GROUPS[g]) == 1
        rows.append({"change t-1 -> t": g, "got worse (n)": int(worse.sum()),
                     "new help if worse (%)": 100 * obs.y_any[worse].mean(),
                     "new help otherwise (%)": 100 * obs.y_any[~worse].mean()})
    out = pd.DataFrame(rows).set_index("change t-1 -> t")
    out["ratio"] = out["new help if worse (%)"] / out["new help otherwise (%)"]
    out["got worse (n)"] = suppress(out["got worse (n)"])
    return out.round(1).sort_values("ratio", ascending=False)


def decline_count_table(windows: pd.DataFrame) -> pd.DataFrame:
    """New-help rate by the count of everyday-activity areas that worsened."""
    from .features import n_declined
    obs = windows[windows.followup == "community"]
    nd = pd.Series(n_declined(obs), index=obs.index).clip(upper=4)
    out = obs.groupby(nd)["y_any"].agg(["size", "mean"]).rename(columns={"size": "windows", "mean": "new help"})
    out["new help"] = (100 * out["new help"]).round(1)
    out["windows"] = suppress(out["windows"])
    out.index = [f"{int(i)}{'+' if i == 4 else ''} areas got worse" for i in out.index]
    return out


def at_risk_group_table(windows: pd.DataFrame) -> pd.DataFrame:
    """At-risk windows, people and outcome rates for the primary fairness groups."""
    obs = windows[windows.followup == "community"].assign(
        sex=lambda d: d.female.map({0: "male", 1: "female"}),
        income=lambda d: d.low_income.map({0: "not lowest quartile", 1: "lowest quartile"}),
    )
    rows = []
    for col in ["sex", "race_eth", "income"]:
        for lvl, g in obs.groupby(col):
            rows.append({"group": col, "level": lvl, "windows": len(g), "people": g.person_id.nunique(),
                         "events": int(g.y_any.sum()), "new help (%)": round(100 * g.y_any.mean(), 1)})
    out = pd.DataFrame(rows)
    for c in ["windows", "people", "events"]:
        out[c] = suppress(out[c])
    return out


def cohort_flow(panel: pd.DataFrame, windows: pd.DataFrame) -> pd.DataFrame:
    """Aggregate flow from sample people to analytic prediction windows."""
    rows = [
        ("sample people, rounds 1-14", panel.person_id.nunique()),
        ("person-rounds living in the community", int((panel.status == "community").sum())),
        ("at-risk windows: community at t-1 and t, no help at t", len(windows)),
        ("  ... died before t+1", int((windows.followup == "deceased").sum())),
        ("  ... moved into care before t+1", int((windows.followup == "care").sum())),
        ("  ... not interviewed at t+1 (lost)", int((windows.followup == "lost").sum())),
        ("analytic windows (outcome observed at home)", int((windows.followup == "community").sum())),
    ]
    out = pd.DataFrame(rows, columns=["step", "n"])
    out["n"] = suppress(out["n"])
    return out


def mean_by(df: pd.DataFrame, cols, by: str = "round") -> pd.DataFrame:
    return df.groupby(by)[list(cols)].mean().T.round(2)


def code_table(raw: dict, template: str) -> pd.DataFrame:
    """Raw NHATS codes of one variable across rounds (rows = code, columns = round), suppressed.
    raw: {round: raw SP-file frame}; template like 'mo{r}douthelp'."""
    out = {}
    for r, d in raw.items():
        v = template.format(r=r)
        if v in d.columns:
            out[r] = pd.to_numeric(d[v], errors="coerce").value_counts(dropna=False)
    t = pd.DataFrame(out).fillna(0).astype(int).sort_index()
    t.index.name = "code"
    return suppress(t)


def code_classes(raw: dict, templates: dict) -> pd.DataFrame:
    """% of each NHATS missing-code class per item, pooled over rounds:
    valid (>= 0), -1 inapplicable, -7 refused, -8 don't know, -9 missing, absent (variable not in file)."""
    rows = []
    for name, tpl in templates.items():
        vals, absent = [], 0
        for r, d in raw.items():
            v = tpl.format(r=r)
            if v in d.columns:
                vals.append(pd.to_numeric(d[v], errors="coerce"))
            else:
                absent += len(d)
        s = pd.concat(vals) if vals else pd.Series(dtype=float)
        n = len(s) + absent
        rows.append({"item": name, "valid %": 100 * (s >= 0).sum() / n, "-1 inapplicable %": 100 * (s == -1).sum() / n,
                     "-7 refused %": 100 * (s == -7).sum() / n, "-8 don't know %": 100 * (s == -8).sum() / n,
                     "-9 missing %": 100 * (s == -9).sum() / n, "not in file %": 100 * absent / n})
    return pd.DataFrame(rows).set_index("item").round(2)


def recode_check(raw: dict, template: str, rule) -> pd.DataFrame:
    """Crosstab of raw code -> recoded value, pooled over rounds (suppressed). Rows whose recoded value is
    NaN while the raw code is >= 0 are codes the recode rule does not cover: check them in the codebook."""
    from .nhats import _recode
    parts = []
    for r, d in raw.items():
        v = template.format(r=r)
        if v in d.columns:
            s = pd.to_numeric(d[v], errors="coerce")
            parts.append(pd.DataFrame({"raw code": s, "recoded": _recode(s, rule)}))
    if not parts:
        return pd.DataFrame()
    t = pd.concat(parts)
    t["recoded"] = t["recoded"].astype(object).where(t["recoded"].notna(), "missing")
    out = t.groupby(["raw code", "recoded"], dropna=False).size().rename("n").reset_index()
    out["n"] = suppress(out["n"])
    return out


def unmapped_codes(raw: dict, cfg: dict) -> pd.DataFrame:
    """For every configured item: valid raw codes (>= 0) that its recode rule turns into missing."""
    from .nhats import _recode
    rows = []
    for name, spec in cfg["items"].items():
        if "nhats" not in spec or spec["recode"] == "identity":
            continue
        rule = cfg["recodes"][spec["recode"]]
        bad = {}
        for r, d in raw.items():
            v = spec["nhats"].format(r=r)
            if v not in d.columns:
                continue
            s = pd.to_numeric(d[v], errors="coerce")
            lost = s[(s >= 0) & _recode(s, rule).isna()]
            for code, n in lost.value_counts().items():
                bad[code] = bad.get(code, 0) + int(n)
        for code, n in sorted(bad.items()):
            rows.append({"item": name, "recode": spec["recode"], "raw code": code, "n set to missing": n})
    df = pd.DataFrame(rows, columns=["item", "recode", "raw code", "n set to missing"])
    if len(df):
        df["n set to missing"] = suppress(df["n set to missing"])
    return df


def numeric_summary(panel: pd.DataFrame, cols) -> pd.DataFrame:
    """Range checks for numeric measures among community residents (percentiles, not individual values)."""
    comm = panel[panel["status"] == "community"]
    d = comm[[c for c in cols if c in comm.columns]]
    q = d.quantile([0.01, 0.25, 0.5, 0.75, 0.99]).T
    q.columns = ["p1", "p25", "median", "p75", "p99"]
    q.insert(0, "% missing", (100 * d.isna().mean()).round(1))
    return q.round(2)


def consistency(panel: pd.DataFrame) -> pd.DataFrame:
    """Checks a clean panel should pass. Each row: what was checked and how many cases broke it."""
    p = panel.sort_values(["person_id", "round"])
    comm = p[p["status"] == "community"]
    dead_round = p[p["status"] == "deceased"].groupby("person_id")["round"].min()
    after_death = p[p["person_id"].map(dead_round).lt(p["round"])]
    help_cols = [c for c in p.columns if c.endswith("_help")]
    diff_cols = [c.replace("_help", "_diff") for c in help_cols]
    items_noncomm = p.loc[p["status"] != "community", help_cols + diff_cols].notna().any(axis=1).sum()
    rows = [
        ("duplicate person-round rows", int(p.duplicated(["person_id", "round"]).sum())),
        ("people whose sex changes across rounds", int((p.groupby("person_id")["female"].nunique() > 1).sum())),
        ("people whose race/ethnicity changes across rounds", int((p.groupby("person_id")["race_eth"].nunique() > 1).sum())),
        ("rows after a person's death round", int(len(after_death))),
        ("non-community rows that still have activity items", int(items_noncomm)),
        ("community rows: help reported but no difficulty in any activity (allowed, but worth knowing)",
         int(((comm[help_cols].fillna(0).sum(axis=1) > 0) & (comm[diff_cols].fillna(0).sum(axis=1) == 0)).sum())),
    ]
    df = pd.DataFrame(rows, columns=["check", "cases"])
    df["cases"] = suppress(df["cases"])
    return df


def data_dictionary(panel: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """One row per panel column: label, NHATS source, recode, and % non-missing among community residents."""
    from .schema import ITEM_LABELS
    comm = panel[panel["status"] == "community"]
    base = {"person_id": ("NHATS sample person ID", "spid"), "round": ("NHATS round (1 = 2011 ... 14 = 2024)", "file"),
            "status": ("community / residential_care / nursing_home / deceased", "r{r}dresid"),
            "cohort": ("round the person entered (1, 5 or 12)", "derived"), "age": ("age, midpoint of 5-year group", "r{r}d2intvrage"),
            "income": ("total income, mean of 20 imputed draws (audit only)", "ia{r}dtoincimi1-20"),
            "low_income": ("lowest income quartile within round (audit only)", "derived"), "phq2": ("PHQ-2 depressive symptoms (0-6)", "hc{r}depresan1-2"),
            "dementia_class": ("dementia: 0 none, 1 possible, 2 probable", "NHATS Technical Paper #5 algorithm"),
            "source": ("data source tag", "derived")}
    rows = []
    for col in panel.columns:
        spec = cfg["items"].get(col, {})
        label, src = base.get(col, (ITEM_LABELS.get(col, col.replace("_", " ")), spec.get("nhats", "nhats_extra.py")))
        rows.append({"column": col, "label": label, "nhats_source": src, "recode": spec.get("recode", ""),
                     "dtype": str(panel[col].dtype), "% non-missing (community)": round(100 * comm[col].notna().mean(), 1)})
    return pd.DataFrame(rows)


def markdown_table(df: pd.DataFrame) -> str:
    """Tiny markdown table writer for already-aggregate notebook outputs."""
    d = df.reset_index() if df.index.name else df
    return "| " + " | ".join(map(str, d.columns)) + " |\n|" + "---|" * len(d.columns) + "\n" + \
        "\n".join("| " + " | ".join(map(str, r)) + " |" for r in d.values)


def write_cleaning_log(path: str, *, built_at: str, rounds: list[int], panel: pd.DataFrame,
                       inventory: pd.DataFrame, dementia_check: pd.DataFrame,
                       unmapped: pd.DataFrame, checks: pd.DataFrame, flow: pd.DataFrame) -> None:
    """Write the aggregate cleaning log used by the cleaning notebook."""
    log = [
        "# Cleaning log: NHATS panel for Willow", "",
        f"- Built: {built_at}",
        f"- Rounds: {rounds[0]}-{rounds[-1]}; {panel.person_id.nunique():,} people; {len(panel):,} person-rounds; "
        f"{panel.shape[1]} columns",
        "- Panel: `data/clean/panel.parquet` (respondent data: keep local, never share)", "",
        "## Files used", "", markdown_table(inventory), "",
        "## Dementia classification check", "",
        f"{int(dementia_check.match.sum())}/{int(dementia_check.match.notna().sum())} published counts matched exactly.", "",
        "## Valid codes set to missing by recode rules", "", markdown_table(unmapped), "",
        "## Consistency checks", "", markdown_table(checks), "",
        "## Cohort flow", "", markdown_table(flow),
    ]
    with open(path, "w") as f:
        f.write("\n".join(log) + "\n")
