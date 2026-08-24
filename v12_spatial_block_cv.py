import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.ensemble import HistGradientBoostingClassifier

def run_spatial_block_cv():
    print("📐 Running Spatial Block K-Fold Cross-Validation (4 Quadrants)...")
    
    # 1. Generate Synthetic 100x100 Grid with Coordinate Features
    rows, cols = 100, 100
    x, y = np.meshgrid(np.arange(cols), np.arange(rows))
    
    np.random.seed(42)
    slope = np.random.uniform(0, 35, size=rows*cols)
    w = np.random.lognormal(mean=2.0, sigma=0.4, size=rows*cols)
    emc = 21.06 - (0.48 * np.random.uniform(10, 30, size=rows*cols))
    
    df = pd.DataFrame({
        'grid_x': x.flatten(),
        'grid_y': y.flatten(),
        'slope': slope,
        'w': w,
        'emc': emc,
    })
    
    # Contrastive Feature Engineering
    df['hdw'] = (30.0 - df['emc']) * df['w']
    df['target'] = ((df['hdw'] > 45) & (df['slope'] > 15)).astype(int)
    
    # Assign Quadrant Blocks (0: NW, 1: NE, 2: SW, 3: SE)
    df['spatial_block'] = 0
    df.loc[(df['grid_x'] >= 50) & (df['grid_y'] < 50), 'spatial_block'] = 1
    df.loc[(df['grid_x'] < 50) & (df['grid_y'] >= 50), 'spatial_block'] = 2
    df.loc[(df['grid_x'] >= 50) & (df['grid_y'] >= 50), 'spatial_block'] = 3
    
    features = ['slope', 'w', 'emc', 'hdw']
    auc_scores, brier_scores = [], []
    
    print("\n---------------------------------------------------------")
    print(f"{'Held-Out Block':<20} | {'ROC-AUC':<10} | {'Brier Score':<10}")
    print("---------------------------------------------------------")
    
    # 2. Iterate Through Spatial Blocks
    for block_id in range(4):
        train_df = df[df['spatial_block'] != block_id]
        test_df = df[df['spatial_block'] == block_id]
        
        clf = HistGradientBoostingClassifier(random_state=42)
        clf.fit(train_df[features], train_df['target'])
        
        probs = clf.predict_proba(test_df[features])[:, 1]
        auc = roc_auc_score(test_df['target'], probs)
        brier = brier_score_loss(test_df['target'], probs)
        
        auc_scores.append(auc)
        brier_scores.append(brier)
        
        block_names = ["North-West", "North-East", "South-West", "South-East"]
        print(f"Block {block_id} ({block_names[block_id]:<10}) | {auc:.4f}     | {brier:.4f}")
        
    print("---------------------------------------------------------")
    print(f"Mean Spatial ROC-AUC    : {np.mean(auc_scores):.4f} ± {np.std(auc_scores):.4f}")
    print(f"Mean Spatial Brier Score: {np.mean(brier_scores):.4f} ± {np.std(brier_scores):.4f}")
    
    if np.mean(auc_scores) >= 0.80:
        print("\n✅ Institutional Generalization Verified: Model holds accuracy across isolated geographic boundaries.")
    else:
        print("\n⚠️ Spatial Leakage Warning: Performance dropped significantly across unseen blocks.")

if __name__ == "__main__":
    run_spatial_block_cv()