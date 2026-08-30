# Deployment Guide: Hazard-Based Red Zone & Relocation Decision-Support System

**SIH26191** — Ministry of Home Affairs | Disaster Management Division

---

## 📋 Quick Start (3 minutes)

### Prerequisites
- Python 3.9+
- pip or conda

### Installation

```bash
# Clone or navigate to project directory
cd hazard-red-zone-system

# Create virtual environment (recommended)
python -m venv venv
source venv/Scripts/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run the Application

```bash
streamlit run app.py
```

The application will open at `http://localhost:8501`

---

## 🏗️ System Architecture

### Core Components

| Module | Purpose |
|--------|---------|
| **app.py** | Streamlit web UI - main entry point |
| **src/spatial_analysis.py** | Hazard index computation (multi-indicator model) |
| **src/risk_engine.py** | AHP-based composite risk scoring |
| **src/carrying_capacity.py** | Shelter capacity assessment (beds, water, roads) |
| **src/ml_zoning.py** | KMeans clustering for evacuation zone planning |
| **src/optimization.py** | Constraint-aware relocation optimization |
| **src/preprocessing.py** | Data validation and normalization |

### Data Flow

```
User Input (CSV)
    ↓
Data Validation & Loading
    ↓
Hazard Index Computation
    ↓
AHP Multi-Criteria Risk Scoring
    ↓
Zone-based Clustering (KMeans)
    ↓
Constraint-Aware Relocation Optimization
    ↓
Visualization & SDMA Action Plan Export
```

---

## 📊 Input Data Specifications

### Habitations Dataset (CSV)

**Required Columns:**
- `name`: Habitation name (string)
- `latitude`: Latitude coordinate (decimal degrees)
- `longitude`: Longitude coordinate (decimal degrees)
- `population`: Total population (integer)
- `children_population`: Number of children (integer)
- `elderly_population`: Number of elderly (integer)
- `accessibility_score`: Evacuation accessibility (0-100)

**Hazard Indicators (at least one required):**
- `historical_floods`: Number of flood events in past 10 years (integer)
- `rainfall_intensity_mm_hr`: Average monsoon rainfall (0-400 mm/hr)
- `elevation_m`: Ground elevation above sea level (meters)
- `distance_to_river_km`: Horizontal distance to nearest river (km)
- `drainage_risk_score`: Local drainage quality assessment (0-100)

**Alternative:**
- `hazard_score`: Pre-computed hazard score (0-100) - system will skip computation if this is provided

### Shelters Dataset (CSV)

**Required Columns:**
- `shelter_id`: Unique identifier (string)
- `name`: Shelter name (string)
- `latitude`: Latitude coordinate (decimal degrees)
- `longitude`: Longitude coordinate (decimal degrees)
- `total_capacity`: Total bed capacity (integer)
- `current_occupancy`: Currently occupied beds (integer)
- `freshwater_liters_day`: Daily freshwater supply (liters, ≥30L per person)
- `road_width_m`: Access road width (meters, ≥6m for convoys)
- `safety_score`: Shelter safety rating (0-100)

### Example Data

```csv
name,latitude,longitude,population,children_population,elderly_population,accessibility_score,historical_floods,rainfall_intensity_mm_hr,elevation_m,distance_to_river_km,drainage_risk_score
Habitation A,26.1800,91.7400,1200,220,140,65,8,280,52,1.2,80
```

---

## ⚙️ Configuration & Customization

### AHP Weight Customization

Users can adjust the Multi-Criteria Decision Analysis weights in the sidebar:

- **Hazard Intensity Weight** (0-1): Impact of natural hazard exposure
- **Exposure Weight** (0-1): Population at risk
- **Vulnerability Weight** (0-1): Proportion of vulnerable populations (children, elderly)
- **Accessibility Weight** (0-1): Ease of evacuation from the habitation

**Default Weights:**
- Hazard: 0.30
- Exposure: 0.30
- Vulnerability: 0.20
- Accessibility: 0.20

Weights are automatically normalized to 1.0.

### Evacuation Zones

Users can specify the number of evacuation zones (1-5) via sidebar slider. The system uses KMeans clustering to group habitations by:
- Geographic proximity
- Similar risk levels

This helps District Emergency Operations Centres (DEOCs) organize evacuation efforts by zone.

### Hazard Model Selection

Two modes:

1. **Computed Mode (Recommended):**
   - System automatically computes hazard index from multiple indicators
   - Weights: Historical Floods (30%) + Rainfall (25%) + Elevation (20%) + River Proximity (15%) + Drainage (10%)
   - Transparent, explainable scoring

2. **Direct Mode:**
   - User provides pre-computed `hazard_score` column
   - Useful for custom hazard models or satellite-based hazard layers

---

## 🚀 Production Deployment

### Cloud Deployment (Streamlit Cloud)

```bash
# 1. Push code to GitHub
git add .
git commit -m "Production release"
git push origin main

# 2. Go to https://share.streamlit.io/
# 3. Deploy from GitHub repository
# 4. Link to requirements.txt
```

### Self-Hosted Deployment (Docker)

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**Build and Run:**
```bash
docker build -t hazard-red-zone .
docker run -p 8501:8501 hazard-red-zone
```

### Government Deployment (On-Premise DEOC)

**For State Disaster Management Authorities:**

1. **Network Setup:**
   - Deploy on secure DEOC network (not internet-facing for sensitive data)
   - Use reverse proxy (Nginx/Apache) with TLS/SSL
   - Restrict access to authorized personnel only

2. **Data Management:**
   - Store habitation/shelter data on secure, encrypted drives
   - Implement regular data backups
   - Use CSV import to keep data current with field surveys

3. **API Integration:**
   - System can be extended to accept HTTP POST requests for real-time hazard data
   - Future: Integration with CWC flood alerts, IMSD rainfall forecasts, DEM-based inundation models

4. **Database Backend:**
   - Current: CSV-based (suitable for districts with <10,000 habitations)
   - Future: PostgreSQL + PostGIS for large-scale multi-district deployments

---

## 🔧 Troubleshooting

### Issue: "No hazard_score available for risk analysis"

**Solution:**
- Ensure your CSV contains `historical_floods` column, OR
- Provide a pre-computed `hazard_score` column
- Check data types are numeric

### Issue: "Shelter assignment optimization failed"

**Solution:**
- Verify shelters CSV has valid coordinates and capacity values
- Check `freshwater_liters_day` and `road_width_m` meet minimum standards (30L/person, 6m width)
- Ensure at least one shelter is available

### Issue: "Slow performance with large datasets"

**Solution:**
- Streamlit caches computations; restart app to clear cache if needed
- For >10,000 habitations, consider database backend (PostgreSQL)
- Deploy on higher-spec hardware for production

### Issue: "Street routing (OSRM) failed"

**Solution:**
- System falls back to straight-line (haversine) distance if OSRM unavailable
- For production: deploy self-hosted OSRM instance
- Requires `osrm-backend` Docker container

---

## 📚 API Reference

### Core Functions

#### `compute_flood_hazard_components(df: pd.DataFrame) -> pd.DataFrame`
Computes multi-indicator hazard index from raw indicators.

```python
from src.spatial_analysis import compute_flood_hazard_components
hazard_df = compute_flood_hazard_components(habitations_df)
```

#### `calculate_ahp_risk(df: pd.DataFrame, weights: dict) -> pd.DataFrame`
Applies AHP multi-criteria analysis to produce composite risk scores.

```python
from src.risk_engine import calculate_ahp_risk
weights = {"hazard": 0.30, "exposure": 0.30, "vulnerability": 0.20, "accessibility": 0.20}
scored_df = calculate_ahp_risk(habitations_df, weights)
```

#### `evaluate_carrying_capacity(shelters_df: pd.DataFrame, population: int) -> list`
Checks shelter capacity constraints.

```python
from src.carrying_capacity import evaluate_carrying_capacity
results = evaluate_carrying_capacity(shelters_df, incoming_population=5000)
```

#### `optimize_relocation_assignment(habitations: pd.DataFrame, shelters: pd.DataFrame) -> tuple`
Computes optimal shelter assignments minimizing distance while respecting constraints.

```python
from src.optimization import optimize_relocation_assignment
relocation_plan, assignments = optimize_relocation_assignment(critical_habitations, shelters_df)
```

---

## 📊 Output Formats

### Interactive Dashboard
- Real-time hazard maps (Folium)
- Risk score breakdowns (bar charts)
- Evacuation routing visualization
- Searchable habitation analyzer

### Exportable Outputs

**SDMA Action Plan (TXT):**
```
GOVERNMENT OF ASSAM
STATE DISASTER MANAGEMENT AUTHORITY (SDMA)

URGENT EVACUATION & RELOCATION DISPATCH PLAN
[Generated through Intelligent Hazard Red Zone System]

RISK ASSESSMENT METHODOLOGY
...

ASSIGNED EVACUATION DIRECTIVES
[Tabular relocation assignments]
...
```

**Tabular Data:**
- Relocation assignments table (Origin → Shelter, Distance, Status)
- Hazard assessment results (CSV export)
- Zone-level summaries

---

## 🔐 Security Considerations

### Data Sensitivity
- Habitation data (population, location) is sensitive
- Restrict access to authorized DEOC personnel only
- Do not expose system to internet without authentication

### Recommendations
- Use VPN for remote access
- Implement role-based access control (RBAC)
- Audit logs for data access
- Encrypt data at rest and in transit
- Regular security audits and penetration testing

---

## 📞 Support & Maintenance

### For SIH Evaluation Team

**Key Demonstration Points:**
1. Upload sample district data (provided in `data/demo/`)
2. Adjust AHP weights to show customizability
3. Select a critical habitation → view risk breakdown + assigned shelter
4. Map view shows hazard zones and evacuation routes
5. Download SDMA action plan

**Performance Metrics:**
- Load time: <5 seconds for 1000 habitations
- Computation time: <30 seconds for multi-criteria analysis
- Optimization: <20 seconds for 100 critical habitations

### Contact
For technical support during SIH evaluation, contact the development team.

---

## 📜 License & Attribution

**SIH26191** — Submission to Startup India Hackathon 2026

**Technologies Used:**
- Streamlit: Interactive web framework
- GeoPandas: Spatial data processing
- Scikit-learn: Machine learning (KMeans, normalization)
- Folium: Interactive maps
- SciPy: Optimization algorithms

---

**Last Updated:** August 30, 2026
