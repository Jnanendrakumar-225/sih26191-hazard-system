import pandas as pd

def compute_hazard_index(df: pd.DataFrame) -> pd.Series:
    """
    Derives a hazard index from observable risk signals instead of trusting
    a manually pre-assigned 'hazard_score' column.

    Uses historical flood frequency (a standard proxy in flood-risk modelling,
    e.g. as used in India's CWC flood atlases) as the primary signal, scaled
    to a 0-100 index.

    NOTE for production: this is designed to be swapped for a real geospatial
    hazard layer without changing the interface — e.g. inundation frequency
    from JRC Global Surface Water, a DEM-based flood-extent model, or a
    distance-to-drainage-network feature pulled via OSMnx. Any of those would
    plug in here and feed the same downstream AHP risk_engine unchanged.
    """
    if 'historical_floods' not in df.columns or df['historical_floods'].max() == 0:
        # No flood history available — fall back to the provided score rather
        # than silently returning zero everywhere.
        return df.get('hazard_score', pd.Series(0, index=df.index)).astype(float)

    max_floods = df['historical_floods'].max()
    hazard_index = (df['historical_floods'] / max_floods) * 100.0
    return hazard_index.round(2)
