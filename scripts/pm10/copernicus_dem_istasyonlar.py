import ee
import pandas as pd
import os

PROJECT_ID = "antalya-environmental-analysis"

INPUT_FILE = "data/pm10/processed/pm10_istasyonlar.csv"
OUTPUT_FILE = "outputs/pm10/copernicus_dem_istasyon_elevation.csv"

ee.Initialize(project=PROJECT_ID)

# Copernicus DEM GLO-30
dem = ee.ImageCollection("COPERNICUS/DEM/GLO30_2024_1").mosaic().select("DEM")

stations = pd.read_csv(INPUT_FILE)

results = []

for _, row in stations.iterrows():
    station = row["istasyon"]
    lat = row["enlem"]
    lon = row["boylam"]

    point = ee.Geometry.Point([lon, lat])

    elevation = dem.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=point.buffer(50),
        scale=30,
        bestEffort=True
    ).get("DEM")

    elevation_value = elevation.getInfo()

    results.append({
        "istasyon": station,
        "enlem": lat,
        "boylam": lon,
        "elevation_m": elevation_value
    })

    print(f"{station:<12} {elevation_value:.2f} m")

result_df = pd.DataFrame(results)

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
result_df.to_csv(OUTPUT_FILE, index=False)

print("\nKaydedildi:")
print(OUTPUT_FILE)