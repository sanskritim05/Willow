# Willow

**An Early-Warning Check-In for Older Adults and Caregivers** · INFO 5600

Willow explores whether changes in a person's own everyday activities over time can predict whether they will begin
needing help from another person with mobility or self-care within about a year. It uses the **National Health and
Aging Trends Study (NHATS)**, Rounds 1–14 (2011–2024).

This repository covers the **data cleaning and exploration** stage: turning the NHATS public-use files into a clean
person-round panel, checking it, and describing the sample and the outcome. Modelling comes later.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                     # fake test data only; no NHATS needed
jupyter lab notebooks/        # 02_clean, then 01_explore (kernel: the project's .venv)
```

NHATS files are expected in `NHATS Data/data/raw/round_01 … round_14` inside the repo (git-ignored). Pass another folder
to `load_panel(nhats_dir=...)` to change it. The first run builds the cleaned panel at `data/clean/panel.parquet`;
later runs reuse it (`load_panel(refresh=True)` rebuilds it, as `02_clean` does).

> **NHATS data rules.** Never upload NHATS files or row-level data, including `NHATS Data/` and `data/clean/`, to
> public AI tools or share them outside the team. Report only aggregate results: everything in `results/` is aggregate,
> and counts under 11 people are suppressed. **Clear notebook outputs before committing**
> (*Kernel → Restart & Clear Output*); a test fails if a notebook is committed with outputs.

## Prediction setup the data is prepared for

For each person at round `t`, compare the previous round (`t-1`) with now (`t`) and ask whether they newly receive
help at `t+1`. A window is **at risk** if the person lives in the community at `t-1` and `t` and gets no help with any
of the 7 activities at `t`: going outside, moving inside, getting out of bed, eating, bathing, toileting, dressing.

## Files

| File | Purpose |
|---|---|
| `notebooks/02_clean.ipynb` | Reviews the cleaning: NHATS missing-data codes, recode checks against the codebook, dementia and income derivations, consistency checks, missingness by round, cohort flow. Rebuilds the panel and writes the `results/` files. |
| `notebooks/01_explore.ipynb` | Aggregate-only tour: source-file coverage, sample and cohorts, how people leave the study, activity trends (survey-weighted), outcome rate, changes before new help, fairness group sizes, pandemic rounds. |
| `config/variables.yaml` | Maps NHATS variable names to Willow's variables and records every recode rule. |
| `src/willow/nhats.py` | Loads the NHATS files, applies the recodes, carries cohort-entry demographics forward, attaches income, builds the long panel. |
| `src/willow/nhats_extra.py` | Extra measures: household tasks, physical capacity and performance tests, symptoms, chronic conditions, memory, social network, Medicaid. |
| `src/willow/dementia.py` | The official NHATS dementia classification (Technical Paper #5), checked against published counts. |
| `src/willow/features.py` | Builds the at-risk `t-1 → t → t+1` windows and their outcomes, plus status and change features. |
| `src/willow/interpret.py` | Data-quality helpers: missingness by round, age check, who leaves the study (attrition). |
| `src/willow/explore.py` | Aggregate-only notebook helpers: small-count suppression, tables, plots, data dictionary, cleaning log. |
| `src/willow/schema.py`, `data.py` | Variable groups and labels; data paths and the local panel cache. |
| `tests/` | Tests on a small fake panel (`fake_panel.py`), never on NHATS. |

## Outputs (`results/`, aggregate only)

| File | What it shows |
|---|---|
| `cleaning_log.md` | Files used per round, dementia check, valid codes set to missing, consistency checks, cohort flow |
| `data_dictionary.csv` | Every panel column: label, NHATS source, recode, % non-missing |
| `quality_missing_by_round.csv` | % missing per variable and round among community residents |
| `quality_age_check.csv` | Whether age groups move forward consistently between interviews |
| `bias_attrition.csv` | Characteristics of people who die, move to care, or are lost before follow-up vs those who stay |

## Main cleaning decisions

- **Help, difficulty and device use** come from NHATS's derived measures, so they're coded the same way in every round.
- **Missing-data codes**: negative codes become missing; `-1` (skipped) becomes "no" only where the skip means no.
  Don't-know/refused variants stay missing (listed in `cleaning_log.md`).
- **Living in the community** means `dresid == 1` only.
- **Dementia** uses the official NHATS classification: 68 of 70 published counts match exactly.
- **Income** is the mean of NHATS's 20 imputed values, carried forward to rounds without an income file; "low income"
  is the bottom quartile within the round. Used only for fairness checks, never as a predictor.
- **Sex and race/ethnicity** are only asked at study entry and are copied to the person's other rounds.
- **Social network size** is missing for proxy interviews in every round (Round 3 codes them 0 instead of not asked).

## What we've learned so far

- 18,439 people, 89,087 person-rounds; 44,805 at-risk windows, of which 79.5% have an observed outcome.
- About 9% of observed windows newly need help a year later.
- People who leave before follow-up are older and sicker (more dementia, more difficulty), so the observed sample
  looks healthier than everyone at risk.
- Missing data is low (mostly under 2%), except physical performance tests, which are absent in Round 10 (2020, phone
  interviews during COVID-19).
- New difficulty and device use, especially for going outside and bathing, tend to come before needing help.

## References

- National Health and Aging Trends Study (NHATS). *User Guide, Rounds 1–14 Final Release.* Johns Hopkins Bloomberg School of Public Health, 2026.
- Kasper, J. D., Freedman, V. A., & Spillman, B. C. *Classification of Persons by Dementia Status in NHATS.* NHATS Technical Paper #5.
- Freedman, V. A., & Kasper, J. D. (2019). *Cohort Profile: The National Health and Aging Trends Study (NHATS).* International Journal of Epidemiology.
- Fried, L. P., Bandeen-Roche, K., Chaves, P. H., & Johnson, B. A. (2000). *Preclinical mobility disability predicts incident mobility disability in older women.*
- Guralnik, J. M., Ferrucci, L., Simonsick, E. M., Salive, M. E., & Wallace, R. B. (1995). *Lower-extremity function in persons over the age of 70 years as a predictor of subsequent disability.*
