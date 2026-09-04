import os
from io import BytesIO

import geopandas as gpd
import requests
from dotenv import load_dotenv
from shapely.geometry import Point


# ==============================
# AYARLAR
# ==============================

KEPEZ_LAT = 36.914883
KEPEZ_LON = 30.700425

BUFFER_M = 1000
SNAPSHOT_DATE = "2025-01-01"

OHSOME_API_URL = "https://api.heigit.org/ohsome-api/v2-rc"

ROAD_FILTER = "type:way and highway in (motorway, motorway_link, trunk, trunk_link, primary, primary_link, secondary, secondary_link) and geometry:line"
# ==============================
# API KEY
# ==============================

load_dotenv()

api_key = os.getenv("OHSOME_API_KEY")

if not api_key:
    raise RuntimeError("OHSOME_API_KEY .env dosyasinda bulunamadi.")


# ==============================
# 1 KM BUFFER OLUSTUR
# ==============================

# Kepez noktasini WGS84 olarak olusturuyoruz.
station = gpd.GeoDataFrame(
    {"istasyon": ["kepez"]},
    geometry=[Point(KEPEZ_LON, KEPEZ_LAT)],
    crs="EPSG:4326",
)

# Antalya icin UTM Zone 36N:
# metre cinsinden buffer olusturabilmek icin kullaniyoruz.
station_utm = station.to_crs("EPSG:32636")

buffer_utm = station_utm.geometry.buffer(BUFFER_M)

buffer_gdf = gpd.GeoDataFrame(
    {"istasyon": ["kepez"]},
    geometry=buffer_utm,
    crs="EPSG:32636",
)

# Ohsome AOI icin tekrar WGS84'e donuyoruz.
buffer_wgs84 = buffer_gdf.to_crs("EPSG:4326")

aoi_geojson = buffer_wgs84.geometry.iloc[0].__geo_interface__


# ==============================
# OHSOME API SORGUSU
# ==============================

url = f"{OHSOME_API_URL}/extraction/features.parquet"

payload = {
    "aoi": aoi_geojson,
    "filter": ROAD_FILTER,
    "time": SNAPSHOT_DATE,
    "clip": True,
}

headers = {
    "authorization": api_key
}

print("==============================")
print("OHSOME KEPEZ YOL TESTI")
print("==============================")
print()
print("Istasyon     : Kepez")
print(f"Buffer       : {BUFFER_M} m")
print(f"Snapshot     : {SNAPSHOT_DATE}")
print()

response = requests.post(
    url,
    json=payload,
    headers=headers,
    timeout=120,
)

print("HTTP status  :", response.status_code)

if response.status_code != 200:
    print()
    print("API HATA MESAJI:")
    print(response.text)
    raise RuntimeError("Ohsome API sorgusu basarisiz oldu.")


# ==============================
# PARQUET VERISINI OKU
# ==============================

roads = gpd.read_parquet(BytesIO(response.content))

print("Gelen yol parcasi:", len(roads))

if len(roads) == 0:
    print("Bu filtre ve alan icin yol bulunamadi.")
    raise SystemExit


# ==============================
# UZUNLUK HESABI
# ==============================

# Gelen geometri WGS84.
# Uzunlugu metre cinsinden hesaplamak icin UTM 36N'e ceviriyoruz.
roads_utm = roads.to_crs("EPSG:32636")

roads_utm["uzunluk_m"] = roads_utm.geometry.length

toplam_m = roads_utm["uzunluk_m"].sum()
toplam_km = toplam_m / 1000


print()
print("==============================")
print("SONUC")
print("==============================")
print(f"Toplam ana yol uzunlugu: {toplam_m:.2f} m")
print(f"Toplam ana yol uzunlugu: {toplam_km:.3f} km")

print()
print("Kolonlar:")
print(list(roads.columns))

print()
print("Ilk 5 kayit:")
print(roads.head().to_string())