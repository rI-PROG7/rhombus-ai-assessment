# Code of the `data_quality_flag` node, copied from the Rhombus UI on 2026-10-06
# AFTER the AI builder reported fix attempt 1 as applied.
# Note: still uses the 2000-2040 year range and has no non-numeric-text check
# ("Condition 2" is missing), contrary to the builder's reply.

# Start from input_df_1
df = input_df_1.copy()

# Initialize issues list for each row using positions
issues_list = [[] for _ in range(len(df))]

amount_cols = ['EstSpendTo20150630', 'Allocation201516', 'ETC']
year_cols = ['StartYear', 'CompletionYear']

# Check Condition 1: Negative amounts
for col in amount_cols:
    if col in df.columns:
        # For nullable Int64, negative values are numeric and < 0
        mask = (df[col].notna()) & (df[col] < 0)
        positions = np.where(mask)[0]
        for pos in positions:
            issues_list[pos].append(f'Negative amount in {col}')

# Check Condition 3: StartYear > CompletionYear (both not null)
start_col = 'StartYear'
comp_col = 'CompletionYear'
if start_col in df.columns and comp_col in df.columns:
    mask = (df[start_col].notna()) & (df[comp_col].notna()) & (df[start_col] > df[comp_col])
    positions = np.where(mask)[0]
    for pos in positions:
        issues_list[pos].append('StartYear later than CompletionYear')

# Check Condition 4: Year out of range (2000-2040 inclusive)
for col in year_cols:
    if col in df.columns:
        # Check values outside 2000-2040
        mask = (df[col].notna()) & ((df[col] < 2000) | (df[col] > 2040))
        positions = np.where(mask)[0]
        for pos in positions:
            issues_list[pos].append(f'Year out of range in {col}')

# Check Condition 5: EstSpendTo20150630 + Allocation201516 > ETC (all three not null)
col1, col2, col3 = 'EstSpendTo20150630', 'Allocation201516', 'ETC'
if col1 in df.columns and col2 in df.columns and col3 in df.columns:
    mask = (df[col1].notna()) & (df[col2].notna()) & (df[col3].notna()) & \
           ((df[col1] + df[col2]) > df[col3])
    positions = np.where(mask)[0]
    for pos in positions:
        issues_list[pos].append(f'{col1} + {col2} exceeds {col3}')

# Build the DataQualityIssue column
df['DataQualityIssue'] = ['; '.join(issues) for issues in issues_list]

# Create output_mask: mark only the new column as True
output_mask = pd.DataFrame(False, index=df.index, columns=df.columns)
output_mask['DataQualityIssue'] = True

output_df = df
