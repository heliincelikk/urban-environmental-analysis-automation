import rasterio
import numpy as np

from rasterio.warp import reproject, Resampling


# ============================================================
# DOSYALAR
# ============================================================

population_file = (
    "outputs/mahmutlar/2026/"
    "population_100m_calibrated.tif"
)


lst_file = (
    "outputs/mahmutlar/2026/yaz/"
    "lst_median.tif"
)

output_file = (
    "outputs/mahmutlar/2026/yaz/"
    "lst_100m.tif"
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
# LST'Yİ NÜFUS GRIDİNE UYARLA
# ============================================================

with rasterio.open(lst_file) as lst_src:

    lst = (
        lst_src.read(1)
        .astype("float32")
    )

    if lst_src.nodata is not None:

        lst[
            lst == lst_src.nodata
        ] = np.nan


    # --------------------------------------------------------
    # LST veri kalite kontrolü
    # --------------------------------------------------------

    lst[
        (lst < -20)
        |
        (lst > 70)
    ] = np.nan


    lst_100m = np.full(
        (pop_height, pop_width),
        np.nan,
        dtype="float32"
    )


    # --------------------------------------------------------
    # Landsat LST'yi WorldPop 100 m gridine getir
    # --------------------------------------------------------

    reproject(
        source=lst,
        destination=lst_100m,

        src_transform=lst_src.transform,
        src_crs=lst_src.crs,

        dst_transform=pop_transform,
        dst_crs=pop_crs,

        resampling=Resampling.average,

        src_nodata=np.nan,
        dst_nodata=np.nan
    )


print(
    "\n[OK] LST nüfus gridine uyarlandı."
)


# ============================================================
# NÜFUS + LST EŞLEŞMESİ
# ============================================================

valid = (
    (population > 0)
    &
    np.isfinite(lst_100m)
    &
    (lst_100m >= -20)
    &
    (lst_100m <= 70)
)


pop_valid = population[
    valid
]

lst_valid = lst_100m[
    valid
]


if len(pop_valid) == 0:
    raise ValueError(
        "Nüfus ve LST arasında geçerli eşleşme bulunamadı."
    )


print("\n==============================")
print("NÜFUS + LST EŞLEŞMESİ")
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
# AĞIRLIKSIZ LST
# ============================================================

unweighted_lst = float(
    np.mean(
        lst_valid
    )
)


# ============================================================
# NÜFUS-AĞIRLIKLI LST
# ============================================================

weighted_lst = float(
    np.sum(
        pop_valid
        *
        lst_valid
    )
    /
    np.sum(
        pop_valid
    )
)


difference = (
    weighted_lst
    -
    unweighted_lst
)


print("\n==============================")
print("NÜFUS-AĞIRLIKLI TERMAL YÜK")
print("==============================")


print(
    "Ağırlıksız ortalama LST:",
    round(
        unweighted_lst,
        2
    ),
    "°C"
)


print(
    "Nüfus-ağırlıklı LST:",
    round(
        weighted_lst,
        2
    ),
    "°C"
)


print(
    "Fark:",
    round(
        difference,
        2
    ),
    "°C"
)


# ============================================================
# TERMAL SINIF EŞİKLERİ
# ============================================================

median_threshold = float(
    np.percentile(
        lst_valid,
        50
    )
)

p75_threshold = float(
    np.percentile(
        lst_valid,
        75
    )
)

p90_threshold = float(
    np.percentile(
        lst_valid,
        90
    )
)


print("\n==============================")
print("LST EŞİKLERİ")
print("==============================")


print(
    "Medyan:",
    round(
        median_threshold,
        2
    ),
    "°C"
)


print(
    "%75:",
    round(
        p75_threshold,
        2
    ),
    "°C"
)


print(
    "%90:",
    round(
        p90_threshold,
        2
    ),
    "°C"
)


# ============================================================
# NÜFUSUN TERMAL DAĞILIMI
# ============================================================

thermal_classes = [

    (
        "< Medyan",
        lst_valid < median_threshold
    ),

    (
        "Medyan - %75",
        (
            (lst_valid >= median_threshold)
            &
            (lst_valid < p75_threshold)
        )
    ),

    (
        "%75 - %90",
        (
            (lst_valid >= p75_threshold)
            &
            (lst_valid < p90_threshold)
        )
    ),

    (
        ">= %90",
        lst_valid >= p90_threshold
    )
]


total_population = float(
    np.sum(
        pop_valid
    )
)


print("\n==============================")
print("NÜFUSUN TERMAL DAĞILIMI")
print("==============================")


for name, class_mask in thermal_classes:

    class_population = float(
        np.sum(
            pop_valid[
                class_mask
            ]
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
        round(
            class_population
        ),
        f"kişi (%{ratio:.2f})"
    )


# ============================================================
# PİLOT KRİTİK TERMAL ALAN
#
# Tanım:
# - Nüfus yoğunluğu en yüksek %10'luk hücreler
# - LST değeri en yüksek %10'luk hücreler
#
# Bu eşikler mahalle içi göreli/pilot eşiklerdir.
# Sağlık eşiği değildir.
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
    np.isfinite(lst_100m)
    &
    (lst_100m >= p90_threshold)
)


critical_cells = int(
    np.sum(
        critical
    )
)


critical_population = float(
    np.sum(
        population[
            critical
        ]
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
print("PİLOT KRİTİK TERMAL ALANLAR")
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
    "Yüksek LST eşiği (%90):",
    round(
        p90_threshold,
        2
    ),
    "°C"
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
# VERİ KAPSAMA KONTROLÜ
# ============================================================

population_total = float(
    np.sum(
        population[
            population > 0
        ]
    )
)


missing_population = (
    population_total
    -
    total_population
)


print("\n==============================")
print("VERİ KAPSAMA KONTROLÜ")
print("==============================")


print(
    "Mahalle toplam nüfusu:",
    round(
        population_total,
        2
    )
)


print(
    "LST ile eşleşen nüfus:",
    round(
        total_population,
        2
    )
)


print(
    "LST verisi olmayan nüfus:",
    round(
        missing_population,
        2
    )
)


if abs(missing_population) < 1:

    print(
        "[OK] Mahalle nüfusunun tamamı LST ile eşleşti."
    )

else:

    print(
        "[UYARI] Bazı nüfus hücrelerinde LST verisi bulunmuyor."
    )


# ============================================================
# 100 m LST RASTERINI KAYDET
# ============================================================

profile.update({
    "dtype": "float32",
    "count": 1,
    "nodata": -9999.0
})


output_array = np.full(
    lst_100m.shape,
    np.nan,
    dtype="float32"
)


output_array[
    valid
] = lst_100m[
    valid
]


save_array = np.where(
    np.isfinite(
        output_array
    ),
    output_array,
    -9999.0
).astype(
    "float32"
)


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