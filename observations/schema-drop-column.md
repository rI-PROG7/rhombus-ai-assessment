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

**First attempt: the drifted file was never used.** Uploading the drift file while the Data Input node was selected
silently created a **second, unconnected Data Input node**. The run reprocessed the old dataset, every node showed a
green tick, and the GCS output was byte-for-byte identical to the baseline output. Nothing warned that the new data
was not connected to the pipeline. Output saved as
[`nswbudgetoutput-drift-schema-drop-column-attempt1.csv`](../data-validation/outputs/nswbudgetoutput-drift-schema-drop-column-attempt1.csv).

**Second attempt** (drift file selected in the original, connected Data Input node):

- Run result: **stopped** at `dedup_rows` (the third cleaning node), not at the nodes that actually use the column.
- Error: `Missing columns: ['EstSpendTo20150630']`. The node had a hardcoded list of expected columns and raised
  an error when any was missing, even though deduplication does not need that column.
- What reached GCS: **nothing**. No new file was written to the bucket for the failed run.

**Third attempt** (after the chatbot's fix, see below):

- Run result: **carried on** and completed successfully. The Data Output destination had to be re-selected before this run.
- What reached GCS: [`nswbudgetoutput-drift-schema-drop-column.csv`](../data-validation/outputs/nswbudgetoutput-drift-schema-drop-column.csv),
  698 rows, 12 columns. `EstSpendTo20150630` is absent; every other column is identical to the baseline output.
- **The "EstSpendTo20150630 + Allocation201516 exceeds ETC" check silently stopped running.** In the baseline it
  flagged 3 rows; here it flagged none, including the two rows where Allocation201516 alone is three times ETC.
  No warning appeared in the logs or the output.

## What the logs said

For the failed run, the log names the node and the missing column clearly:
`Pipeline failed at dedup_rows: … Missing columns: ['EstSpendTo20150630']`.
The "Generated code" part of the message is truncated in the UI, so the failing line cannot be seen from the log.
Full entry: [schema-drop-column-logs.txt](evidence/schema-drop-column-logs.txt).

For the run after the fix, the logs reported success with no mention that a data-quality rule was skipped.

## What the chatbot said

Using **Ask Chatbot** on the error, with no hints:

> `dedup_rows` has been updated on the canvas. The fix removes the hardcoded `expected_columns` validation and the
> `raise ValueError` — the node now deduplicates against whatever columns are actually present in the incoming
> dataframe, making it resilient to schema drift. Re-running the pipeline from `dedup_rows` should clear the error.

- **Diagnosis correct?** Yes, for the node that failed: it identified the hardcoded column check as the cause.
- **Fix applied:** applied automatically to the canvas, without asking first.
- **Did the fix work?** Partly. The run completed, but only because the downstream nodes skip logic for missing
  columns. The chatbot did not mention that `data_quality_flag` also depends on `EstSpendTo20150630`, or that one of
  its checks would now silently stop running.

## What happened to the schedule

No change. The schedule stayed **Active** throughout, but **no scheduled run fired** during this case, before or
after the failed run, so the drift was only ever exercised through manual runs. Because the schedule never runs at all
for this project (see [schedule-custom-cron-not-firing.md](schedule-custom-cron-not-firing.md)), it is not possible to
say whether a failed run would pause or disable it.

## Validation result

Report: [validation-schema-drop-column.txt](evidence/validation-schema-drop-column.txt), run with the baseline output as `--reference`.

- **Caught:** `EstSpendTo20150630` missing compared with the reference output.
- **Caught:** the spend-exceeds-ETC rule flagged 3 rows in the reference and none here ("No data-quality rule silently stopped firing").
- Other failures (Region separator, data lost at upload) are the known baseline defects, unchanged by this drift.

## Severity

**High.** The pipeline first stopped (safe), but after the chatbot's one-click fix it ran successfully while silently
dropping a data-quality check, so invalid rows reach GCS unflagged and nothing tells the user.

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
     --reference outputs/nswbudgetoutput-manual-run.csv
   ```
