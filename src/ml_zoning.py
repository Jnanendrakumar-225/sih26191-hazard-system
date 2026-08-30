import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import MinMaxScaler


def assign_risk_zones(df: pd.DataFrame, n_clusters: int = 3, random_state: int = 42) -> pd.DataFrame:
    """
    Clusters habitations into spatial risk zones using KMeans over
    normalized (latitude, longitude, composite_risk_score).

    This groups nearby, similarly-at-risk habitations into a single
    operational zone, which is how a District Emergency Operations Centre
    actually plans evacuations — by zone, not habitation-by-habitation.

    Returns the input df with an added 'risk_zone' column (e.g. 'Zone A').
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

    zone_names = [f"Zone {chr(65 + i)}" for i in range(n_clusters)]
    df['risk_zone'] = [zone_names[label] for label in labels]
    return df