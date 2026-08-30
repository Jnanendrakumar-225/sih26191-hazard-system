import numpy as np
import pandas as pd
from typing import Dict


def _normalize_to_100(series: pd.Series) -> pd.Series:
    """
    Safely normalize numeric values to a 0-100 scale.

    If all values are identical, returns 50 because there is
    no relative difference between habitations.
    
    Args:
        series: Numeric pandas Series to normalize
    
    Returns:
        Normalized Series with values in range [0, 100]
    """
    values = pd.to_numeric(series, errors="coerce").fillna(0)

    minimum = values.min()
    maximum = values.max()

    if maximum == minimum:
        return pd.Series(50.0, index=values.index)

    return ((values - minimum) / (maximum - minimum)) * 100.0


def calculate_ahp_risk(df: pd.DataFrame, weights: Dict[str, float]) -> pd.DataFrame:
    """
    Computes overall habitation risk using Multi-Criteria Decision Analysis (MCDA).
    
    Combines four criteria:
    1. Hazard intensity (natural hazard exposure)
    2. Population exposure (total population)
    3. Population vulnerability (children + elderly proportion)
    4. Evacuation accessibility (ease of egress)
    
    Weights are automatically normalized to sum to 1.0.
    
    Args:
        df: DataFrame with columns: hazard_score, population, children_population,
                                   elderly_population, accessibility_score
        weights: Dict with keys 'hazard', 'exposure', 'vulnerability', 'accessibility'
                Values should be 0-1 (will be normalized to 1.0)
    
    Returns:
        Original DataFrame with added columns:
            - hazard_factor: Normalized hazard intensity (0-100)
            - exposure_factor: Population exposure (0-100)
            - vulnerability_factor: Proportion of vulnerable population (0-100)
            - accessibility_factor: Evacuation difficulty (0-100)
            - hazard_contribution: Weighted contribution to risk score
            - exposure_contribution: Weighted contribution to risk score
            - vulnerability_contribution: Weighted contribution to risk score
            - accessibility_contribution: Weighted contribution to risk score
            - composite_risk_score: Final AHP risk score (0-100)
            - risk_tier: Classification (CRITICAL/MODERATE/LOW)
    
    Raises:
        ValueError: If required columns are missing
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