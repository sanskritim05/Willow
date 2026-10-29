"""Tests run on a small FAKE panel (tests/fake_panel.py), never on NHATS. No result from them is reported."""
import numpy as np
import pandas as pd
import pytest

from fake_panel import generate
from willow import interpret as it
from willow.features import analytic_windows, build_windows, counterfactual, make_X
from willow.nhats import _recode, add_income
from willow.schema import HELP_COLS


@pytest.fixture(scope="module")
def panel():
    return generate(seed=1, scale=0.15)


@pytest.fixture(scope="module")
def windows(panel):
    return build_windows(panel)


def test_at_risk_means_community_and_no_help_at_t(windows):
    assert (windows[[f"{h}__cur" for h in HELP_COLS]].sum(axis=1) == 0).all()
    assert (windows["status__cur"] == "community").all() and (windows["status__prev"] == "community").all()


def test_outcome_only_when_followed_up_in_community(windows):
    assert windows.loc[windows.followup != "community", "y_any"].isna().all()
    assert windows.loc[windows.followup == "community", "y_any"].notna().all()
    assert (windows.loc[windows.followup.isin(["deceased", "care"]), "y_composite"] == 1).all()


def test_outcome_matches_panel(panel, windows):
    row = windows[windows.y_any.notna()].iloc[0]
    nxt = panel[(panel.person_id == row.person_id) & (panel["round"] == row["round"] + 1)].iloc[0]
    assert int(row.y_any) == int(nxt[HELP_COLS].sum() > 0)


@pytest.mark.parametrize("fs", ["status", "snapshot", "change"])
def test_no_future_information_in_features(windows, fs):
    X = make_X(windows, fs)
    assert not any("next" in c or c.startswith("y_") or c in ("race_eth", "low_income", "income") for c in X.columns)
    w2 = windows.copy()
    w2["y_any"] = 1 - w2["y_any"].fillna(0)
    pd.testing.assert_frame_equal(X, make_X(w2, fs))


def test_counterfactual_removes_change(windows):
    cf = counterfactual(windows.head(50), ["go_out_freq"])
    assert (make_X(cf)["d_go_out_freq"].fillna(0) == 0).all()


def test_recode_handles_nhats_missing_codes():
    out = _recode(pd.Series([1, 2, -1, -7, -8, -9]), {1: 1, 2: 0, -1: 0})
    assert out.tolist()[:3] == [1, 0, 0] and out.iloc[3:].isna().all()


def test_income_carried_forward_and_quartile():
    p = pd.DataFrame({"person_id": [1, 1, 2, 2, 3, 3, 4, 4], "round": [1, 2] * 4, "status": "community"})
    inc = pd.DataFrame({"person_id": [1, 2, 3, 4], "round": 1, "income": [10e3, 20e3, 30e3, 40e3]})
    out = add_income(p, inc)
    assert out.income.notna().all()
    assert out[out.person_id == 1].low_income.eq(1).all() and out[out.person_id == 4].low_income.eq(0).all()


def test_age_check_flags_decreases():
    p = pd.DataFrame({"person_id": [1, 1, 2, 2], "round": [1, 2, 1, 2], "age": [72, 77, 82, 77]})
    res = it.age_check(p).set_index("check").value
    assert res["age group went DOWN"] == 1


def test_attrition_weights_only_for_observed(windows):
    ipw = it.attrition_weights(windows, split_round=10)
    obs = windows.loc[ipw.index, "followup"] == "community"
    assert ipw[obs].notna().all() and ipw[~obs].isna().all() and (ipw[obs] > 0).all()


def test_explore_helpers_suppress_small_counts(panel):
    from willow import explore
    s = explore.suppress(pd.Series([0, 3, 10, 11, 500]))
    assert s.tolist() == [0, "<11", "<11", 11, 500]
    c = explore.consistency(panel)
    assert set(c.check.str[:9]) and c.loc[c.check.str.startswith("duplicate"), "cases"].iloc[0] == 0
    assert explore.table_by(panel[panel.status == "community"], ["proxy"]).shape[0] == 1


def test_notebooks_are_committed_without_outputs():
    """Outputs can contain NHATS-derived numbers: notebooks must be saved cleared (Restart & Clear Output)."""
    import re
    from pathlib import Path
    import nbformat
    for path in Path(__file__).parents[1].joinpath("notebooks").glob("*.ipynb"):
        nb = nbformat.read(path, as_version=4)
        code = [c for c in nb.cells if c.cell_type == "code"]
        assert code and all(not c.outputs and c.execution_count is None for c in code), path.name
        # never show records from frames that hold one row per person(-round)
        rows = re.compile(r"\b(panel|windows|obs|obs2|comm|last|inc|t|p|raw\[[^\]]*\])\.(head|tail|sample)\(")
        assert not any(rows.search(c.source) for c in code), path.name
