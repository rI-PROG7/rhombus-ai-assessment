# Semantic drift: start and completion years swapped

## What I changed

Swapped the values of `StartYear` and `CompletionYear` in every row, as if an upstream export mapped the two fields
the wrong way round. This is the same kind of error as month/day becoming day/month: column names, types and value
ranges all still look valid, but the meaning is reversed. Nothing else changed.

- Input file: [`datasets/nswbudgetmessy-drift-semantic-years-swapped.csv`](../datasets/nswbudgetmessy-drift-semantic-years-swapped.csv)
- Baseline input: [`datasets/nswbudgetmessy.csv`](../datasets/nswbudgetmessy.csv)
- Regenerate with `python3 make_semantic_drift.py` in `datasets/`

## What I expected

The pipeline has a rule that flags "StartYear later than CompletionYear", so I expected Rhombus to **run
successfully** but flag almost every row with a known start and completion year. The flag is per row, though, so I
expected **no run-level warning**: the output would reach GCS looking like hundreds of individual data errors rather
than one systematic problem. I expected my validator to catch it both with a reference-free check (start later than
completion in most rows) and by comparing year medians with the baseline output.

## What happened

- Run result: **carried on**. The run completed successfully with no run-level warning.
- What reached GCS: [`nswbudgetoutput-drift-semantic-years-swapped.csv`](../data-validation/outputs/nswbudgetoutput-drift-semantic-years-swapped.csv),
  698 rows, 13 columns. `StartYear` and `CompletionYear` are reversed in every row.
- Rows flagged "StartYear later than CompletionYear": **524 of 698**, against 2 in the baseline. Every row with
  both years present is flagged.
- **Rhombus noticed only row by row.** The existing rule fired on each row, but nothing at run level said that
  almost the entire dataset was suspect. The output arrives in GCS looking like hundreds of separate data errors
  rather than one systematic mapping problem, and downstream users still receive the swapped years.

## What the logs said

The run reported success. No warning that 75% of rows failed a data-quality rule. _(Confirm against the Logs panel.)_

## What the chatbot said

There was no error to give it. _To be filled in: ask the chatbot "Does the output of my latest run look correct?"
without hinting at the change, and record whether it notices._

## What happened to the schedule

No change. The schedule stayed **Active** and no scheduled run fired (see
[schedule-custom-cron-not-firing.md](schedule-custom-cron-not-firing.md)). This case was exercised through a manual run.

## Validation result

Report: [validation-semantic-years-swapped.txt](evidence/validation-semantic-years-swapped.txt), with the baseline output as `--reference`.

- **Caught without a reference:** "StartYear rarely later than CompletionYear" failed at **97.8%** of rows
  (0.4% in the baseline).
- **Caught against the reference:** median StartYear 2017 vs 2014 and median CompletionYear 2014 vs 2017.
- The remaining failures are the known baseline defects (Region separator, data lost at upload).

## Severity

**Medium.** Unlike the units case the pipeline's own rule does fire, so a user reading the flag column would see a
problem. But the run still reports success, there is no threshold or alert when most rows fail a check, and the
swapped data is delivered to GCS regardless.

## How to reproduce

1. Click the **connected** Data Input node, upload `datasets/nswbudgetmessy-drift-semantic-years-swapped.csv` while
   it is selected, select it under **Select Dataset** and click **Apply**. Delete any second, unconnected Data Input node.
2. Run the pipeline manually (scheduled runs did not fire for this project; see
   [schedule-custom-cron-not-firing.md](schedule-custom-cron-not-firing.md)).
3. Download the newest output from the GCS bucket.
4. Run:
   ```bash
   cd data-validation
   python validate.py --input ../datasets/nswbudgetmessy-drift-semantic-years-swapped.csv \
     --output outputs/nswbudgetoutput-drift-semantic-years-swapped.csv \
     --reference outputs/nswbudgetoutput-manual-run.csv
   ```
