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

df = pd.read_csv(input_file)

df["tarih"] = pd.to_datetime(
    df["tarih"]
)


# =========================================================
# 2. SADECE GEÇERLİ PM10 GÜNLERİ
# =========================================================

df = df[
    (df["gecerli_gun"] == True)
    &
    (df["pm10_gunluk"].notna())
].copy()


print("\n==============================")
print("ISTASYON BAZLI KORELASYON")
print("==============================")

print("\nKullanilan toplam satir:")
print(len(df))


# =========================================================
# 3. METEOROLOJİ DEĞİŞKENLERİ
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
# 4. HER İSTASYONU AYRI İNCELE
# =========================================================

results = []


for station, station_df in df.groupby("istasyon"):

    print("\n==============================")
    print(station.upper())
    print("==============================")

    print("Gun sayisi:")
    print(len(station_df))


    # -----------------------------------------------------
    # Pearson
    # -----------------------------------------------------

    pearson = (
        station_df[
            ["pm10_gunluk", *met_columns]
        ]
        .corr(method="pearson")
        ["pm10_gunluk"]
    )


    # -----------------------------------------------------
    # Spearman
    # -----------------------------------------------------

    spearman = (
        station_df[
            ["pm10_gunluk", *met_columns]
        ]
        .corr(method="spearman")
        ["pm10_gunluk"]
    )


    print("\nPearson:")

    print(
        pearson
        .drop("pm10_gunluk")
        .sort_values(ascending=False)
        .round(3)
    )


    print("\nSpearman:")

    print(
        spearman
        .drop("pm10_gunluk")
        .sort_values(ascending=False)
        .round(3)
    )


    # -----------------------------------------------------
    # Sonuç tablosuna ekle
    # -----------------------------------------------------

    for variable in met_columns:

        results.append({

            "istasyon":
                station,

            "degisken":
                variable,

            "pearson":
                pearson[variable],

            "spearman":
                spearman[variable],

            "gun_sayisi":
                len(station_df)

        })


# =========================================================
# 5. SONUÇ TABLOSU
# =========================================================

result_df = pd.DataFrame(
    results
)


# =========================================================
# 6. KAYDET
# =========================================================

output_file = (
    output_dir
    / "pm10_istasyon_meteoroloji_korelasyon.csv"
)


result_df.to_csv(
    output_file,
    index=False
)


# =========================================================
# 7. DEĞİŞKENLERİN İSTASYONLAR ARASINDAKİ DAVRANIŞI
# =========================================================

print("\n==============================")
print("DEGISKEN BAZINDA ISTASYON ARALIKLARI")
print("==============================")


variable_summary = (
    result_df
    .groupby("degisken")
    .agg(

        pearson_min=(
            "pearson",
            "min"
        ),

        pearson_max=(
            "pearson",
            "max"
        ),

        pearson_ortalama=(
            "pearson",
            "mean"
        ),

        spearman_min=(
            "spearman",
            "min"
        ),

        spearman_max=(
            "spearman",
            "max"
        ),

        spearman_ortalama=(
            "spearman",
            "mean"
        )

    )
)


print(
    variable_summary.round(3)
)


variable_summary.to_csv(
    output_dir
    / "pm10_meteoroloji_istasyon_araliklari.csv"
)


print("\n==============================")
print("ANALIZ TAMAMLANDI")
print("==============================")

print("\nKaydedildi:")
print(output_file)