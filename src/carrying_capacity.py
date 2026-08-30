import pandas as pd

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