import pandas as pd
import numpy as np
import joblib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "orbis_calibrated_model.joblib"

def generate_synthetic_grid(size=10):
    np.random.seed(42)
    data = []
    base_t = 30.0
    base_rh = 20.0
    
    for row in range(size):
        for col in range(size):
            t = base_t + np.random.normal(0, 1)
            rh = np.clip(base_rh + np.random.normal(0, 2), 5, 100)
            w = np.random.lognormal(mean=2.0, sigma=0.5) 
            
            # The extreme wind tunnel anomaly
            if 4 <= row <= 6 and 4 <= col <= 6:
                w += 15.0  
                slope = np.random.uniform(20, 45) 
            else:
                slope = np.random.uniform(0, 15)  
                
            aspect = np.random.uniform(0, 360)
            ndvi = np.random.uniform(0.2, 0.6)
            dist_to_road = np.random.uniform(0.1, 5.0)
            
            data.append({'row': row, 'col': col, 't': t, 'rh': rh, 'w': w, 
                         'slope': slope, 'aspect': aspect, 'ndvi': ndvi, 'dist_to_road': dist_to_road})
            
    return pd.DataFrame(data)

def run_spatial_inference():
    if not MODEL_PATH.exists():
        print("❌ Error: Model missing.")
        return

    print("🛰️ Initializing ORBIS Spatial Inference Engine (v11.1 Clipped)...")
    df = generate_synthetic_grid(size=10)
    
    df['emc'] = 21.06 - (0.48 * df['rh']) - (0.00035 * df['rh'] * df['t'])
    df['aspect_sin'] = np.sin(np.radians(df['aspect']))
    df['aspect_cos'] = np.cos(np.radians(df['aspect']))
    
    svp = 0.61078 * np.exp((17.27 * df['t']) / (df['t'] + 237.3))
    df['vpd'] = svp * (1.0 - (df['rh'] / 100.0))
    df['w_channeled'] = df['w'] * (1.0 + (df['slope'] / 45.0) * np.maximum(0.0, df['aspect_cos']))
    df['hdw'] = df['vpd'] * df['w_channeled']
    
    features = ['slope', 'aspect_sin', 'aspect_cos', 'ndvi', 'w', 'w_channeled', 'emc', 'vpd', 'hdw', 'dist_to_road']
    
    # Gate 1: Macro-Climate Check
    regional_emc = df['emc'].mean()
    if regional_emc > 15.0:
        print(f"✅ Region is safe. Regional EMC ({regional_emc:.2f}%) exceeds ignition threshold.")
        return
        
    print(f"⚠️ Regional EMC ({regional_emc:.2f}%) is critical. Engaging Gate 2 Contrastive Mapping...\n")
    
    # Gate 2: Contrastive Anomaly Calculation
    mean_state = df[features].mean()
    contrast_df = df[features] - mean_state
    
    # --- THE FIX: FEATURE CLIPPING ---
    # Cap the contrast inputs so XGBoost never falls out-of-distribution
    contrast_df['w'] = np.clip(contrast_df['w'], -5.0, 5.0)
    contrast_df['w_channeled'] = np.clip(contrast_df['w_channeled'], -5.0, 5.0)
    
    model = joblib.load(MODEL_PATH)
    df['risk_prob'] = model.predict_proba(contrast_df)[:, 1]
    
    print("🔥 ORBIS LOCALIZED IGNITION RISK MAP 🔥")
    print("=" * 40)
    grid_map = np.zeros((10, 10))
    for _, row in df.iterrows():
        grid_map[int(row['row']), int(row['col'])] = row['risk_prob']
        
    for r in range(10):
        row_str = ""
        for c in range(10):
            prob = grid_map[r, c]
            if prob > 0.8: row_str += "🟥 "
            elif prob > 0.6: row_str += "🟧 "
            elif prob > 0.4: row_str += "🟨 "
            else: row_str += "🟩 "
        print(row_str)
    print("=" * 40)
    print("🟩 <40% | 🟨 40-60% | 🟧 60-80% | 🟥 >80% Anomaly Risk")

if __name__ == "__main__":
    run_spatial_inference()