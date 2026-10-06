# Data validation

`validate.py` compares a Rhombus AI pipeline output (downloaded from GCS) with the CSV given to the pipeline,
and prints a PASS / FAIL / SKIP report. It exits with code 1 if any check fails.

## Setup

```bash
cd data-validation
python3 -m pip install -r requirements.txt
```

## Usage

```bash
# Baseline run, with the change log of injected issues
python3 validate.py \
  --input ../datasets/nswbudgetmessy.csv \
  --output outputs/nswbudgetoutput-run1.csv \
  --changes ../datasets/nswbudgetmessy_changes.csv

# Determinism: two scheduled runs on the same input
python3 validate.py \
  --input ../datasets/nswbudgetmessy.csv \
  --output outputs/nswbudgetoutput-run1.csv \
  --compare outputs/nswbudgetoutput-run2.csv

# Drift run: compare against the baseline output as reference
python3 validate.py \
  --input ../datasets/nswbudgetmessy-drift-<case>.csv \
  --output outputs/nswbudgetoutput-drift-<case>.csv \
  --reference outputs/nswbudgetoutput-run1.csv
```

Save each report as evidence, for example:

```bash
python3 validate.py --input ... --output ... > ../observations/evidence/validation-baseline.txt
```

## Checks

| Section | What it checks |
|---|---|
| Schema | All input columns plus `DataQualityIssue` present, nothing unexpected, order kept; numeric columns are numeric with no trailing `.0` |
| Row counts | Output rows = input rows minus exact (or normalised) duplicates; no duplicates left |
| Cleaning rules | Text trimmed and collapsed, no control characters; AgencyName / Type / LGA / Region have no blanks or null markers; canonical Type and Region values; Region separator `, ` |
| Data loss | Every amount or year present in the input (including `$57,366`, `22,647`, `2015-16` formats) still has a value in the output |
| Change log | Each of the 54 injected issues in `nswbudgetmessy_changes.csv` was handled: formatted values converted, invalid entries flagged, null markers filled, case standardised, whitespace cleaned |
| Determinism | Two outputs from the same input are identical (ignoring row order) |
| Semantic | Years outside 1900–2050 are flagged; known AgencyCategory values; spend to date rarely exceeds total cost; with `--reference`, amount medians within 0.2–5x and year medians within 2 years of the reference (catches unit changes such as dollars → cents, or shifted dates) |

## Notes and limitations

- Rows are matched between input and output by `ProjectName`; the dataset has no unique ID, and a few projects share a name.
- A null marker injected as an "invalid" entry (e.g. `N/A` in `EstSpendTo20150630`) passes if it is either flagged or treated as missing.
- The data-loss check allows for rows removed as near-duplicates, so it can under-count by one or two values; the change-log check covers those rows exactly.
