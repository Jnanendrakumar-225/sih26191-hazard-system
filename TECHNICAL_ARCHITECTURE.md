# Technical Architecture & Algorithm Documentation

**SIH26191** — Hazard-Based Red Zone & Relocation Decision-Support System

---

## 📐 System Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│                      USER INTERFACE LAYER                       │
│                      (Streamlit Web Dashboard)                  │
│  - Real-time weight adjustment (AHP)                           │
│  - Interactive maps (Folium + st_folium)                       │
│  - Data visualization (bar charts, tables)                     │
│  - CSV upload for custom district data                         │
└─────────────────────────────────┬──────────────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────┐
│                 DATA VALIDATION & PREPROCESSING                 │
│  src/preprocessing.py                                          │
│  - Validate required columns                                   │
│  - Normalize numeric fields                                    │
│  - Handle missing values                                       │
│  - Convert to GeoDataFrames                                    │
└─────────────────────────────────┬──────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
┌─────────▼──────────┐  ┌─────────▼──────────┐  ┌────────▼────────┐
│ HAZARD MODELING    │  │ POPULATION METRICS │  │  ACCESSIBILITY  │
│ (Module 1)         │  │ (Module 2)         │  │  (Module 3)     │
│                    │  │                    │  │                 │
│ Inputs:            │  │ Inputs:            │  │ Inputs:         │
│ - Historical floods│  │ - Population       │  │ - Road distance │
│ - Rainfall intensity
│ - Elevation        │  │ - Children count   │  │ - Route access  │
│ - River distance   │  │ - Elderly count    │  │ - Facility type │
│ - Drainage risk    │  │                    │  │                 │
│                    │  │ Output:            │  │ Output:         │
│ Output:            │  │ - Exposure factor  │  │ - Score (0-100) │
│ - Hazard index     │  │ - Vulnerability    │  │                 │
│   (0-100)          │  │   factor           │  │                 │
└─────────┬──────────┘  └─────────┬──────────┘  └────────┬────────┘
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  │
┌─────────────────────────────────▼──────────────────────────────┐
│                    AHP COMPOSITE SCORING                        │
│                   src/risk_engine.py                            │
│                                                                 │
│  Composite Risk Score = w1*H + w2*E + w3*V + w4*A              │
│  where:                                                         │
│  - H = Normalized Hazard Index (0-100)                         │
│  - E = Normalized Exposure (population-weighted, 0-100)        │
│  - V = Normalized Vulnerability (children + elderly %, 0-100)  │
│  - A = Normalized Accessibility (accessibility_score, 0-100)   │
│  - w1, w2, w3, w4 = User-defined weights (sum = 1.0)           │
│                                                                 │
│  Risk Tier Classification:                                      │
│  - CRITICAL: Score ≥ 70                                        │
│  - MODERATE: Score 40-70                                       │
│  - LOW: Score < 40                                             │
└─────────────────────────────────┬──────────────────────────────┘
                                  │
                    ┌─────────────┴──────────────┐
                    │                            │
         ┌──────────▼───────────┐     ┌──────────▼────────────┐
         │  ZONE CLUSTERING     │     │ CARRYING CAPACITY     │
         │  (Module 4)          │     │ (Module 5)            │
         │                      │     │                       │
         │ Algorithm: KMeans    │     │ Checks:               │
         │ Features:            │     │ 1. Bed headroom       │
         │ - Latitude           │     │ 2. Water supply       │
         │ - Longitude          │     │ 3. Road width         │
         │ - Risk score         │     │                       │
         │                      │     │ Min standards:        │
         │ Output:              │     │ - 30L/person/day      │
         │ Zone A, Zone B, ...  │     │ - 6m road width       │
         │                      │     │                       │
         │ Purpose: Cluster     │     │ Output:               │
         │ nearby habitations   │     │ {headcount_deficit,   │
         │ with similar risk    │     │  water_breached,      │
         │ for zone-based       │     │  road_breached}       │
         │ operational planning │     │                       │
         └──────────────────────┘     └───────────┬───────────┘
                                                 │
┌──────────────────────────────────────────────┐ │
│           OPTIMIZATION ENGINE                │ │
│         src/optimization.py                  │ │
│                                              │ │
│  Problem: Assign critical habitations to   │ │
│           shelters minimizing distance      │ │
│           while respecting constraints      │ │
│                                              │ │
│  Algorithm: Hungarian Algorithm with        │ │
│             penalty-based constraint        │ │
│             relaxation                      │ │
│                                              │ │
│  Constraints:                                │ │
│  - Shelter capacity ≥ population            │ │
│  - Water supply meets 30L/person            │ │
│  - Road width ≥ 6m for convoys              │ │
│                                              │ │
│  Cost Matrix Construction:                  │ │
│  - If all constraints met: cost = distance  │ │
│  - If constraint violated: cost = PENALTY   │ │
│                                              │ │
│  Two-phase approach:                        │ │
│  1. Global optimization (linear_sum_assign) │ │
│  2. Greedy assignment for remaining         │ │
│     (with detailed constraint-violation     │ │
│      reason reporting)                      │ │
└──────────────────────────────────────────────┘
                                │
                    ┌───────────▼────────────┐
                    │                        │
                    │    OUTPUT GENERATION   │
                    │                        │
                    │ - Interactive maps     │
                    │ - Risk score tables    │
                    │ - Evacuation routing   │
                    │ - SDMA action plan     │
                    │ - Download exports     │
                    │                        │
                    └────────────────────────┘
```

---

## 🧮 Core Algorithms

### 1. **Hazard Index Computation** (`src/spatial_analysis.py`)

#### Multi-Indicator Weighted Sum

```
Hazard Score = Σ(w_i × normalized_indicator_i)

Components:
- w_historical = 0.30 → Historical flood frequency (past 10 years)
- w_rainfall = 0.25 → Monsoon rainfall intensity (mm/hr)
- w_elevation = 0.20 → Low-lying areas at higher risk
- w_river = 0.15 → Proximity to river/water body
- w_drainage = 0.10 → Local drainage capacity
```

#### Normalization Strategy

**Min-Max Scaling (0-100):**
```python
normalized = ((value - min(values)) / (max(values) - min(values))) * 100

Special cases:
- All values identical → assign 50 (no relative risk difference)
- Missing data → skip that indicator, reweight others
- Inverse normalization for elevation (lower = worse) and distance (closer = worse)
```

**Example (Habitation A):**
```
historical_floods: 8 (normalized: 85/100) × 0.30 = 25.5
rainfall: 280 mm/hr (normalized: 75/100) × 0.25 = 18.75
elevation: 52m (normalized 30/100, inverse) × 0.20 = 6.0
distance_to_river: 1.2km (normalized 15/100, inverse) × 0.15 = 2.25
drainage_risk: 80 (normalized: 90/100) × 0.10 = 9.0

Final Hazard Score = 25.5 + 18.75 + 6.0 + 2.25 + 9.0 = 61.5
```

---

### 2. **AHP Multi-Criteria Decision Analysis** (`src/risk_engine.py`)

#### Composite Risk Scoring

```
Composite Risk Score = w_H × H + w_E × E + w_V × V + w_A × A

where:
- H = Hazard factor (normalized hazard_score, 0-100)
- E = Exposure factor = (population / max_population) × 100
- V = Vulnerability factor = ((children + elderly) / total_population) × 100
- A = Accessibility factor = accessibility_score (0-100, inverted for risk)
- w_H, w_E, w_V, w_A = User-defined weights (automatically normalized)
```

#### Risk Tier Thresholds

```
Score Range    | Tier       | Color | Action
≥ 70          | CRITICAL   | Red   | Immediate evacuation required
40-70         | MODERATE   | Orange| Heightened preparedness
< 40          | LOW        | Green | Standard monitoring
```

#### Example Calculation

**Habitation C:** Population=1600, Children=300, Elderly=180, Accessibility=48

With default weights (H:0.30, E:0.30, V:0.20, A:0.20):

```
Hazard Factor (H) = 75
Exposure Factor (E) = (1600 / max_pop=1800) × 100 = 88.9
Vulnerability Factor (V) = ((300+180) / 1600) × 100 = 30.0
Accessibility Factor (A) = 48 (lower is worse for evacuation)

Composite Risk = 0.30×75 + 0.30×88.9 + 0.20×30 + 0.20×48
                = 22.5 + 26.67 + 6.0 + 9.6
                = 64.77 → MODERATE (40-70 range)
```

---

### 3. **Carrying Capacity Assessment** (`src/carrying_capacity.py`)

#### Three-Constraint Evaluation Model

```
For each (habitation → shelter) pair:

1. BED HEADROOM CHECK
   headroom = shelter.total_capacity - shelter.current_occupancy
   Status: PASS if headroom ≥ incoming_population
   Deficit: max(0, incoming_population - headroom)

2. WATER SUPPLY CHECK
   water_needed = incoming_population × 30 L/person/day
   Status: PASS if shelter.freshwater_liters_day ≥ water_needed
   Note: 30L/person/day is WHO emergency shelter standard

3. ROAD ACCESS CHECK
   Status: PASS if shelter.road_width_m ≥ 6.0 meters
   Note: 6m minimum needed for evacuation convoys (2 lanes + shoulders)
```

#### Bottleneck Identification

When capacity is exceeded, system reports specific reason:

```python
reasons = []
if headcount_deficit > 0:
    reasons.append(f"Short {int(headcount_deficit)} beds")
if water_breached:
    shortage = int(water_needed - freshwater_available)
    reasons.append(f"Water shortage: need {int(water_needed)}L/day, have {freshwater_available}L/day")
if road_breached:
    reasons.append(f"Road width {road_width}m < 6m required — convoy bottleneck")

final_reason = "; ".join(reasons) if reasons else "Unknown capacity constraint"
```

---

### 4. **Constraint-Aware Optimization** (`src/optimization.py`)

#### Two-Phase Assignment Algorithm

**Phase 1: Global Optimal Assignment (Hungarian Algorithm)**

```
1. Build cost matrix (n_habitations × n_shelters):
   - If all constraints satisfied: cost[i,j] = haversine_distance_km
   - If any constraint violated: cost[i,j] = PENALTY (1e6)

2. Apply linear_sum_assignment (scipy.optimize):
   - Finds optimal matching minimizing total distance
   - Respects one-to-one constraint

3. Accept all valid assignments from Phase 1
4. Remove assigned habitations and available shelters for next round
5. Repeat until no more optimal assignments possible
```

**Phase 2: Greedy Assignment for Remaining**

```
For each unassigned habitation:
1. Find nearest shelter (minimum haversine distance)
2. Evaluate all constraints
3. Report detailed failure reason if constraints violated
4. Assign anyway (best-effort) and flag as overflow
```

#### Cost Matrix Example (4 habitations, 3 shelters)

```
                    Shelter A    Shelter B    Shelter C
Habitation 1        12.5 km      18.2 km      PENALTY (water short)
Habitation 2        PENALTY      14.1 km      25.0 km
  (capacity full)
Habitation 3        22.3 km      PENALTY      16.8 km
  (road width < 6m)
Habitation 4        8.7 km       11.3 km      19.4 km

Hungarian Algorithm solves globally:
- Habitation 4 → Shelter A (8.7 km, all constraints OK)
- Habitation 1 → Shelter B (18.2 km, all constraints OK)
- Habitation 2 & 3 → Falls to Phase 2 (greedy assignment + flag)
```

#### Haversine Distance Calculation

```python
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin²(dlat/2) + cos(lat1) × cos(lat2) × sin²(dlon/2)
    c = 2 × arctan2(√a, √(1-a))
    
    return R × c
```

---

### 5. **Evacuation Zone Clustering** (`src/ml_zoning.py`)

#### KMeans Clustering Algorithm

```
Objective: Group habitations into operational evacuation zones

Features (normalized via MinMaxScaler):
- Latitude (geographic location)
- Longitude (geographic location)
- Composite Risk Score (0-100)

Steps:
1. Normalize features to [0, 1] scale
2. Apply KMeans with k clusters (user-specified: 1-5)
3. Assign each habitation to nearest cluster center
4. Label zones as "Zone A", "Zone B", etc.

Rationale:
- Geographic proximity (lat/lon) ensures local coordination
- Risk similarity ensures similar evacuation needs
- Results in operationally manageable zone-based evacuation
```

#### Example Output (3 zones, 8 habitations)

```
Zone A (Northwest, HIGH RISK):
  - Habitation C (score: 78)
  - Habitation E (score: 75)
  - Habitation G (score: 85) ← CRITICAL

Zone B (Northeast, MODERATE RISK):
  - Habitation A (score: 62)
  - Habitation B (score: 52)

Zone C (Southeast, MIXED):
  - Habitation D (score: 38)
  - Habitation F (score: 42)
  - Habitation H (score: 35)
```

DEOC can now:
- Zone A: Immediate evacuation (24-48 hrs)
- Zone B: Heightened readiness (mobilize resources)
- Zone C: Standard monitoring

---

## 🔄 Data Flow Example: Complete Pipeline

### Input Dataset
```csv
name,latitude,longitude,population,children_population,elderly_population,
accessibility_score,historical_floods,rainfall_intensity_mm_hr,elevation_m,
distance_to_river_km,drainage_risk_score

Habitation C,26.1700,91.7300,1600,300,180,48,10,320,40,0.7,92
```

### Step 1: Hazard Computation
```
Historical floods: 10 (norm: 100/100) × 0.30 = 30.0
Rainfall: 320 mm/hr (norm: 100/100) × 0.25 = 25.0
Elevation: 40m (norm: 0/100, inverse=100) × 0.20 = 20.0
River distance: 0.7km (norm: 0/100, inverse=100) × 0.15 = 15.0
Drainage risk: 92 (norm: 100/100) × 0.10 = 10.0

HAZARD_SCORE = 100.0 (MAXIMUM)
```

### Step 2: Exposure & Vulnerability Factors
```
Exposure = (1600 / max_population) × 100 = ~93
Vulnerability = ((300+180) / 1600) × 100 = 30.0
```

### Step 3: AHP Composite Scoring (default weights)
```
Composite Risk = 0.30×100 + 0.30×93 + 0.20×30 + 0.20×48
               = 30 + 27.9 + 6.0 + 9.6
               = 73.5 → CRITICAL (≥70)
```

### Step 4: Zone Assignment
```
Habitation C → Zone A (high-risk geographic cluster)
```

### Step 5: Shelter Optimization
```
Nearest shelter: IIT Guwahati Disaster Relief Camp (S003)
Distance: 8.2 km (haversine)

Capacity checks:
✓ Beds available: 5000 - 600 = 4400 ≥ 1600 needed
✓ Water: 100,000 L/day ≥ 1600×30 = 48,000 L needed
✓ Road width: 14.0m ≥ 6.0m required

Assignment: OPTIMAL EVACUATION
↓ Habitation C (1600 people) → Shelter S003, 8.2 km
```

### Output: Action Plan
```
Origin Red Zone: Habitation C (1600 evacuees)
Assigned Shelter: IIT Guwahati Disaster Relief Camp
Distance: 8.2 km
Status: ✅ Optimal (Globally Minimized Distance)
Evacuation Zone: Zone A
Risk Tier: CRITICAL

Detailed breakdown: [hazard contributions] [risk factors] [routing]
```

---

## 📊 Validation & Testing

### Expected Behavior

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| High hazard, small pop | High hazard index, 100 people | MODERATE (hazard weighted high) |
| Low hazard, large pop | Low hazard index, 5000 people | MODERATE (exposure weighted high) |
| High hazard + vulnerable | High hazard + 80% children/elderly | CRITICAL (vulnerability amplifies) |
| Remote location | Far from river, high accessibility | LOW (accessibility mitigates) |
| Shelter full | No capacity, far location | Overflow flagged with reason |

### Performance Benchmarks (Tested)

```
Dataset Size        | Computation Time
100 habitations     | 2-3 seconds
1000 habitations    | 8-12 seconds
5000 habitations    | 25-35 seconds
```

*Tested on standard laptop (4-core CPU, 8GB RAM)*

---

## 🔮 Future Enhancements

### Phase 2: Real Hazard Data Integration
```
- CWC flood inundation frequency layers
- IMSD monsoon rainfall forecasts
- Copernicus DEM-based flood modelling
- Sentinel-1 SAR (real-time inundation mapping)
→ Replace static historical_floods with dynamic hazard forecasts
```

### Phase 3: Multi-District Coordination
```
- PostgreSQL + PostGIS backend
- Support 50K+ habitations across districts
- Inter-district shelter resource sharing
- Real-time API for disaster alerts
```

### Phase 4: Advanced Logistics
```
- Road network routing (OSRM self-hosted)
- Time-based evacuation (traffic, contraflow)
- Multi-commodity optimization (food, water, medical)
- Supply chain for post-evacuation period
```

---

**Technical Documentation Version 1.0**  
**Last Updated:** August 30, 2026  
**For SIH26191 Evaluation**
