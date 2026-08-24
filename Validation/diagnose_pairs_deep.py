import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "orbis_paired_backtest.csv"

def deep_diagnose():
    if not CSV_PATH.exists():
        print(f"❌ Error: Could not find {CSV_PATH.name}")
        return

    df = pd.read_csv(CSV_PATH)
    features = ['t', 'rh', 'w', 'ndvi', 'slope', 'vpd', 'emc']

    # Normalize names if needed
    rename_map = {'temp_c': 't', 'humidity': 'rh', 'wind_speed': 'w'}
    df = df.rename(columns=rename_map)

    # Re-derive VPD/EMC if missing
    if 'vpd' not in df.columns:
        df['vpd'] = 0.61078 * np.exp((17.27 * df['t']) / (df['t'] + 237.3)) * (1 - df['rh'] / 100)
    if 'emc' not in df.columns:
        df['emc'] = 21.06 - (0.48 * df['rh']) - (0.00035 * df['rh'] * df['t'])

    fire = df[df['label'] == 1]
    ctrl = df[df['label'] == 0]

    print(f"📊 DEEP PAIR DIAGNOSTIC ({df['pair_id'].nunique()} pairs)\n")
    print("=" * 80)
    print(f"{'Feature':<10} | {'Fire Mean':<10} | {'Ctrl Mean':<10} | {'Fire Med':<10} | {'Ctrl Med':<10} | {'Fire > Ctrl %':<12}")
    print("=" * 80)

    for f in features:
        f_mean = fire[f].mean()
        c_mean = ctrl[f].mean()
        f_med = fire[f].median()
        c_med = ctrl[f].median()

        # Compute how often Fire value is greater than Control value in paired comparisons
        greater_count = 0
        total_pairs = 0
        for pair_id, grp in df.groupby('pair_id'):
            f_val = grp[grp['label'] == 1][f].values
            c_val = grp[grp['label'] == 0][f].values
            if len(f_val) > 0 and len(c_val) > 0:
                total_pairs += 1
                if f_val[0] > c_val[0]:
                    greater_count += 1
        
        pct_greater = (greater_count / total_pairs * 100) if total_pairs > 0 else 0.0
        print(f"{f:<10} | {f_mean:<10.4f} | {c_mean:<10.4f} | {f_med:<10.4f} | {c_med:<10.4f} | {pct_greater:<12.2f}%")

    print("=" * 80)

if __name__ == "__main__":
    deep_diagnose()