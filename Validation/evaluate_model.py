import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.metrics import roc_auc_score, brier_score_loss

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

BACKTEST_CSV = SCRIPT_DIR / "orbis_paired_backtest.csv"
if not BACKTEST_CSV.exists():
    BACKTEST_CSV = SCRIPT_DIR / "orbis_2023_holdout.csv"
if not BACKTEST_CSV.exists():
    BACKTEST_CSV = ROOT_DIR / "firms_era5_joined.csv"

MODEL_PATH = ROOT_DIR / "orbis_calibrated_model.joblib"
if not MODEL_PATH.exists():
    MODEL_PATH = ROOT_DIR / "orbis_base_xgb_model.joblib"

def evaluate():
    if not BACKTEST_CSV.exists():
        print("❌ Error: Evaluation dataset not found.")
        return
    if not MODEL_PATH.exists():
        print(f"❌ Error: Model binary not found at {MODEL_PATH}")
        return

    print(f"📊 Loading dataset: {BACKTEST_CSV.name}")
    df = pd.read_csv(BACKTEST_CSV)

    # 1. Column Normalization
    rename_map = {'temp_c': 't', 'humidity': 'rh', 'wind_speed': 'w', 'target': 'label'}
    df = df.rename(columns=rename_map)

    # 2. Derive Physical Features if missing
    if 'emc' not in df.columns:
        df['emc'] = 21.06 - (0.48 * df['rh']) - (0.00035 * df['rh'] * df['t'])
    if 'aspect' not in df.columns:
        df['aspect'] = 0.0

    # 3. Match feature set with training script
    features = ['slope', 'aspect', 'ndvi', 'w', 'emc']
    available_features = [f for f in features if f in df.columns]

    missing_feats = [f for f in features if f not in df.columns and f != 'aspect']
    if missing_feats:
        print(f"❌ Error: Missing required features in dataset: {missing_feats}")
        return

    X = df[available_features]
    y = df['label']

    # 4. Predict Probabilities
    model = joblib.load(MODEL_PATH)
    probs = model.predict_proba(X)[:, 1]
    df['prob'] = probs

    # 5. Metrics Calculation
    auc = roc_auc_score(y, probs)
    brier = brier_score_loss(y, probs)

    has_pairs = 'pair_id' in df.columns and df['pair_id'].nunique() > 1
    val_type = "Paired Spatial Contrast Backtest" if has_pairs else "Unpaired Backtest"

    print("\n" + "=" * 55)
    print(f"      ORBIS EVALUATION REPORT ({BACKTEST_CSV.name})")
    print("=" * 55)
    print(f"{'Validation Type':<35} : {val_type}")
    print(f"{'Total Evaluated Samples':<35} : {len(df)}")
    print(f"{'ROC-AUC Score':<35} : {auc:.4f}")
    print(f"{'Brier Score':<35} : {brier:.4f}")

    if has_pairs:
        correct = 0
        total_pairs = 0
        
        grouped = df.groupby('pair_id')
        for pair_id, group in grouped:
            fire_row = group[group['label'] == 1]
            ctrl_row = group[group['label'] == 0]

            if not fire_row.empty and not ctrl_row.empty:
                total_pairs += 1
                fire_prob = fire_row['prob'].values[0]
                ctrl_prob = ctrl_row['prob'].values[0]

                if fire_prob > ctrl_prob:
                    correct += 1

        pair_acc = (correct / total_pairs * 100) if total_pairs > 0 else 0.0
        print(f"{'Total Spatial Pairs':<35} : {total_pairs}")
        print(f"{'Paired Fire-vs-Control Accuracy':<35} : {pair_acc:.2f}% ({correct}/{total_pairs})")
    else:
        print("Notice: Unpaired dataset detected. Skipping spatial pair ranking.")

    print("=" * 55)

if __name__ == "__main__":
    evaluate()