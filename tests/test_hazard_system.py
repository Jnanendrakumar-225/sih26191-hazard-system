import pandas as pd
import pytest

from src.carrying_capacity import evaluate_ecological_limits
from src.ml_zoning import assign_risk_zones
from src.optimization import optimize_relocation_assignment
from src.risk_engine import calculate_ahp_risk
from src.spatial_analysis import compute_hazard_components


@pytest.fixture
def base_habitation_df():
    return pd.DataFrame(
        {
            "name": ["A", "B", "C"],
            "latitude": [26.15, 26.18, 26.20],
            "longitude": [91.77, 91.75, 91.80],
            "population": [1200, 800, 1400],
            "children_population": [120, 80, 150],
            "elderly_population": [50, 45, 60],
            "accessibility_score": [70, 55, 62],
            "historical_floods": [2, 5, 3],
            "rainfall_intensity_mm_hr": [80, 90, 70],
            "elevation_m": [25, 18, 30],
            "distance_to_river_km": [3.5, 1.2, 2.8],
            "drainage_risk_score": [60, 82, 70],
        }
    )


def test_division_by_zero_population():
    df = pd.DataFrame(
        {
            "hazard_score": [50.0, 35.0],
            "population": [0, 500],
            "children_population": [0, 100],
            "elderly_population": [0, 50],
            "accessibility_score": [60, 70],
        }
    )
    result = calculate_ahp_risk(
        df,
        {"hazard": 0.30, "exposure": 0.30, "vulnerability": 0.20, "accessibility": 0.20},
    )
    assert not result["composite_risk_score"].isna().any()
    assert result["risk_tier"].isin(["CRITICAL - Immediate Relocation (0–3 Months)", "MODERATE - Short-Term Action", "SAFE - Medium-Term Monitoring"]).all()


def test_missing_required_columns_raises_value_error():
    df = pd.DataFrame({"population": [100], "hazard_score": [40]})
    with pytest.raises(ValueError):
        calculate_ahp_risk(df, {"hazard": 1.0, "exposure": 0.0, "vulnerability": 0.0, "accessibility": 0.0})


def test_all_same_hazard_values():
    df = pd.DataFrame(
        {
            "historical_floods": [5, 5, 5],
            "rainfall_intensity_mm_hr": [40, 40, 40],
            "elevation_m": [20, 20, 20],
            "distance_to_river_km": [5, 5, 5],
            "drainage_risk_score": [70, 70, 70],
        }
    )
    result = compute_hazard_components(df, hazard_type="flood")
    assert "hazard_score" in result.columns
    assert result["hazard_score"].notna().all()
    assert (result["hazard_score"] == 0).all()


def test_capacity_exceeded():
    shelter = pd.Series({
        "total_capacity": 150,
        "current_occupancy": 100,
        "freshwater_liters_day": 50000,
        "road_width_m": 10,
    })
    result = evaluate_ecological_limits(shelter, 120)
    assert result["headcount_deficit"] == 70


def test_water_constraint_breached():
    shelter = pd.Series({
        "total_capacity": 500,
        "current_occupancy": 100,
        "freshwater_liters_day": 4000,
        "road_width_m": 10,
    })
    result = evaluate_ecological_limits(shelter, 200)
    assert result["water_breached"] is True


def test_road_constraint_breached():
    shelter = pd.Series({
        "total_capacity": 500,
        "current_occupancy": 100,
        "freshwater_liters_day": 200000,
        "road_width_m": 5,
    })
    result = evaluate_ecological_limits(shelter, 50)
    assert result["road_breached"] is True


def test_risk_zone_assignment(base_habitation_df):
    scored = calculate_ahp_risk(
        base_habitation_df.assign(hazard_score=[50, 60, 70]),
        {"hazard": 0.30, "exposure": 0.30, "vulnerability": 0.20, "accessibility": 0.20},
    )
    result = assign_risk_zones(scored, n_clusters=2)
    assert "risk_zone" in result.columns
    assert set(result["risk_zone"]).issubset({"Zone A", "Zone B"})


def test_optimizer_tracks_cumulative_water_limit():
    shelters_df = pd.DataFrame(
        [{
            "shelter_id": "S001",
            "name": "Test Shelter",
            "latitude": 26.17,
            "longitude": 91.78,
            "total_capacity": 5000,
            "current_occupancy": 1000,
            "freshwater_liters_day": 100000,
            "road_width_m": 12.0,
            "safety_score": 95,
        }]
    )
    crit_habitations = pd.DataFrame(
        {
            "name": ["A", "B"],
            "latitude": [26.15, 26.16],
            "longitude": [91.77, 91.79],
            "population": [2000, 2000],
        }
    )

    plan, _ = optimize_relocation_assignment(crit_habitations, shelters_df)
    optimal_assignments = [item for item in plan if "✅ Optimal" in item["Status"]]
    overflow_assignments = [item for item in plan if "⚠️ OVERFLOW" in item["Status"]]

    assert len(optimal_assignments) == 1
    assert len(overflow_assignments) == 1
