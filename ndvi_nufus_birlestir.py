import rasterio
import numpy as np

from rasterio.warp import reproject, Resampling


# ============================================================
# DOSYALAR
# ============================================================

population_file = (
    "outputs/oba/2026/"
    "population_100m_calibrated.tif"
)

ndvi_file = (
    "outputs/oba/2026/ilkbahar/"
    "ndvi_median.tif"
)

output_file = (
    "outputs/oba/2026/ilkbahar/"
    "ndvi_100m.tif"
)


# ============================================================
# NÜFUS GRIDİNİ OKU
# ============================================================

with rasterio.open(population_file) as pop_src:

    population = (
        pop_src.read(1)
        .astype("float32")
    )

    pop_transform = pop_src.transform
    pop_crs = pop_src.crs
    pop_width = pop_src.width
    pop_height = pop_src.height

    profile = pop_src.profile.copy()

    if pop_src.nodata is not None:
        population[
            population == pop_src.nodata
        ] = np.nan


population[
    ~np.isfinite(population)
] = 0

population[
    population < 0
] = 0


# ============================================================
# NDVI'YI NÜFUS GRIDİNE UYARLA
# ============================================================

with rasterio.open(ndvi_file) as ndvi_src:

    ndvi = (
        ndvi_src.read(1)
        .astype("float32")
    )

    if ndvi_src.nodata is not None:

        if not np.isnan(ndvi_src.nodata):

            ndvi[
                ndvi == ndvi_src.nodata
            ] = np.nan

    # Fiziksel NDVI sınırı
    ndvi[
        (ndvi < -1)
        |
        (ndvi > 1)
    ] = np.nan

    ndvi_100m = np.full(
        (pop_height, pop_width),
        np.nan,
        dtype="float32"
    )

    reproject(
        source=ndvi,
        destination=ndvi_100m,

        src_transform=ndvi_src.transform,
        src_crs=ndvi_src.crs,

        dst_transform=pop_transform,
        dst_crs=pop_crs,

        resampling=Resampling.average,

        src_nodata=np.nan,
        dst_nodata=np.nan
    )


print(
    "\n[OK] NDVI nüfus gridine uyarlandı."
)


# ============================================================
# NÜFUS + NDVI EŞLEŞMESİ
# ============================================================

valid = (
    (population > 0)
    &
    np.isfinite(ndvi_100m)
    &
    (ndvi_100m >= -1)
    &
    (ndvi_100m <= 1)
)

pop_valid = population[valid]
ndvi_valid = ndvi_100m[valid]


print("\n==============================")
print("NÜFUS + NDVI EŞLEŞMESİ")
print("==============================")

print(
    "Eşleşen nüfuslu grid:",
    len(pop_valid)
)

print(
    "Eşleşen toplam nüfus:",
    round(
        float(
            np.sum(pop_valid)
        ),
        2
    )
)


# ============================================================
# AĞIRLIKSIZ NDVI
# ============================================================

unweighted_ndvi = float(
    np.mean(ndvi_valid)
)


# ============================================================
# NÜFUS-AĞIRLIKLI NDVI
# ============================================================

weighted_ndvi = float(
    np.sum(
        pop_valid * ndvi_valid
    )
    /
    np.sum(pop_valid)
)


difference = (
    weighted_ndvi
    -
    unweighted_ndvi
)


print("\n==============================")
print("NÜFUS-AĞIRLIKLI YEŞİLLİK")
print("==============================")

print(
    "Ağırlıksız ortalama NDVI:",
    round(
        unweighted_ndvi,
        4
    )
)

print(
    "Nüfus-ağırlıklı NDVI:",
    round(
        weighted_ndvi,
        4
    )
)

print(
    "Fark:",
    round(
        difference,
        4
    )
)


# ============================================================
# NDVI SINIFLARINA GÖRE NÜFUS
# ============================================================

classes = [

    (
        "NDVI < 0.20",
        ndvi_valid < 0.20
    ),

    (
        "0.20 - 0.30",
        (
            (ndvi_valid >= 0.20)
            &
            (ndvi_valid < 0.30)
        )
    ),

    (
        "0.30 - 0.50",
        (
            (ndvi_valid >= 0.30)
            &
            (ndvi_valid < 0.50)
        )
    ),

    (
        "NDVI >= 0.50",
        ndvi_valid >= 0.50
    )
]


total_population = float(
    np.sum(pop_valid)
)


print("\n==============================")
print("NÜFUSUN NDVI DAĞILIMI")
print("==============================")


for name, class_mask in classes:

    class_population = float(
        np.sum(
            pop_valid[class_mask]
        )
    )

    ratio = (
        class_population
        /
        total_population
        *
        100
    )

    print(
        name,
        ":",
        round(class_population),
        f"kişi (%{ratio:.2f})"
    )


# ============================================================
# PİLOT KRİTİK ALAN
# YÜKSEK NÜFUS + DÜŞÜK NDVI
# ============================================================

population_threshold = float(
    np.percentile(
        pop_valid,
        90
    )
)

critical = (
    valid
    &
    (population >= population_threshold)
    &
    (ndvi_100m < 0.20)
)


critical_cells = int(
    np.sum(critical)
)

critical_population = float(
    np.sum(
        population[critical]
    )
)

critical_ratio = (
    critical_population
    /
    total_population
    *
    100
)


print("\n==============================")
print("PİLOT KRİTİK YEŞİLLİK ALANLARI")
print("==============================")

print(
    "Yüksek nüfus eşiği (%90):",
    round(
        population_threshold,
        2
    ),
    "kişi/grid"
)

print(
    "Düşük NDVI pilot eşiği:",
    "0.20"
)

print(
    "Kritik grid sayısı:",
    critical_cells
)

print(
    "Kritik gridlerdeki nüfus:",
    round(
        critical_population
    )
)

print(
    "Toplam nüfus içindeki oran:",
    f"%{critical_ratio:.2f}"
)


# ============================================================
# 100 m NDVI RASTERINI KAYDET
# ============================================================

profile.update({
    "dtype": "float32",
    "count": 1,
    "nodata": -9999.0
})


save_array = np.where(
    np.isfinite(ndvi_100m),
    ndvi_100m,
    -9999.0
).astype("float32")


with rasterio.open(
    output_file,
    "w",
    **profile
) as dst:

    dst.write(
        save_array,
        1
    )


print("\n==============================")
print("KAYDEDİLDİ")
print("==============================")

print(
    output_file
)