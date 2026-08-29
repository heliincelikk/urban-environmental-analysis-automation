import json
import rasterio
import numpy as np

from rasterio.mask import mask
from rasterio.warp import transform_geom


# ============================================================
# DOSYALAR
# ============================================================

ndvi_file = "outputs/oba/2026/ilkbahar/ndvi_median.tif"

boundary_file = (
    "data/boundaries/"
    "oba_pilot_sinir.geojson"
)


# ============================================================
# SINIRI OKU
# ============================================================

with open(
    boundary_file,
    "r",
    encoding="utf-8"
) as f:

    geojson = json.load(f)


if geojson["type"] == "FeatureCollection":

    geometry = (
        geojson["features"][0]["geometry"]
    )

elif geojson["type"] == "Feature":

    geometry = geojson["geometry"]

else:

    geometry = geojson


# ============================================================
# NDVI RASTERINI AÇ
# ============================================================

with rasterio.open(ndvi_file) as src:

    print("\n==============================")
    print("NDVI RASTER BİLGİSİ")
    print("==============================")

    print(
        "CRS:",
        src.crs
    )

    print(
        "Boyut:",
        src.width,
        "x",
        src.height
    )

    print(
        "Bounds:",
        src.bounds
    )

    print(
        "Nodata:",
        src.nodata
    )

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
    # RASTERI GERÇEK OBA POLİGONUNA KIRP
    # --------------------------------------------------------

    clipped, transform = mask(
        src,
        [geometry_projected],
        crop=True,
        filled=False
    )

    ndvi = (
        clipped[0]
        .astype("float32")
    )

    # Maskeli alanları NaN yap
    if np.ma.isMaskedArray(ndvi):

        ndvi = ndvi.filled(
            np.nan
        )

    if src.nodata is not None:

        if np.isnan(src.nodata):

            pass

        else:

            ndvi[
                ndvi == src.nodata
            ] = np.nan


# ============================================================
# FİZİKSEL NDVI KONTROLÜ
# ============================================================

ndvi[
    (ndvi < -1)
    |
    (ndvi > 1)
] = np.nan


valid = ndvi[
    np.isfinite(ndvi)
]


if len(valid) == 0:

    raise ValueError(
        "Oba sınırı içinde geçerli "
        "NDVI pikseli bulunamadı."
    )


# ============================================================
# SONUÇLAR
# ============================================================

print("\n==============================")
print("OBA SINIRI İÇİN NDVI")
print("==============================")

print(
    "Geçerli piksel sayısı:",
    len(valid)
)

print(
    "Ortalama NDVI:",
    round(
        float(np.mean(valid)),
        4
    )
)

print(
    "Medyan NDVI:",
    round(
        float(np.median(valid)),
        4
    )
)

print(
    "Minimum:",
    round(
        float(np.min(valid)),
        4
    )
)

print(
    "Maksimum:",
    round(
        float(np.max(valid)),
        4
    )
)

print(
    "%25:",
    round(
        float(
            np.percentile(
                valid,
                25
            )
        ),
        4
    )
)

print(
    "%75:",
    round(
        float(
            np.percentile(
                valid,
                75
            )
        ),
        4
    )
)

print(
    "%90:",
    round(
        float(
            np.percentile(
                valid,
                90
            )
        ),
        4
    )
)


# ============================================================
# NDVI SINIFLARI
# ============================================================

print("\n==============================")
print("NDVI SINIF DAĞILIMI")
print("==============================")


classes = [

    (
        "NDVI < 0.20",
        valid < 0.20
    ),

    (
        "0.20 - 0.30",
        (
            (valid >= 0.20)
            &
            (valid < 0.30)
        )
    ),

    (
        "0.30 - 0.50",
        (
            (valid >= 0.30)
            &
            (valid < 0.50)
        )
    ),

    (
        "NDVI >= 0.50",
        valid >= 0.50
    )
]


for name, class_mask in classes:

    count = int(
        np.sum(
            class_mask
        )
    )

    ratio = (
        count
        /
        len(valid)
        *
        100
    )

    print(
        name,
        ":",
        count,
        f"piksel (%{ratio:.2f})"
    )


print("\n==============================")
print("KONTROL TAMAMLANDI")
print("==============================")