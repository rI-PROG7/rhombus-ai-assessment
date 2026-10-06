# AI builder: initial cleaning pipeline

## What I did

Uploaded `datasets/baseline.csv` (704 rows, 54 injected issues, see `datasets/baseline_changes.csv`)
and sent the cleaning prompt in [ai-builder-prompt.md](evidence/ai-builder-prompt.md) to the AI builder.

## Attempt 1

### What the builder reported

Six cleaning nodes added between Data Input and Data Output:
`null_and_whitespace_clean` → `region_type_standardised` → `dedup_rows` → `fill_missing` →
`numeric_convert` → `data_quality_flag`. The reply said "seven transformation nodes" but listed six plus Data Output.

### How I verified it

Downloaded the full preview of `data_quality_flag` (698 rows, sampling not limiting) and compared it
row by row with the input and the change log.
Downloaded file: [`data-validation/outputs/ai-build-v1_preview.csv`](../data-validation/outputs/ai-build-v1_preview.csv)

### What worked

- 5 exact duplicates removed, plus the trailing-space near-duplicate (704 → 698 rows).
- Whitespace trimmed and repeated spaces collapsed; no `None` strings or control characters.
- Real LGAs kept where Location is `Various` (e.g. Northern Sydney Freight Corridor still `Hornsby`).
- Blank Type / LGA / Region / AgencyName filled with `Not specified`.
- Negative amounts and spend-exceeds-ETC rows flagged in `DataQualityIssue`.

### What failed

Row numbers refer to `ai-build-v1_preview.csv` (header excluded).

| #   | Problem | Where to see it |
| --- | ------- | --------------- |
| 1   | **CompletionYear blank in all 698 rows** (input had 112 blanks). Real data destroyed; swapped-year and year-2105 checks could never fire. | Any row, e.g. rows 1–20 |
| 2   | `$57,366`-style amounts (4), `22,647`-style ETCs (2) and `2015-16` start years (3) became **null and unflagged**, despite the prompt forbidding silent nulls. | Row 233, Byron Central Hospital (Allocation201516 blank) |
| 3   | `TBC` / `TBA` in ETC became null and were **not flagged** (conversion runs before the flag node). | Row 563, Ferry Fleet Replacement |
| 4   | `metropolitan sydney` (4), `HUNTER` (2), `work in progress` (3) **not standardised**, although the reply listed these exact fixes. | Rows 30–32; rows 207, 209 |
| 5   | Multi-region values still joined with `,` instead of `, ` (21 values). | e.g. `Metropolitan Sydney,Illawarra` |
| 6   | 18 rows flagged "Year out of range in StartYear"; 17 are genuine 1990s programs. **Caused by my prompt** (2000–2040 range was too strict), not the builder. | e.g. Warragamba Dam General Upgrade (1997) |

### Takeaway

The builder's summary claimed fixes (points 2–4) that the data shows were not applied, and one node
silently wiped a whole column. Checking the node preview against the input, not the chat reply,
was the only way to find this.

## Fix attempt 1

### What I asked for

Sent the six problems above back to the builder, asking it to update the existing nodes rather than add new ones.
Full prompt and reply: [ai-builder-prompt.md → Fix attempt 1](evidence/ai-builder-prompt.md#fix-attempt-1).

### What the builder reported

- `region_type_standardised`: replaced what it described as **stub code** (`import re`) with a case-insensitive
  canonical mapping for Region and Type; multi-region values split on `/`, `|`, `;` or `and`, then rejoined with `, `.
- `numeric_convert`: keeps a copy of each raw value in a `_orig_` helper column, strips `$` and commas, parses
  `YYYY-YY` financial years, and handles CompletionYear the same way as StartYear so it is no longer wiped.
- `data_quality_flag`: checks the `_orig_` copies for non-numeric text (`TBC`, `TBA`) before conversion,
  uses a year range of < 1900 or > 2050, and drops the helper columns from the output.

### Early observations (before re-checking the data)

- The builder's own wording confirms the attempt-1 Region/Type node was a stub, so the attempt-1 summary
  described a mapping that had never been implemented.
- The new split list does **not include a comma**, which is the separator the data actually uses
  (`Metropolitan Sydney,Illawarra`). Problem 5 may still be unfixed.

### Result of re-checking

**None of the fixes were applied. The builder's edits were never saved to the nodes.**

1. Downloading the `data_quality_flag` preview straight after the builder's reply failed with
   *"Download failed for node … Error downloading output"*, although every node showed a green tick.
2. After re-running the pipeline, the downloaded preview
   ([`ai-build-v2_preview.csv`](../data-validation/outputs/ai-build-v2_preview.csv)) was
   **byte-for-byte identical** to the attempt-1 output (same size, same MD5 checksum). A second download gave the same result.
3. Opening the `data_quality_flag` node's code showed it is **still the attempt-1 code**
   ([saved copy](evidence/data_quality_flag-code-after-fix-1.py)):
   - the year range is still `< 2000 or > 2040`, not the `< 1900 or > 2050` the builder reported;
   - there is no `_orig_` helper column and no check for non-numeric text at all;
   - the code comments skip "Condition 2" (non-numeric text), so that rule was never implemented, even in attempt 1.

| #   | Problem | Fixed? |
| --- | ------- | ------ |
| 1   | CompletionYear wiped | ❌ Still blank in all 698 rows |
| 2   | Formatted amounts and years nulled | ❌ Byron row 233 still blank, unflagged |
| 3   | TBC / TBA not flagged | ❌ Rows 563, 214 blank, unflagged |
| 4   | Region / Type case not standardised | ❌ `metropolitan sydney` 4, `HUNTER` 2, `work in progress` 3 |
| 5   | Region separator | ❌ Still `,` with no space (21 values) |
| 6   | Year range false positives | ❌ Still 18 flags; code still uses 2000–2040 |

### Takeaway (fix attempt 1)

The builder replied "All three compiles succeeded … fixes applied to the existing nodes" and described
specific code changes (`_orig_` columns, a new year range) that do not exist in the node. The canvas gave no
sign that anything was wrong. Only inspecting the node's code and diffing the output exposed it.
This is a higher-severity finding than attempt 1: the platform reported a fix as applied when it was not.
