import json
import numpy as np
import rasterio
import pystac_client
import planetary_computer

from rasterio.mask import mask
from rasterio.warp import transform_geom


# ============================================================
# AYARLAR
# ============================================================

boundary_file = "data/boundaries/oba_pilot_sinir.geojson"

start_date = "2026-03-01"
end_date = "2026-05-31"

max_cloud = 30


# ============================================================
# GEOJSON OKU
# ============================================================

with open(boundary_file, "r", encoding="utf-8") as f:
    geojson = json.load(f)

if geojson["type"] == "FeatureCollection":
    geometry = geojson["features"][0]["geometry"]

elif geojson["type"] == "Feature":
    geometry = geojson["geometry"]

else:
    geometry = geojson


# ============================================================
# BBOX
# ============================================================

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

bbox = [
    min(p[0] for p in points),
    min(p[1] for p in points),
    max(p[0] for p in points),
    max(p[1] for p in points)
]


# ============================================================
# STAC ARAMASI
# ============================================================

print("\n==============================")
print("LANDSAT LST İLK SAHNE TESTİ")
print("==============================")

catalog = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace
)

search = catalog.search(
    collections=["landsat-c2-l2"],
    bbox=bbox,
    datetime=f"{start_date}/{end_date}",
    query={
        "eo:cloud_cover": {
            "lt": max_cloud
        }
    }
)

items = list(search.items())

if not items:
    raise ValueError(
        "Uygun Landsat sahnesi bulunamadı."
    )


# ============================================================
# EN AZ BULUTLU SAHNEYİ SEÇ
# ============================================================

items = sorted(
    items,
    key=lambda item:
    item.properties.get(
        "eo:cloud_cover",
        999
    )
)

item = items[0]


print("Seçilen sahne:")
print("ID:", item.id)
print("Tarih:", item.datetime)

print(
    "Bulut:",
    item.properties.get(
        "eo:cloud_cover"
    ),
    "%"
)


# ============================================================
# ST_B10 ASSET
# ============================================================

if "lwir11" not in item.assets:
    raise ValueError(
        "Bu sahnede lwir11 / ST_B10 bulunamadı."
    )


asset = item.assets["lwir11"]

print("\nAsset:")
print(asset.title)


# ============================================================
# SCALE / OFFSET BİLGİSİNİ KONTROL ET
# ============================================================

scale = None
offset = None

raster_bands = asset.extra_fields.get(
    "raster:bands",
    []
)

if raster_bands:

    band_info = raster_bands[0]

    scale = band_info.get("scale")
    offset = band_info.get("offset")


print("\nMetadata:")
print("Scale:", scale)
print("Offset:", offset)


# Landsat Collection 2 L2 ST_B10 standard conversion
if scale is None:
    scale = 0.00341802

if offset is None:
    offset = 149.0


# ============================================================
# RASTERI UZAKTAN AÇ
# ============================================================

print("\nST_B10 rasterı okunuyor...")


with rasterio.open(asset.href) as src:

    print("\n==============================")
    print("RASTER BİLGİSİ")
    print("==============================")

    print("CRS:", src.crs)
    print("Boyut:", src.width, "x", src.height)
    print("Nodata:", src.nodata)
    print("Datatype:", src.dtypes[0])

    # --------------------------------------------------------
    # OBA SINIRINI RASTER CRS'İNE ÇEVİR
    # --------------------------------------------------------

    geometry_projected = transform_geom(
        "EPSG:4326",
        src.crs,
        geometry,
        precision=6
    )

    # --------------------------------------------------------
    # OBA SINIRINA KIRP
    # --------------------------------------------------------

    clipped, _ = mask(
        src,
        [geometry_projected],
        crop=True,
        filled=False
    )

    dn = clipped[0].astype("float32")

    if np.ma.isMaskedArray(dn):
        dn = dn.filled(np.nan)

    if src.nodata is not None:
        dn[
            dn == src.nodata
        ] = np.nan


# ============================================================
# DN -> KELVIN -> CELSIUS
# ============================================================

kelvin = (
    dn * scale
    + offset
)

celsius = (
    kelvin
    - 273.15
)


# ============================================================
# FİZİKSEL FİLTRE
# ============================================================

# Pilot kalite kontrolü:
# aşırı saçma sıcaklıkları kaldır.
celsius[
    (celsius < -20)
    |
    (celsius > 70)
] = np.nan


valid = celsius[
    np.isfinite(celsius)
]


if len(valid) == 0:
    raise ValueError(
        "Oba sınırı içinde geçerli "
        "LST pikseli bulunamadı."
    )


# ============================================================
# SONUÇ
# ============================================================

print("\n==============================")
print("OBA LST SONUÇLARI")
print("==============================")

print(
    "Geçerli piksel:",
    len(valid)
)

print(
    "Ortalama °C:",
    round(
        float(np.mean(valid)),
        2
    )
)

print(
    "Medyan °C:",
    round(
        float(np.median(valid)),
        2
    )
)

print(
    "Minimum °C:",
    round(
        float(np.min(valid)),
        2
    )
)

print(
    "Maksimum °C:",
    round(
        float(np.max(valid)),
        2
    )
)

print(
    "%25:",
    round(
        float(np.percentile(valid, 25)),
        2
    )
)

print(
    "%75:",
    round(
        float(np.percentile(valid, 75)),
        2
    )
)

print(
    "%90:",
    round(
        float(np.percentile(valid, 90)),
        2
    )
)


print("\n==============================")
print("TEST TAMAMLANDI")
print("==============================")