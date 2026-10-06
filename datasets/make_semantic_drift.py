"""
Create semantic-drift versions of nswbudgetmessy.csv. The structure (columns, names, types,
row count) is unchanged; only the meaning of the values changes.

  units:        amounts reported in dollars instead of thousands of dollars (x1000)
  years-swapped: StartYear and CompletionYear values swapped in every row

Usage: python3 make_semantic_drift.py
"""
import re

import pandas as pd

SRC = "nswbudgetmessy.csv"
AMOUNTS = ["ETC", "EstSpendTo20150630", "Allocation201516"]
base = pd.read_csv(SRC, dtype=str, keep_default_na=False)


def times_1000(v):
    """Scale plain integers by 1000; leave blanks, text and formatted values unchanged."""
    s = str(v).strip()
    return str(int(s) * 1000) if re.fullmatch(r"-?\d+", s) else v


units = base.copy()
for c in AMOUNTS:
    units[c] = units[c].map(times_1000)
units.to_csv("nswbudgetmessy-drift-semantic-units.csv", index=False)

swapped = base.copy()
swapped["StartYear"], swapped["CompletionYear"] = base["CompletionYear"], base["StartYear"]
swapped.to_csv("nswbudgetmessy-drift-semantic-years-swapped.csv", index=False)

for name, df in [("units", units), ("years-swapped", swapped)]:
    print(f"{name:14s} {df.shape[0]} rows, {df.shape[1]} cols, same columns: {list(df.columns) == list(base.columns)}")
