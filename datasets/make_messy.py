"""
Create datasets/baseline.csv from the clean NSW Budget Paper 2 (2015-16) file
by injecting a known, documented set of data-quality problems.

Deterministic: the same seed always produces the same file and change log.
Usage: python3 make_messy.py
"""
import random
import pandas as pd

SEED = 42
SRC = "nswbudgetpaper2201516.csv"
OUT = "nswbudgetmessy.csv"
LOG = "nswbudgetmessy_changes.csv"

rng = random.Random(SEED)
df = pd.read_csv(SRC, dtype=str, keep_default_na=False)
df.insert(0, "_src_row", range(1, len(df) + 1))  # original data-row number (header excluded)

used = set()
log = []


def pick(cond=lambda r: True):
    pool = [i for i in df.index if i not in used and cond(df.loc[i])]
    i = rng.choice(pool)
    used.add(i)
    return i


def change(i, col, new, category, issue):
    old = df.at[i, col]
    df.at[i, col] = new
    log.append(dict(category=category, issue=issue, src_row=df.at[i, "_src_row"],
                    project=df.at[i, "ProjectName"].strip(), column=col,
                    original=old, injected=new))


has = lambda c: (lambda r: r[c].strip() != "")
num_all = lambda r: all(r[c].strip() != "" for c in ["ETC", "EstSpendTo20150630", "Allocation201516"])
years = lambda r: r["StartYear"].strip() != "" and r["CompletionYear"].strip() != ""

# ---- Missing values / inconsistent null markers ----
for _ in range(3):
    change(pick(), "AgencyName", "", "missing", "AgencyName blanked")
for _ in range(2):
    change(pick(has("Allocation201516")), "Allocation201516", "", "missing", "Allocation blanked")
for marker in ["N/A", "n/a", "-"]:
    change(pick(has("LGA")), "LGA", marker, "missing", f"Null placeholder '{marker}' in LGA")
for marker in ["NULL", "unknown"]:
    change(pick(has("Type")), "Type", marker, "missing", f"Null placeholder '{marker}' in Type")

# ---- Inconsistent formatting ----
for _ in range(4):
    i = pick(lambda r: r["Region"] == "Metropolitan Sydney")
    change(i, "Region", "metropolitan sydney", "formatting", "Region lowercase")
for _ in range(2):
    i = pick(lambda r: r["Region"] == "Hunter")
    change(i, "Region", "HUNTER", "formatting", "Region uppercase")
for _ in range(3):
    i = pick(lambda r: r["Type"] == "Work-In-Progress")
    change(i, "Type", "work in progress", "formatting", "Type variant spelling")
for _ in range(3):
    i = pick()
    change(i, "AgencyName", "  " + df.at[i, "AgencyName"] + " ", "formatting", "AgencyName extra leading/trailing spaces")
for _ in range(3):
    i = pick(lambda r: " " in r["ProjectName"].strip())
    change(i, "ProjectName", df.at[i, "ProjectName"].strip().replace(" ", "  ", 1), "formatting", "ProjectName double internal space")
for _ in range(4):
    i = pick(lambda r: r["Allocation201516"].strip() not in ("", "0") and int(r["Allocation201516"]) >= 1000)
    v = int(df.at[i, "Allocation201516"])
    change(i, "Allocation201516", f"${v:,}", "formatting", "Amount with $ and thousands separator")
for _ in range(2):
    i = pick(lambda r: r["ETC"].strip() != "" and int(r["ETC"]) >= 1000)
    v = int(df.at[i, "ETC"])
    change(i, "ETC", f"{v:,}", "formatting", "Amount with thousands separator")
for _ in range(3):
    i = pick(has("StartYear"))
    y = int(df.at[i, "StartYear"])
    change(i, "StartYear", f"{y}-{str(y + 1)[2:]}", "formatting", "StartYear as financial-year text (e.g. 2015-16)")

# ---- Invalid entries ----
for _ in range(3):
    i = pick(lambda r: r["Allocation201516"].strip() not in ("", "0"))
    change(i, "Allocation201516", "-" + df.at[i, "Allocation201516"], "invalid", "Negative allocation")
i = pick(has("ETC")); change(i, "ETC", "-" + df.at[i, "ETC"], "invalid", "Negative ETC")
for val in ["TBC", "TBA"]:
    change(pick(has("ETC")), "ETC", val, "invalid", f"Non-numeric '{val}' in ETC")
change(pick(has("EstSpendTo20150630")), "EstSpendTo20150630", "N/A", "invalid", "Non-numeric 'N/A' in EstSpend")
for _ in range(2):
    i = pick(lambda r: years(r) and int(r["StartYear"]) < int(r["CompletionYear"]))
    s, c = df.at[i, "StartYear"], df.at[i, "CompletionYear"]
    change(i, "StartYear", c, "invalid", "StartYear later than CompletionYear (swapped)")
    df.at[i, "CompletionYear"] = s
    log[-1]["issue"] += f" (CompletionYear {c}->{s})"
i = pick(has("CompletionYear")); change(i, "CompletionYear", "2105", "invalid", "Impossible CompletionYear (typo)")
i = pick(has("StartYear")); change(i, "StartYear", "1899", "invalid", "Impossible StartYear")
for _ in range(2):
    i = pick(lambda r: num_all(r) and int(r["ETC"]) > 0)
    etc = int(df.at[i, "ETC"])
    change(i, "Allocation201516", str(etc * 3), "invalid", "Spend + allocation exceeds ETC")

# ---- Duplicates (rows otherwise untouched) ----
dup_rows = []
for _ in range(5):
    i = pick()
    dup_rows.append(df.loc[i].copy())
    log.append(dict(category="duplicate", issue="Exact duplicate row", src_row=df.at[i, "_src_row"],
                    project=df.at[i, "ProjectName"].strip(), column="(all)", original="", injected="copy inserted"))
near = []
i = pick(); r = df.loc[i].copy(); r["ProjectName"] = r["ProjectName"].upper(); near.append(r)
log.append(dict(category="duplicate", issue="Near-duplicate: ProjectName uppercased", src_row=df.at[i, "_src_row"],
                project=df.at[i, "ProjectName"].strip(), column="ProjectName", original=df.at[i, "ProjectName"], injected=r["ProjectName"]))
i = pick(); r = df.loc[i].copy(); r["Location"] = r["Location"] + " "; near.append(r)
log.append(dict(category="duplicate", issue="Near-duplicate: trailing space in Location", src_row=df.at[i, "_src_row"],
                project=df.at[i, "ProjectName"].strip(), column="Location", original=df.at[i, "Location"], injected=r["Location"]))

rows = [df.loc[i] for i in df.index]
for r in dup_rows + near:
    rows.insert(rng.randrange(len(rows) + 1), r)
out = pd.DataFrame(rows).reset_index(drop=True)

out.drop(columns="_src_row").to_csv(OUT, index=False)
pd.DataFrame(log).to_csv(LOG, index=False)
print(f"{OUT}: {len(out)} rows ({len(df)} original + {len(dup_rows)} exact + {len(near)} near duplicates)")
print(f"{LOG}: {len(log)} injected issues")
