#!/usr/bin/env python3
"""Quick test to inspect coverage data."""
import pandas as pd
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COVERAGE_FILE = os.path.join(SCRIPT_DIR, 'insurance_medicine_coverage.csv')

print(f"Reading from: {COVERAGE_FILE}")
print(f"File exists: {os.path.exists(COVERAGE_FILE)}\n")

df = pd.read_csv(COVERAGE_FILE)
print(f"Shape: {df.shape} (rows, cols)")
print(f"Columns: {df.columns.tolist()}\n")

print("First 10 rows:")
print(df.head(10))

print(f"\nUnique medicines: {df['medicine_name'].unique().tolist()}")
print(f"Unique insurances: {df['insurance_name'].unique().tolist()}")

print(f"\nTotal coverage entries: {len(df)}")
print(f"\nCoverage 'covered' values: {df['covered'].unique().tolist()}")

# Show sample of coverage map
print("\n--- Sample Coverage Map ---")
for med in df['medicine_name'].unique()[:2]:
    med_data = df[df['medicine_name'] == med]
    print(f"\n{med}:")
    for _, row in med_data.iterrows():
        print(f"  {row['insurance_name']}: covered={row['covered']}")
