import numpy as np
import pandas as pd


def _normalize_to_100(series: pd.Series) -> pd.Series:
    """
    Safely normalize numeric values to a 0-100 scale.

    If all values are identical, returns 50 because there is
    no relative difference between habitations.
    """
    values = pd.to_numeric(series, errors="coerce").fillna(0)

    minimum = values.min()
    maximum = values.max()

    if maximum == minimum:
        return pd.Series(50.0, index=values.index)

    return ((values - minimum) / (maximum - minimum)) * 100.0


def calculate_ahp_risk(df, weights):
    """
    Computes overall habitation risk using four MCDA/AHP criteria:

    1. Hazard intensity
    2. Population exposure
    3. Population vulnerability
    4. Evacuation accessibility

    The supplied weights are automatically normalized to 1.0.

    Returns the original dataframe with:
        - hazard_factor
        - exposure_factor
        - vulnerability_factor
        - accessibility_factor
        - weighted contribution columns
        - composite_risk_score
        - risk_tier
    """

    df = df.copy()

    # ---------------------------------------------------------
    # VALIDATE REQUIRED COLUMNS
    # ---------------------------------------------------------
    required_columns = {
        "hazard_score",
        "population",
        "children_population",
        "elderly_population",
        "accessibility_score",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns for risk calculation: "
            f"{sorted(missing)}"
        )

    # ---------------------------------------------------------
    # NORMALIZE WEIGHTS
    # ---------------------------------------------------------
    total_weight = sum(weights.values())

    if total_weight <= 0:
        normalized_weights = {
            "hazard": 0.30,
            "exposure": 0.30,
            "vulnerability": 0.20,
            "accessibility": 0.20,
        }
    else:
        normalized_weights = {
            key: value / total_weight
            for key, value in weights.items()
        }

    # Ensure all required criteria exist
    for criterion in [
        "hazard",
        "exposure",
        "vulnerability",
        "accessibility",
    ]:
        if criterion not in normalized_weights:
            normalized_weights[criterion] = 0.0

    # ---------------------------------------------------------
    # 1. HAZARD FACTOR
    # hazard_score is already on a 0-100 scale
    # ---------------------------------------------------------
    hazard_factor = (
        pd.to_numeric(
            df["hazard_score"],
            errors="coerce"
        )
        .fillna(0)
        .clip(0, 100)
    )

    # ---------------------------------------------------------
    # 2. POPULATION EXPOSURE
    # Higher population = higher exposure
    # ---------------------------------------------------------
    exposure_factor = _normalize_to_100(
        df["population"]
    )

    # ---------------------------------------------------------
    # 3. VULNERABILITY FACTOR
    #
    # Vulnerable population =
    # children + elderly
    #
    # replace(0, 1) prevents division-by-zero.
    # ---------------------------------------------------------
    vulnerability_ratio = (
        pd.to_numeric(
            df["children_population"],
            errors="coerce"
        ).fillna(0)
        +
        pd.to_numeric(
            df["elderly_population"],
            errors="coerce"
        ).fillna(0)
    ) / (
        pd.to_numeric(
            df["population"],
            errors="coerce"
        )
        .fillna(0)
        .replace(0, 1)
    )

    vulnerability_factor = (
        _normalize_to_100(vulnerability_ratio)
    )

    # ---------------------------------------------------------
    # 4. ACCESSIBILITY FACTOR
    #
    # Lower accessibility = higher risk
    # ---------------------------------------------------------
    accessibility_normalized = (
        _normalize_to_100(
            df["accessibility_score"]
        )
    )

    accessibility_factor = (
        100.0 - accessibility_normalized
    )

    # ---------------------------------------------------------
    # STORE NORMALIZED FACTORS
    # ---------------------------------------------------------
    df["hazard_factor"] = (
        hazard_factor.round(2)
    )

    df["exposure_factor"] = (
        exposure_factor.round(2)
    )

    df["vulnerability_factor"] = (
        vulnerability_factor.round(2)
    )

    df["accessibility_factor"] = (
        accessibility_factor.round(2)
    )

    # ---------------------------------------------------------
    # WEIGHTED CONTRIBUTIONS
    # These make the final risk score explainable.
    # ---------------------------------------------------------
    df["hazard_contribution"] = (
        df["hazard_factor"]
        * normalized_weights["hazard"]
    )

    df["exposure_contribution"] = (
        df["exposure_factor"]
        * normalized_weights["exposure"]
    )

    df["vulnerability_contribution"] = (
        df["vulnerability_factor"]
        * normalized_weights["vulnerability"]
    )

    df["accessibility_contribution"] = (
        df["accessibility_factor"]
        * normalized_weights["accessibility"]
    )

    # ---------------------------------------------------------
    # FINAL COMPOSITE RISK SCORE
    # ---------------------------------------------------------
    df["composite_risk_score"] = (
        df["hazard_contribution"]
        + df["exposure_contribution"]
        + df["vulnerability_contribution"]
        + df["accessibility_contribution"]
    ).round(2)

    # ---------------------------------------------------------
    # AUTOMATED RELOCATION PRIORITY
    # ---------------------------------------------------------
    conditions = [
        df["composite_risk_score"] >= 75,
        df["composite_risk_score"] >= 50,
        df["composite_risk_score"] < 50,
    ]

    choices = [
        "CRITICAL - Immediate Relocation (0–3 Months)",
        "MODERATE - Short-Term Action",
        "SAFE - Medium-Term Monitoring",
    ]

    df["risk_tier"] = np.select(
        conditions,
        choices,
        default="SAFE - Medium-Term Monitoring",
    )

    return df