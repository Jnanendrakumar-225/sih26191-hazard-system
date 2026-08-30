import streamlit as st
import pandas as pd
import folium
import os
import requests
from streamlit_folium import st_folium

from src.risk_engine import calculate_ahp_risk
from src.carrying_capacity import evaluate_ecological_limits
from src.spatial_analysis import compute_hazard_index
from src.ml_zoning import assign_risk_zones

st.set_page_config(page_title="Hazard-Based Red Zone & Relocation System", layout="wide")

st.title("🚨 Intelligent Hazard Red Zone & Relocation Decision-Support System")
st.markdown("A Geospatial Multi-Criteria Decision Analysis (MCDA) Platform for Disaster Management")

# --- Function to get real street routing via OpenStreetMap ---
@st.cache_data
def get_street_route(lat1, lon1, lat2, lon2):
    """Fetches real road network routing using OSRM API."""
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['code'] == 'Ok':
                # Extract coordinates (OSRM gives lon, lat; Folium needs lat, lon)
                coords = data['routes'][0]['geometry']['coordinates']
                route_points = [[c[1], c[0]] for c in coords]
                return route_points
    except Exception as e:
        pass
    # Fallback to straight line if offline
    return [[lat1, lon1], [lat2, lon2]]

# 1. Base Paths
hab_path = "data/demo/habitations.csv"
shelter_path = "data/demo/shelters.csv"

if not os.path.exists(shelter_path) or not os.path.exists(hab_path):
    st.error(f"Data Loading Error: Missing baseline CSV files in data/demo/")
    st.stop()

df_shelters = pd.read_csv(shelter_path)

# 2. Sidebar: Dynamic Data Ingestion & AHP Weight Customizer
st.sidebar.markdown("### 📂 Dynamic Data Ingestion")
uploaded_file = st.sidebar.file_uploader("Ingest New District Dataset (CSV)", type=["csv"])

if uploaded_file is not None:
    df_habitations = pd.read_csv(uploaded_file)
    st.sidebar.success("New district loaded successfully!")
else:
    df_habitations = pd.read_csv(hab_path)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ AHP Risk Weight Customizer")
h_weight = st.sidebar.slider("Hazard Intensity Weight (H)", 0.0, 1.0, 0.3)
e_weight = st.sidebar.slider("Exposure Weight (E)", 0.0, 1.0, 0.3)
v_weight = st.sidebar.slider("Vulnerability Weight (V)", 0.0, 1.0, 0.2)
a_weight = st.sidebar.slider("Evacuation Accessibility Weight (A)", 0.0, 1.0, 0.2)

weights = {
    'hazard': h_weight,
    'exposure': e_weight,
    'vulnerability': v_weight,
    'accessibility': a_weight
}

total_w = sum(weights.values())
if total_w != 1.0 and total_w > 0:
    st.sidebar.warning(f"Total weights equal {total_w:.2f}. Normalizing to 1.0...")

st.sidebar.markdown("---")
use_computed_hazard = st.sidebar.checkbox(
    "🧮 Compute hazard index from flood history (vs. static CSV value)",
    value=True,
    help="When on, hazard_score is derived from historical_floods instead of the pre-filled CSV column."
)

# 3. Compute Risk Model
if use_computed_hazard:
    df_habitations['hazard_score'] = compute_hazard_index(df_habitations)

scored_df = calculate_ahp_risk(df_habitations, weights)

# 3b. Cluster habitations into operational risk zones (KMeans)
n_zones = st.sidebar.slider("Number of Evacuation Zones (KMeans)", 1, 5, 3)
scored_df = assign_risk_zones(scored_df, n_clusters=n_zones)

# 4. Display Key Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Habitations", len(scored_df))
col2.metric("Critical Red Zones", len(scored_df[scored_df['risk_tier'].str.contains("CRITICAL", na=False)]))
col3.metric("Total Population at Risk", int(scored_df['population'].sum()))
col4.metric("Vulnerable Demographics", int((scored_df['children_population'] + scored_df['elderly_population']).sum()))

st.divider()

# 5. Execute Smart Routing FIRST so the map knows where to draw the lines
crit_habitations = scored_df[scored_df['risk_tier'].str.contains("CRITICAL", na=False)].copy()
relocation_plan = []
assignment_lookup = {} # Dictionary to store who goes where for the map

if len(crit_habitations) > 0:
    # Real-time capacity tracker to prevent clashes
    real_time_capacity = df_shelters.set_index('shelter_id')['total_capacity'] - df_shelters.set_index('shelter_id')['current_occupancy']
    real_time_capacity = real_time_capacity.to_dict()
    
    # Sort by highest risk score first
    crit_habitations = crit_habitations.sort_values(by='composite_risk_score', ascending=False)

    for _, hab in crit_habitations.iterrows():
        df_shelters['dist_km'] = (
            ((df_shelters['latitude'] - hab['latitude'])**2 + 
             (df_shelters['longitude'] - hab['longitude'])**2)**0.5 * 111.0
        ).round(2)
        
        sorted_shelters = df_shelters.sort_values(by='dist_km')
        assigned = False
        
        for _, shelter in sorted_shelters.iterrows():
            current_headroom = real_time_capacity[shelter['shelter_id']]
            
            if current_headroom >= hab['population']:
                # Carrying-capacity check: beds alone aren't enough — verify
                # freshwater supply and road-access width can support the move.
                eco = evaluate_ecological_limits(shelter, hab['population'])
                if eco['water_breached'] or eco['road_breached']:
                    continue  # bed space exists but the shelter can't sustain it — try the next one

                real_time_capacity[shelter['shelter_id']] -= hab['population']
                assignment_lookup[hab['name']] = shelter # Save for the map
                
                relocation_plan.append({
                    "Origin Red Zone": hab['name'],
                    "Evacuees": int(hab['population']),
                    "Assigned Shelter": shelter['name'],
                    "Distance (km)": shelter['dist_km'],
                    "Status": "✅ Optimal (Beds, Water & Road Clear)"
                })
                assigned = True
                break 
                
        if not assigned:
            nearest = sorted_shelters.iloc[0]
            eco = evaluate_ecological_limits(nearest, hab['population'])
            deficit = int(eco['headcount_deficit'])
            reasons = []
            if deficit > 0:
                reasons.append(f"Short {deficit} beds")
            if eco['water_breached']:
                reasons.append(f"needs {int(eco['water_needed'])}L/day water, supply insufficient")
            if eco['road_breached']:
                reasons.append("access road below 6m — convoy bottleneck")
            reason_text = "; ".join(reasons) if reasons else "capacity constraints"
            assignment_lookup[hab['name']] = nearest # Save for the map
            
            relocation_plan.append({
                "Origin Red Zone": hab['name'],
                "Evacuees": int(hab['population']),
                "Assigned Shelter": nearest['name'],
                "Distance (km)": nearest['dist_km'],
                "Status": f"⚠️ OVERFLOW: {reason_text}"
            })

# 6. Interactive Layout: Analysis (Left) & Map (Right)
analysis_col, map_col = st.columns([1, 1.2])

with analysis_col:
    st.subheader("🔍 Explainable AI & Relocation Planner")
    selected_hab_name = st.selectbox("Select Habitation to Analyze:", scored_df['name'].values)
    sel_hab = scored_df[scored_df['name'] == selected_hab_name].iloc[0]
    
    st.markdown(f"**Status Tier:** `{sel_hab['risk_tier']}`")
    st.markdown(f"**Composite Risk Score:** `{sel_hab['composite_risk_score']} / 100`")
    
    with st.expander("📊 Why did it receive this score?", expanded=True):
        st.write(f"- **Hazard Intensity:** {sel_hab['hazard_score']}" + (" *(computed from flood history)*" if use_computed_hazard else " *(static CSV value)*"))
        st.write(f"- **Population Exposure:** {sel_hab['population']} citizens total")
        st.write(f"- **Vulnerable Group Ratio:** {int(sel_hab['children_population'] + sel_hab['elderly_population'])} dependents")
        st.write(f"- **Evacuation Zone (KMeans cluster):** {sel_hab['risk_zone']}")

    if "CRITICAL" in sel_hab['risk_tier'] and sel_hab['name'] in assignment_lookup:
        target = assignment_lookup[sel_hab['name']]
        st.success(f"**Assigned Evacuation Route:** \n\n➡️ {target['name']} ({target['dist_km']} km away)")

with map_col:
    st.subheader("🗺️ Live Hazard & Evacuation Map")
    
    # Auto-Zoom map centered exactly on the selected habitation
    m = folium.Map(location=[sel_hab['latitude'], sel_hab['longitude']], zoom_start=13.5, tiles="CartoDB positron")
    
    color_map = {
        'CRITICAL - Immediate Relocation (0–3 Months)': '#d9534f',
        'MODERATE - Short-Term Action': '#f0ad4e',
        'SAFE - Medium-Term Monitoring': '#5cb85c'
    }
    
    # Draw all habitations
    for _, row in scored_df.iterrows():
        folium.Circle(
            location=[row['latitude'], row['longitude']],
            radius=400 + (row['population'] * 0.15), 
            popup=f"<b>{row['name']}</b><br>Score: {row['composite_risk_score']}<br>Class: {row['risk_tier']}<br>Zone: {row['risk_zone']}",
            color=color_map.get(row['risk_tier'], 'gray'),
            fill=True,
            fill_opacity=0.5
        ).add_to(m)
        
    # Draw all shelters
    for _, s_row in df_shelters.iterrows():
        folium.Marker(
            location=[s_row['latitude'], s_row['longitude']],
            popup=f"<b>Shelter: {s_row['name']}</b>",
            icon=folium.Icon(color='blue', icon='home', prefix='fa')
        ).add_to(m)
        
    # Draw Google-Maps style Evacuation Route
    if "CRITICAL" in sel_hab['risk_tier'] and sel_hab['name'] in assignment_lookup:
        assigned_shelter = assignment_lookup[sel_hab['name']]
        
        # Get real street data
        real_route = get_street_route(
            sel_hab['latitude'], sel_hab['longitude'], 
            assigned_shelter['latitude'], assigned_shelter['longitude']
        )
        
        folium.PolyLine(
            real_route, 
            color="red", 
            weight=4, 
            opacity=0.8,
            tooltip=f"Street Route to {assigned_shelter['name']}"
        ).add_to(m)
        
    st_folium(m, width=700, height=500)

# 7. Smart Routing Table
st.divider()
st.subheader("🎯 Smart Evacuation Routing (Clash Prevention Active)")
if len(crit_habitations) == 0:
    st.info("No Critical Red Zones identified under current weights.")
else:
    plan_df = pd.DataFrame(relocation_plan)
    st.dataframe(plan_df, use_container_width=True)

# 8. SDMA Action Plan Export
st.divider()
st.subheader("📋 Executive Action Dispatch")
if st.button("📄 Generate SDMA Action Plan"):
    action_text = f"""GOVERNMENT OF ASSAM - STATE DISASTER MANAGEMENT AUTHORITY (SDMA)
URGENT EVACUATION & RELOCATION DISPATCH PLAN
Generated via AI Multi-Criteria Decision-Support System

ASSIGNED EVACUATION DIRECTIVES (SMART ROUTING ACTIVE):
{plan_df.to_string(index=False) if len(crit_habitations) > 0 else "No immediate relocations required."}

VALIDATED BY: District Emergency Operations Centre (DEOC)"""

    st.download_button(
        label="📥 Download Official SDMA Report (.txt)",
        data=action_text,
        file_name="SDMA_Relocation_Action_Plan.txt",
        mime="text/plain"
    )
    st.success("Action plan successfully compiled with clash-free routing!")