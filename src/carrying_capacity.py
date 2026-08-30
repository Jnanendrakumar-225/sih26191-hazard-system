import pandas as pd

WATER_LITERS_PER_PERSON_DAY = 30.0   # standard emergency-shelter ration
MIN_ROAD_WIDTH_M = 6.0               # minimum width for evacuation convoys

def evaluate_ecological_limits(shelter: pd.Series, incoming_population: float) -> dict:
    """
    Single-shelter carrying capacity check used by relocation.py when picking
    the nearest safe zone for one habitation. Checks bed headroom, freshwater
    supply, and road-access width against the incoming population.
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

def evaluate_carrying_capacity(shelter_df, incoming_population):
    """
    Evaluates if target shelters can absorb displaced population based on 
    freshwater limits, road width capacity, and available spatial headroom.
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