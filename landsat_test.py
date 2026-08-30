import os
import json
import requests
from dotenv import load_dotenv


# ============================================================
# .ENV YÜKLE
# ============================================================

load_dotenv()

client_id = os.getenv("COPERNICUS_CLIENT_ID")
client_secret = os.getenv("COPERNICUS_CLIENT_SECRET")

if not client_id or not client_secret:
    raise ValueError(
        ".env içinde COPERNICUS_CLIENT_ID "
        "veya COPERNICUS_CLIENT_SECRET bulunamadı."
    )


# ============================================================
# AYARLAR
# ============================================================

boundary_file = (
    "data/boundaries/"
    "mahmutlar_belediye_sinir_DUZELTILMIS.geojson"
)

start_date = "2026-03-01"
end_date = "2026-05-31"

max_cloud = 30


# ============================================================
# ACCESS TOKEN AL
# ============================================================

token_url = (
    "https://identity.dataspace.copernicus.eu/"
    "auth/realms/CDSE/protocol/openid-connect/token"
)

token_response = requests.post(
    token_url,
    data={
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    },
    timeout=60
)

if token_response.status_code != 200:
    print("Token alınamadı.")
    print(token_response.text)
    raise SystemExit

access_token = token_response.json().get("access_token")

if not access_token:
    raise ValueError("Access token bulunamadı.")

print("[OK] Access token alındı.")


# ============================================================
# GEOJSON'DAN BBOX ÜRET
# ============================================================

with open(boundary_file, "r", encoding="utf-8") as f:
    geojson = json.load(f)

if geojson["type"] == "FeatureCollection":
    geometry = geojson["features"][0]["geometry"]
elif geojson["type"] == "Feature":
    geometry = geojson["geometry"]
else:
    geometry = geojson


def flatten_coordinates(values):
    result = []

    for item in values:
        if (
            isinstance(item, list)
            and len(item) >= 2
            and isinstance(item[0], (int, float))
            and isinstance(item[1], (int, float))
        ):
            result.append(item)
        else:
            result.extend(flatten_coordinates(item))

    return result


points = flatten_coordinates(geometry["coordinates"])

longitudes = [p[0] for p in points]
latitudes = [p[1] for p in points]

bbox = [
    min(longitudes),
    min(latitudes),
    max(longitudes),
    max(latitudes)
]


# ============================================================
# CATALOG API ARAMASI
# ============================================================

url = (
    "https://sh.dataspace.copernicus.eu/"
    "api/v1/catalog/1.0.0/search"
)

payload = {
    "collections": [
        "landsat-ot-l2"
    ],

    "bbox": bbox,

    "datetime": (
        f"{start_date}T00:00:00Z/"
        f"{end_date}T23:59:59Z"
    ),

    "limit": 100,

    "filter": f"eo:cloud_cover <= {max_cloud}",

    "filter-lang": "cql2-text"
}

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}


print("\n==============================")
print("LANDSAT 8/9 L2 TEST")
print("==============================")

print("BBOX:", bbox)
print("Dönem:", start_date, "-", end_date)
print("Maksimum bulut:", max_cloud, "%")

print("\nCopernicus Landsat kataloğu aranıyor...")


response = requests.post(
    url,
    headers=headers,
    json=payload,
    timeout=60
)

print(
    "HTTP durum kodu:",
    response.status_code
)


if response.status_code != 200:
    print("\nHATA:")
    print(response.text)
    raise SystemExit


data = response.json()

features = data.get(
    "features",
    []
)


# ============================================================
# SONUÇLAR
# ============================================================

print("\n==============================")
print("BULUNAN LANDSAT SAHNELERİ")
print("==============================")

print(
    "Toplam:",
    len(features)
)


if len(features) == 0:

    print(
        "Bu dönem için uygun "
        "Landsat sahnesi bulunamadı."
    )

else:

    features = sorted(
        features,
        key=lambda x:
        x.get(
            "properties",
            {}
        ).get(
            "eo:cloud_cover",
            999
        )
    )

    for i, feature in enumerate(
        features,
        start=1
    ):

        properties = feature.get(
            "properties",
            {}
        )

        scene_id = feature.get(
            "id",
            "?"
        )

        date = properties.get(
            "datetime",
            "?"
        )

        cloud = properties.get(
            "eo:cloud_cover",
            "?"
        )

        print(f"\n{i}.")
        print("Tarih:", date)
        print("Bulut:", cloud)
        print("ID:", scene_id)


print("\n==============================")
print("TEST TAMAMLANDI")
print("==============================")