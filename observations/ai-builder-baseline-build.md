# AI builder: initial cleaning pipeline (attempt 1)

## What I did

Uploaded `datasets/baseline.csv` (704 rows, 54 injected issues, see `datasets/baseline_changes.csv`)
and sent the cleaning prompt in [ai-builder-prompt.md](evidence/ai-builder-prompt.md) to the AI builder.

## What the builder reported

Six cleaning nodes added between Data Input and Data Output:
`null_and_whitespace_clean` → `region_type_standardised` → `dedup_rows` → `fill_missing` →
`numeric_convert` → `data_quality_flag`. The reply said "seven transformation nodes" but listed six plus Data Output.

## How I verified it

Downloaded the full preview of `data_quality_flag` (698 rows, sampling not limiting) and compared it
row by row with the input and the change log.

## What worked

- 5 exact duplicates removed, plus the trailing-space near-duplicate (704 → 698 rows).
- Whitespace trimmed and repeated spaces collapsed; no `None` strings or control characters.
- Real LGAs kept where Location is `Various` (e.g. Northern Sydney Freight Corridor still `Hornsby`).
- Blank Type / LGA / Region / AgencyName filled with `Not specified`.
- Negative amounts and spend-exceeds-ETC rows flagged in `DataQualityIssue`.

## What failed

| #   | Problem                                                                                                                                                       | Evidence |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| 1   | **CompletionYear blank in all 698 rows** (input had 112 blanks). Real data destroyed; swapped-year and year-2105 checks could never fire.                     |
| 2   | `$57,366`-style amounts (4), `22,647`-style ETCs (2) and `2015-16` start years (3) became **null and unflagged**, despite the prompt forbidding silent nulls. |
| 3   | `TBC` / `TBA` in ETC became null and were **not flagged** (conversion runs before the flag node).                                                             |
| 4   | `metropolitan sydney` (4), `HUNTER` (2), `work in progress` (3) **not standardised**, although the reply listed these exact fixes.                            |
| 5   | Multi-region values still joined with `,` instead of `, ` (21 values).                                                                                        |
| 6   | 18 rows flagged "Year out of range in StartYear"; 17 are genuine 1990s programs. **Caused by my prompt** (2000–2040 range was too strict), not the builder.   |

## Takeaway

The builder's summary claimed fixes (points 2–4) that the data shows were not applied, and one node
silently wiped a whole column. Checking the node preview against the input, not the chat reply,
was the only way to find this.

## Fix attempt

_To be filled in after sending the correction prompt and re-checking._
