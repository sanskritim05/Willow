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

## Cleaning

The cleaning code is in `src/willow/nhats.py`, `nhats_extra.py` and `dementia.py`. Every recode rule is in
`config/variables.yaml`, and `notebooks/02_clean.ipynb` checks each step.

**What we built.** One row per person per NHATS round, Rounds 1–14 (2011–2024): 18,439 people, 89,087 person-rounds,
85 columns. 73,928 of those rows are people living in the community.

**Main decisions**
- **Help, difficulty and device use** come from NHATS's derived measures, so they're coded the same way in every round.
- **Missing-data codes.** NHATS's negative codes (missing, don't know, refused) become missing. `-1` ("not asked")
  becomes "no" only where the skip pattern means no, for example "went without help" when the person has no
  difficulty. Every valid code that we set to missing is listed in `results/cleaning_log.md`.
- **"Not done in the last month" (code 8)** counts as *no help* for the help items but as *missing* for difficulty and
  device use, since we can't tell how hard an activity is if it wasn't done.
- **Living in the community** means NHATS residence code 1 only. Residential care and nursing homes don't count.
- **Dementia** uses the official NHATS classification (Technical Paper #5). Our counts match 68 of 70 published
  counts exactly. Round 12 is off by 5 of 6,327 people because NHATS re-released that round with a machine-scored
  clock test.
- **Income** is the average of NHATS's 20 imputed values, carried forward to rounds without an income file. "Low
  income" means the bottom quarter within each round. It's used only to check fairness, never to predict.
- **Sex and race/ethnicity** are only asked when someone joins the study, so they're copied to the person's later
  rounds.
- **Social network size** is set to missing for proxy interviews. Round 3 codes proxies as 0 (no network) instead of
  "not asked", which would have looked like a sudden loss of social contacts.

**Checks** (all passed): no duplicate person-rounds, no rows after a person's death, sex and race never change within a
person, and people outside the community have no activity answers. In 1 of 65,479 pairs of consecutive interviews a
person's age group goes down. 1,480 community rows report help without difficulty in any activity: NHATS allows this,
but it's worth knowing.

**Missing data** is low, mostly under 2% per item per round. The exceptions:
- Physical performance tests (walking speed, chair stands, grip, balance) are missing for everyone in 2020, because
  that round was done by phone during COVID-19. They're also missing for 5–18% of people in other rounds.
- Medicaid status is 2–5% missing, and social network size about 4–7%.

## Exploration results

From `notebooks/01_explore.ipynb`. Counts are unweighted unless marked weighted. Counts under 11 are suppressed.

**Who is in the study.** People joined in four groups: 8,245 in 2011, 4,182 in 2015, 3,082 in 2022 and 2,930 in 2023.
Between 4% and 7% of interviews each year are answered by a proxy (someone else on the person's behalf), with the
highest share, 7.2%, in 2011 and in 2020.

**What happens a year later.** Of people living at home in a given round, on average by the next round:

| Next round | Average % | Range across years |
|---|---|---|
| Still at home | 85.5 | 78.1–89.6 |
| Not interviewed | 7.8 | 3.5–15.5 |
| Died | 4.9 | 3.7–6.8 |
| Moved to care | 1.8 | |

**Needing help is common and steady.** Weighted to US adults 65+ living at home, the share getting help from another
person stays fairly flat from 2011 to 2024:
- dressing 9–11%, going outside 8–10%, bathing 5–7% (falling to 5% by 2024)
- moving inside about 5–6%, getting out of bed about 4–5%, eating about 3–4%, toileting about 2–3%

**The prediction sample.** There are 44,805 at-risk windows from 11,109 people: at home a year earlier and now, with
no help now. By the next round:

| Outcome at t+1 | Windows | % |
|---|---|---|
| At home, outcome observed | 35,632 | 79.5 |
| Not interviewed | 7,560 | 16.9 |
| Died | 1,107 | 2.5 |
| Moved to care | 506 | 1.1 |

**How often people newly need help.** 9.2% of observed windows (3,289) newly get help with at least one of the 7
activities a year later: about 6% with mobility and about 6% with self-care. The yearly rate is 8.4–9.5%, except
2020 → 2021, when it rose to 11.4%.

**Getting worse comes before needing help.** People whose situation got worse over the previous year were much more
likely to need help the next year:

| Change from t-1 to t | People who got worse | New help if worse | New help otherwise | Ratio |
|---|---|---|---|---|
| Harder to eat independently | 482 | 24.1% | 9.0% | 2.7× |
| Household tasks getting harder | 7,843 | 18.2% | 6.7% | 2.7× |
| Changes in dressing | 2,490 | 20.9% | 8.4% | 2.5× |
| Harder to move around inside | 4,241 | 18.7% | 7.9% | 2.4× |
| Harder to go outside | 3,128 | 18.7% | 8.3% | 2.3× |
| Harder to get out of bed | 3,140 | 18.6% | 8.3% | 2.2× |
| Going out less often | 7,313 | 14.1% | 8.0% | 1.8× |
| Changes in bathing | 5,388 | 13.0% | 8.6% | 1.5× |
| Recent fall | 2,502 | 13.6% | 8.9% | 1.5× |
| Harder to use the toilet | 4,038 | 12.4% | 8.8% | 1.4× |
| Hospital stay | 3,695 | 12.5% | 8.8% | 1.4× |
| Memory getting worse (self-report) | 5,031 | 12.4% | 8.7% | 1.4× |

The more areas that got worse, the higher the risk:

| Areas that got worse | Windows | New help next year |
|---|---|---|
| 0 | 17,923 | 5.6% |
| 1 | 10,382 | 9.3% |
| 2 | 4,142 | 14.6% |
| 3 | 1,864 | 20.9% |
| 4 or more | 1,321 | 24.8% |

**Who leaves the study is not random.** People who die or move to care before follow-up are older (average age about
83–84 vs 78), much more likely to have dementia (41% and 58% vs 17%), and have about twice as many difficulties.
People lost to follow-up are somewhat sicker too (22% dementia vs 17%). So the sample with an observed outcome looks
healthier than everyone at risk (`results/bias_attrition.csv`).

**Groups for the fairness checks.** New-help rates differ across groups, and some groups are small:

| Group | Windows | People | New help |
|---|---|---|---|
| Women | 19,649 | 4,415 | 10.5% |
| Men | 15,983 | 3,577 | 7.6% |
| White | 25,712 | 5,384 | 8.3% |
| Black | 6,811 | 1,661 | 11.5% |
| Hispanic | 1,860 | 630 | 12.6% |
| Other race/ethnicity | 868 | 226 | 10.7% |
| Lowest income quarter | 7,197 | 2,362 | 13.8% |
| Higher income | 28,435 | 6,636 | 8.1% |

The "Other" and Hispanic groups are small, so results for them will be less certain.

**The pandemic (2020).** Interviews were by phone, physical tests weren't done, more interviews were answered by a
proxy, and the new-help rate a year later was higher (11.4%). Modelling should check results with and without these
years.

### What this means for modelling
- New help is uncommon (about 9%), so the model has to give well-calibrated risks, not just yes/no rules.
- Changes over the past year carry a clear signal, especially in daily activities and household tasks, and several
  changes together are a stronger warning than one.
- Dropout, small groups and the 2020 round all need explicit checks.

## References

- National Health and Aging Trends Study (NHATS). *User Guide, Rounds 1–14 Final Release.* Johns Hopkins Bloomberg School of Public Health, 2026.
- Kasper, J. D., Freedman, V. A., & Spillman, B. C. *Classification of Persons by Dementia Status in NHATS.* NHATS Technical Paper #5.
- Freedman, V. A., & Kasper, J. D. (2019). *Cohort Profile: The National Health and Aging Trends Study (NHATS).* International Journal of Epidemiology.
- Fried, L. P., Bandeen-Roche, K., Chaves, P. H., & Johnson, B. A. (2000). *Preclinical mobility disability predicts incident mobility disability in older women.*
- Guralnik, J. M., Ferrucci, L., Simonsick, E. M., Salive, M. E., & Wallace, R. B. (1995). *Lower-extremity function in persons over the age of 70 years as a predictor of subsequent disability.*
