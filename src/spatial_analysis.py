import pandas as pd
from typing import Optional


FLOOD_HAZARD_WEIGHTS = {
    "historical_floods": 0.30,
    "rainfall_intensity_mm_hr": 0.25,
    "elevation_m": 0.20,
    "distance_to_river_km": 0.15,
    "drainage_risk_score": 0.10,
}

CYCLONE_HAZARD_WEIGHTS = {
    "rainfall_intensity_mm_hr": 0.35,
    "historical_floods": 0.20,
    "drainage_risk_score": 0.25,
    "elevation_m": 0.10,
    "distance_to_river_km": 0.10,
}


def _normalize(
    series: pd.Series,
    inverse: bool = False,
) -> pd.Series:
    """Min-max normalize a numeric indicator to a 0-100 risk score."""
    values = pd.to_numeric(series, errors="coerce")
    minimum = values.min()
    maximum = values.max()

    if pd.isna(minimum) or pd.isna(maximum):
        return pd.Series(0.0, index=series.index)

    if maximum == minimum:
        return pd.Series(0.0, index=series.index)

    normalized = ((values - minimum) / (maximum - minimum)) * 100.0
    if inverse:
        normalized = 100.0 - normalized
    return normalized.fillna(0.0)


def compute_hazard_components(
    df: pd.DataFrame,
    hazard_type: str = "flood",
) -> pd.DataFrame:
    """Compute a transparent multi-indicator hazard model for flood or cyclone scenarios."""
    hazard_type = (hazard_type or "flood").lower()

    if hazard_type == "flood":
        weights = FLOOD_HAZARD_WEIGHTS
        required_columns = ["historical_floods"]
    elif hazard_type in {"cyclone", "storm"}:
        weights = CYCLONE_HAZARD_WEIGHTS
        required_columns = ["rainfall_intensity_mm_hr"]
    else:
        raise ValueError(f"Unsupported hazard type: {hazard_type}. Use 'flood' or 'cyclone'.")

    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Computed {hazard_type} hazard requires {missing}.")

    components = pd.DataFrame(index=df.index)
    active_weights = {}

    for column, weight in weights.items():
        if column in df.columns:
            inverse = column in {"elevation_m", "distance_to_river_km"}
            components[column] = _normalize(df[column], inverse=inverse)
            active_weights[column] = weight

    if not active_weights:
        raise ValueError(f"No usable {hazard_type} hazard indicators were found.")

    weight_total = sum(active_weights.values())
    normalized_weights = {
        column: weight / weight_total for column, weight in active_weights.items()
    }

    for column in normalized_weights:
        components[f"{column}_contribution"] = components[column] * normalized_weights[column]

    contribution_columns = [f"{column}_contribution" for column in normalized_weights]
    components["hazard_score"] = components[contribution_columns].sum(axis=1).round(2)
    components.attrs["active_weights"] = normalized_weights
    return components


def compute_flood_hazard_components(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Backward-compatible flood hazard model wrapper."""
    return compute_hazard_components(df, hazard_type="flood")


def compute_hazard_index(
    df: pd.DataFrame,
    hazard_type: str = "flood",
) -> pd.Series:
    """Return the final 0-100 multi-indicator hazard score."""
    return compute_hazard_components(df, hazard_type=hazard_type)["hazard_score"]