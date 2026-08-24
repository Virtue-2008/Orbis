import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "orbis_paired_backtest.csv"

def diagnose():
    if not CSV_PATH.exists():
        print(f"❌ Error: Could not find {CSV_PATH.name}")
        return

    df = pd.read_csv(CSV_PATH)
    features = ['t', 'rh', 'w', 'ndvi', 'slope', 'vpd', 'emc']

    print(f"📊 Analyzing {len(df)} samples ({df['pair_id'].nunique()} pairs) from {CSV_PATH.name}\n")

    # 1. Overall Feature Means (Fire vs. Control)
    fire = df[df['label'] == 1]
    ctrl = df[df['label'] == 0]

    print("=" * 65)
    print(f"{'Feature':<10} | {'Fire Mean':<12} | {'Control Mean':<12} | {'Delta (Fire - Ctrl)':<20}")
    print("=" * 65)
    for f in features:
        f_mean = fire[f].mean()
        c_mean = ctrl[f].mean()
        delta = f_mean - c_mean
        print(f"{f:<10} | {f_mean:<12.4f} | {c_mean:<12.4f} | {delta:<20.4f}")
    print("=" * 65)

    # 2. Direct Paired Differences (Fire - Control for each pair)
    deltas = []
    for pair_id, group in df.groupby('pair_id'):
        f_row = group[group['label'] == 1]
        c_row = group[group['label'] == 0]
        if not f_row.empty and not c_row.empty:
            d = {feat: f_row[feat].values[0] - c_row[feat].values[0] for feat in features}
            deltas.append(d)

    p_df = pd.DataFrame(deltas)

    print("\n--- PAIRED DIFFERENCE SUMMARY (Fire - Control per Pair) ---")
    summary = p_df[features].describe().T[['mean', 'std', 'min', '50%', 'max']]
    summary.columns = ['Mean Delta', 'Std Dev', 'Min Delta', 'Median Delta', 'Max Delta']
    print(summary.round(4))
    print("=" * 65)

if __name__ == "__main__":
    diagnose()