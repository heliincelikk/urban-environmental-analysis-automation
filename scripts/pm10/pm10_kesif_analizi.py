from pathlib import Path

import pandas as pd


# =========================================================
# PROJE YOLLARI
# =========================================================

PROJECT_DIR = Path(__file__).resolve().parents[2]

input_file = (
    PROJECT_DIR
    / "data"
    / "pm10"
    / "processed"
    / "pm10_meteoroloji_birlestirilmis.csv"
)

output_dir = (
    PROJECT_DIR
    / "outputs"
    / "pm10"
)

output_dir.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# 1. VERİYİ OKU
# =========================================================

df = pd.read_csv(
    input_file
)

df["tarih"] = pd.to_datetime(
    df["tarih"]
)


print("\n==============================")
print("PM10 KESIF ANALIZI")
print("==============================")


print("\nTum veri satiri:")
print(len(df))


# =========================================================
# 2. SADECE GEÇERLİ PM10 GÜNLERİ
# =========================================================

model_df = df[
    (
        df["gecerli_gun"] == True
    )
    &
    (
        df["pm10_gunluk"].notna()
    )
].copy()


print("\nGecerli PM10 satiri:")
print(len(model_df))


# =========================================================
# 3. GENEL PM10 ÖZETİ
# =========================================================

print("\n==============================")
print("GENEL PM10 OZETI")
print("==============================")

print(
    model_df[
        "pm10_gunluk"
    ].describe(
        percentiles=[
            0.25,
            0.50,
            0.75,
            0.90,
            0.95,
            0.99
        ]
    )
)


# =========================================================
# 4. İSTASYON BAZINDA PM10
# =========================================================

station_summary = (
    model_df
    .groupby(
        "istasyon"
    )
    .agg(

        gun_sayisi=(
            "pm10_gunluk",
            "count"
        ),

        pm10_ortalama=(
            "pm10_gunluk",
            "mean"
        ),

        pm10_medyan=(
            "pm10_gunluk",
            "median"
        ),

        pm10_min=(
            "pm10_gunluk",
            "min"
        ),

        pm10_max=(
            "pm10_gunluk",
            "max"
        )

    )
    .sort_values(
        "pm10_ortalama",
        ascending=False
    )
)


print("\n==============================")
print("ISTASYON BAZINDA PM10")
print("==============================")

print(
    station_summary.round(2)
)


station_summary.to_csv(
    output_dir
    / "pm10_istasyon_ozet.csv"
)


# =========================================================
# 5. YIL BAZINDA PM10
# =========================================================

year_summary = (
    model_df
    .groupby(
        "yil"
    )
    .agg(

        gun_sayisi=(
            "pm10_gunluk",
            "count"
        ),

        pm10_ortalama=(
            "pm10_gunluk",
            "mean"
        ),

        pm10_medyan=(
            "pm10_gunluk",
            "median"
        ),

        pm10_max=(
            "pm10_gunluk",
            "max"
        )

    )
)


print("\n==============================")
print("YIL BAZINDA PM10")
print("==============================")

print(
    year_summary.round(2)
)


# =========================================================
# 6. MEVSİM OLUŞTUR
# =========================================================

def mevsim_bul(month):

    if month in [12, 1, 2]:
        return "kis"

    elif month in [3, 4, 5]:
        return "ilkbahar"

    elif month in [6, 7, 8]:
        return "yaz"

    else:
        return "sonbahar"


model_df["ay"] = (
    model_df[
        "tarih"
    ].dt.month
)

model_df["mevsim"] = (
    model_df[
        "ay"
    ].apply(
        mevsim_bul
    )
)


# =========================================================
# 7. MEVSİM BAZINDA PM10
# =========================================================

season_summary = (
    model_df
    .groupby(
        "mevsim"
    )
    .agg(

        gun_sayisi=(
            "pm10_gunluk",
            "count"
        ),

        pm10_ortalama=(
            "pm10_gunluk",
            "mean"
        ),

        pm10_medyan=(
            "pm10_gunluk",
            "median"
        ),

        pm10_max=(
            "pm10_gunluk",
            "max"
        )

    )
)


season_order = [
    "kis",
    "ilkbahar",
    "yaz",
    "sonbahar"
]


season_summary = (
    season_summary
    .reindex(
        season_order
    )
)


print("\n==============================")
print("MEVSIM BAZINDA PM10")
print("==============================")

print(
    season_summary.round(2)
)


season_summary.to_csv(
    output_dir
    / "pm10_mevsim_ozet.csv"
)


# =========================================================
# 8. METEOROLOJİ DEĞİŞKENLERİ
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


# =========================================================
# 9. PEARSON KORELASYONU
# =========================================================

pearson_columns = [
    "pm10_gunluk",
    *met_columns
]


pearson_corr = (
    model_df[
        pearson_columns
    ]
    .corr(
        method="pearson"
    )
)


print("\n==============================")
print("PM10 - METEOROLOJI PEARSON")
print("==============================")

print(
    pearson_corr[
        "pm10_gunluk"
    ]
    .sort_values(
        ascending=False
    )
    .round(3)
)


pearson_corr.to_csv(
    output_dir
    / "pm10_meteoroloji_pearson.csv"
)


# =========================================================
# 10. SPEARMAN KORELASYONU
# =========================================================

spearman_corr = (
    model_df[
        pearson_columns
    ]
    .corr(
        method="spearman"
    )
)


print("\n==============================")
print("PM10 - METEOROLOJI SPEARMAN")
print("==============================")

print(
    spearman_corr[
        "pm10_gunluk"
    ]
    .sort_values(
        ascending=False
    )
    .round(3)
)


spearman_corr.to_csv(
    output_dir
    / "pm10_meteoroloji_spearman.csv"
)


# =========================================================
# 11. EN YÜKSEK 20 PM10 GÜNÜ
# =========================================================

highest_pm10 = (
    model_df[
        [
            "tarih",
            "istasyon",
            "pm10_gunluk",
            "sicaklik_ort_c",
            "bagil_nem_ort_yuzde",
            "yagis_toplam_mm",
            "basinc_ort_hpa",
            "ruzgar_hizi_ort_ms"
        ]
    ]
    .sort_values(
        "pm10_gunluk",
        ascending=False
    )
    .head(
        20
    )
)


print("\n==============================")
print("EN YUKSEK 20 PM10 GUNU")
print("==============================")

print(
    highest_pm10.to_string(
        index=False
    )
)


highest_pm10.to_csv(
    output_dir
    / "pm10_en_yuksek_20_gun.csv",
    index=False
)


# =========================================================
# 12. İSTASYON + MEVSİM ÖZETİ
# =========================================================

station_season = (
    model_df
    .groupby(
        [
            "istasyon",
            "mevsim"
        ]
    )
    .agg(

        pm10_ortalama=(
            "pm10_gunluk",
            "mean"
        ),

        pm10_medyan=(
            "pm10_gunluk",
            "median"
        ),

        gun_sayisi=(
            "pm10_gunluk",
            "count"
        )

    )
    .reset_index()
)


station_season.to_csv(
    output_dir
    / "pm10_istasyon_mevsim_ozet.csv",
    index=False
)


# =========================================================
# 13. SONUÇ
# =========================================================

print("\n==============================")
print("KESIF ANALIZI TAMAMLANDI")
print("==============================")

print("\nOlusturulan dosyalar:")

print(
    output_dir
    / "pm10_istasyon_ozet.csv"
)

print(
    output_dir
    / "pm10_mevsim_ozet.csv"
)

print(
    output_dir
    / "pm10_meteoroloji_pearson.csv"
)

print(
    output_dir
    / "pm10_meteoroloji_spearman.csv"
)

print(
    output_dir
    / "pm10_en_yuksek_20_gun.csv"
)

print(
    output_dir
    / "pm10_istasyon_mevsim_ozet.csv"
)