from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

import numpy as np
import pandas as pd
import xarray as xr


PROJECT_DIR = Path(__file__).resolve().parents[2]

station_file = (
    PROJECT_DIR
    / "data"
    / "pm10"
    / "processed"
    / "pm10_istasyonlar.csv"
)

era5_file = (
    PROJECT_DIR
    / "data"
    / "pm10"
    / "raw"
    / "era5"
    / "era5_land_antalya_2024_01.nc"
)

output_file = (
    PROJECT_DIR
    / "data"
    / "pm10"
    / "processed"
    / "era5_istasyon_eslestirme.csv"
)


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return R * c


stations = pd.read_csv(station_file)

ds = xr.open_dataset(era5_file)

# Tek bir saat üzerinden hangi ERA5-Land hücrelerinin
# geçerli kara hücresi olduğunu belirliyoruz.
sample = ds["t2m"].isel(valid_time=0)

valid_mask = np.isfinite(sample.values)

latitudes = sample["latitude"].values
longitudes = sample["longitude"].values

results = []

for _, row in stations.iterrows():

    station_name = row["istasyon"]
    station_lat = float(row["enlem"])
    station_lon = float(row["boylam"])

    candidates = []

    for i, lat in enumerate(latitudes):

        for j, lon in enumerate(longitudes):

            # Deniz / maskeli hücreleri atla.
            if not valid_mask[i, j]:
                continue

            distance = haversine_km(
                station_lat,
                station_lon,
                float(lat),
                float(lon)
            )

            candidates.append(
                (
                    distance,
                    float(lat),
                    float(lon)
                )
            )

    if not candidates:
        raise ValueError(
            f"{station_name} için geçerli ERA5 hücresi bulunamadı."
        )

    # En yakın geçerli kara hücresi
    candidates.sort(key=lambda x: x[0])

    distance, era5_lat, era5_lon = candidates[0]

    results.append({
        "istasyon": station_name,
        "istasyon_enlem": station_lat,
        "istasyon_boylam": station_lon,
        "era5_enlem": era5_lat,
        "era5_boylam": era5_lon,
        "uzaklik_km": round(distance, 2)
    })


result_df = pd.DataFrame(results)

print("\n==============================")
print("EN YAKIN GECERLI ERA5 HUCRESI")
print("==============================")

print(result_df.to_string(index=False))

result_df.to_csv(
    output_file,
    index=False
)

print("\nKaydedildi:")
print(output_file)