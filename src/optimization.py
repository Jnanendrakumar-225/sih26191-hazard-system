import numpy as np
import pandas as pd
from typing import Tuple, Dict, List, Any
from scipy.optimize import linear_sum_assignment

from src.carrying_capacity import evaluate_ecological_limits

PENALTY = 1e6

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two geographic points using Haversine formula.
    
    Args:
        lat1, lon1: First point coordinates (decimal degrees)
        lat2, lon2: Second point coordinates (decimal degrees)
    
    Returns:
        Distance in kilometers
    """
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

def optimize_relocation_assignment(
    crit_habitations: pd.DataFrame, 
    shelters_df: pd.DataFrame
) -> Tuple[List[Dict[str, Any]], Dict[str, pd.Series]]:
    """
    Assign critical habitations to shelters minimizing evacuation distance while 
    respecting carrying capacity constraints (beds, water, road width).
    
    Uses two-phase approach:
    1. Global optimization via Hungarian algorithm with penalty-based constraints
    2. Greedy best-effort assignment for remaining habitations with failure reason reporting
    
    Args:
        crit_habitations: DataFrame of habitations requiring evacuation
                         Must include: name, latitude, longitude, population
        shelters_df: DataFrame of available shelters
                    Must include: shelter_id, name, latitude, longitude, total_capacity,
                                 current_occupancy, freshwater_liters_day, road_width_m
    
    Returns:
        Tuple of:
        - relocation_plan: List[Dict] with keys:
            * "Origin Red Zone": habitation name
            * "Evacuees": population
            * "Assigned Shelter": shelter name
            * "Distance (km)": haversine distance
            * "Status": assignment status (✅ Optimal or ⚠️ OVERFLOW)
        - assignment_lookup: Dict mapping habitation name -> shelter record
    """
    shelters = shelters_df.set_index('shelter_id', drop=False).copy()
    capacity_left = (shelters['total_capacity'] - shelters['current_occupancy']).to_dict()
    water_left = shelters['freshwater_liters_day'].to_dict()
    remaining = crit_habitations.reset_index(drop=True).copy()
    relocation_plan, assignment_lookup = [], {}

    max_rounds = len(remaining) + 1
    for _ in range(max_rounds):
        if len(remaining) == 0:
            break
        shelter_ids = list(capacity_left.keys())
        n_hab, n_shelter = len(remaining), len(shelter_ids)
        cost = np.full((n_hab, n_shelter), PENALTY)
        eco_cache = {}

        for i, hab in remaining.iterrows():
            for j, sid in enumerate(shelter_ids):
                shelter = shelters.loc[sid]
                dist_km = _haversine_km(hab['latitude'], hab['longitude'], shelter['latitude'], shelter['longitude'])
                water_required_liters = float(hab['population']) * 30.0
                eco = evaluate_ecological_limits(shelter, hab['population'])
                dynamic_water_breached = water_left.get(sid, 0.0) < water_required_liters
                eco['water_breached'] = dynamic_water_breached
                eco_cache[(i, sid)] = (dist_km, eco)
                if (
                    capacity_left[sid] >= hab['population']
                    and not dynamic_water_breached
                    and not eco['road_breached']
                ):
                    cost[i, j] = dist_km

        row_idx, col_idx = linear_sum_assignment(cost)
        assigned_any, newly_assigned_rows = False, []
        for r, c in zip(row_idx, col_idx):
            if cost[r, c] >= PENALTY:
                continue
            hab = remaining.iloc[r]
            sid = shelter_ids[c]
            dist_km, eco = eco_cache[(r, sid)]
            water_required_liters = float(hab['population']) * 30.0
            if capacity_left[sid] < hab['population']:
                continue
            if water_left.get(sid, 0.0) < water_required_liters:
                continue
            if eco['road_breached']:
                continue
            capacity_left[sid] -= int(hab['population'])
            water_left[sid] -= water_required_liters
            shelter_record = shelters.loc[sid].copy()
            shelter_record['dist_km'] = round(float(dist_km), 2)
            assignment_lookup[hab['name']] = shelter_record
            relocation_plan.append({
                "Origin Red Zone": hab['name'], "Evacuees": int(hab['population']),
                "Assigned Shelter": shelters.loc[sid, 'name'], "Distance (km)": round(float(dist_km), 2),
                "Status": "✅ Optimal (Globally Minimized Distance)"
            })
            newly_assigned_rows.append(r)
            assigned_any = True

        remaining = remaining.drop(remaining.index[newly_assigned_rows]).reset_index(drop=True)
        if not assigned_any:
            break

    for _, hab in remaining.iterrows():
        best_sid, best_dist, best_eco = None, None, None
        for sid in shelters.index:
            shelter = shelters.loc[sid]
            dist_km = _haversine_km(hab['latitude'], hab['longitude'], shelter['latitude'], shelter['longitude'])
            if best_dist is None or dist_km < best_dist:
                best_sid, best_dist = sid, dist_km
                best_eco = evaluate_ecological_limits(shelter, hab['population'])
                water_required_liters = float(hab['population']) * 30.0
                best_eco['water_breached'] = water_left.get(sid, 0.0) < water_required_liters
        deficit = int(best_eco['headcount_deficit'])
        reasons = []
        if deficit > 0: reasons.append(f"Short {deficit} beds")
        if best_eco['water_breached']:
            reasons.append(f"needs {int(float(hab['population']) * 30.0)}L/day water, supply insufficient")
        if best_eco['road_breached']: reasons.append("access road below 6m — convoy bottleneck")
        reason_text = "; ".join(reasons) if reasons else "capacity constraints"
        shelter_record = shelters.loc[best_sid].copy()
        shelter_record['dist_km'] = round(float(best_dist), 2)
        assignment_lookup[hab['name']] = shelter_record
        relocation_plan.append({
            "Origin Red Zone": hab['name'], "Evacuees": int(hab['population']),
            "Assigned Shelter": shelters.loc[best_sid, 'name'], "Distance (km)": round(float(best_dist), 2),
            "Status": f"⚠️ OVERFLOW: {reason_text}"
        })
    return relocation_plan, assignment_lookup