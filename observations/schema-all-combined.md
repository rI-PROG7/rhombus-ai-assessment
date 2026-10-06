# Schema drift: all four changes combined

## What I changed

Applied all four schema changes to the input at once:

| Change | Detail |
|---|---|
| Drop a column | `EstSpendTo20150630` removed |
| Rename a column | `Allocation201516` → `Budget201516` |
| Change a data type | `StartYear` from a 4-digit year (`2015`) to a date string (`2015-07-01`) |
| Add a column | New `FundingSource` column after `AgencyCategory` (`State`, `Commonwealth`, `Joint`, `Private Partnership`) |

- Input file: [`datasets/nswbudgetmessy-drift-schema-all-combined.csv`](../datasets/nswbudgetmessy-drift-schema-all-combined.csv)
- Baseline input: [`datasets/nswbudgetmessy.csv`](../datasets/nswbudgetmessy.csv)
- Regenerate with `python3 make_drift.py` in `datasets/`

**Pipeline state before this run:** `dedup_rows` had already been changed by the chatbot during the
[drop-column case](schema-drop-column.md) to deduplicate on whatever columns are present, so the missing column
will not stop the pipeline at that node any more. This case was run before the individual rename, type-change and
add-column cases.

## What I expected

- **Dropped `EstSpendTo20150630`:** no longer stops `dedup_rows`; the spend-exceeds-ETC check silently stops
  running, as in the drop-column case.
- **Renamed `Allocation201516` → `Budget201516`:** `numeric_convert` and `data_quality_flag` look for
  `Allocation201516` by name, so I expected either a "missing column" error, or `Budget201516` passing through
  **unconverted** (still containing values like `$57,366` if they survived upload) with the negative-allocation
  check silently skipped.
- **`StartYear` as `2015-07-01`:** the year parser handles `YYYY` and `YYYY-YY`. A full date may be cut to `2015`,
  turned into null, or rejected by Rhombus's upload type detection, so start years may be silently lost and the
  StartYear > CompletionYear check would stop working.
- **New `FundingSource` column:** probably passed through to the output unchanged, or dropped without notice.

Overall I expected the pipeline either to **stop** at the first node that needs a missing column, or to **carry on**
and write an output to GCS with several checks silently disabled, which would be the worst outcome.

## What happened

- Run result: **carried on**. Every node completed and the run reported success; nothing stopped or warned.
- What reached GCS: [`nswbudgetoutput-drift-schema-all-combined.csv`](../data-validation/outputs/nswbudgetoutput-drift-schema-all-combined.csv),
  704 rows, 13 columns.

How each change was handled:

| Change | What reached GCS | Verdict |
|---|---|---|
| `EstSpendTo20150630` dropped | Column absent; the spend-exceeds-ETC check flagged **0 rows** (3 in the baseline) | ❌ Check silently disabled |
| `Allocation201516` → `Budget201516` | Column passed through **without the cleaning applied**: values written as decimals (`250.0`) instead of whole numbers; the 3 **negative allocations** (`-200.0`, `-500.0`, `-30207.0`) are **no longer flagged**; the allocation-exceeds-ETC rows are no longer flagged | ❌ Cleaning and two checks silently skipped |
| `StartYear` as `2015-07-01` | Converted back to `2015`; the swapped-year and year-1899 rows were still flagged | ✅ Handled correctly |
| New `FundingSource` column | Passed through unchanged, in its original position | ✅ Passed through |

Flags overall: **5 rows flagged, against 10 in the baseline**. The rows that lost their flags are exactly the
invalid entries in the renamed and dropped columns, and nothing in the output or the logs says these checks were
skipped.

**Rows: 704, against 698 in the baseline.** The five injected duplicate rows were **not removed**. This is mostly
an artefact of how I generated the test file: `FundingSource` was assigned by row position, so each duplicate got a
different `FundingSource` value and the rows were no longer exact duplicates. Deduplicating on all columns was
therefore technically correct, but it shows that adding a column can quietly change which rows count as duplicates.

## What the logs said

The run reported success. No warning about the missing `EstSpendTo20150630` or `Allocation201516` columns, the
unexpected `Budget201516` and `FundingSource` columns, or the skipped checks. _(Confirm against the Logs panel.)_

## What the chatbot said

Not consulted for an error, because there was no error to give it. The pipeline completed and gave no indication
that anything needed fixing, which is the core problem with this case: a user relying on run status and logs would
not know to ask.

## What happened to the schedule

No change. The schedule stayed **Active** and no scheduled run fired (see
[schedule-custom-cron-not-firing.md](schedule-custom-cron-not-firing.md)). This case was exercised through a manual run.

## Validation result

Report: [validation-schema-all-combined.txt](evidence/validation-schema-all-combined.txt), with the baseline output as `--reference`.

- **Caught:** columns missing vs reference (`EstSpendTo20150630`, `Allocation201516`) and new columns (`FundingSource`, `Budget201516`).
- **Caught:** two data-quality rules stopped firing: "Negative amount in Allocation201516" (3 rows) and the spend-exceeds-ETC rule (3 rows).
- **Not caught by the validator:** the decimal formatting in `Budget201516` and the retained duplicates. The validator
  checks amount formats by column name, so a renamed column escapes those checks; this is a limitation of my script.

## Comparison with the drop-column case

In the [drop-column case](schema-drop-column.md) the first run **stopped** at `dedup_rows`. Here it did not stop at
all, because the chatbot's fix from that case made `dedup_rows` accept any columns. A one-click fix for one drift
made the pipeline tolerate a much larger drift silently.

## Severity

**High.** Four structural changes at once produced a successful run, a plausible-looking output in GCS, and half
the data-quality flags missing, with no error, warning or log message.

## How to reproduce

1. Start from the pipeline as it was after the drop-column case (chatbot fix to `dedup_rows` applied).
2. Click the **connected** Data Input node at the start of the chain, upload
   `datasets/nswbudgetmessy-drift-schema-all-combined.csv` while it is selected, select it under **Select Dataset**,
   and click **Apply**. Check that no second, unconnected Data Input node appeared.
3. Run the pipeline manually (scheduled runs did not fire for this project; see
   [schedule-custom-cron-not-firing.md](schedule-custom-cron-not-firing.md)).
4. Check Logs, then the newest output file in the GCS bucket.
5. Run:
   ```bash
   cd data-validation
   python validate.py --input ../datasets/nswbudgetmessy-drift-schema-all-combined.csv \
     --output outputs/nswbudgetoutput-drift-schema-all-combined.csv \
     --reference outputs/nswbudgetoutput-manual-run.csv
   ```
