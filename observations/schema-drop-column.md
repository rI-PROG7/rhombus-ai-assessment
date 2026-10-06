# Schema drift: drop a column

## What I changed

Removed the `EstSpendTo20150630` column from the input. Nothing else changed.

- Input file: [`datasets/nswbudgetmessy-drift-schema-drop-column.csv`](../datasets/nswbudgetmessy-drift-schema-drop-column.csv)
- Baseline input: [`datasets/nswbudgetmessy.csv`](../datasets/nswbudgetmessy.csv)
- Regenerate with `python3 make_drift.py` in `datasets/`

## What I expected

`EstSpendTo20150630` is used by two cleaning nodes:

- `numeric_convert` converts it to a number;
- `data_quality_flag` uses it in the rule "EstSpendTo20150630 + Allocation201516 > ETC".

So I expected the pipeline to either **stop with a clear "column not found" error** at one of those nodes, or
**carry on silently**, skipping the spend check and writing an output without that column to GCS. The second outcome
would be the more dangerous one, because nothing would tell the user that a check stopped running.

## What happened

_To be filled in._

- Run result (stopped / warned / carried on):
- Failing node, if any:
- What reached GCS:

## What the logs said

_To be filled in._

## What the chatbot said

_To be filled in._

- Diagnosis correct?
- Fix applied:
- Did the fix work?

## What happened to the schedule

_To be filled in._

## Validation result

_To be filled in._

## How to reproduce

1. Start from the baseline pipeline with `datasets/nswbudgetmessy.csv` as input and confirm it runs successfully.
2. In the Data Input node, upload `datasets/nswbudgetmessy-drift-schema-drop-column.csv` and select it.
3. Run the pipeline manually (scheduled runs did not fire for this project; see [schedule-custom-cron-not-firing.md](schedule-custom-cron-not-firing.md)).
4. Check Logs, then the output file in the GCS bucket.
5. Run:
   ```bash
   cd data-validation
   python3 validate.py --input ../datasets/nswbudgetmessy-drift-schema-drop-column.csv \
     --output outputs/nswbudgetoutput-drift-schema-drop-column.csv \
     --reference outputs/baseline-manual-run.csv
   ```
