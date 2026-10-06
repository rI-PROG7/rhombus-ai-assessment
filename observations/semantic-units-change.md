# Semantic drift: amounts in dollars instead of thousands

## What I changed

Multiplied every plain numeric value in `ETC`, `EstSpendTo20150630` and `Allocation201516` by 1000, as if the
source system started reporting **dollars instead of thousands of dollars** (the Budget Paper's unit is $'000).
Columns, names, types and row count are unchanged. Blank, text and already-formatted values were left as they were.

- Input file: [`datasets/nswbudgetmessy-drift-semantic-units.csv`](../datasets/nswbudgetmessy-drift-semantic-units.csv)
- Baseline input: [`datasets/nswbudgetmessy.csv`](../datasets/nswbudgetmessy.csv)
- Regenerate with `python3 make_semantic_drift.py` in `datasets/`

## What I expected

The structure is identical, so I expected the pipeline to **run successfully** and write amounts 1000 times too
large to GCS **without noticing**. The data-quality rules are all relative (negative values, spend + allocation vs
ETC), so scaling every amount by the same factor should not trigger any of them. I expected my validator to catch it
by comparing amount medians with the baseline output.

## What happened

- Run result: **carried on**. The run completed successfully with no warning.
- What reached GCS: [`nswbudgetoutput-drift-semantic-units.csv`](../data-validation/outputs/nswbudgetoutput-drift-semantic-units.csv),
  698 rows, 13 columns: the same rows and columns as the baseline output.
- Every amount is **exactly 1000 times** the baseline value (median ETC 13,196,000 against 13,196; median
  Allocation201516 3,591,500 against 3,591.5).
- **Rhombus did not notice.** The `DataQualityIssue` column flagged exactly the same 10 rows with the same
  messages as the baseline. All of its rules are relative (negative amounts, spend + allocation vs ETC), so scaling
  every amount by the same factor cannot trigger any of them.

## What the logs said

The run reported success, with nothing about the change in magnitude. _(Confirm against the Logs panel.)_

## What the chatbot said

There was no error to give it. _To be filled in: ask the chatbot "Does the output of my latest run look correct?"
without hinting at the change, and record whether it notices._

## What happened to the schedule

No change. The schedule stayed **Active** and no scheduled run fired (see
[schedule-custom-cron-not-firing.md](schedule-custom-cron-not-firing.md)). This case was exercised through a manual run.

## Validation result

Report: [validation-semantic-units.txt](evidence/validation-semantic-units.txt), with the baseline output as `--reference`.

- **Caught:** all three amount columns failed "scale vs reference" at **1000.00x** the baseline median.
- No other new failures: the schema, row count and cleaning checks all pass, which is exactly why this drift is
  dangerous. Only a comparison with known-good output reveals it. (The remaining failures are the known baseline
  defects: Region separator and data lost at upload.)

## Severity

**High.** A unit change that inflates every budget figure 1000-fold reaches GCS as a successful run with an
unchanged quality flag column. Any report built on this output would be wrong by three orders of magnitude.

## How to reproduce

1. Click the **connected** Data Input node, upload `datasets/nswbudgetmessy-drift-semantic-units.csv` while it is
   selected, select it under **Select Dataset** and click **Apply**. Delete any second, unconnected Data Input node.
2. Run the pipeline manually (scheduled runs did not fire for this project; see
   [schedule-custom-cron-not-firing.md](schedule-custom-cron-not-firing.md)).
3. Download the newest output from the GCS bucket.
4. Run:
   ```bash
   cd data-validation
   python validate.py --input ../datasets/nswbudgetmessy-drift-semantic-units.csv \
     --output outputs/nswbudgetoutput-drift-semantic-units.csv \
     --reference outputs/nswbudgetoutput-manual-run.csv
   ```
