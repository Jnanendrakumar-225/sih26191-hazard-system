import numpy as np
import pandas as pd

def calculate_ahp_risk(df, weights):
    """
    Computes multi-hazard risk scores using Analytical Hierarchy Process (AHP) weights 
    and multi-criteria spatial factors.
    """
    total_w = sum(weights.values())
    if total_w == 0:
        normalized_w = {k: 0.25 for k in weights}
    else:
        normalized_w = {k: val / total_w for k, val in weights.items()}
    
    # Extract criteria vectors (normalized 0-1 scale)
    hazard_factor = df['hazard_score'] / 100.0
    exposure_factor = df['population'] / df['population'].max()
    vulnerability_factor = (df['children_population'] + df['elderly_population']) / df['population']
    accessibility_factor = (100.0 - df['accessibility_score']) / 100.0 
    
    # Composite AHP Score Calculation
    composite_score = (
        normalized_w.get('hazard', 0.3) * hazard_factor +
        normalized_w.get('exposure', 0.3) * exposure_factor +
        normalized_w.get('vulnerability', 0.2) * vulnerability_factor +
        normalized_w.get('accessibility', 0.2) * accessibility_factor
    ) * 100.0
    
    df['composite_risk_score'] = np.round(composite_score, 2)
    
    # Automated Phased Relocation Priority Matrix
    conditions = [
        (df['composite_risk_score'] >= 75),
        (df['composite_risk_score'] >= 50),
        (df['composite_risk_score'] < 50)
    ]
    choices = [
        'CRITICAL - Immediate Relocation (0–3 Months)', 
        'MODERATE - Short-Term Action', 
        'SAFE - Medium-Term Monitoring'
    ]
    df['risk_tier'] = np.select(conditions, choices, default='SAFE')
    
    return df