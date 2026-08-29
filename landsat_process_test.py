import json
import pystac_client
import planetary_computer


# ============================================================
# AYARLAR
# ============================================================

boundary_file = "data/boundaries/oba_pilot_sinir.geojson"

start_date = "2026-03-01"
end_date = "2026-05-31"

max_cloud = 30


# ============================================================
# GEOJSON'DAN BBOX
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
            result.extend(
                flatten_coordinates(item)
            )

    return result


points = flatten_coordinates(
    geometry["coordinates"]
)

longitudes = [p[0] for p in points]
latitudes = [p[1] for p in points]

bbox = [
    min(longitudes),
    min(latitudes),
    max(longitudes),
    max(latitudes)
]


# ============================================================
# PLANETARY COMPUTER STAC
# ============================================================

print("\n==============================")
print("LANDSAT C2 L2 TEST")
print("==============================")

print("BBOX:", bbox)
print("Dönem:", start_date, "-", end_date)
print("Maksimum bulut:", max_cloud, "%")


catalog = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace
)


print("\nPlanetary Computer aranıyor...")


search = catalog.search(
    collections=["landsat-c2-l2"],

    bbox=bbox,

    datetime=(
        f"{start_date}/"
        f"{end_date}"
    ),

    query={
        "eo:cloud_cover": {
            "lt": max_cloud
        }
    }
)


items = list(
    search.items()
)


# ============================================================
# SONUÇ
# ============================================================

print("\n==============================")
print("BULUNAN LANDSAT SAHNELERİ")
print("==============================")

print(
    "Toplam:",
    len(items)
)


items = sorted(
    items,
    key=lambda item:
    item.properties.get(
        "eo:cloud_cover",
        999
    )
)


for i, item in enumerate(
    items,
    start=1
):

    print(
        f"\n{i}."
    )

    print(
        "ID:",
        item.id
    )

    print(
        "Tarih:",
        item.datetime
    )

    print(
        "Bulut:",
        item.properties.get(
            "eo:cloud_cover"
        )
    )

    print(
        "Platform:",
        item.properties.get(
            "platform"
        )
    )

    # --------------------------------------------------------
    # TERMAL BANDI KONTROL ET
    # --------------------------------------------------------

    if "lwir11" in item.assets:

        asset = item.assets["lwir11"]

        print(
            "Surface Temperature:",
            "VAR"
        )

        print(
            "Asset:",
            asset.title
        )

    elif "lwir" in item.assets:

        asset = item.assets["lwir"]

        print(
            "Surface Temperature:",
            "VAR"
        )

        print(
            "Asset:",
            asset.title
        )

    else:

        print(
            "Surface Temperature:",
            "BULUNAMADI"
        )


print("\n==============================")
print("TEST TAMAMLANDI")
print("==============================")