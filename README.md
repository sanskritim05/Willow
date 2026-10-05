# Willow 

**An Early-Warning Check-In for Older Adults and Caregivers**

Willow is a healthcare AI project designed to identify early changes in an older adult's everyday functioning before those changes develop into a larger loss of independence.

Many older adults may still appear independent while quietly changing how they complete everyday activities. They may go out less often, use support while walking, skip certain activities, or change how they bathe or dress. These small changes can go unnoticed until a fall, hospitalization, or new need for assistance occurs.

Willow explores whether changes in a person's own behavior over time can help predict whether they will begin needing assistance with mobility or self-care within approximately one year.

## Project Goal

Willow combines longitudinal health data with an explainable machine-learning pipeline to answer several questions:

- Can changes from a person's previous behavior predict a new need for assistance one year later?
- Do longitudinal changes provide more predictive value than a single snapshot of someone's current condition?
- How does an interpretable logistic regression model compare with tree-based machine-learning models?
- Does model performance remain consistent across demographic and economic groups?
- Can older adults and caregivers understand and use the explanations produced by the system?

The long-term product concept is a short weekly check-in that tracks functional changes and presents them through an understandable timeline.

## Dataset

The project uses data from the **National Health and Aging Trends Study (NHATS)**.

For each person at year `t`, Willow compares information from the previous year (`t-1`) with their current status (`t`) and predicts whether they will newly require assistance at `t+1`.

Only participants who:

- are living at home, and
- are not currently receiving assistance at year `t`

are included in the prediction population.

## Features

The model uses both a person's **current status** and **changes from their own previous behavior**.

### Current Status

Features include difficulty with everyday activities such as:

- Going outside
- Moving around inside
- Getting out of bed
- Bathing
- Dressing
- Toileting
- Eating

Additional variables include device use, activity frequency, falls, pain, mood, memory, and age.

### Changes Over Time

Longitudinal features capture changes such as:

- Increased difficulty with activities
- New assistive-device use
- Going outside less frequently
- New falls
- Number of functional areas that declined

Additional measures available in NHATS include household activities, walking speed, chair stands, grip strength, and chronic conditions.

The planned application version focuses on approximately **30 features that a person can answer from home**.

## Machine Learning Models

Willow compares several approaches:

1. **Logistic Regression: Status Only**

   Serves as the baseline model using a person's current status.

2. **Logistic Regression: Status + Change Features**

   Adds information describing how the person's functioning has changed over time.

3. **Random Forest**

   Captures more complex relationships between features.

4. **XGBoost**

   Provides another tree-based approach for evaluating whether nonlinear models improve prediction.

The comparison helps determine whether additional model complexity provides enough benefit over a simpler and more interpretable model.

## Prediction Pipeline

```text
NHATS Data
    ↓
Data Cleaning & Preprocessing
    ↓
Longitudinal Feature Engineering
    ↓
Model Training
    ↓
Model Validation
    ↓
Explainability Analysis
    ↓
Willow Check-In Interface
    ↓
Risk Level + Key Changes + Timeline
```

The product concept translates the model output into three understandable levels:

```text
Steady → Watch → Talk to Someone
```

Rather than displaying only a prediction score, Willow is designed to show the changes that contributed to the result.

## Preventing Overfitting

Several validation strategies are planned to make sure the model generalizes to new people and future data.

**People-based split:**  
30% of participants are held out entirely so the final model is evaluated on people it has never seen.

**Time-based split:**  
Models are trained using earlier years and evaluated using later years to better represent real-world deployment.

**Cross-validation:**  
5-fold cross-validation is performed on the training data and grouped by person.

The final test set is used only once, and experiments are repeated across **10 different splits**.

## Model Evaluation

Performance will be evaluated using:

| Metric | Purpose |
|---|---|
| **AUROC** | Measures how well the model ranks people who will need help above those who will not |
| **AUPRC** | Evaluates performance when positive cases are relatively uncommon |
| **Calibration** | Tests whether predicted probabilities correspond to actual outcomes |
| **Sensitivity** | Measures how many people who eventually need help are correctly identified |
| **Precision** | Measures how many flagged individuals actually develop the outcome |

Approximately **9% of participants newly need assistance each year**, making AUPRC particularly important.

### Validation Targets

| Goal | Target |
|---|---|
| Overall performance | AUROC ≥ 0.75 |
| Calibration | Observed/expected ratio between 0.9 and 1.1 |
| Usability | Check-in completed in under 3 minutes |
| SUS | ≥ 68 |
| Explanation understanding | ≥ 80% correctly explain why they received their result |

## Explainability

Healthcare predictions should not simply produce a risk score without explaining where it came from.

Willow uses several approaches to make model behavior understandable.

### SHAP

For tree-based models, SHAP values are used to determine:

- which features matter most overall
- which features contributed most to an individual prediction

### Logistic Regression Coefficients

The coefficients from logistic regression provide an interpretable baseline for understanding the relationship between individual features and the predicted outcome.

### Functional Timeline

The application will visualize changes in activities over time so users can see trends themselves rather than relying entirely on the model's interpretation.

## Fairness & Error Analysis

Model performance will be compared across:

- Gender
- Race/ethnicity
- Economic status

The analysis will examine both accuracy and calibration across these groups.

Willow will also examine **false negatives**—people who eventually needed help but were not flagged—and **false positives**—people who were flagged but did not ultimately need assistance.

Because longitudinal studies can experience participant dropout, the project will also compare participants who leave NHATS with those who remain. This helps identify whether attrition could make the dataset appear healthier than the underlying population.

## Product Concept

Willow is designed as a lightweight weekly check-in rather than a wearable or continuous monitoring system.

A typical interaction would look like:

```text
Complete ~2 minute check-in
            ↓
Compare answers with personal history
            ↓
Identify meaningful changes
            ↓
Estimate future assistance risk
            ↓
Show risk level
            ↓
Explain which changes contributed
            ↓
Display longitudinal timeline
```

The goal is to make subtle functional changes easier for older adults, caregivers, and healthcare professionals to recognize.

## Usability Testing

The prototype will be evaluated with approximately **8–10 participants**, including older adults, caregivers, friends, or family members.

Testing will measure:

- Time required to complete the check-in
- System Usability Scale (SUS)
- Whether users understand the explanation
- Feedback gathered through short interviews

## Why Willow?

Existing systems often focus on a single signal, require additional hardware, or respond after an event has already happened.

Willow instead explores whether a short self-reported check-in can identify gradual changes before a major loss of independence.

The system is intended to provide:

**For older adults and caregivers:**  
A clear timeline showing how everyday functioning has changed.

**For clinicians:**  
A short and explainable summary of the changes contributing to a person's risk estimate.

Willow is intended to **support professional review, not replace it**. It does not diagnose conditions or recommend medical treatment.

## Potential Challenges

The project considers several limitations and implementation challenges:

- NHATS coding and missingness vary across survey waves.
- Only around 9% of participants newly require assistance each year, creating class imbalance.
- Some demographic subgroups may be too small for reliable fairness comparisons.
- Longitudinal participant dropout may introduce bias.
- Translating machine-learning explanations into language that caregivers can easily understand is an important design challenge.


## References

- CDC. *Older Adult Fall Prevention: Facts About Falls.*
- National Health and Aging Trends Study (NHATS). *User Guide, Rounds 1–14 Final Release.* Johns Hopkins Bloomberg School of Public Health, 2026.
- Freedman, V. A., & Kasper, J. D. (2019). *Cohort Profile: The National Health and Aging Trends Study (NHATS).* International Journal of Epidemiology.
- Fried, L. P., Bandeen-Roche, K., Chaves, P. H., & Johnson, B. A. (2000). *Preclinical mobility disability predicts incident mobility disability in older women.*
- Guralnik, J. M., Ferrucci, L., Simonsick, E. M., Salive, M. E., & Wallace, R. B. (1995). *Lower-extremity function in persons over the age of 70 years as a predictor of subsequent disability.*
- Kaye, J. A., et al. (2011). *Intelligent Systems for Assessing Aging Changes: home-based, unobtrusive, and continuous assessment of aging.*

-
