import os
import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

from src.risk_engine import calculate_ahp_risk
from src.spatial_analysis import compute_hazard_components
from src.ml_zoning import assign_risk_zones
from src.optimization import optimize_relocation_assignment


def validate_numeric_columns(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    """Coerce numeric columns and fail fast on invalid values."""
    bad_columns = []
    for column in columns:
        if column not in frame.columns:
            continue
        converted = pd.to_numeric(frame[column], errors="coerce")
        if converted.isna().any():
            bad_columns.append(column)
        frame[column] = converted

    if bad_columns:
        raise ValueError(
            f"{label} contains non-numeric values in: {', '.join(bad_columns)}. "
            "Please convert them to numeric values before uploading."
        )

st.set_page_config(
    page_title="Hazard-Based Red Zone & Relocation System",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🚨 Intelligent Hazard Red Zone & Relocation Decision-Support System")
st.markdown(
    """
    ### A Geospatial Multi-Criteria Decision Analysis (MCDA) Platform for Disaster Management
    
    **📍 Purpose:** Identify hazard-based red zones, assess shelter carrying capacity, and plan immediate relocation for vulnerable habitations.
    
    **🎯 Solution SIH26191** — Ministry of Home Affairs | Disaster Management Division
    """
)

@st.cache_data
def get_street_route(lat1, lon1, lat2, lon2):
    try:
        url = (
            "https://router.project-osrm.org/route/v1/driving/"
            + str(lon1)
            + ","
            + str(lat1)
            + ";"
            + str(lon2)
            + ","
            + str(lat2)
            + "?overview=full&geometries=geojson"
        )

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()

            if data.get("code") == "Ok" and len(data.get("routes", [])) > 0:
                coordinates = data["routes"][0]["geometry"]["coordinates"]

                route_points = []

                for coordinate in coordinates:
                    route_points.append(
                        [coordinate[1], coordinate[0]]
                    )

                return route_points

    except Exception:
        pass

    return [
        [lat1, lon1],
        [lat2, lon2]
    ]


hab_path = "data/demo/habitations.csv"
shelter_path = "data/demo/shelters.csv"

if not os.path.exists(hab_path):
    st.error("Habitations CSV not found at data/demo/habitations.csv")
    st.stop()

if not os.path.exists(shelter_path):
    st.error("Shelters CSV not found at data/demo/shelters.csv")
    st.stop()

try:
    df_shelters = pd.read_csv(shelter_path)
except Exception as error:
    st.error("Unable to load shelter data: " + str(error))
    st.stop()

st.sidebar.markdown("### 📂 Dynamic Data Ingestion")
st.sidebar.markdown(
    """
    Upload your own district dataset (CSV format) to run the analysis on new data.
    
    **Required columns:** name, latitude, longitude, population, children_population, elderly_population, accessibility_score
    
    **Optional hazard indicators:** historical_floods, rainfall_intensity_mm_hr, elevation_m, distance_to_river_km, drainage_risk_score
    """
)

uploaded_file = st.sidebar.file_uploader(
    "📤 Ingest New District Dataset (CSV)",
    type=["csv"],
    help="Upload a CSV file with habitation data matching the required schema"
)

if uploaded_file is not None:
    try:
        df_habitations = pd.read_csv(uploaded_file)

        required_columns = {
            "name",
            "latitude",
            "longitude",
            "population",
            "children_population",
            "elderly_population",
            "accessibility_score"
        }

        missing_columns = required_columns - set(df_habitations.columns)

        if missing_columns:
            st.sidebar.error(
                f"❌ **Upload Failed:** Missing required columns:\n\n"
                + ", ".join(f"`{col}`" for col in sorted(missing_columns))
                + "\n\nPlease include these columns in your CSV and try again."
            )
            st.stop()

        try:
            validate_numeric_columns(
                df_habitations,
                [
                    "latitude",
                    "longitude",
                    "population",
                    "children_population",
                    "elderly_population",
                    "accessibility_score",
                    "historical_floods",
                    "rainfall_intensity_mm_hr",
                    "elevation_m",
                    "distance_to_river_km",
                    "drainage_risk_score",
                ],
                "Uploaded habitation dataset",
            )
        except ValueError as error:
            st.sidebar.error(f"❌ **Validation Failed:** {str(error)}")
            st.stop()

        hazard_columns = {
            "historical_floods",
            "rainfall_intensity_mm_hr",
            "elevation_m",
            "distance_to_river_km",
            "drainage_risk_score"
        }

        available_hazard_columns = (
            hazard_columns & set(df_habitations.columns)
        )

        if (
            len(available_hazard_columns) == 0
            and "hazard_score" not in df_habitations.columns
        ):
            st.sidebar.error(
                "❌ **No Hazard Data Found:**\n\n"
                "Your dataset must include either:\n"
                "- A `hazard_score` column, OR\n"
                "- At least one hazard indicator: historical_floods, rainfall_intensity_mm_hr, elevation_m, distance_to_river_km, or drainage_risk_score"
            )
            st.stop()

        st.sidebar.success(f"✅ New district loaded: {len(df_habitations)} habitations processed successfully!")

    except pd.errors.ParserError as error:
        st.sidebar.error(
            f"❌ **CSV Parse Error:** {str(error)}\n\n"
            "Please ensure your file is a valid CSV format."
        )
        st.stop()
    except Exception as error:
        st.sidebar.error(
            f"❌ **Error reading uploaded CSV:** {str(error)}"
        )
        st.stop()

else:
    try:
        df_habitations = pd.read_csv(hab_path)
    except Exception as error:
        st.error(
            "Unable to load habitation data: " + str(error)
        )
        st.stop()

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Multi-Criteria Risk Weighting (AHP)")
st.sidebar.markdown(
    """
    Adjust the weights to reflect your disaster management priorities.
    Higher weights = greater influence on the final risk score.
    
    **Weights are automatically normalized to 1.0**
    """
)

h_weight = st.sidebar.slider(
    "Hazard Intensity Weight",
    0.0,
    1.0,
    0.30
)

e_weight = st.sidebar.slider(
    "Exposure Weight",
    0.0,
    1.0,
    0.30
)

v_weight = st.sidebar.slider(
    "Vulnerability Weight",
    0.0,
    1.0,
    0.20
)

a_weight = st.sidebar.slider(
    "Accessibility Weight",
    0.0,
    1.0,
    0.20
)

weights = {
    "hazard": h_weight,
    "exposure": e_weight,
    "vulnerability": v_weight,
    "accessibility": a_weight
}

total_weight = sum(weights.values())

if total_weight <= 0:
    st.sidebar.error(
        "At least one AHP weight must be greater than zero."
    )
    st.stop()

if abs(total_weight - 1.0) > 0.001:
    st.sidebar.warning(
        "Total weights = "
        + str(round(total_weight, 2))
        + ". They will be normalized automatically."
    )

st.sidebar.markdown("---")

hazard_model = st.sidebar.selectbox(
    "Hazard Model",
    ["Flood", "Cyclone"],
    index=0,
    help="Choose the disaster profile used to compute the hazard score. Cyclone mode uses rainfall, drainage, flood history, and elevation context."
)

use_computed_hazard = st.sidebar.checkbox(
    "🧮 Compute Multi-Indicator Hazard Index",
    value=True,
    help="Uses the selected hazard model to compute a composite risk score from the available geospatial indicators"
)

hazard_components = None

if use_computed_hazard:
    try:
        with st.sidebar.status("Computing hazard index...", expanded=False):
            hazard_components = compute_hazard_components(
                df_habitations,
                hazard_type=hazard_model.lower(),
            )

            df_habitations["hazard_score"] = (
                hazard_components["hazard_score"]
            )

        st.sidebar.success(
            f"✅ {hazard_model} model active | Hazard score now uses the selected indicators and weights for scenario planning."
        )

    except ValueError as error:
        if "hazard_score" in df_habitations.columns:
            st.sidebar.warning(
                f"⚠️ Could not compute {hazard_model.lower()} hazard index: {str(error)}\n\nUsing existing hazard_score column instead."
            )
            use_computed_hazard = False
        else:
            st.sidebar.error(
                f"❌ **Hazard Calculation Failed:** {str(error)}\n\n"
                "Please ensure your data includes the required indicators for the selected hazard model, or provide a 'hazard_score' column."
            )
            st.stop()
    except Exception as error:
        st.sidebar.error(f"❌ Unexpected error: {str(error)}")
        st.stop()

if "hazard_score" not in df_habitations.columns:
    st.error(
        "❌ **Critical Error:** No hazard_score available for risk analysis.\n\n"
        "Please either:\n"
        "1. Enable 'Compute Multi-Indicator Flood Hazard Index' with proper data, OR\n"
        "2. Upload a CSV with a 'hazard_score' column"
    )
    st.stop()

try:
    with st.status("Computing AHP risk scores...", expanded=False):
        scored_df = calculate_ahp_risk(
            df_habitations,
            weights
        )
except ValueError as error:
    st.error(
        f"❌ **Risk Calculation Failed:** {str(error)}\n\n"
        "Please verify your input data contains all required columns."
    )
    st.stop()
except Exception as error:
    st.error(
        f"❌ **Unexpected Error During Risk Calculation:** {str(error)}"
    )
    st.stop()

n_zones = st.sidebar.slider(
    "Number of Evacuation Zones",
    1,
    5,
    3
)

try:
    scored_df = assign_risk_zones(
        scored_df,
        n_clusters=n_zones
    )
except Exception as error:
    st.error(
        "Risk zoning failed: " + str(error)
    )
    st.stop()

total_habitations = len(scored_df)

critical_count = len(
    scored_df[
        scored_df["risk_tier"]
        .astype(str)
        .str.contains("CRITICAL", na=False)
    ]
)

total_population = int(
    pd.to_numeric(
        scored_df["population"],
        errors="coerce"
    )
    .fillna(0)
    .sum()
)

vulnerable_total = int(
    (
        pd.to_numeric(
            scored_df["children_population"],
            errors="coerce"
        ).fillna(0)
        +
        pd.to_numeric(
            scored_df["elderly_population"],
            errors="coerce"
        ).fillna(0)
    ).sum()
)

metric1, metric2, metric3, metric4 = st.columns(4)

metric1.metric(
    "Total Habitations",
    total_habitations
)

metric2.metric(
    "Critical Red Zones",
    critical_count
)

metric3.metric(
    "Total Population at Risk",
    total_population
)

metric4.metric(
    "Vulnerable Demographics",
    vulnerable_total
)

st.divider()

crit_habitations = (
    scored_df[
        scored_df["risk_tier"]
        .astype(str)
        .str.contains("CRITICAL", na=False)
    ]
    .copy()
)

relocation_plan = []
assignment_lookup = {}

if len(crit_habitations) > 0:
    try:
        result = optimize_relocation_assignment(
            crit_habitations,
            df_shelters
        )

        if isinstance(result, tuple):
            relocation_plan = result[0]
            assignment_lookup = result[1]
        else:
            relocation_plan = result

    except Exception as error:
        st.warning(
            "Relocation optimization failed: " + str(error)
        )

analysis_col, map_col = st.columns([1, 1.2])

with analysis_col:
    st.subheader("🔍 Explainable AI & Relocation Planner")

    selected_hab_name = st.selectbox(
        "Select Habitation to Analyze:",
        scored_df["name"].tolist()
    )

    sel_hab = (
        scored_df[
            scored_df["name"] == selected_hab_name
        ]
        .iloc[0]
    )

    st.markdown(
        "**Status Tier:** `" + str(sel_hab["risk_tier"]) + "`"
    )

    st.markdown(
        "**Composite Risk Score:** `"
        + str(sel_hab["composite_risk_score"])
        + " / 100`"
    )

    with st.expander(
        "📊 Why did it receive this score?",
        expanded=True
    ):
        hazard_score = float(
            sel_hab["hazard_score"]
        )

        population = int(
            sel_hab["population"]
        )

        vulnerable_population = int(
            sel_hab["children_population"]
            +
            sel_hab["elderly_population"]
        )

        st.write(
            "- **Hazard Intensity:** "
            + str(round(hazard_score, 2))
        )

        st.write(
            "- **Population Exposure:** "
            + str(population)
            + " citizens"
        )

        st.write(
            "- **Vulnerable Population:** "
            + str(vulnerable_population)
        )

        st.write(
            "- **Evacuation Zone:** "
            + str(sel_hab["risk_zone"])
        )

        if (
            use_computed_hazard
            and hazard_components is not None
        ):
            selected_index = sel_hab.name

            contribution_columns = []

            for column in hazard_components.columns:
                if column.endswith("_contribution"):
                    contribution_columns.append(column)

            if len(contribution_columns) > 0:
                contribution_values = hazard_components.loc[
                    selected_index,
                    contribution_columns
                ]

                readable_names = []

                name_map = {
                    "historical_floods": "Historical Floods",
                    "rainfall_intensity_mm_hr": "Rainfall Intensity",
                    "elevation_m": "Low Elevation Risk",
                    "distance_to_river_km": "River Proximity",
                    "drainage_risk_score": "Drainage Risk"
                }

                for column in contribution_columns:
                    name = column.replace(
                        "_contribution",
                        ""
                    )

                    readable_names.append(
                        name_map.get(
                            name,
                            name.replace(
                                "_",
                                " "
                            ).title()
                        )
                    )

                contribution_chart = pd.DataFrame(
                    {
                        "Factor": readable_names,
                        "Contribution": contribution_values.values
                    }
                )

                st.markdown(
                    "#### 🌊 Hazard Score Contributions"
                )

                st.bar_chart(
                    contribution_chart.set_index(
                        "Factor"
                    )
                )

        contribution_columns_needed = [
            "hazard_contribution",
            "exposure_contribution",
            "vulnerability_contribution",
            "accessibility_contribution"
        ]

        if all(
            column in scored_df.columns
            for column in contribution_columns_needed
        ):
            risk_chart = pd.DataFrame(
                {
                    "Factor": [
                        "Hazard",
                        "Population Exposure",
                        "Vulnerability",
                        "Poor Accessibility"
                    ],
                    "Contribution": [
                        float(
                            sel_hab[
                                "hazard_contribution"
                            ]
                        ),
                        float(
                            sel_hab[
                                "exposure_contribution"
                            ]
                        ),
                        float(
                            sel_hab[
                                "vulnerability_contribution"
                            ]
                        ),
                        float(
                            sel_hab[
                                "accessibility_contribution"
                            ]
                        )
                    ]
                }
            )

            st.markdown(
                "#### 🧠 Composite Risk Contributions"
            )

            st.bar_chart(
                risk_chart.set_index("Factor")
            )

    if (
        "CRITICAL" in str(sel_hab["risk_tier"])
        and selected_hab_name in assignment_lookup
    ):
        target = assignment_lookup[
            selected_hab_name
        ]

        target_name = target.get(
            "name",
            "Assigned Shelter"
        )

        target_distance = target.get(
            "dist_km",
            "N/A"
        )

        st.success(
            "**Assigned Evacuation Route:**\n\n➡️ "
            + str(target_name)
            + " ("
            + str(target_distance)
            + " km away)"
        )

with map_col:
    st.subheader("🗺️ Live Hazard & Evacuation Map")

    m = folium.Map(
        location=[
            float(sel_hab["latitude"]),
            float(sel_hab["longitude"])
        ],
        zoom_start=13,
        tiles="CartoDB positron"
    )

    for _, row in scored_df.iterrows():
        tier = str(row["risk_tier"])

        if "CRITICAL" in tier:
            color = "red"
        elif "MODERATE" in tier:
            color = "orange"
        else:
            color = "green"

        population_value = pd.to_numeric(
            row["population"],
            errors="coerce"
        )

        if pd.isna(population_value):
            population_value = 0

        radius = 400 + (
            float(population_value) * 0.15
        )

        folium.Circle(
            location=[
                float(row["latitude"]),
                float(row["longitude"])
            ],
            radius=radius,
            popup=(
                "<b>"
                + str(row["name"])
                + "</b>"
                + "<br>Risk Score: "
                + str(row["composite_risk_score"])
                + "<br>Hazard Score: "
                + str(row["hazard_score"])
                + "<br>Status: "
                + str(row["risk_tier"])
                + "<br>Zone: "
                + str(row["risk_zone"])
            ),
            color=color,
            fill=True,
            fill_opacity=0.5
        ).add_to(m)

    for _, shelter_row in df_shelters.iterrows():
        folium.Marker(
            location=[
                float(shelter_row["latitude"]),
                float(shelter_row["longitude"])
            ],
            popup=(
                "<b>Shelter: "
                + str(shelter_row["name"])
                + "</b>"
            ),
            icon=folium.Icon(
                color="blue",
                icon="home",
                prefix="fa"
            )
        ).add_to(m)

    if (
        "CRITICAL" in str(sel_hab["risk_tier"])
        and selected_hab_name in assignment_lookup
    ):
        assigned_shelter = assignment_lookup[
            selected_hab_name
        ]

        shelter_latitude = assigned_shelter.get(
            "latitude"
        )

        shelter_longitude = assigned_shelter.get(
            "longitude"
        )

        if (
            shelter_latitude is not None
            and shelter_longitude is not None
        ):
            real_route = get_street_route(
                float(sel_hab["latitude"]),
                float(sel_hab["longitude"]),
                float(shelter_latitude),
                float(shelter_longitude)
            )

            folium.PolyLine(
                real_route,
                color="red",
                weight=4,
                opacity=0.8,
                tooltip="Evacuation Route"
            ).add_to(m)

    st_folium(
        m,
        width=700,
        height=500
    )

st.divider()

st.subheader("🎯 Smart Evacuation Routing")

if len(crit_habitations) == 0:
    st.info(
        "No Critical Red Zones identified under the current AHP weights."
    )

    plan_df = pd.DataFrame()

else:
    plan_df = pd.DataFrame(
        relocation_plan
    )

    if len(plan_df) > 0:
        st.dataframe(
            plan_df,
            use_container_width=True
        )
    else:
        st.warning(
            "Critical habitations were found, but no optimized relocation plan was generated."
        )

st.divider()

st.subheader("📋 Executive Action Dispatch")

if st.button("📄 Generate SDMA Action Plan"):
    if (
        len(crit_habitations) > 0
        and len(plan_df) > 0
    ):
        relocation_table = plan_df.to_string(
            index=False
        )
    else:
        relocation_table = (
            "No immediate relocations required."
        )

    action_text = (
        "GOVERNMENT OF ASSAM\n"
        "STATE DISASTER MANAGEMENT AUTHORITY (SDMA)\n\n"
        "URGENT EVACUATION & RELOCATION DISPATCH PLAN\n\n"
        "Generated through the Intelligent Hazard Red Zone "
        "and Relocation Decision-Support System.\n\n"
        "====================================================\n"
        "RISK ASSESSMENT METHODOLOGY\n"
        "====================================================\n\n"
        f"Selected hazard profile: {hazard_model} scenario\n"
        "Composite hazard inputs considered:\n"
        "- Historical hazard exposure\n"
        "- Rainfall intensity\n"
        "- Elevation risk\n"
        "- River / drainage context\n"
        "- Operational vulnerability\n\n"
        "Overall relocation priority considers:\n"
        "- Hazard intensity\n"
        "- Population exposure\n"
        "- Population vulnerability\n"
        "- Evacuation accessibility\n\n"
        "====================================================\n"
        "ASSIGNED EVACUATION DIRECTIVES\n"
        "====================================================\n\n"
        + relocation_table
        + "\n\n"
        "====================================================\n"
        "SYSTEM CAPABILITIES\n"
        "====================================================\n\n"
        "Operational zoning: KMeans-based evacuation zones.\n\n"
        "Shelter assignment: Constraint-aware optimization.\n\n"
        "Constraints considered:\n"
        "- Shelter capacity\n"
        "- Water availability\n"
        "- Road accessibility\n\n"
        "====================================================\n"
        "GENERATED FOR DECISION SUPPORT\n"
        "District Emergency Operations Centre (DEOC)\n"
        "====================================================\n"
    )

    st.download_button(
        label="📥 Download Government Dispatch (.txt)",
        data=action_text,
        file_name="SDMA_Relocation_Action_Plan.txt",
        mime="text/plain"
    )

    st.success("Action plan successfully generated!")