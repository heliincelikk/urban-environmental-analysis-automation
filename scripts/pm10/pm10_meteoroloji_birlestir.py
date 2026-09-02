from pathlib import Path

import pandas as pd


# =========================================================
# PROJE YOLLARI
# =========================================================

PROJECT_DIR = Path(__file__).resolve().parents[2]

processed_dir = (
    PROJECT_DIR
    / "data"
    / "pm10"
    / "processed"
)

pm10_file = (
    processed_dir
    / "pm10_gunluk_tum.csv"
)

met_file = (
    processed_dir
    / "era5_istasyon_gunluk_2024_2025.csv"
)

output_file = (
    processed_dir
    / "pm10_meteoroloji_birlestirilmis.csv"
)


# =========================================================
# 1. DOSYALARI OKU
# =========================================================

print("\nDosyalar okunuyor...")

pm10 = pd.read_csv(
    pm10_file
)

met = pd.read_csv(
    met_file
)


print(
    f"PM10 satir sayisi: {len(pm10)}"
)

print(
    f"Meteoroloji satir sayisi: {len(met)}"
)


# =========================================================
# 2. TARİH FORMATLARINI EŞİTLE
# =========================================================

pm10["tarih"] = pd.to_datetime(
    pm10["tarih"]
)

met["tarih"] = pd.to_datetime(
    met["tarih"]
)


# =========================================================
# 3. İSTASYON İSİMLERİNİ STANDARTLAŞTIR
# =========================================================

pm10["istasyon"] = (
    pm10["istasyon"]
    .astype(str)
    .str.strip()
    .str.lower()
)

met["istasyon"] = (
    met["istasyon"]
    .astype(str)
    .str.strip()
    .str.lower()
)


# =========================================================
# 4. MERGE ÖNCESİ DUPLICATE KONTROLÜ
# =========================================================

pm10_duplicates = (
    pm10
    .duplicated(
        subset=[
            "tarih",
            "istasyon"
        ]
    )
    .sum()
)

met_duplicates = (
    met
    .duplicated(
        subset=[
            "tarih",
            "istasyon"
        ]
    )
    .sum()
)


print(
    "\nMerge oncesi duplicate kontrolu:"
)

print(
    f"PM10 duplicate: {pm10_duplicates}"
)

print(
    f"Meteoroloji duplicate: {met_duplicates}"
)


if pm10_duplicates != 0:

    raise ValueError(
        "PM10 tablosunda duplicate istasyon-tarih bulundu."
    )


if met_duplicates != 0:

    raise ValueError(
        "Meteoroloji tablosunda duplicate istasyon-tarih bulundu."
    )


# =========================================================
# 5. PM10 + METEOROLOJİ BİRLEŞTİR
# =========================================================

merged = pd.merge(

    pm10,

    met,

    on=[
        "tarih",
        "istasyon"
    ],

    how="left",

    validate="one_to_one",

    indicator=True

)


# =========================================================
# 6. EŞLEŞME KONTROLÜ
# =========================================================

print(
    "\nMerge sonucu:"
)

print(
    merged["_merge"]
    .value_counts()
)


unmatched_count = (
    merged["_merge"]
    != "both"
).sum()


print(
    "\nEslesmeyen satir sayisi:"
)

print(
    unmatched_count
)


if unmatched_count != 0:

    print(
        "\nEslesmeyen kayitlar:"
    )

    print(
        merged.loc[
            merged["_merge"] != "both",
            [
                "tarih",
                "istasyon"
            ]
        ].head(
            20
        )
    )

    raise ValueError(
        "PM10 ile meteoroloji tamamen eslesmedi."
    )


# Merge kontrol kolonu artık gerekmiyor
merged = merged.drop(
    columns=[
        "_merge"
    ]
)


# =========================================================
# 7. SATIR SAYISI KONTROLÜ
# =========================================================

expected_rows = 5848


print(
    "\nToplam satir:"
)

print(
    len(merged)
)


print(
    "\nBeklenen satir:"
)

print(
    expected_rows
)


if len(merged) != expected_rows:

    raise ValueError(
        f"Beklenen {expected_rows}, "
        f"elde edilen {len(merged)}."
    )


# =========================================================
# 8. PM10 GEÇERLİLİK KONTROLÜ
# =========================================================

valid_days = (
    merged[
        "gecerli_gun"
    ]
    .astype(bool)
    .sum()
)


invalid_days = (
    len(merged)
    - valid_days
)


print(
    "\nPM10 gecerli gun sayisi:"
)

print(
    valid_days
)


print(
    "\nPM10 gecersiz gun sayisi:"
)

print(
    invalid_days
)


# =========================================================
# 9. GEÇERLİ / GEÇERSİZ PM10 VE NaN KONTROLÜ
# =========================================================

valid_pm10_nan = (
    merged.loc[
        merged["gecerli_gun"] == True,
        "pm10_gunluk"
    ]
    .isna()
    .sum()
)


invalid_pm10_non_nan = (
    merged.loc[
        merged["gecerli_gun"] == False,
        "pm10_gunluk"
    ]
    .notna()
    .sum()
)


print(
    "\nGecerli gunlerde PM10 NaN sayisi:"
)

print(
    valid_pm10_nan
)


print(
    "\nGecersiz gunlerde PM10 degeri bulunan satir:"
)

print(
    invalid_pm10_non_nan
)


# =========================================================
# 10. METEOROLOJİ NaN KONTROLÜ
# =========================================================

met_columns = [

    "sicaklik_ort_c",

    "bagil_nem_ort_yuzde",

    "yagis_toplam_mm",

    "basinc_ort_hpa",

    "ruzgar_u_ort_ms",

    "ruzgar_v_ort_ms",

    "ruzgar_hizi_ort_ms"

]


print(
    "\nMeteoroloji NaN sayilari:"
)

print(
    merged[
        met_columns
    ]
    .isna()
    .sum()
)


meteorology_nan_total = (
    merged[
        met_columns
    ]
    .isna()
    .sum()
    .sum()
)


if meteorology_nan_total != 0:

    raise ValueError(
        "Birlesik tabloda meteoroloji NaN bulundu."
    )


# =========================================================
# 11. İSTASYON BAZINDA ÖZET
# =========================================================

station_summary = (
    merged
    .groupby(
        "istasyon"
    )
    .agg(

        toplam_gun=(
            "tarih",
            "count"
        ),

        gecerli_pm10_gun=(
            "gecerli_gun",
            "sum"
        ),

        pm10_ortalama=(
            "pm10_gunluk",
            "mean"
        )

    )
)


station_summary[
    "gecersiz_pm10_gun"
] = (
    station_summary[
        "toplam_gun"
    ]
    - station_summary[
        "gecerli_pm10_gun"
    ]
)


print(
    "\nIstasyon bazinda ozet:"
)

print(
    station_summary
)


# =========================================================
# 12. MODELDE KULLANILABİLECEK SATIR SAYISI
# =========================================================

model_data = merged[
    (
        merged["gecerli_gun"] == True
    )
    &
    (
        merged["pm10_gunluk"].notna()
    )
].copy()


print(
    "\nModelde kullanilabilecek satir:"
)

print(
    len(model_data)
)


# =========================================================
# 13. SON DUPLICATE KONTROLÜ
# =========================================================

final_duplicates = (
    merged
    .duplicated(
        subset=[
            "tarih",
            "istasyon"
        ]
    )
    .sum()
)


print(
    "\nFinal duplicate istasyon-tarih:"
)

print(
    final_duplicates
)


assert (
    final_duplicates == 0
), (
    "Birlesik tabloda duplicate bulundu."
)


# =========================================================
# 14. TARİHE GÖRE SIRALA
# =========================================================

merged = (
    merged
    .sort_values(
        [
            "istasyon",
            "tarih"
        ]
    )
    .reset_index(
        drop=True
    )
)


# =========================================================
# 15. KAYDET
# =========================================================

merged.to_csv(
    output_file,
    index=False
)


print(
    "\n=============================="
)

print(
    "PM10 + METEOROLOJI BIRLESTIRME BASARILI"
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
    len(merged)
)


print(
    "\nModel satiri:"
)

print(
    len(model_data)
)