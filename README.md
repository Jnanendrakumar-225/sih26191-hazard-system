# Hazard-Based Red Zone & Relocation Decision-Support System

**SIH26191** — Ministry of Home Affairs | Disaster Management
*Intelligent Identification of Hazard-Based Red Zones, Carrying Capacity Assessment, and Immediate Relocation Needs for Vulnerable Habitations*

## What this does

A geospatial decision-support tool for District Emergency Operations Centres (DEOCs) that:

1. **Identifies hazard-based red zones** — computes a data-driven hazard index from historical flood frequency (swappable for satellite/DEM hazard layers), then scores every habitation with a transparent, adjustable Multi-Criteria Decision Analysis (AHP) model combining hazard, population exposure, vulnerability, and evacuation accessibility.
2. **Assesses carrying capacity** — before assigning any habitation to a shelter, checks bed headroom, freshwater supply (30L/person/day), and road-access width (6m minimum for convoys), not just raw capacity numbers.
3. **Plans immediate relocation** — runs clash-free shelter assignment (no shelter gets double-booked across habitations), flags overflow with the specific reason (beds / water / road), clusters habitations into operational evacuation zones via KMeans, and generates a downloadable SDMA action dispatch.

## How the three PS requirements map to the code

| PS Requirement | Module |
|---|---|
| Hazard identification | `src/spatial_analysis.py` -> `compute_hazard_index()` |
| Risk scoring / red zones | `src/risk_engine.py` -> `calculate_ahp_risk()` |
| Carrying capacity assessment | `src/carrying_capacity.py` -> `evaluate_ecological_limits()`, `evaluate_carrying_capacity()` |
| Relocation planning | `app.py` assignment loop + `src/relocation.py` |
| Zone-level planning (ML) | `src/ml_zoning.py` -> `assign_risk_zones()` (KMeans) |

## Architecture

```
data/demo/           Sample habitation & shelter datasets (Guwahati, Assam)
src/
  spatial_analysis.py    Hazard index computation
  risk_engine.py         AHP composite risk scoring
  carrying_capacity.py   Bed / water / road capacity checks
  relocation.py          Per-habitation nearest-safe-zone lookup
  ml_zoning.py           KMeans evacuation-zone clustering
  preprocessing.py       CSV loading/cleaning into GeoDataFrames
app.py               Streamlit dashboard tying everything together
scripts/generate_real_data.py   OSM-based real shelter data fetch (fallback to demo data offline)
```

## Running it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Upload your own district CSV (same schema as `data/demo/habitations.csv`) via the sidebar to run the model on new data, or use the bundled Guwahati/Kamrup demo dataset.

## Known limitations (next steps)

- Hazard index currently derives from historical flood counts; production deployment should pull inundation-frequency data from a real hazard layer (e.g. JRC Global Surface Water, CWC flood atlas, or DEM-based flood modelling).
- Live street routing depends on the public OSRM demo server; a self-hosted OSRM instance or cached road network is needed for production reliability.
- Demo data covers one district (Kamrup/Guwahati) for a flood scenario; the schema generalizes to other hazard types and regions given equivalent input data.
