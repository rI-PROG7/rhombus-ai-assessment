"""
Create schema-drift versions of nswbudgetmessy.csv. Each file changes exactly one thing,
except the combined file, which applies all four changes together.

Usage: python3 make_drift.py
"""
import pandas as pd

SRC = "nswbudgetmessy.csv"
base = pd.read_csv(SRC, dtype=str, keep_default_na=False)


def to_date(v):
    """StartYear integer -> ISO date string (start of the financial year)."""
    v = str(v).strip()
    return f"{v}-07-01" if v.isdigit() and len(v) == 4 else v


def drop_column(df):
    return df.drop(columns=["EstSpendTo20150630"])


def rename_column(df):
    return df.rename(columns={"Allocation201516": "Budget201516"})


def change_type(df):
    df = df.copy()
    df["StartYear"] = df["StartYear"].map(to_date)
    return df


def add_column(df):
    df = df.copy()
    sources = ["State", "Commonwealth", "Joint", "Private Partnership"]
    df.insert(df.columns.get_loc("AgencyCategory") + 1, "FundingSource",
              [sources[i % len(sources)] for i in range(len(df))])
    return df


cases = {
    "drop-column": drop_column,
    "rename-column": rename_column,
    "change-type": change_type,
    "add-column": add_column,
}
for name, fn in cases.items():
    fn(base).to_csv(f"nswbudgetmessy-drift-schema-{name}.csv", index=False)

combined = base
for fn in cases.values():
    combined = fn(combined)
combined.to_csv("nswbudgetmessy-drift-schema-all-combined.csv", index=False)

for name in list(cases) + ["all-combined"]:
    d = pd.read_csv(f"nswbudgetmessy-drift-schema-{name}.csv", dtype=str, keep_default_na=False)
    print(f"{name:14s} {d.shape[0]} rows, {d.shape[1]} cols")
