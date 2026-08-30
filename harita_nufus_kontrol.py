import numpy as np
import rasterio


# ============================================================
# DOSYALAR
# ============================================================

population_file = (
    "outputs/oba/2026/"
    "population_100m_calibrated.tif"
)

ndvi_file = (
    "outputs/oba/2026/yaz/"
    "ndvi_100m.tif"
)

lst_file = (
    "outputs/oba/2026/yaz/"
    "lst_100m.tif"
)


# ============================================================
# RASTER OKUMA
# ============================================================

def read_raster(path):

    with rasterio.open(path) as src:

        data = (
            src.read(1)
            .astype("float32")
        )

        nodata = src.nodata

        if nodata is not None:

            if np.isnan(nodata):
                pass

            else:
                data[
                    data == nodata
                ] = np.nan

        return data


population = read_raster(
    population_file
)

ndvi = read_raster(
    ndvi_file
)

lst = read_raster(
    lst_file
)


# ============================================================
# NÜFUS TEMİZLE
# ============================================================

population[
    ~np.isfinite(population)
] = 0

population[
    population < 0
] = 0


population_mask = (
    population > 0
)


# ============================================================
# TÜM NÜFUS GRIDLERİ
# ============================================================

total_population = float(
    np.sum(
        population[
            population_mask
        ]
    )
)

total_grids = int(
    np.sum(
        population_mask
    )
)


# ============================================================
# NDVI HARİTASINDA GÖRÜNENLER
# ============================================================

ndvi_visible = (
    population_mask
    &
    np.isfinite(ndvi)
    &
    (ndvi >= -1)
    &
    (ndvi <= 1)
)


ndvi_population = float(
    np.sum(
        population[
            ndvi_visible
        ]
    )
)

ndvi_grids = int(
    np.sum(
        ndvi_visible
    )
)


# ============================================================
# LST HARİTASINDA GÖRÜNENLER
# ============================================================

lst_visible = (
    population_mask
    &
    np.isfinite(lst)
    &
    (lst > -20)
    &
    (lst < 70)
)


lst_population = float(
    np.sum(
        population[
            lst_visible
        ]
    )
)

lst_grids = int(
    np.sum(
        lst_visible
    )
)


# ============================================================
# EKSİK NÜFUS
# ============================================================

ndvi_missing = (
    total_population
    -
    ndvi_population
)

lst_missing = (
    total_population
    -
    lst_population
)


# ============================================================
# SONUÇ
# ============================================================

print("\n==============================")
print("HARİTA NÜFUS KONTROLÜ")
print("==============================")

print("\nTÜM NÜFUS GRIDLERİ")
print("------------------------------")
print(
    "Grid sayısı:",
    total_grids
)
print(
    "Toplam nüfus:",
    round(
        total_population,
        2
    )
)


print("\nNDVI HARİTASINDA GÖRÜNEN")
print("------------------------------")
print(
    "Grid sayısı:",
    ndvi_grids
)
print(
    "Toplam nüfus:",
    round(
        ndvi_population,
        2
    )
)
print(
    "Eksik nüfus:",
    round(
        ndvi_missing,
        2
    )
)


print("\nLST HARİTASINDA GÖRÜNEN")
print("------------------------------")
print(
    "Grid sayısı:",
    lst_grids
)
print(
    "Toplam nüfus:",
    round(
        lst_population,
        2
    )
)
print(
    "Eksik nüfus:",
    round(
        lst_missing,
        2
    )
)


print("\n==============================")
print("KONTROL TAMAMLANDI")
print("==============================")