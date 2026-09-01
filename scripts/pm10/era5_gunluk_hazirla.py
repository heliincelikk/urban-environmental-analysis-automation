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
    / "era5_istasyon_gunluk_test.csv"
)


# =========================================================
# 1. ERA5 DOSYALARINI AÇ
# =========================================================

buffer_file = (
    era5_dir
    / "era5_land_antalya_2023_12_31_buffer.nc"
)

january_file = (
    era5_dir
    / "era5_land_antalya_2024_01.nc"
)

ds_buffer = xr.open_dataset(buffer_file)

ds_january = xr.open_dataset(january_file)


# =========================================================
# 2. ZAMAN EKSENİNDE BİRLEŞTİR
# =========================================================

ds = xr.concat(
    [
        ds_buffer,
        ds_january
    ],
    dim="valid_time"
)

ds = ds.sortby(
    "valid_time"
)


# =========================================================
# 3. UTC VE TÜRKİYE YEREL SAATİ
# =========================================================

utc_time = pd.to_datetime(
    ds["valid_time"].values
)

# Türkiye = UTC+3
local_time = (
    utc_time
    + pd.to_timedelta(
        3,
        unit="h"
    )
)


# =========================================================
# 4. DOĞRULANMIŞ İSTASYON-GRID EŞLEŞMESİNİ OKU
# =========================================================

mapping = pd.read_csv(
    mapping_file
)

all_station_data = []


# =========================================================
# 5. HER İSTASYON İÇİN METEOROLOJİ VERİSİNİ HAZIRLA
# =========================================================

for _, row in mapping.iterrows():

    station_name = row["istasyon"]

    era5_lat = float(
        row["era5_enlem"]
    )

    era5_lon = float(
        row["era5_boylam"]
    )


    # -----------------------------------------------------
    # Daha önce doğruladığımız ERA5 grid hücresini seçiyoruz.
    #
    # Buradaki method="nearest",
    # istasyon için yeniden nearest aramak amacıyla değil,
    # NetCDF içindeki çok küçük floating-point farklarını
    # çözmek amacıyla kullanılıyor.
    # -----------------------------------------------------

    point = ds.sel(
        latitude=era5_lat,
        longitude=era5_lon,
        method="nearest",
        tolerance=0.001
    )


    # =====================================================
    # 6. SICAKLIK VE ÇİY NOKTASI
    # =====================================================

    # Kelvin -> Celsius
    sicaklik_c = (
        point["t2m"].values
        - 273.15
    )

    ciy_noktasi_c = (
        point["d2m"].values
        - 273.15
    )


    # =====================================================
    # 7. BAĞIL NEM
    # =====================================================

    # Doygun buhar basıncı - sıcaklık
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


    # Doygun buhar basıncı - çiy noktası
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


    # Bağıl nem (%)
    bagil_nem = (
        100
        * es_td
        / es_t
    )


    # =====================================================
    # 8. RÜZGAR HIZI
    # =====================================================

    # Önce her saatin gerçek rüzgar hızını hesaplıyoruz.
    #
    # speed = sqrt(u^2 + v^2)
    #
    # Daha sonra günlük ortalaması alınacak.
    ruzgar_hizi = np.sqrt(
        point["u10"].values ** 2
        + point["v10"].values ** 2
    )


    # =====================================================
    # 9. SAATLİK METEOROLOJİ TABLOSU
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

        # Surface pressure
        # Pascal -> hPa
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


    # Türkiye yerel tarihini oluştur
    hourly["tarih"] = (
        hourly["local_time"]
        .dt.date
    )


    # =====================================================
    # 10. SICAKLIK / NEM / BASINÇ / RÜZGAR
    #     GÜNLÜK ÖZETİ
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
    # 11. SADECE TAM 24 SAATLİK YEREL GÜNLERİ TUT
    # =====================================================

    daily = daily[
        daily["saat_sayisi"] == 24
    ].copy()


    # =====================================================
    # 12. GÜNLÜK YAĞIŞ HESABI
    # =====================================================

    # ERA5-Land total precipitation (tp)
    # birikimli bir değişkendir.
    #
    # Türkiye UTC+3 olduğu için:
    #
    # Yerel gün:
    # 00:00 -> 24:00
    #
    # UTC karşılığı:
    # önceki gün 21 UTC -> mevcut gün 21 UTC
    #
    # Formül:
    #
    # [tp(D 00) - tp(D-1 21)]
    # +
    # tp(D 21)
    #
    # tp birimi metre olduğu için
    # sonuç x1000 ile mm'ye çevrilir.


    tp_series = pd.Series(
        point["tp"].values,
        index=utc_time
    ).sort_index()


    precipitation_results = []


    for local_date in daily["tarih"]:

        day = pd.Timestamp(
            local_date
        )


        # Önceki gün 21 UTC
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


        # Mevcut gün 00 UTC
        current_00 = day


        # Mevcut gün 21 UTC
        current_21 = (
            day
            + pd.to_timedelta(
                21,
                unit="h"
            )
        )


        # Gerekli zamanlardan biri yoksa
        # o gün için yağışı NaN bırak
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


        # Önceki UTC gününün
        # 21 -> 24 aralığındaki yağışı
        part_1 = (
            tp_current_00
            - tp_previous_21
        )


        # Mevcut UTC gününün
        # 00 -> 21 aralığındaki yağışı
        part_2 = (
            tp_current_21
        )


        # Toplam yerel günlük yağış
        # metre -> mm
        precipitation_mm = (
            part_1
            + part_2
        ) * 1000


        precipitation_results.append(
            precipitation_mm
        )


    # Yağışı günlük tabloya ekle
    daily["yagis_toplam_mm"] = (
        precipitation_results
    )


    # İstasyon adını ekle
    daily["istasyon"] = (
        station_name
    )


    all_station_data.append(
        daily
    )


# =========================================================
# 13. TÜM İSTASYONLARI BİRLEŞTİR
# =========================================================

result = pd.concat(
    all_station_data,
    ignore_index=True
)


# =========================================================
# 14. KOLON SIRASI
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
# 15. KALİTE KONTROL
# =========================================================

print(
    "\n=============================="
)

print(
    "ERA5 GUNLUK TEST"
)

print(
    "=============================="
)


# İlk 16 satır
print(
    result
    .head(16)
    .to_string(
        index=False
    )
)


# ---------------------------------------------------------
# Satır sayısı
# ---------------------------------------------------------

print(
    "\nSatir sayisi:"
)

print(
    len(result)
)


# ---------------------------------------------------------
# Saat sayısı
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
# Bağıl nem kalite kontrolü
# ---------------------------------------------------------

print(
    "\nBagil nem araligi:"
)

print(
    result
    .groupby(
        "istasyon"
    )[
        "bagil_nem_ort_yuzde"
    ]
    .agg(
        [
            "min",
            "max",
            "mean"
        ]
    )
)


# ---------------------------------------------------------
# Rüzgar hızı kalite kontrolü
# ---------------------------------------------------------

print(
    "\nRuzgar hizi araligi:"
)

print(
    result
    .groupby(
        "istasyon"
    )[
        "ruzgar_hizi_ort_ms"
    ]
    .agg(
        [
            "min",
            "max",
            "mean"
        ]
    )
)


# ---------------------------------------------------------
# Yağış kalite kontrolü
# ---------------------------------------------------------

print(
    "\nYagis araligi:"
)

print(
    result
    .groupby(
        "istasyon"
    )[
        "yagis_toplam_mm"
    ]
    .agg(
        [
            "min",
            "max",
            "mean",
            "sum"
        ]
    )
)


# ---------------------------------------------------------
# Negatif yağış kontrolü
# ---------------------------------------------------------

print(
    "\nNegatif yagis sayisi:"
)

print(
    (
        result[
            "yagis_toplam_mm"
        ]
        < -0.001
    )
    .sum()
)


# =========================================================
# 16. CSV OLARAK KAYDET
# =========================================================

result.to_csv(
    output_file,
    index=False
)


print(
    "\nKaydedildi:"
)

print(
    output_file
)