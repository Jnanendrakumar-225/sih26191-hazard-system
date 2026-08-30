import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import os
import streamlit as st

@st.cache_data
def load_and_clean_habitations(filepath: str) -> gpd.GeoDataFrame:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Missing file: {filepath}")
    df = pd.read_csv(filepath)
    df.fillna({'children_population': 0, 'elderly_population': 0}, inplace=True)
    geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
    return gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

@st.cache_data
def load_and_clean_shelters(filepath: str) -> pd.DataFrame:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Missing file: {filepath}")
    df = pd.read_csv(filepath)
    df['available_capacity'] = (df['total_capacity'] - df['current_occupancy']).clip(lower=0)
    return df