#!/usr/bin/env python3
"""
Validate a Rhombus AI pipeline output (GCS) against its input (S3 / uploaded CSV).

Checks
  1. Schema        - expected columns present, nothing unexpected, order kept
  2. Row counts    - output rows = input rows minus removed duplicates
  3. Cleaning rules- whitespace, null markers, fills, canonical values, numeric formats
  4. Data loss     - values present in the input are not silently blanked
  5. Change log    - every injected issue (datasets/*_changes.csv) was handled
  6. Determinism   - two outputs from the same input are identical (--compare)
  7. Semantic      - values are plausible vs a reference output (--reference):
                     amount scale, year range, known categories, spend vs cost

Usage
  python3 validate.py --input ../datasets/nswbudgetmessy.csv \
                      --output outputs/nswbudgetoutput-run1.csv \
                      [--changes ../datasets/nswbudgetmessy_changes.csv] \
                      [--compare outputs/nswbudgetoutput-run2.csv] \
                      [--reference outputs/nswbudgetoutput-run1.csv]

Exit code 0 if every check passes, 1 otherwise.
"""
import argparse
import re
import sys

import pandas as pd

TEXT_COLS = ["AgencyName", "AgencyCategory", "ProjectName", "Type", "Location", "LGA", "Region"]
AMOUNT_COLS = ["ETC", "EstSpendTo20150630", "Allocation201516"]
YEAR_COLS = ["StartYear", "CompletionYear"]
FILL_COLS = ["AgencyName", "Type", "LGA", "Region"]
FLAG_COL = "DataQualityIssue"
NULL_MARKERS = {"n/a", "-", "null", "unknown", "none", "nan", "<na>"}
REGIONS = {"Central Coast", "Central West & Orana", "Far West", "Hunter", "Illawarra",
           "Metropolitan Sydney", "Murray-Murrumbidgee", "New England-North West",
           "North Coast", "South East & Tablelands", "Not specified"}
TYPES = {"New Works", "Work-In-Progress", "Not specified"}
CATEGORIES = {"Community Services", "Education", "Government Services", "Health",
              "Police and Justice", "Roads", "Transport", "Utilities"}
YEAR_MIN, YEAR_MAX = 1900, 2050


class Report:
    def __init__(self):
        self.results = []

    def check(self, section, name, ok, detail=""):
        self.results.append((section, name, bool(ok), detail))

    def skip(self, section, name, reason):
        self.results.append((section, name, None, reason))

    def print(self):
        current = None
        for section, name, ok, detail in self.results:
            if section != current:
                print(f"\n== {section} ==")
                current = section
            tag = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
            print(f"[{tag}] {name}" + (f": {detail}" if detail else ""))
        passed = sum(1 for r in self.results if r[2] is True)
        failed = sum(1 for r in self.results if r[2] is False)
        skipped = sum(1 for r in self.results if r[2] is None)
        print(f"\nSummary: {passed} passed, {failed} failed, {skipped} skipped")
        return failed == 0


def load(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def blank(s):
    return s.str.strip() == ""


def parse_amount(v):
    """Expected numeric value of an input amount, or None if it is not a number."""
    t = str(v).strip().replace("$", "").replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


def parse_year(v):
    t = str(v).strip()
    m = re.fullmatch(r"(\d{4})(?:[-/]\d{2,4})?", t)
    return int(m.group(1)) if m else None


def norm_text(v):
    return re.sub(r"\s+", " ", str(v)).strip()


def examples(series, n=3):
    vals = list(dict.fromkeys(series.tolist()))[:n]
    return ", ".join(repr(v) for v in vals)


# ---------------------------------------------------------------- checks

def check_schema(rep, inp, out):
    s = "Schema"
    expected = list(inp.columns) + [FLAG_COL]
    missing = [c for c in expected if c not in out.columns]
    extra = [c for c in out.columns if c not in expected]
    rep.check(s, "All expected columns present", not missing, f"missing {missing}" if missing else f"{len(expected)} columns")
    rep.check(s, "No unexpected columns", not extra, f"extra {extra}" if extra else "")
    common = [c for c in out.columns if c in expected]
    rep.check(s, "Column order kept", common == [c for c in expected if c in common])
    for c in YEAR_COLS + AMOUNT_COLS:
        if c not in out.columns:
            continue
        vals = out[c][~blank(out[c])]
        bad = vals[pd.to_numeric(vals, errors="coerce").isna()]
        rep.check(s, f"{c} is numeric", bad.empty, f"{len(bad)} non-numeric, e.g. {examples(bad)}" if len(bad) else "")
        dot0 = vals[vals.str.endswith(".0")]
        rep.check(s, f"{c} has no trailing .0", dot0.empty, f"{len(dot0)} values" if len(dot0) else "")


def check_rows(rep, inp, out):
    s = "Row counts"
    exact = int(inp.duplicated().sum())
    normed = inp.apply(lambda col: col.map(norm_text).str.lower())
    loose = int(normed.duplicated().sum())
    lo, hi = len(inp) - loose, len(inp) - exact
    ok = lo <= len(out) <= hi
    rep.check(s, "Output rows = input rows minus duplicates", ok,
              f"{len(inp)} in -> {len(out)} out (expected {hi} after exact dedup, {lo} after normalised dedup)")
    rep.check(s, "No duplicate rows in output", not out.duplicated().any(), f"{int(out.duplicated().sum())} duplicates")


def check_rules(rep, inp, out):
    s = "Cleaning rules"
    for c in [c for c in TEXT_COLS if c in out.columns]:
        bad = out[c][(out[c] != out[c].str.strip()) | out[c].str.contains("  ")]
        rep.check(s, f"{c}: whitespace trimmed and collapsed", bad.empty, f"{len(bad)} values" if len(bad) else "")
        ctrl = out[c][out[c].str.contains(r"[\x00-\x1f]")]
        rep.check(s, f"{c}: no control characters", ctrl.empty, f"{len(ctrl)} values" if len(ctrl) else "")
    for c in [c for c in FILL_COLS if c in out.columns]:
        bad = out[c][blank(out[c]) | out[c].str.strip().str.lower().isin(NULL_MARKERS)]
        rep.check(s, f"{c}: no blanks or null markers", bad.empty, f"{len(bad)} values, e.g. {examples(bad)}" if len(bad) else "")
    if "Type" in out.columns:
        bad = out.Type[~out.Type.isin(TYPES)]
        rep.check(s, "Type: canonical values only", bad.empty, f"{len(bad)} values, e.g. {examples(bad)}" if len(bad) else "")
    if "Region" in out.columns:
        multi = out.Region[out.Region.str.contains(",")]
        badsep = multi[multi.str.contains(r",(?! )")]
        rep.check(s, "Region: multi-region separator is ', '", badsep.empty, f"{len(badsep)} values, e.g. {examples(badsep)}" if len(badsep) else "")
        parts = out.Region.str.split(r",\s*").explode()
        bad = parts[~parts.isin(REGIONS)]
        rep.check(s, "Region: canonical names only", bad.empty, f"{len(bad)} values, e.g. {examples(bad)}" if len(bad) else "")
    if {"Location", "LGA"} <= set(inp.columns) and {"Location", "LGA"} <= set(out.columns) and len(inp) == len(out):
        rep.skip(s, "LGA 'Various' rule", "row alignment not guaranteed; checked per project in change log")
    if FLAG_COL in out.columns:
        rep.check(s, f"{FLAG_COL} column populated for some rows", (~blank(out[FLAG_COL])).any())


def check_data_loss(rep, inp, out):
    s = "Data loss"
    inp = inp.drop_duplicates()  # exact duplicate rows are expected to disappear
    tol = max(0, len(inp) - len(out))  # near-duplicates removed after normalisation
    for c in [c for c in AMOUNT_COLS + YEAR_COLS if c in inp.columns and c in out.columns]:
        parse = parse_year if c in YEAR_COLS else parse_amount
        in_parseable = int(inp[c].map(lambda v: parse(v) is not None).sum())
        in_text = int((~blank(inp[c]) & inp[c].map(lambda v: parse(v) is None)
                       & ~inp[c].str.strip().str.lower().isin(NULL_MARKERS)).sum())
        out_values = int((~blank(out[c])).sum())
        lost = in_parseable - out_values
        rep.check(s, f"{c}: input values kept", lost <= tol,
                  f"{in_parseable} parseable in input, {out_values} in output"
                  + (f" -> {lost - tol} lost" if lost > tol else "")
                  + (f"; {in_text} non-numeric input values" if in_text else ""))


def check_changes(rep, out, changes_path):
    s = "Change log"
    log = load(changes_path)
    key = out["ProjectName"].map(norm_text).str.lower() if "ProjectName" in out.columns else None
    if key is None:
        rep.skip(s, "Injected issues", "ProjectName column missing")
        return
    flags = out[FLAG_COL] if FLAG_COL in out.columns else pd.Series([""] * len(out))
    handled, failed = 0, []
    for _, r in log.iterrows():
        cat, issue, col = r["category"], r["issue"], r["column"]
        rows = out[key == norm_text(r["project"]).lower()]
        if rows.empty:
            failed.append(f"{issue} ({r['project'][:40]}): row not found")
            continue
        flag_vals = flags[rows.index]
        vals = rows[col] if col in rows.columns else None
        ok = True
        if cat == "duplicate":
            ok = len(rows) >= 1 and not rows.duplicated().any()
        elif cat == "invalid":
            # a null marker such as 'N/A' may legitimately be treated as missing instead of flagged
            as_missing = str(r["injected"]).strip().lower() in NULL_MARKERS and vals is not None and blank(vals).all()
            ok = (~blank(flag_vals)).any() or as_missing
        elif "Amount with" in issue:
            want = parse_amount(r["injected"])
            ok = vals is not None and (pd.to_numeric(vals, errors="coerce") == want).any()
        elif "financial-year" in issue:
            want = parse_year(r["injected"])
            ok = vals is not None and (pd.to_numeric(vals, errors="coerce") == want).any()
        elif issue == "Allocation blanked":
            ok = vals is not None and blank(vals).any()
        elif cat == "missing":
            ok = vals is not None and not (blank(vals) | vals.str.strip().str.lower().isin(NULL_MARKERS)).any()
        elif "Region" in issue:
            ok = vals is not None and vals.str.split(r",\s*").explode().isin(REGIONS).all()
        elif "Type" in issue:
            ok = vals is not None and vals.isin(TYPES).all()
        elif "space" in issue:
            ok = vals is not None and (vals == vals.map(norm_text)).all()
        if ok:
            handled += 1
        else:
            shown = examples(vals) if vals is not None else ""
            failed.append(f"{issue} ({r['project'][:40]}): got {shown or 'n/a'}")
    rep.check(s, f"Injected issues handled", not failed, f"{handled}/{len(log)} handled")
    for f in failed:
        rep.check(s, "  " + f, False)


def check_determinism(rep, out, other_path):
    s = "Determinism"
    other = load(other_path)
    same_cols = list(out.columns) == list(other.columns)
    rep.check(s, "Same columns in both runs", same_cols)
    if not same_cols:
        return
    a = out.sort_values(list(out.columns)).reset_index(drop=True)
    b = other.sort_values(list(other.columns)).reset_index(drop=True)
    same = a.equals(b)
    detail = f"{len(out)} vs {len(other)} rows"
    if not same and len(a) == len(b):
        diff_cells = int((a != b).sum().sum())
        detail += f", {diff_cells} cells differ"
    rep.check(s, "Identical output for identical input", same, detail)


def check_semantic(rep, out, ref_path):
    s = "Semantic"
    for c in YEAR_COLS:
        if c not in out.columns:
            continue
        y = pd.to_numeric(out[c], errors="coerce").dropna()
        bad = y[(y < YEAR_MIN) | (y > YEAR_MAX)]
        flagged = 0
        if FLAG_COL in out.columns and len(bad):
            flagged = int((~blank(out.loc[bad.index, FLAG_COL])).sum())
        rep.check(s, f"{c}: implausible years flagged", len(bad) == flagged,
                  f"{len(bad)} outside {YEAR_MIN}-{YEAR_MAX}, {flagged} flagged")
    if "AgencyCategory" in out.columns:
        bad = out.AgencyCategory[~out.AgencyCategory.isin(CATEGORIES)]
        rep.check(s, "AgencyCategory: known values only", bad.empty, f"{len(bad)} values, e.g. {examples(bad)}" if len(bad) else "")
    if {"EstSpendTo20150630", "ETC"} <= set(out.columns):
        sp = pd.to_numeric(out.EstSpendTo20150630, errors="coerce")
        etc = pd.to_numeric(out.ETC, errors="coerce")
        both = sp.notna() & etc.notna() & (etc > 0)
        share = float((sp[both] > etc[both]).mean()) if both.any() else 0.0
        rep.check(s, "Spend to date rarely exceeds total cost", share <= 0.05, f"{share:.1%} of rows")
    if not ref_path:
        rep.skip(s, "Distribution vs reference", "no --reference given")
        return
    ref = load(ref_path)
    lost_cols = [c for c in ref.columns if c not in out.columns]
    new_cols = [c for c in out.columns if c not in ref.columns]
    rep.check(s, "Columns match reference output", not lost_cols and not new_cols,
              (f"missing vs reference {lost_cols}" if lost_cols else "")
              + ("; " if lost_cols and new_cols else "")
              + (f"new vs reference {new_cols}" if new_cols else ""))
    if FLAG_COL in out.columns and FLAG_COL in ref.columns:
        def flag_counts(df):
            return df[FLAG_COL][~blank(df[FLAG_COL])].str.split("; ").explode().value_counts()
        fo, fr = flag_counts(out), flag_counts(ref)
        gone = {k: int(v) for k, v in fr.items() if k not in fo.index}
        rep.check(s, "No data-quality rule silently stopped firing", not gone,
                  f"rules flagged in reference but not here: {gone}" if gone else
                  f"{int((~blank(out[FLAG_COL])).sum())} rows flagged vs {int((~blank(ref[FLAG_COL])).sum())} in reference")
    for c in AMOUNT_COLS:
        if c not in out.columns or c not in ref.columns:
            rep.skip(s, f"{c}: scale vs reference", "column missing")
            continue
        m_out = pd.to_numeric(out[c], errors="coerce").median()
        m_ref = pd.to_numeric(ref[c], errors="coerce").median()
        if pd.isna(m_out) or pd.isna(m_ref) or m_ref == 0:
            rep.skip(s, f"{c}: scale vs reference", "no numeric values")
            continue
        ratio = m_out / m_ref
        rep.check(s, f"{c}: scale vs reference", 0.2 <= ratio <= 5, f"median {m_out:g} vs {m_ref:g} ({ratio:.2f}x)")
    for c in YEAR_COLS:
        if c not in out.columns or c not in ref.columns:
            continue
        m_out = pd.to_numeric(out[c], errors="coerce").median()
        m_ref = pd.to_numeric(ref[c], errors="coerce").median()
        if pd.notna(m_out) and pd.notna(m_ref):
            rep.check(s, f"{c}: median vs reference", abs(m_out - m_ref) <= 2, f"{m_out:g} vs {m_ref:g}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="CSV given to the pipeline")
    ap.add_argument("--output", required=True, help="CSV the pipeline wrote to GCS")
    ap.add_argument("--changes", help="change log of injected issues")
    ap.add_argument("--compare", help="second output from the same input (determinism)")
    ap.add_argument("--reference", help="known-good output to compare value distributions against")
    a = ap.parse_args()

    inp, out = load(a.input), load(a.output)
    print(f"Input:  {a.input} ({len(inp)} rows, {len(inp.columns)} columns)")
    print(f"Output: {a.output} ({len(out)} rows, {len(out.columns)} columns)")

    rep = Report()
    check_schema(rep, inp, out)
    check_rows(rep, inp, out)
    check_rules(rep, inp, out)
    check_data_loss(rep, inp, out)
    if a.changes:
        check_changes(rep, out, a.changes)
    else:
        rep.skip("Change log", "Injected issues", "no --changes given")
    if a.compare:
        check_determinism(rep, out, a.compare)
    else:
        rep.skip("Determinism", "Identical output for identical input", "no --compare given")
    check_semantic(rep, out, a.reference)
    sys.exit(0 if rep.print() else 1)


if __name__ == "__main__":
    main()
