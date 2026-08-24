import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from xgboost import XGBClassifier
from sklearn.calibration import CalibratedClassifierCV

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "firms_era5_joined.csv"

def train_and_export():
    if not DATA_FILE.exists():
        print(f"❌ Error: Training data not found at {DATA_FILE}")
        return

    print(f"📖 Loading dataset: {DATA_FILE.name}")
    df = pd.read_csv(DATA_FILE)

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

    print(f"🔄 Constructing True Spatial Contrast pairs (v11.0)...")
    fires = df[df['label'] == 1].copy()
    controls = df[df['label'] == 0].copy()

    paired_rows = []
    has_date = 'date_str' in df.columns
    groups = fires.groupby('date_str') if has_date else [(0, fires)]

    for _, f_group in groups:
        for _, f_row in f_group.iterrows():
            c_row = controls.sample(1, random_state=42).iloc[0]
            
            # Label 1: Fire - Control (Positive spatial anomaly)
            diff_feat = {f: f_row[f] - c_row[f] for f in available_features}
            diff_feat['label'] = 1
            paired_rows.append(diff_feat)

            # Label 0: Control - Fire (Negative spatial anomaly)
            inv_feat = {f: c_row[f] - f_row[f] for f in available_features}
            inv_feat['label'] = 0
            paired_rows.append(inv_feat)

    train_df = pd.DataFrame(paired_rows)
    X_train = train_df[available_features]
    y_train = train_df['label']

    print(f"🌲 Training Contrastive XGBoost (v11.0) on {len(train_df)} anomalies...")
    base_xgb = XGBClassifier(
        n_estimators=600,
        max_depth=5,
        learning_rate=0.01,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric='logloss',
        random_state=42
    )
    base_xgb.fit(X_train, y_train)

    print("🎯 Calibrating Probabilities (5-Fold CV)...")
    calibrated_model = CalibratedClassifierCV(estimator=base_xgb, method='isotonic', cv=5)
    calibrated_model.fit(X_train, y_train)

    joblib.dump(calibrated_model, BASE_DIR / "orbis_calibrated_model.joblib")
    joblib.dump(base_xgb, BASE_DIR / "orbis_base_xgb_model.joblib")
    
    with open(BASE_DIR / "model_metadata.json", "w") as f:
        json.dump({"model_version": "11.0_true_contrastive", "training_samples": len(train_df), "features": available_features}, f, indent=4)
        
    print("✅ Model v11.0 exported successfully.")

if __name__ == "__main__":
    train_and_export()