import pandas as pd
from typing import List
from sklearn.cluster import KMeans
from sklearn.preprocessing import MinMaxScaler


def assign_risk_zones(
    df: pd.DataFrame, 
    n_clusters: int = 3, 
    random_state: int = 42
) -> pd.DataFrame:
    """
    Cluster habitations into spatial risk zones using KMeans.
    
    Groups nearby habitations with similar risk levels into operational zones
    for coordinated DEOC evacuation planning.
    
    Features used for clustering (normalized):
    - Latitude: Geographic location
    - Longitude: Geographic location
    - Composite risk score: Risk level
    
    Args:
        df: DataFrame with columns: latitude, longitude, composite_risk_score
        n_clusters: Number of zones (1-5 typical), automatically capped to 
                   min(n_clusters, len(df))
        random_state: Seed for reproducibility
    
    Returns:
        DataFrame with added 'risk_zone' column containing zone names ('Zone A', 'Zone B', etc.)
    """
    df = df.copy()
    n_clusters = max(1, min(n_clusters, len(df)))

    if n_clusters == 1 or len(df) < 2:
        df['risk_zone'] = 'Zone A'
        return df

    features = df[['latitude', 'longitude', 'composite_risk_score']].to_numpy()
    scaled = MinMaxScaler().fit_transform(features)

    model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    labels = model.fit_predict(scaled)

    zone_names: List[str] = [f"Zone {chr(65 + i)}" for i in range(n_clusters)]
    df['risk_zone'] = [zone_names[label] for label in labels]
    return df