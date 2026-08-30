import pandas as pd
import numpy as np
from src.carrying_capacity import evaluate_ecological_limits

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2.0)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2.0)**2
    return R * (2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)))

def find_optimal_safe_zone(hab_row: pd.Series, shelters_df: pd.DataFrame) -> dict:
    shelters = shelters_df.copy()
    shelters['distance_km'] = haversine_distance(
        hab_row['latitude'], hab_row['longitude'],
        shelters['latitude'], shelters['longitude']
    ).round(2)
    
    best_shelter = shelters.sort_values(by='distance_km').iloc[0]
    report = evaluate_ecological_limits(best_shelter, hab_row['population'])
    
    warnings = []
    if report['headcount_deficit'] > 0:
        warnings.append(f"Bed Deficit: {int(report['headcount_deficit'])} citizens exceed shelter headroom.")
    if report['water_breached']:
        warnings.append(f"Ecological Breach: Demands {report['water_needed']} L/day freshwater (exceeds supply).")
    if report['road_breached']:
        warnings.append(f"Bottleneck: Access road width ({best_shelter.get('road_width_m')}m) restricts evacuation convoys.")
        
    return {
        "recommended_shelter": best_shelter['name'],
        "distance_km": best_shelter['distance_km'],
        "available_capacity": int(best_shelter['total_capacity'] - best_shelter['current_occupancy']),
        "warnings": warnings,
        "is_viable": len(warnings) == 0
    }