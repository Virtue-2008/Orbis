import joblib
import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def run_analysis():
    print("🔍 Analyzing Orbis v11.0 Feature Importance...")
    
    # Load model and metadata
    model_path = BASE_DIR / "orbis_base_xgb_model.joblib"
    meta_path = BASE_DIR / "model_metadata.json"
    
    if not model_path.exists() or not meta_path.exists():
        print("❌ Error: Model or metadata missing.")
        return

    model = joblib.load(model_path)
    with open(meta_path, "r") as f:
        meta = json.load(f)
        
    features = meta["features"]
    importances = model.feature_importances_
    
    # Create a sorted dataframe
    df = pd.DataFrame({
        'Feature': features,
        'Importance (Gain)': importances
    }).sort_values(by='Importance (Gain)', ascending=False)
    
    print("\n" + "="*50)
    print("    V11.0 CONTRASTIVE FEATURE IMPORTANCE")
    print("="*50)
    for idx, row in df.iterrows():
        print(f"{row['Feature']:<15} : {row['Importance (Gain)']:.4f}")
    print("="*50)
    print("Note: Higher values mean this feature's local spatial")
    print("contrast is highly predictive of ignition.")

if __name__ == "__main__":
    run_analysis()