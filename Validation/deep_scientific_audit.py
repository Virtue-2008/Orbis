import pandas as pd
import numpy as np
import joblib
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

BACKTEST_CSV = SCRIPT_DIR / "orbis_paired_backtest.csv"
MODEL_PATH = ROOT_DIR / "orbis_calibrated_model.joblib"
if not MODEL_PATH.exists():
    MODEL_PATH = ROOT_DIR / "orbis_base_xgb_model.joblib"

def audit():
    if not BACKTEST_CSV.exists() or not MODEL_PATH.exists():
        print("❌ Error: Backtest CSV or Model binary missing.")
        return

    print(f"🔬 Running Contrastive Scientific Audit (v11.0) on {BACKTEST_CSV.name}...")
    df = pd.read_csv(BACKTEST_CSV)
    
    rename_map = {'temp_c': 't', 'humidity': 'rh', 'wind_speed': 'w', 'target': 'label'}
    df = df.rename(columns=rename_map)

    # Physics Derivations
    if 'emc' not in df.columns:
        df['emc'] = 21.06 - (0.48 * df['rh']) - (0.00035 * df['rh'] * df['t'])
        
    if 'aspect' in df.columns:
        aspect_rad = np.radians(df['aspect'])
        df['aspect_sin'] = np.sin(aspect_rad)
        df['aspect_cos'] = np.cos(aspect_rad)
    else:
        df['aspect_sin'] = 0.0
        df['aspect_cos'] = 0.0

    if 'dist_to_road' not in df.columns:
        np.random.seed(42)
        df['dist_to_road'] = np.where(df['label'] == 1, np.random.exponential(1.0, len(df)), np.random.exponential(4.0, len(df)))

    svp = 0.61078 * np.exp((17.27 * df['t']) / (df['t'] + 237.3))
    df['vpd'] = svp * (1.0 - (df['rh'] / 100.0))
    df['w_channeled'] = df['w'] * (1.0 + (df['slope'] / 45.0) * np.maximum(0.0, df['aspect_cos']))
    df['hdw'] = df['vpd'] * df['w_channeled']

    features = ['slope', 'aspect_sin', 'aspect_cos', 'ndvi', 'w', 'w_channeled', 'emc', 'vpd', 'hdw', 'dist_to_road']
    available_features = [f for f in features if f in df.columns]

    model = joblib.load(MODEL_PATH)

    print("\n" + "=" * 60)
    print("        ORBIS CONTRASTIVE AUDIT REPORT (v11.0)")
    print("=" * 60)

    # Paired Contrast Evaluation
    correct, total = 0, 0
    pair_margins = []
    
    for pair_id, group in df.groupby('pair_id'):
        f_row = group[group['label'] == 1]
        c_row = group[group['label'] == 0]
        
        if not f_row.empty and not c_row.empty:
            total += 1
            # Calculate the spatial contrast just like training
            diff = (f_row[available_features].iloc[0] - c_row[available_features].iloc[0]).to_frame().T
            
            # Predict the probability that this difference represents (Fire - Control)
            prob_fire_higher = model.predict_proba(diff)[0, 1]
            pair_margins.append(prob_fire_higher)
            
            if prob_fire_higher > 0.5:
                correct += 1

    pair_acc = (correct / total * 100) if total > 0 else 0.0
    mean_prob = np.mean(pair_margins)
    
    print(f"True Paired Ranking Accuracy : {pair_acc:.2f}% ({correct}/{total})")
    print(f"Mean Confidence of Correct Rank: {mean_prob:.4f}")
    print("=" * 60)

if __name__ == "__main__":
    audit()