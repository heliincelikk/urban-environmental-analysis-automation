import pandas as pd
import os

# --------------------------------------------------
# DOSYALAR
# --------------------------------------------------

PM10_MET_FILE = (
    "data/pm10/processed/"
    "pm10_meteoroloji_birlestirilmis.csv"
)

BUILT_FILE = (
    "outputs/pm10/"
    "dynamic_world_quarterly_land_only_2024_2025.csv"
)

OUTPUT_FILE = (
    "data/pm10/processed/"
    "pm10_meteoroloji_built_birlestirilmis.csv"
)

# --------------------------------------------------
# VERILERI OKU
# --------------------------------------------------

pm10_met = pd.read_csv(PM10_MET_FILE)
built = pd.read_csv(BUILT_FILE)

# --------------------------------------------------
# ISTASYON BAZINDA STATIC BUILT MEDIAN
# --------------------------------------------------

built_static = (
    built
    .groupby("istasyon", as_index=False)
    ["built_land_only_mean"]
    .median()
    .rename(
        columns={
            "built_land_only_mean":
            "built_static_median"
        }
    )
)

print("=" * 70)
print("STATIC BUILT DEGERLERI")
print("=" * 70)

print(
    built_static
    .sort_values("built_static_median")
    .to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)

# --------------------------------------------------
# BIRLESTIR
# --------------------------------------------------

merged = pm10_met.merge(
    built_static,
    on="istasyon",
    how="left",
    validate="many_to_one"
)

# --------------------------------------------------
# KONTROLLER
# --------------------------------------------------

print()
print("=" * 70)
print("BIRLESTIRME KONTROLU")
print("=" * 70)

print(f"PM10+met satir sayisi : {len(pm10_met)}")
print(f"Birlesmis satir sayisi: {len(merged)}")

print(
    "Eksik built degeri   : "
    f"{merged['built_static_median'].isna().sum()}"
)

print(
    "Duplicate satir      : "
    f"{merged.duplicated().sum()}"
)

print()
print("Istasyon bazinda built kontrolu:")

print(
    merged
    .groupby("istasyon")["built_static_median"]
    .agg(["min", "max", "nunique"])
    .round(4)
    .to_string()
)

# --------------------------------------------------
# KAYDET
# --------------------------------------------------

os.makedirs(
    os.path.dirname(OUTPUT_FILE),
    exist_ok=True
)

merged.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

print()
print("=" * 70)
print("TAMAMLANDI")
print("=" * 70)

print(
    "Dosya kaydedildi:"
)

print(OUTPUT_FILE)