"""TEST FIXTURE ONLY: a small fake panel with the same columns as the NHATS loader's output.

The analysis itself runs only on NHATS. This file exists so the unit tests (no leakage from the
future, person-disjoint splits, recodes, end-to-end smoke test) can run anywhere without NHATS
files, e.g. on a laptop without the data or in CI. Nothing here is used by the pipeline, the
notebook, the reports, or the apps, and no result from it should ever be reported.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from willow.schema import ACTIVITIES, DEVICE_ACTS, LESS_ACTS, WOUT_ACTS

ROUNDS = list(range(1, 15))
COHORTS = {1: 6000, 5: 3000, 12: 3000}  # entry round -> new sample size

# how early in the disablement process each activity is affected (higher = earlier)
HARDNESS = {
    "go_outside": 0.55, "bathing": 0.45, "dressing": 0.05, "get_around_inside": -0.05,
    "get_out_of_bed": -0.2, "toileting": -0.3, "eating": -0.8,
}


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def _new_people(rng, n, entry_round, start_id):
    age = np.where(rng.random(n) < 0.6, rng.uniform(65, 80, n), rng.uniform(80, 92, n))
    race = rng.choice(["white", "black", "hispanic", "other"], n, p=[0.70, 0.13, 0.10, 0.07])
    low_income = (rng.random(n) < np.where(np.isin(race, ["black", "hispanic"]), 0.45, 0.22)).astype(int)
    female = (rng.random(n) < 0.56).astype(int)
    disparity = np.where(np.isin(race, ["black", "hispanic"]), -0.2, 0.0) - 0.25 * low_income
    capacity = rng.normal(1.45, 0.8, n) - 0.045 * (age - 65) + disparity
    fast = rng.random(n) < 0.12 + 0.004 * (age - 65)  # a minority enters a faster-declining phase
    decline = np.where(fast, rng.uniform(0.25, 0.6, n), np.abs(rng.normal(0.02 + 0.002 * (age - 65), 0.04, n)))
    return pd.DataFrame({
        "person_id": np.arange(start_id, start_id + n),
        "cohort": entry_round,
        "age0": age,
        "entry_round": entry_round,
        "female": female,
        "race_eth": race,
        "low_income": low_income,
        "lives_alone": (rng.random(n) < 0.30 + 0.1 * female).astype(int),
        "capacity": capacity,
        "decline": decline,
        "dementia_class": np.where(rng.random(n) < 0.08 + 0.006 * (age - 65), rng.choice([1, 2], n), 0),
        "help_propensity": rng.normal(0, 0.9, n),  # unobserved: family availability, preferences
        "act_effect": [rng.normal(0, 0.35, len(ACTIVITIES)) for _ in range(n)],
        "base_weight": rng.lognormal(7.5, 0.5, n) * np.where(race == "black", 0.6, 1.0),
        "stratum": rng.integers(1, 57, n),
        "psu": rng.integers(1, 3, n),
        "active": True,
    })


def generate(seed: int = 7, scale: float = 1.0) -> pd.DataFrame:
    """Return the canonical long panel (one row per person-round, including exit rows)."""
    rng = np.random.default_rng(seed)
    people = pd.DataFrame()
    rows = []
    next_id = 100001
    for r in ROUNDS:
        if r in COHORTS:
            n = int(COHORTS[r] * scale)
            people = pd.concat([people, _new_people(rng, n, r, next_id)], ignore_index=True)
            next_id += n
        p = people[people.active].copy()
        if p.empty:
            continue
        first = p.entry_round == r
        age = p.age0 + (r - p.entry_round)

        # --- latent evolution (skip in entry round)
        if (~first).any():
            idx = ~first
            shock = (rng.random(idx.sum()) < 0.06) * rng.uniform(0.2, 0.9, idx.sum())
            dem_speed = 0.12 * p.loc[idx, "dementia_class"].values
            p.loc[idx, "capacity"] = (p.loc[idx, "capacity"] - p.loc[idx, "decline"] - dem_speed - shock
                                      + rng.normal(0, 0.12, idx.sum()))
            switch = idx.values & (rng.random(len(p)) < 0.03) & (p.decline.values < 0.2)
            p.loc[switch, "decline"] = rng.uniform(0.25, 0.6, switch.sum())
            prog = rng.random(len(p)) < _sigmoid(-4.2 + 0.08 * (age - 65) - 0.4 * p.capacity)
            p.loc[idx & prog, "dementia_class"] = np.minimum(p.loc[idx & prog, "dementia_class"] + 1, 2)
        c = p.capacity.values
        n = len(p)

        # --- exits (death / residential care / nursing home / nonresponse), not in entry round
        status = np.full(n, "community", dtype=object)
        if (~first).any():
            u = rng.random(n)
            p_death = _sigmoid(-3.7 + 0.075 * (age.values - 75) - 0.75 * c)
            p_nh = _sigmoid(-5.0 - 0.9 * c + 0.7 * p.dementia_class.values)
            p_rc = _sigmoid(-5.2 - 0.6 * c)
            p_nr = 0.035
            cut1, cut2, cut3 = p_death, p_death + p_nh, p_death + p_nh + p_rc
            status = np.where(u < cut1, "deceased",
                     np.where(u < cut2, "nursing_home",
                     np.where(u < cut3, "residential_care",
                     np.where(u < cut3 + p_nr, "nonresponse", "community")))).astype(object)
            status[first.values] = "community"

        # --- reporting
        proxy = (rng.random(n) < _sigmoid(-3.2 - 0.9 * c + 1.2 * p.dementia_class.values)).astype(int)
        noise_sd = np.where(proxy == 1, 0.95, 0.55)
        act_eff = np.vstack(p.act_effect.values)
        out = {
            "person_id": p.person_id.values, "round": r, "cohort": p.cohort.values,
            "status": status, "age": age.values.round(1), "female": p.female.values,
            "race_eth": p.race_eth.values, "low_income": p.low_income.values,
            "income": np.where(p.low_income.values == 1, 14000, 45000) * rng.lognormal(0, 0.3, n),
            "lives_alone": p.lives_alone.values, "proxy": proxy,
            "weight": (p.base_weight.values * rng.lognormal(0, 0.1, n)).round(1),
            "stratum": p.stratum.values, "psu": p.psu.values,
            "_capacity": c.round(3),
        }
        for j, a in enumerate(ACTIVITIES):
            strain = HARDNESS[a] - c + act_eff[:, j]
            obs = strain + rng.normal(0, noise_sd)
            out[f"{a}_diff"] = np.digitize(obs, [-0.9, -0.2, 0.5])
            out[f"{a}_help"] = (rng.random(n) < _sigmoid(2.4 * (strain - 1.45) + p.help_propensity.values - 0.3 * p.lives_alone.values)).astype(int)
            if a in DEVICE_ACTS:
                access = np.where(p.low_income.values == 1, -1.6, 0.0)
                report = np.where(proxy == 1, -0.9, 0.0)
                out[f"{a}_device"] = (rng.random(n) < _sigmoid(2.4 * (obs + 0.35) + access + report)).astype(int)
            if a in LESS_ACTS:
                report = np.where(proxy == 1, -0.8, 0.0)
                out[f"{a}_less"] = (rng.random(n) < _sigmoid(2.2 * (obs + 0.15) - 1.0 + report)).astype(int)
            if a in WOUT_ACTS:
                report = np.where(proxy == 1, -0.8, 0.0)
                out[f"{a}_wout"] = (rng.random(n) < _sigmoid(2.0 * (obs - 0.3) - 1.6 + report)).astype(int)
        out["go_out_freq"] = np.clip(np.rint(0.6 - 1.1 * c + rng.normal(0, 0.55 + 0.3 * proxy)), 0, 4).astype(int)
        out["fell_last_year"] = (rng.random(n) < _sigmoid(-1.6 - 0.7 * c)).astype(int)
        out["self_rated_health"] = np.clip(np.rint(2.6 - 0.8 * c + rng.normal(0, 0.7, n)), 1, 5).astype(int)
        out["pain_limits"] = (rng.random(n) < _sigmoid(-0.9 - 0.6 * c)).astype(int)
        out["hospital_stay"] = (rng.random(n) < _sigmoid(-1.9 - 0.55 * c)).astype(int)
        out["phq2"] = np.clip(rng.poisson(np.exp(0.1 - 0.45 * c)), 0, 6)
        out["dementia_class"] = p.dementia_class.values
        # expanded measures (synthetic): household tasks and physical measures react earlier than ADLs
        for x in ["laundry", "shopping", "meals", "banking", "meds"]:
            hard = {"shopping": 0.7, "laundry": 0.4, "meals": 0.3, "banking": 0.0, "meds": -0.2}[x]
            s_ = hard - c + rng.normal(0, noise_sd)
            out[f"iadl_{x}_diff"] = (s_ > 0.1).astype(int)
            out[f"iadl_{x}_hhelp"] = (rng.random(n) < _sigmoid(2.5 * (s_ - 0.6))).astype(int)
        out["capacity_limits"] = np.clip(np.rint(3.5 - 2.2 * c + rng.normal(0, 1.2, n)), 0, 10)
        out["cannot_walk_6blocks"] = (rng.random(n) < _sigmoid(-0.3 - 1.6 * c)).astype(int)
        out["cannot_climb_10stairs"] = (rng.random(n) < _sigmoid(-1.8 - 1.5 * c)).astype(int)
        for k, b in {"low_energy": -0.2, "balance_problem": -0.8, "lower_body_weak": -0.9,
                     "breathing_problem": -1.2, "weight_loss_10lb": -1.4, "poor_vision": -2.8,
                     "poor_hearing": -3.2, "stroke": -2.3}.items():
            out[k] = (rng.random(n) < _sigmoid(b - 0.7 * c)).astype(int)
        out["n_chronic"] = np.clip(rng.poisson(np.exp(0.9 - 0.25 * c)), 0, 9)
        perf_ok = rng.random(n) > (0.06 + 0.1 * (c < 0))
        out["walk_time"] = np.where(perf_ok & (r != 10), np.exp(1.4 - 0.25 * c + rng.normal(0, 0.2, n)), np.nan)
        out["chair_time"] = np.where(perf_ok & (r != 10) & (c > -0.8), 11 - 2 * c + rng.normal(0, 2, n), np.nan)
        out["grip_max"] = np.where(perf_ok & (r != 10), 24 + 5 * c + 8 * (1 - p.female.values) + rng.normal(0, 5, n), np.nan)
        out["balance_score"] = np.where(perf_ok & (r != 10), np.clip(np.rint(2 + 0.8 * c + rng.normal(0, 0.7, n)), 0, 3), np.nan)
        out["perf_unable"] = np.where(r != 10, (~perf_ok).astype(int) * rng.integers(1, 4, n), np.nan)
        out["network_size"] = np.clip(np.rint(2.2 + 0.3 * c + rng.normal(0, 1.2, n)), 0, 5)
        out["bmi"] = np.clip(27 + rng.normal(0, 5, n), 15, 50)
        out["memory_worse"] = (rng.random(n) < _sigmoid(-2.6 - 0.5 * c + 0.9 * p.dementia_class.values)).astype(int)
        out["memory_poor"] = (rng.random(n) < _sigmoid(-2.0 - 0.4 * c + 0.9 * p.dementia_class.values)).astype(int)
        out["medicaid"] = (rng.random(n) < np.where(p.low_income.values == 1, 0.45, 0.05)).astype(int)
        df = pd.DataFrame(out)

        # items are unobserved for people who have left the community / did not respond
        gone = df.status != "community"
        item_cols = [col for col in df.columns if col.endswith(("_diff", "_help", "_device", "_less", "_wout"))] + [
            "go_out_freq", "fell_last_year", "self_rated_health", "pain_limits", "hospital_stay", "phq2",
            "dementia_class", "proxy", "capacity_limits", "cannot_walk_6blocks", "cannot_climb_10stairs",
            "low_energy", "balance_problem", "lower_body_weak", "breathing_problem", "weight_loss_10lb",
            "poor_vision", "poor_hearing", "stroke", "n_chronic", "walk_time", "chair_time", "grip_max",
            "balance_score", "perf_unable", "network_size", "bmi", "memory_worse", "memory_poor"] + [c for c in df.columns if c.startswith("iadl_")]
        item_cols = list(dict.fromkeys(item_cols))
        df[item_cols] = df[item_cols].astype(float)
        df.loc[gone, item_cols] = np.nan
        rows.append(df)

        # people who died / moved into care leave the panel; nonresponders can come back
        leaving = p.person_id[np.isin(status, ["deceased", "nursing_home", "residential_care"])].values
        people.loc[people.person_id.isin(leaving), "active"] = False
        people.loc[people.person_id.isin(p.person_id), "capacity"] = p.capacity.values
        people.loc[people.person_id.isin(p.person_id), "dementia_class"] = p.dementia_class.values
        people.loc[people.person_id.isin(p.person_id), "decline"] = p.decline.values

    panel = pd.concat(rows, ignore_index=True)
    panel["source"] = "test_fixture"
    return panel.sort_values(["person_id", "round"]).reset_index(drop=True)


if __name__ == "__main__":
    df = generate()
    print(df.shape)
    print(df.status.value_counts())
