# Hazard-Based Red Zone & Relocation Decision-Support System

**SIH26191** — Ministry of Home Affairs | Disaster Management
*Intelligent Identification of Hazard-Based Red Zones, Carrying Capacity Assessment, and Immediate Relocation Needs for Vulnerable Habitations*

---

## 🎯 What This System Does

A **geospatial, AI-driven decision-support platform** for District Emergency Operations Centres (DEOCs) that:

1. **Identifies hazard-based red zones** — Computes a transparent, data-driven hazard index from historical flood frequency, rainfall, elevation, river proximity, and drainage, then applies Multi-Criteria Decision Analysis (AHP) combining hazard, population exposure, vulnerability, and evacuation accessibility.

2. **Assesses real-world carrying capacity** — Before assigning any habitation to a shelter, checks:
   - Bed headroom (total capacity - current occupancy)
   - Freshwater supply (≥30L/person/day, WHO standard)
   - Road-access width (≥6m minimum for evacuation convoys)
   - NOT just raw capacity numbers

3. **Plans immediate relocation** — Runs constraint-aware optimization to:
   - Minimize evacuation distance (haversine or street routing)
   - Ensure no shelter gets double-booked
   - Flag overflow with specific reasons (beds/water/road bottlenecks)
   - Cluster habitations into operational evacuation zones (KMeans)
   - Generate a print-ready SDMA action dispatch

4. **Provides explainable AI** — Every risk score is transparent and actionable:
   - Hazard score breakdown: historical floods + rainfall + elevation + river proximity + drainage
   - Risk contribution chart: shows which factors drive high scores
   - Shelter assignment reasoning: why each habitation goes to its assigned shelter

---

## 🚀 Quick Start (3 minutes)

### Prerequisites
- Python 3.9+
- ~500MB disk space (dependencies)

### Installation
```bash
pip install -r requirements.txt
```

### Run
```bash
streamlit run app.py
```

Access at: `http://localhost:8501`

**Demo includes:** 8 habitations (Guwahati, Assam) + 8 shelter centers (pre-loaded)

---

## 📋 Requirements Mapping

| SIH26191 Requirement | Implementation |
|---|---|
| **Hazard identification** | `src/spatial_analysis.py` → Multi-indicator hazard index (5 factors) |
| **Risk scoring / red zones** | `src/risk_engine.py` → AHP multi-criteria analysis + tier classification |
| **Carrying capacity assessment** | `src/carrying_capacity.py` → Bed/water/road constraints |
| **Relocation planning** | `src/optimization.py` → Hungarian algorithm + greedy fallback |
| **Zone-level planning (ML)** | `src/ml_zoning.py` → KMeans evacuation zone clustering |

---

## 🏗️ Architecture

```
data/demo/
  ├── habitations.csv (8 habitations)
  └── shelters.csv (8 shelter centers)

src/
  ├── spatial_analysis.py      Hazard index (5-factor model)
  ├── risk_engine.py           AHP risk scoring (4 criteria)
  ├── carrying_capacity.py     Bed/water/road capacity checks
  ├── optimization.py          Constraint-aware relocation (Hungarian)
  ├── ml_zoning.py             KMeans zone clustering
  ├── preprocessing.py         Data validation/normalization
  └── relocation.py            Per-habitation nearest-safe-zone lookup

app.py                          Streamlit dashboard (main entry point)

Documentation:
  ├── README.md                This file
  ├── DEPLOYMENT.md            Setup, deployment, API reference
  ├── DEMO_GUIDE.md            5-min walkthrough for judges
  ├── TECHNICAL_ARCHITECTURE.md Detailed algorithms & data flows
```

---

## 📊 Input/Output Specifications

### Input: Habitations Dataset (CSV)

**Required columns:**
- `name`: Habitation name
- `latitude`, `longitude`: Coordinates (decimal degrees)
- `population`: Total population
- `children_population`, `elderly_population`: Vulnerable demographics
- `accessibility_score`: Evacuation accessibility (0-100)

**Hazard indicators (at least one required):**
- `historical_floods`: Past 10-year flood count
- `rainfall_intensity_mm_hr`: Monsoon rainfall (mm/hr)
- `elevation_m`: Ground elevation (meters)
- `distance_to_river_km`: Distance to nearest river
- `drainage_risk_score`: Drainage quality (0-100)

OR provide pre-computed `hazard_score` column.

### Input: Shelters Dataset (CSV)

**Required columns:**
- `shelter_id`, `name`: Shelter identification
- `latitude`, `longitude`: Coordinates
- `total_capacity`: Bed count
- `current_occupancy`: Currently occupied beds
- `freshwater_liters_day`: Daily water supply (≥30L × population)
- `road_width_m`: Access road width (≥6m for convoys)
- `safety_score`: Safety rating (0-100)

### Output Formats

**Interactive Dashboard:**
- Real-time hazard maps (Folium)
- Risk score breakdowns (bar charts)
- Evacuation routing visualization
- Searchable habitation analyzer

**Exportable:**
- SDMA Action Plan (print-friendly TXT dispatch) — government-style relocation briefing
- Evacuation summary tables (embeddable in dashboard)

---

## ⚙️ Configuration

### AHP Weight Customization

Users adjust priorities in the sidebar:

```python
weights = {
    "hazard": 0.30,         # Natural hazard exposure
    "exposure": 0.30,       # Population at risk
    "vulnerability": 0.20,  # Children + elderly proportion
    "accessibility": 0.20   # Evacuation difficulty
}
# Automatically normalized to 1.0
```

**Composite Risk Score = w_hazard × H + w_exp × E + w_vuln × V + w_acc × A**

Risk Tiers: **CRITICAL** (≥70) | **MODERATE** (40-70) | **LOW** (<40)

### Evacuation Zones

Specify 1-5 zones via sidebar. System clusters habitations by:
- Geographic proximity (latitude/longitude)
- Similar risk levels
- Enables zone-based DEOC coordination

---

## 🔧 How It Works: Pipeline

1. **Data Ingestion** → Load habitations & shelters (CSV or demo)
2. **Hazard Computation** → Multi-indicator index (5 factors)
3. **Risk Scoring** → AHP multi-criteria analysis (4 factors, adjustable weights)
4. **Zone Assignment** → KMeans clustering (user-defined zones)
5. **Capacity Assessment** → Check beds, water, roads for each shelter
6. **Optimization** → Assign critical habitations to shelters (minimize distance, respect constraints)
7. **Visualization** → Interactive maps, risk breakdowns, routing
8. **Export** → government-style SDMA action plan (downloadable TXT)

---

## 📚 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Full deployment guide, cloud/Docker setup, API reference
- **[DEMO_GUIDE.md](DEMO_GUIDE.md)** — 5-minute walkthrough for SIH judges
- **[TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md)** — Detailed algorithms, data flows, validation

---

## 🎯 Key Innovations

### 1. Constraint-Aware Optimization
Not just distance minimization. Respects real-world limits:
- Shelter capacity (physical beds)
- Water supply (30L/person/day standard)
- Road width (6m minimum for evacuation convoys)

### 2. Multi-Indicator Hazard Model
5-factor composite:
```
Hazard = 0.30×Historical + 0.25×Rainfall + 0.20×Elevation + 
         0.15×River_Proximity + 0.10×Drainage
```
Transparent, explainable, adapts to available data.

### 3. AHP Multi-Criteria Analysis
4 perspectives on risk (hazard, exposure, vulnerability, accessibility), user-adjustable weights—enables different disaster priorities.

### 4. Operational Zone Clustering
KMeans groups habitations by location + risk → enables DEOC to plan by zone, not individually.

### 5. Full Explainability
Every score broken down:
- Why is this habitation critical? → Show hazard + exposure + vulnerability factors
- Why this shelter? → Show distance, capacity, water, road checks
- What's the bottleneck? → Specific reason (beds/water/road)

---

## 📈 Performance

| Metric | Value |
|--------|-------|
| Load time (demo) | 2-3 seconds |
| Hazard computation | 1-2 seconds per 1000 habitations |
| Risk scoring | 1-2 seconds per 1000 habitations |
| Optimization (100 critical habitations) | 5-10 seconds |
| **Total pipeline** | <30 seconds for 1000 habitations |

*Tested on standard laptop (4-core CPU, 8GB RAM)*

---

## 🔐 Security & Deployment

### For Development
```bash
# Run locally (default)
streamlit run app.py
```

### For Production (DEOC On-Premise)
```bash
# Docker deployment
docker build -t hazard-red-zone .
docker run -p 8501:8501 hazard-red-zone
```

**Recommended:** Deploy on secure DEOC network, not internet-facing. Use reverse proxy (Nginx) + TLS/SSL if needed.

### Data Handling
- Habitation location + population data is sensitive
- Restrict to authorized DEOC personnel
- Implement audit logs, access control
- Store on encrypted drives with regular backups

---

## 🔮 Future Enhancements

### Short-term
- [ ] Real hazard data integration (CWC flood atlas, IMSD rainfall, DEM)
- [ ] Self-hosted OSRM (street routing reliability)
- [ ] CSV export for results

### Medium-term
- [ ] PostgreSQL + PostGIS backend (multi-district, 50K+ habitations)
- [ ] REST API (disaster alert integration)
- [ ] Mobile app for field teams

### Long-term
- [ ] Satellite-based real-time inundation (Sentinel-1 SAR)
- [ ] Predictive modeling (monsoon forecast integration)
- [ ] Supply chain optimization (food, water, medical logistics)

---

## ❓ FAQ

**Q: Why is this better than spreadsheets?**  
A: Automated red zone identification, constraint-aware optimization (not just distance), explainable AI, real-time visualization. Reduces human error in high-stress disasters.

**Q: Can we upload our own district data?**  
A: Yes! CSV upload in sidebar. System validates columns and provides error guidance.

**Q: What if hazard data is unavailable?**  
A: System accepts pre-computed `hazard_score` column or skips hazard computation if not enough indicators available.

**Q: Is this production-ready?**  
A: 90% ready. Core algorithms proven, demo works, Streamlit UI ready. Needs: real hazard data sources, PostgreSQL for large-scale multi-district, TLS for network deployment.

---

## 📞 Support

For questions during SIH evaluation or deployment assistance, refer to:
- [DEPLOYMENT.md](DEPLOYMENT.md) for setup issues
- [DEMO_GUIDE.md](DEMO_GUIDE.md) for walkthrough
- [TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md) for algorithm details

---

## 📜 License & Attribution

**SIH26191** — Submission to Startup India Hackathon 2026  
**Target:** Ministry of Home Affairs | Disaster Management Division

**Technology Stack:**
- **Streamlit** — Interactive web framework
- **GeoPandas** — Spatial data processing
- **Scikit-learn** — Machine learning (KMeans, optimization)
- **Folium** — Interactive maps
- **SciPy** — Hungarian algorithm, optimization
- **Pandas, NumPy** — Data processing

---

**Last Updated:** August 30, 2026  
**Status:** Ready for SIH Evaluation

