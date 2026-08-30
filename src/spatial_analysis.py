import pandas as pd


FLOOD_HAZARD_WEIGHTS = {
    "historical_floods": 0.30,
    "rainfall_intensity_mm_hr": 0.25,
    "elevation_m": 0.20,
    "distance_to_river_km": 0.15,
    "drainage_risk_score": 0.10,
}


def _normalize(
    series: pd.Series,
    inverse: bool = False,
) -> pd.Series:
    """
    Min-max normalize a numeric indicator to 0-100.

    If inverse=True:
    lower raw values become higher risk values.
    """

    values = pd.to_numeric(
        series,
        errors="coerce",
    )

    minimum = values.min()
    maximum = values.max()

    if (
        pd.isna(minimum)
        or pd.isna(maximum)
    ):
        return pd.Series(
            0.0,
            index=series.index,
        )

    if maximum == minimum:

        return pd.Series(
            0.0,
            index=series.index,
        )

    normalized = (
        (values - minimum)
        /
        (maximum - minimum)
        * 100.0
    )

    if inverse:

        normalized = (
            100.0 - normalized
        )

    return normalized.fillna(0.0)


def compute_flood_hazard_components(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute a transparent multi-indicator
    flood hazard model.

    Full indicator set:

    1. Historical flood frequency
    2. Rainfall intensity
    3. Elevation
    4. Distance to river
    5. Drainage risk

    Missing optional indicators are automatically
    reweighted.

    historical_floods is required for computed mode.
    """

    if "historical_floods" not in df.columns:

        raise ValueError(
            "Computed flood hazard requires "
            "'historical_floods'."
        )

    components = pd.DataFrame(
        index=df.index
    )

    active_weights = {}


    for column, weight in (
        FLOOD_HAZARD_WEIGHTS.items()
    ):

        if column in df.columns:

            inverse = column in {
                "elevation_m",
                "distance_to_river_km",
            }

            components[column] = _normalize(
                df[column],
                inverse=inverse,
            )

            active_weights[column] = weight


    if not active_weights:

        raise ValueError(
            "No usable flood-hazard indicators "
            "were found."
        )


    weight_total = sum(
        active_weights.values()
    )


    normalized_weights = {

        column:
        weight / weight_total

        for column, weight
        in active_weights.items()

    }


    for column, weight in (
        normalized_weights.items()
    ):

        components[
            f"{column}_contribution"
        ] = (
            components[column]
            * weight
        )


    contribution_columns = [

        f"{column}_contribution"

        for column
        in normalized_weights

    ]


    components["hazard_score"] = (

        components[
            contribution_columns
        ]

        .sum(axis=1)

        .round(2)

    )


    components.attrs[
        "active_weights"
    ] = normalized_weights


    return components


def compute_hazard_index(
    df: pd.DataFrame,
) -> pd.Series:
    """
    Return the final 0-100
    multi-indicator flood hazard score.
    """

    return (
        compute_flood_hazard_components(
            df
        )["hazard_score"]
    )