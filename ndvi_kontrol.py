import rasterio
import numpy as np
import json

from rasterio.mask import mask
from rasterio.warp import transform_geom


ndvi_file = "outputs/mahmutlar/2026/ilkbahar/ndvi_median.tif"
boundary_file = "data/boundaries/mahmutlar_pilot_sinir.geojson"


# ============================================================
# MAHALLE SINIRINI OKU
# ============================================================

with open(boundary_file, "r", encoding="utf-8") as f:
    geojson = json.load(f)


if geojson["type"] == "FeatureCollection":
    geometries = [
        feature["geometry"]
        for feature in geojson["features"]
    ]

elif geojson["type"] == "Feature":
    geometries = [
        geojson["geometry"]
    ]

else:
    geometries = [
        geojson
    ]


# GeoJSON standart olarak EPSG:4326 kabul edilir.
boundary_crs = "EPSG:4326"


# ============================================================
# NDVI RASTERINI AÇ
# ============================================================

with rasterio.open(ndvi_file) as src:

    print("\n==============================")
    print("NDVI RASTER BİLGİSİ")
    print("==============================")

    print("CRS:", src.crs)
    print("Boyut:", src.width, "x", src.height)
    print("Bounds:", src.bounds)
    print("Nodata:", src.nodata)


    # --------------------------------------------------------
    # MAHALLE SINIRINI RASTER CRS'İNE DÖNÜŞTÜR
    # --------------------------------------------------------

    transformed_geometries = []

    for geometry in geometries:

        transformed = transform_geom(
            boundary_crs,
            src.crs,
            geometry
        )

        transformed_geometries.append(
            transformed
        )


    print("\n[OK] Mahalle sınırı raster CRS'ine dönüştürüldü.")


    # --------------------------------------------------------
    # MAHALLE SINIRINA GÖRE KIRP
    # --------------------------------------------------------

    clipped, transform = mask(
        src,
        transformed_geometries,
        crop=True
    )


    ndvi = clipped[0].astype(
        "float32"
    )


# ============================================================
# GEÇERLİ NDVI DEĞERLERİ
# ============================================================
valid = ndvi[
    np.isfinite(ndvi)
    & (ndvi >= -1.0)
    & (ndvi <= 1.0)
]

if valid.size == 0:
    raise ValueError(
        "Mahmutlar sınırı içinde geçerli NDVI verisi bulunamadı."
    )


# ============================================================
# TEMEL İSTATİSTİKLER
# ============================================================

print("\n==============================")
print("MAHMUTLAR SINIRI İÇİN NDVI")
print("==============================")


print(
    "Geçerli piksel sayısı:",
    valid.size
)

print(
    "Ortalama NDVI:",
    round(float(np.mean(valid)), 4)
)

print(
    "Medyan NDVI:",
    round(float(np.median(valid)), 4)
)

print(
    "Minimum:",
    round(float(np.min(valid)), 4)
)

print(
    "Maksimum:",
    round(float(np.max(valid)), 4)
)

print(
    "%25:",
    round(float(np.percentile(valid, 25)), 4)
)

print(
    "%75:",
    round(float(np.percentile(valid, 75)), 4)
)

print(
    "%90:",
    round(float(np.percentile(valid, 90)), 4)
)


# ============================================================
# NDVI SINIFLARI
# ============================================================

n1 = np.sum(
    valid < 0.20
)

n2 = np.sum(
    (valid >= 0.20)
    &
    (valid < 0.30)
)

n3 = np.sum(
    (valid >= 0.30)
    &
    (valid < 0.50)
)

n4 = np.sum(
    valid >= 0.50
)


total = valid.size


print("\n==============================")
print("NDVI SINIF DAĞILIMI")
print("==============================")


print(
    f"NDVI < 0.20 : "
    f"{n1} piksel "
    f"(%{n1 / total * 100:.2f})"
)

print(
    f"0.20 - 0.30 : "
    f"{n2} piksel "
    f"(%{n2 / total * 100:.2f})"
)

print(
    f"0.30 - 0.50 : "
    f"{n3} piksel "
    f"(%{n3 / total * 100:.2f})"
)

print(
    f"NDVI >= 0.50 : "
    f"{n4} piksel "
    f"(%{n4 / total * 100:.2f})"
)


print("\n==============================")
print("KONTROL TAMAMLANDI")
print("==============================")