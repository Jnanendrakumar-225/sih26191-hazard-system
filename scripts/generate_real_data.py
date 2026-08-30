import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import osmnx as ox

def build_kamrup_dataset():
    os.makedirs("data/demo", exist_ok=True)
    print("⚡ Fetching real emergency shelters and facilities from OpenStreetMap...")
    
    place_name = "Guwahati, Assam, India"
    shelters_data = []
    
    try:
        tags = {'amenity': ['school', 'hospital', 'community_centre', 'place_of_worship']}
        gdf_amenities = ox.geometries_from_place(place_name, tags=tags)
        
        for idx, row in gdf_amenities.iterrows():
            if hasattr(row.geometry, 'centroid'):
                lat, lon = row.geometry.centroid.y, row.geometry.centroid.x
            else:
                lat, lon = row.geometry.y, row.geometry.x
                
            name = row.get('name', None)
            if pd.isna(name) or name is None:
                name = f"Public Relief Center {len(shelters_data)+1}"
                
            shelters_data.append({
                "shelter_id": f"S{len(shelters_data)+1:03d}",
                "name": str(name),
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                "total_capacity": 2000,
                "current_occupancy": 350,
                "freshwater_liters_day": 45000,
                "road_width_m": 8.5,
                "safety_score": 95
            })
            if len(shelters_data) >= 12:
                break
        shelters_df = pd.DataFrame(shelters_data)
    except Exception as e:
        print(f"Using fallback Kamrup infrastructure coordinates: {e}")
        shelters_df = pd.DataFrame([
            {"shelter_id": "S001", "name": "Guwahati Medical College Centre", "latitude": 26.1585, "longitude": 91.7712, "total_capacity": 3500, "current_occupancy": 500, "freshwater_liters_day": 70000, "road_width_m": 12.0, "safety_score": 98},
            {"shelter_id": "S002", "name": "Saradakanta Community Hall", "latitude": 26.1821, "longitude": 91.7510, "total_capacity": 1500, "current_occupancy": 300, "freshwater_liters_day": 25000, "road_width_m": 7.5, "safety_score": 92},
            {"shelter_id": "S003", "name": "IIT Guwahati Disaster Relief Camp", "latitude": 26.1912, "longitude": 91.6925, "total_capacity": 5000, "current_occupancy": 600, "freshwater_liters_day": 100000, "road_width_m": 14.0, "safety_score": 99},
            {"shelter_id": "S004", "name": "Kamrup District Sports Complex", "latitude": 26.1380, "longitude": 91.7950, "total_capacity": 2200, "current_occupancy": 400, "freshwater_liters_day": 35000, "road_width_m": 9.0, "safety_score": 94}
        ])

    shelters_df.to_csv("data/demo/shelters.csv", index=False)
    print("✅ Saved shelter infrastructure to data/demo/shelters.csv")

    habitations_data = [
        {"habitation_id": "H201", "name": "Pandu Port Ghat", "latitude": 26.1720, "longitude": 91.7015, "population": 3400, "children_population": 620, "elderly_population": 480, "hazard_score": 94, "accessibility_score": 30, "historical_floods": 7},
        {"habitation_id": "H202", "name": "Uzan Bazar Riverside", "latitude": 26.1932, "longitude": 91.7580, "population": 2800, "children_population": 450, "elderly_population": 390, "hazard_score": 88, "accessibility_score": 45, "historical_floods": 5},
        {"habitation_id": "H203", "name": "North Guwahati Island Ward", "latitude": 26.2085, "longitude": 91.7240, "population": 4100, "children_population": 850, "elderly_population": 620, "hazard_score": 96, "accessibility_score": 20, "historical_floods": 8},
        {"habitation_id": "H204", "name": "Kamakhyapuram Hill Foot", "latitude": 26.1660, "longitude": 91.7080, "population": 1950, "children_population": 310, "elderly_population": 220, "hazard_score": 78, "accessibility_score": 40, "historical_floods": 4},
        {"habitation_id": "H205", "name": "Dispur Capital Sector", "latitude": 26.1430, "longitude": 91.7890, "population": 5200, "children_population": 720, "elderly_population": 610, "hazard_score": 32, "accessibility_score": 90, "historical_floods": 1},
        {"habitation_id": "H206", "name": "Khanapara Foothills", "latitude": 26.1180, "longitude": 91.8210, "population": 1600, "children_population": 240, "elderly_population": 180, "hazard_score": 65, "accessibility_score": 60, "historical_floods": 3},
        {"habitation_id": "H207", "name": "Boragaon Deepor Beel Basin", "latitude": 26.1285, "longitude": 91.6850, "population": 3100, "children_population": 580, "elderly_population": 410, "hazard_score": 91, "accessibility_score": 25, "historical_floods": 6},
        {"habitation_id": "H208", "name": "Noonmati Refinery Colony", "latitude": 26.1890, "longitude": 91.8020, "population": 2900, "children_population": 410, "elderly_population": 360, "hazard_score": 45, "accessibility_score": 75, "historical_floods": 2},
        {"habitation_id": "H209", "name": "Amingaon Industrial Belt", "latitude": 26.1970, "longitude": 91.6780, "population": 2450, "children_population": 380, "elderly_population": 290, "hazard_score": 72, "accessibility_score": 55, "historical_floods": 4},
        {"habitation_id": "H210", "name": "Jalukbari Transit Hub", "latitude": 26.1510, "longitude": 91.6610, "population": 3800, "children_population": 490, "elderly_population": 430, "hazard_score": 58, "accessibility_score": 85, "historical_floods": 2}
    ]

    hab_df = pd.DataFrame(habitations_data)
    hab_df.to_csv("data/demo/habitations.csv", index=False)
    print("✅ Saved Kamrup habitations to data/demo/habitations.csv")

if __name__ == "__main__":
    build_kamrup_dataset()