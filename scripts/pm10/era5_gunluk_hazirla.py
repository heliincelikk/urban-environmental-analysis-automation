from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


# =========================================================
# PROJE YOLLARI
# =========================================================

PROJECT_DIR = Path(__file__).resolve().parents[2]

era5_dir = (
    PROJECT_DIR
    / "data"
    / "pm10"
    / "raw"
    / "era5"
)

mapping_file = (
    PROJECT_DIR
    / "data"
    / "pm10"
    / "processed"
    / "era5_istasyon_eslestirme.csv"
)

output_file = (
    PROJECT_DIR
    / "data"
    / "pm10"
    / "processed"
    / "era5_istasyon_gunluk_2024_2025.csv"
)


# =========================================================
# 1. ERA5 DOSYALARINI HAZIRLA
# =========================================================

buffer_file = (
    era5_dir
    / "era5_land_antalya_2023_12_31_buffer.nc"
)

monthly_files = []

for year in [2024, 2025]:

    for month in range(1, 13):

        file_path = (
            era5_dir
            / f"era5_land_antalya_{year}_{month:02d}.nc"
        )

        monthly_files.append(
            file_path
        )


# =========================================================
# 2. DOSYALARIN VARLIĞINI KONTROL ET
# =========================================================

all_files = [
    buffer_file,
    *monthly_files
]

missing_files = [
    file
    for file in all_files
    if not file.exists()
]

if missing_files:

    print("\nEksik ERA5 dosyalari:")

    for file in missing_files:
        print(file)

    raise FileNotFoundError(
        "Tum ERA5 dosyalari bulunamadi."
    )


print("\nERA5 dosya sayisi:")
print(len(monthly_files))

print(
    "24 aylik dosya bulundu."
)


# =========================================================
# 3. ERA5 DOSYALARINI AÇ VE BİRLEŞTİR
# =========================================================

datasets = []


print("\nDosyalar aciliyor...")


ds_buffer = xr.open_dataset(
    buffer_file
)

datasets.append(
    ds_buffer
)


for file_path in monthly_files:

    print(
        file_path.name
    )

    ds_month = xr.open_dataset(
        file_path
    )

    datasets.append(
        ds_month
    )


ds = xr.concat(
    datasets,
    dim="valid_time"
)

ds = ds.sortby(
    "valid_time"
)


# =========================================================
# 4. DUPLICATE ZAMAN KONTROLÜ
# =========================================================

time_index = pd.to_datetime(
    ds["valid_time"].values
)

duplicate_time_count = (
    pd.Index(time_index)
    .duplicated()
    .sum()
)

print(
    "\nDuplicate UTC zaman sayisi:"
)

print(
    duplicate_time_count
)


if duplicate_time_count > 0:

    raise ValueError(
        "ERA5 zaman ekseninde duplicate kayit bulundu."
    )


# =========================================================
# 5. UTC VE TÜRKİYE YEREL SAATİ
# =========================================================

utc_time = time_index

local_time = (
    utc_time
    + pd.to_timedelta(
        3,
        unit="h"
    )
)


# =========================================================
# 6. İSTASYON-GRID EŞLEŞMESİNİ OKU
# =========================================================

mapping = pd.read_csv(
    mapping_file
)


print(
    "\nIstasyon sayisi:"
)

print(
    len(mapping)
)


if len(mapping) != 8:

    raise ValueError(
        "Beklenen istasyon sayisi 8."
    )


all_station_data = []


# =========================================================
# 7. HER İSTASYON İÇİN METEOROLOJİYİ HAZIRLA
# =========================================================

for _, row in mapping.iterrows():

    station_name = row[
        "istasyon"
    ]

    era5_lat = float(
        row[
            "era5_enlem"
        ]
    )

    era5_lon = float(
        row[
            "era5_boylam"
        ]
    )


    print(
        f"\nIsleniyor: {station_name}"
    )


    # -----------------------------------------------------
    # Daha önce doğrulanmış ERA5 grid koordinatını seçiyoruz.
    #
    # method="nearest" burada sadece floating-point
    # koordinat farkını çözmek için kullanılıyor.
    # tolerance=0.001, komşu 0.1 derece hücreye
    # yanlışlıkla atlamayı engeller.
    # -----------------------------------------------------

    point = ds.sel(
        latitude=era5_lat,
        longitude=era5_lon,
        method="nearest",
        tolerance=0.001
    )


    # =====================================================
    # 8. SICAKLIK VE ÇİY NOKTASI
    # =====================================================

    sicaklik_c = (
        point["t2m"].values
        - 273.15
    )

    ciy_noktasi_c = (
        point["d2m"].values
        - 273.15
    )


    # =====================================================
    # 9. BAĞIL NEM
    # =====================================================

    es_t = (
        6.1121
        * np.exp(
            (
                18.729
                - sicaklik_c / 227.3
            )
            * sicaklik_c
            / (
                sicaklik_c
                + 257.87
            )
        )
    )


    es_td = (
        6.1121
        * np.exp(
            (
                18.729
                - ciy_noktasi_c / 227.3
            )
            * ciy_noktasi_c
            / (
                ciy_noktasi_c
                + 257.87
            )
        )
    )


    bagil_nem = (
        100
        * es_td
        / es_t
    )


    # =====================================================
    # 10. RÜZGAR HIZI
    # =====================================================

    ruzgar_hizi = np.sqrt(
        point["u10"].values ** 2
        + point["v10"].values ** 2
    )


    # =====================================================
    # 11. SAATLİK TABLO
    # =====================================================

    hourly = pd.DataFrame({

        "utc_time":
            utc_time,

        "local_time":
            local_time,

        "sicaklik_c":
            sicaklik_c,

        "bagil_nem_yuzde":
            bagil_nem,

        "basinc_hpa":
            point["sp"].values
            / 100,

        "ruzgar_u_ms":
            point["u10"].values,

        "ruzgar_v_ms":
            point["v10"].values,

        "ruzgar_hizi_ms":
            ruzgar_hizi

    })


    hourly[
        "tarih"
    ] = (
        hourly[
            "local_time"
        ]
        .dt.date
    )


    # =====================================================
    # 12. GÜNLÜK ORTALAMALAR
    # =====================================================

    daily = (
        hourly
        .groupby(
            "tarih"
        )
        .agg(

            sicaklik_ort_c=(
                "sicaklik_c",
                "mean"
            ),

            bagil_nem_ort_yuzde=(
                "bagil_nem_yuzde",
                "mean"
            ),

            basinc_ort_hpa=(
                "basinc_hpa",
                "mean"
            ),

            ruzgar_u_ort_ms=(
                "ruzgar_u_ms",
                "mean"
            ),

            ruzgar_v_ort_ms=(
                "ruzgar_v_ms",
                "mean"
            ),

            ruzgar_hizi_ort_ms=(
                "ruzgar_hizi_ms",
                "mean"
            ),

            saat_sayisi=(
                "local_time",
                "count"
            )

        )
        .reset_index()
    )


    # =====================================================
    # 13. YALNIZCA 2024-2025 GÜNLERİNİ TUT
    # =====================================================

    daily[
        "tarih"
    ] = pd.to_datetime(
        daily[
            "tarih"
        ]
    )


    daily = daily[
        (
            daily["tarih"]
            >= pd.Timestamp(
                "2024-01-01"
            )
        )
        &
        (
            daily["tarih"]
            <= pd.Timestamp(
                "2025-12-31"
            )
        )
    ].copy()


    # =====================================================
    # 14. TAM 24 SAATLİK GÜNLERİ KONTROL ET
    # =====================================================

    incomplete_days = daily[
        daily[
            "saat_sayisi"
        ] != 24
    ]


    if len(incomplete_days) > 0:

        print(
            f"\nUYARI - {station_name}: "
            f"{len(incomplete_days)} eksik gun var."
        )


    # Yalnızca tam günler
    daily = daily[
        daily[
            "saat_sayisi"
        ] == 24
    ].copy()


    # =====================================================
    # 15. GÜNLÜK YAĞIŞ
    # =====================================================

    tp_series = pd.Series(
        point[
            "tp"
        ].values,
        index=utc_time
    ).sort_index()


    precipitation_results = []


    for local_date in daily[
        "tarih"
    ]:

        day = pd.Timestamp(
            local_date
        )


        # Yerel gün D:
        #
        # D-1 21 UTC
        # ->
        # D 21 UTC


        previous_21 = (
            day
            - pd.to_timedelta(
                1,
                unit="D"
            )
            + pd.to_timedelta(
                21,
                unit="h"
            )
        )


        current_00 = (
            day
        )


        current_21 = (
            day
            + pd.to_timedelta(
                21,
                unit="h"
            )
        )


        if (
            previous_21
            not in tp_series.index
            or current_00
            not in tp_series.index
            or current_21
            not in tp_series.index
        ):

            precipitation_results.append(
                np.nan
            )

            continue


        tp_previous_21 = float(
            tp_series.loc[
                previous_21
            ]
        )


        tp_current_00 = float(
            tp_series.loc[
                current_00
            ]
        )


        tp_current_21 = float(
            tp_series.loc[
                current_21
            ]
        )


        # Önceki UTC gün:
        # 21 -> 24
        part_1 = (
            tp_current_00
            - tp_previous_21
        )


        # Mevcut UTC gün:
        # 00 -> 21
        part_2 = (
            tp_current_21
        )


        # metre -> mm
        precipitation_mm = (
            part_1
            + part_2
        ) * 1000


        precipitation_results.append(
            precipitation_mm
        )


    daily[
        "yagis_toplam_mm"
    ] = (
        precipitation_results
    )
    daily["yagis_toplam_mm"] = (
    daily["yagis_toplam_mm"]
    .clip(lower=0)
)


    daily[
        "istasyon"
    ] = (
        station_name
    )


    all_station_data.append(
        daily
    )


# =========================================================
# 16. TÜM İSTASYONLARI BİRLEŞTİR
# =========================================================

result = pd.concat(
    all_station_data,
    ignore_index=True
)


# =========================================================
# 17. TARİHİ STANDART HALE GETİR
# =========================================================

result[
    "tarih"
] = pd.to_datetime(
    result[
        "tarih"
    ]
)


# =========================================================
# 18. KOLON SIRASI
# =========================================================

result = result[
    [
        "tarih",
        "istasyon",
        "sicaklik_ort_c",
        "bagil_nem_ort_yuzde",
        "yagis_toplam_mm",
        "basinc_ort_hpa",
        "ruzgar_u_ort_ms",
        "ruzgar_v_ort_ms",
        "ruzgar_hizi_ort_ms",
        "saat_sayisi"
    ]
]


# =========================================================
# 19. SIRALA
# =========================================================

result = result.sort_values(
    [
        "istasyon",
        "tarih"
    ]
).reset_index(
    drop=True
)


# =========================================================
# 20. KALİTE KONTROLLERİ
# =========================================================

print(
    "\n=============================="
)

print(
    "ERA5 2024-2025 GUNLUK"
)

print(
    "=============================="
)


# ---------------------------------------------------------
# Satır sayısı
# ---------------------------------------------------------

expected_rows = (
    731
    * 8
)


print(
    "\nSatir sayisi:"
)

print(
    len(result)
)


print(
    "\nBeklenen satir sayisi:"
)

print(
    expected_rows
)


# ---------------------------------------------------------
# İstasyon başına gün sayısı
# ---------------------------------------------------------

print(
    "\nIstasyon basina gun sayisi:"
)

print(
    result
    .groupby(
        "istasyon"
    )
    .size()
)


# ---------------------------------------------------------
# Tarih aralığı
# ---------------------------------------------------------

print(
    "\nTarih araligi:"
)

print(
    result[
        "tarih"
    ].min()
)

print(
    result[
        "tarih"
    ].max()
)


# ---------------------------------------------------------
# Duplicate istasyon + tarih kontrolü
# ---------------------------------------------------------

duplicate_rows = (
    result
    .duplicated(
        subset=[
            "istasyon",
            "tarih"
        ]
    )
    .sum()
)


print(
    "\nDuplicate istasyon-tarih sayisi:"
)

print(
    duplicate_rows
)


# ---------------------------------------------------------
# NaN kontrolü
# ---------------------------------------------------------

print(
    "\nNaN sayilari:"
)

print(
    result
    .isna()
    .sum()
)


# ---------------------------------------------------------
# Saat kontrolü
# ---------------------------------------------------------

print(
    "\nSaat sayisi dagilimi:"
)

print(
    result[
        "saat_sayisi"
    ]
    .value_counts()
)


# ---------------------------------------------------------
# Negatif yağış
# ---------------------------------------------------------

negative_precip = (
    result[
        "yagis_toplam_mm"
    ]
    < -0.001
).sum()


print(
    "\nNegatif yagis sayisi:"
)

print(
    negative_precip
)


# ---------------------------------------------------------
# Bağıl nem fiziksel kontrol
# ---------------------------------------------------------

print(
    "\nBagil nem min/max:"
)

print(
    result[
        "bagil_nem_ort_yuzde"
    ].min()
)

print(
    result[
        "bagil_nem_ort_yuzde"
    ].max()
)


# ---------------------------------------------------------
# Meteoroloji genel özet
# ---------------------------------------------------------

print(
    "\nMeteoroloji genel ozet:"
)

print(
    result[
        [
            "sicaklik_ort_c",
            "bagil_nem_ort_yuzde",
            "yagis_toplam_mm",
            "basinc_ort_hpa",
            "ruzgar_hizi_ort_ms"
        ]
    ]
    .describe()
)


# =========================================================
# 21. KRİTİK ASSERT KONTROLLERİ
# =========================================================

assert (
    len(result)
    == expected_rows
), (
    f"Satir sayisi beklenenden farkli: "
    f"{len(result)} != {expected_rows}"
)


assert (
    duplicate_rows
    == 0
), (
    "Duplicate istasyon-tarih kaydi bulundu."
)


assert (
    result
    .isna()
    .sum()
    .sum()
    == 0
), (
    "Meteoroloji tablosunda NaN bulundu."
)


assert (
    negative_precip
    == 0
), (
    "Negatif yagis bulundu."
)


# =========================================================
# 22. CSV KAYDET
# =========================================================

result.to_csv(
    output_file,
    index=False
)


print(
    "\n=============================="
)

print(
    "BASARILI"
)

print(
    "=============================="
)


print(
    "\nKaydedildi:"
)

print(
    output_file
)


print(
    "\nToplam satir:"
)

print(
    len(result)
)