import pandas as pd
import numpy as np
import xarray as xr
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

# =========================================================
# DOSYALAR
# =========================================================
STATION_FILE = Path(
    "data/pm10/processed/pm10_istasyonlar.csv"
)

CAMS_BASE = Path(
    "data/pm10/raw/cams"
)

OUTPUT_FILE = Path(
    "data/pm10/processed/cams_istasyon_eslestirme.csv"
)


# =========================================================
# HAVERSINE
# =========================================================
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088

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


# =========================================================
# İSTASYONLARI OKU
# =========================================================
stations = pd.read_csv(STATION_FILE)

required_cols = {
    "istasyon",
    "enlem",
    "boylam"
}

missing = required_cols - set(stations.columns)

if missing:
    raise ValueError(
        f"Eksik istasyon sütunları: {missing}"
    )


# =========================================================
# REFERANS CAMS DOSYASI
# =========================================================
nc_files = sorted(
    CAMS_BASE.glob("20??_??/*.nc")
)

if not nc_files:
    raise FileNotFoundError(
        "CAMS NetCDF dosyası bulunamadı."
    )

reference_file = nc_files[0]

ds = xr.open_dataset(
    reference_file,
    engine="netcdf4"
)

cams_lats = ds["lat"].values
cams_lons = ds["lon"].values


# =========================================================
# EN YAKIN GRID HÜCRESİ
# =========================================================
results = []

for _, row in stations.iterrows():

    station_lat = row["enlem"]
    station_lon = row["boylam"]

    lat_idx = np.abs(
        cams_lats - station_lat
    ).argmin()

    lon_idx = np.abs(
        cams_lons - station_lon
    ).argmin()

    cams_lat = float(
        cams_lats[lat_idx]
    )

    cams_lon = float(
        cams_lons[lon_idx]
    )

    distance = haversine_km(
        station_lat,
        station_lon,
        cams_lat,
        cams_lon
    )

    results.append({
        "istasyon": row["istasyon"],
        "istasyon_enlem": station_lat,
        "istasyon_boylam": station_lon,
        "cams_lat": cams_lat,
        "cams_lon": cams_lon,
        "mesafe_km": distance
    })


result_df = pd.DataFrame(results)


# =========================================================
# KAYDET
# =========================================================
OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

result_df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)


# =========================================================
# ÇIKTI
# =========================================================
print("\n==============================")
print("CAMS - İSTASYON EŞLEŞTİRME")
print("==============================")

print(
    result_df.to_string(
        index=False
    )
)

print("\nMesafe özeti (km):")
print(
    result_df["mesafe_km"].describe()
)

print(
    f"\n[OK] Kaydedildi: {OUTPUT_FILE}"
)