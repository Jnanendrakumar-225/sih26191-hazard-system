import pandas as pd
from typing import Dict, List

WATER_LITERS_PER_PERSON_DAY = 30.0   # WHO emergency shelter standard
MIN_ROAD_WIDTH_M = 6.0               # Minimum for evacuation convoys


def evaluate_ecological_limits(
    shelter: pd.Series, 
    incoming_population: float
) -> Dict[str, float | bool]:
    """
    Single-shelter carrying capacity check for relocation optimization.
    
    Evaluates three constraints for one shelter receiving one habitation:
    1. Bed headroom (physical capacity)
    2. Freshwater supply (≥30L/person/day, WHO standard)
    3. Road access width (≥6m minimum for evacuation convoys)
    
    Args:
        shelter: pandas Series with shelter attributes
                Required: total_capacity, current_occupancy, freshwater_liters_day, road_width_m
        incoming_population: Number of evacuees to check
    
    Returns:
        Dict with keys:
            - headcount_deficit: Number of people exceeding bed capacity (0 if OK)
            - water_needed: Liters/day needed for incoming population
            - water_breached: Boolean, True if water supply insufficient
            - road_breached: Boolean, True if road width < 6m
    """
    headroom = shelter['total_capacity'] - shelter['current_occupancy']
    headcount_deficit = max(0.0, incoming_population - headroom)

    water_needed = round(incoming_population * WATER_LITERS_PER_PERSON_DAY, 1)
    water_breached = shelter['freshwater_liters_day'] < water_needed

    road_breached = shelter.get('road_width_m', MIN_ROAD_WIDTH_M) < MIN_ROAD_WIDTH_M

    return {
        'headcount_deficit': headcount_deficit,
        'water_needed': water_needed,
        'water_breached': bool(water_breached),
        'road_breached': bool(road_breached),
    }


def evaluate_carrying_capacity(
    shelter_df: pd.DataFrame, 
    incoming_population: int
) -> List[Dict]:
    """
    Evaluate shelter carrying capacity for a given incoming population.
    
    Checks bed headroom, freshwater supply, and road width constraints.
    
    Args:
        shelter_df: DataFrame of shelters with required columns:
                   total_capacity, current_occupancy, freshwater_liters_day, road_width_m
        incoming_population: Total population to be sheltered
    
    Returns:
        List[Dict] with feasibility assessment per shelter:
            - shelter_id: Unique identifier
            - name: Shelter name
            - headroom_capacity: Available beds
            - water_limit_population: Max population by water supply
            - feasibility_status: Descriptive status message
    """
    results = []
    for _, shelter in shelter_df.iterrows():
        headroom = shelter['total_capacity'] - shelter['current_occupancy']
        max_people_by_water = shelter['freshwater_liters_day'] / 30.0 # 30L/person/day standard
        is_logistics_constrained = shelter['road_width_m'] < 6.0
        
        can_support = (headroom >= incoming_population) and (max_people_by_water >= incoming_population)
        
        status = "Optimal" if can_support else "Capacity Exceeded / Resource Bottleneck"
        if is_logistics_constrained:
            status += " (Restricted Road Access - <6m width)"
            
        results.append({
            'shelter_id': shelter['shelter_id'],
            'name': shelter['name'],
            'headroom_capacity': int(headroom),
            'water_limit_population': int(max_people_by_water),
            'feasibility_status': status
        })
        
    return results