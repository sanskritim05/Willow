"""Canonical long-format schema produced by the NHATS loader.

One row per person per round. Every downstream step (features, models, app export) only sees
these names; `nhats.py` is the only module that knows NHATS variable names.

Feature groups follow the proposal (System/Analysis Plan, 02 Features):
  * status now      - difficulty with 7 activities, device use, doing things less often, how often
                      they go out, falls, pain, mood, memory/cognition, age
  * change          - built in features.py from the same items at t-1 vs t
  * extra measures  - household tasks, walking speed, chair stands, grip strength, chronic conditions ...
"""

MOBILITY = ["go_outside", "get_around_inside", "get_out_of_bed"]
SELFCARE = ["eating", "bathing", "toileting", "dressing"]
ACTIVITIES = MOBILITY + SELFCARE

DEVICE_ACTS = list(ACTIVITIES)  # NHATS derived device-use measures exist for all seven
LESS_ACTS = ["go_outside", "get_around_inside", "bathing", "dressing"]          # *yrgo items
WOUT_ACTS = ["go_outside", "get_around_inside", "get_out_of_bed", "eating", "bathing", "dressing"]  # *wout

HELP_COLS = [f"{a}_help" for a in ACTIVITIES]
DIFF_COLS = [f"{a}_diff" for a in ACTIVITIES]
DEVICE_COLS = [f"{a}_device" for a in DEVICE_ACTS]
LESS_COLS = [f"{a}_less" for a in LESS_ACTS]
WOUT_COLS = [f"{a}_wout" for a in WOUT_ACTS]

# ---- status-now items (the core check-in content)
CORE_ORDINAL = DIFF_COLS + ["go_out_freq", "self_rated_health", "phq2", "dementia_class"]
CORE_BINARY = DEVICE_COLS + LESS_COLS + WOUT_COLS + ["fell_last_year", "pain_limits", "hospital_stay"]
CORE_ITEMS = CORE_ORDINAL + CORE_BINARY

# ---- extra measures
IADL_TASKS = ["laundry", "shopping", "meals", "banking", "meds"]
EXTRA_NUMERIC = ["capacity_limits", "n_chronic", "walk_time", "chair_time", "grip_max", "balance_score",
                 "perf_unable", "network_size", "bmi"]
EXTRA_BINARY = ([f"iadl_{x}_diff" for x in IADL_TASKS] + [f"iadl_{x}_hhelp" for x in IADL_TASKS] +
                ["cannot_walk_6blocks", "cannot_climb_10stairs", "low_energy", "balance_problem",
                 "lower_body_weak", "breathing_problem", "weight_loss_10lb", "stroke", "poor_vision",
                 "poor_hearing", "memory_worse", "memory_poor"])
EXTRA_ITEMS = EXTRA_NUMERIC + EXTRA_BINARY

ORDINAL_ITEMS = CORE_ORDINAL + EXTRA_NUMERIC
BINARY_ITEMS = CORE_BINARY + EXTRA_BINARY
TRACKED_ITEMS = ORDINAL_ITEMS + BINARY_ITEMS        # everything carried into the windows

STATIC = ["medicaid"]                                # status predictor and an economic-status subgroup
DEMOGRAPHICS = ["age", "female", "lives_alone", "proxy"]   # race/ethnicity and income are NOT predictors
HIGHER_IS_BETTER = {"grip_max", "balance_score", "network_size"}
NO_DIRECTION = {"bmi"}

# ---- fairness (proposal: gender, race/ethnicity, economic status) + secondary audit groups
FAIRNESS_PRIMARY = ["female", "race_eth", "low_income"]
FAIRNESS_SECONDARY = ["medicaid", "lives_alone", "proxy", "dementia_any", "age_85plus"]
SUBGROUP_COLS = FAIRNESS_PRIMARY + FAIRNESS_SECONDARY

STATUS_COMMUNITY = "community"

# Groups of items that form one human-readable "change" for explanations.
CHANGE_GROUPS = {
    "Going out less often": ["go_out_freq", "go_outside_less", "go_outside_wout"],
    "Harder to go outside": ["go_outside_diff", "go_outside_device"],
    "Harder to move around inside": ["get_around_inside_diff", "get_around_inside_device",
                                     "get_around_inside_less", "get_around_inside_wout"],
    "Harder to get out of bed": ["get_out_of_bed_diff", "get_out_of_bed_device", "get_out_of_bed_wout"],
    "Changes in bathing": ["bathing_diff", "bathing_device", "bathing_less", "bathing_wout"],
    "Changes in dressing": ["dressing_diff", "dressing_device", "dressing_less", "dressing_wout"],
    "Harder to use the toilet": ["toileting_diff", "toileting_device"],
    "Harder to eat independently": ["eating_diff", "eating_device", "eating_wout"],
    "Recent fall": ["fell_last_year"],
    "Worse self-rated health": ["self_rated_health"],
    "More depressive symptoms": ["phq2"],
    "Cognitive change": ["dementia_class"],
    "Memory getting worse (self-report)": ["memory_worse", "memory_poor"],
    "Pain limiting activity": ["pain_limits"],
    "Hospital stay": ["hospital_stay"],
    "Household tasks getting harder": [f"iadl_{x}_diff" for x in IADL_TASKS] + [f"iadl_{x}_hhelp" for x in IADL_TASKS],
    "Physical capacity declining": ["capacity_limits", "cannot_walk_6blocks", "cannot_climb_10stairs",
                                    "lower_body_weak"],
    "Slower or weaker on physical tests": ["walk_time", "chair_time", "grip_max", "balance_score", "perf_unable"],
    "Low energy, balance or breathing problems": ["low_energy", "balance_problem", "breathing_problem"],
    "Unintended weight loss": ["weight_loss_10lb"],
    "New chronic condition or stroke": ["n_chronic", "stroke"],
    "Vision or hearing decline": ["poor_vision", "poor_hearing"],
    "Shrinking social network": ["network_size"],
}

# the everyday-activity changes the check-in is built around (subset of CHANGE_GROUPS)
ACTIVITY_GROUPS = ["Going out less often", "Harder to go outside", "Harder to move around inside",
                   "Harder to get out of bed", "Changes in bathing", "Changes in dressing", "Harder to use the toilet",
                   "Harder to eat independently"]

ITEM_LABELS = {
    "go_out_freq": "How often goes outside (0 = every day, 4 = never)",
    "self_rated_health": "Self-rated health (1 excellent - 5 poor)",
    "phq2": "Depressive symptoms (PHQ-2, 0-6)",
    "dementia_class": "Dementia classification (0 none, 1 possible, 2 probable)",
    "fell_last_year": "Recent fall (NHATS: fell in the last month)",
    "pain_limits": "Pain limits activities",
    "hospital_stay": "Hospital stay in the last year",
    "capacity_limits": "Number of 10 physical tasks the person cannot do (walk 6 blocks, climb stairs, ...)",
    "n_chronic": "Number of chronic conditions (of 9)", "walk_time": "Seconds to walk 3 m (best trial)",
    "chair_time": "Seconds for 5 chair stands", "grip_max": "Grip strength (kg, best trial)",
    "balance_score": "Balance stands completed (0-3)", "perf_unable": "Physical tests not completed (0-4)",
    "network_size": "People in social network (0-5)", "bmi": "Body-mass index",
    "cannot_walk_6blocks": "Cannot walk 6 blocks", "cannot_climb_10stairs": "Cannot climb 10 stairs",
    "low_energy": "Low energy in last month", "balance_problem": "Balance or coordination problems",
    "lower_body_weak": "Lower-body strength limits activity", "breathing_problem": "Breathing problems",
    "weight_loss_10lb": "Lost 10+ lb in last year", "stroke": "Ever had a stroke",
    "poor_vision": "Cannot see across the street", "poor_hearing": "Cannot hear well on the phone",
    "memory_worse": "Memory worse than a year ago (self or proxy report)",
    "memory_poor": "Rates memory fair or poor",
    "medicaid": "Covered by Medicaid",
}
for a in ACTIVITIES:
    nice = a.replace("_", " ")
    ITEM_LABELS[f"{a}_diff"] = f"Difficulty {nice} alone"
    ITEM_LABELS[f"{a}_help"] = f"Help from a person: {nice}"
    ITEM_LABELS[f"{a}_device"] = f"Uses a device for {nice}"
for a in LESS_ACTS:
    ITEM_LABELS[f"{a}_less"] = f"Does {a.replace('_', ' ')} less often than a year ago"
for a in WOUT_ACTS:
    ITEM_LABELS[f"{a}_wout"] = f"Went without {a.replace('_', ' ')} (no help / too hard)"
for x in IADL_TASKS:
    ITEM_LABELS[f"iadl_{x}_diff"] = f"Difficulty doing {x} by self"
    ITEM_LABELS[f"iadl_{x}_hhelp"] = f"Someone else does {x} because of health"
