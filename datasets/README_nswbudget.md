# Datasets

| File | What it is |
|---|---|
| `original_nswbudgetpaper2201516.csv` | Clean source: NSW Budget Paper 2, 2015-16 infrastructure statement (697 rows, 12 columns) |
| `baseline.csv` | Messy baseline used as pipeline input (704 rows) |
| `baseline_changes.csv` | Row-level log of every injected issue (54 entries) |
| `make_messy.py` | Script that generates `baseline.csv` and the log from the original (seed 42, deterministic) |

Regenerate with `python3 make_messy.py`. The output is byte-identical each run.

## Injected issues (54)

### Duplicates (7)
- 5 exact duplicate rows inserted at random positions.
- 2 near-duplicates: one with `ProjectName` uppercased, one with a trailing space in `Location`.
  These are not exact copies, so they only disappear if the pipeline trims/normalises before de-duplicating.

### Missing values (10)
- `AgencyName` blanked in 3 rows.
- `Allocation201516` blanked in 2 rows (on top of the 46 already blank in the source).
- Inconsistent null markers: `N/A`, `n/a`, `-` in `LGA`; `NULL`, `unknown` in `Type`.

### Inconsistent formatting (24)
- `Region`: `metropolitan sydney` (4 rows), `HUNTER` (2 rows).
- `Type`: `work in progress` instead of `Work-In-Progress` (3 rows).
- `AgencyName` with extra leading/trailing spaces (3 rows).
- `ProjectName` with a double internal space (3 rows).
- `Allocation201516` as currency text, e.g. `$57,366` (4 rows).
- `ETC` with a thousands separator, e.g. `88,000` (2 rows).
- `StartYear` as financial-year text, e.g. `2015-16` (3 rows).

### Invalid entries (13)
- Negative `Allocation201516` (3 rows), negative `ETC` (1 row).
- Non-numeric text: `TBC`, `TBA` in `ETC`; `N/A` in `EstSpendTo20150630`.
- `StartYear` later than `CompletionYear`, years swapped (2 rows).
- Impossible years: `CompletionYear` 2105, `StartYear` 1899.
- `Allocation201516` set to 3x ETC so spend + allocation exceeds ETC (2 rows).

Each issue is on a different row, so every finding traces back to one injected cause.
The original data also contains natural issues (blank Type/LGA/Region/years, 58 untrimmed
ProjectNames, a standalone `Sydney` region) which are not in the log.

## Expected result after cleaning
- Rows: 704 in -> 699 out after exact de-duplication (697 if near-duplicates are also removed).
- No amount or year values lost: formatted values (`$57,366`, `88,000`, `2015-16`) converted, not nulled.
- Null markers (`N/A`, `n/a`, `-`, `NULL`, `unknown`) treated as missing.
- Every invalid entry above flagged in `DataQualityIssue` (rows kept, not deleted).
