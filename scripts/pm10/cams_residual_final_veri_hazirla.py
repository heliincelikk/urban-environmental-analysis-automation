import pandas as pd
import numpy as np
from pathlib import Path

# =========================================================
# DOSYALAR
# =========================================================
INPUT_FILE = Path(
    "data/pm10/processed/cams_sim_gunluk_eslestirilmis.csv"
)

OUTPUT_FILE = Path(
    "data/pm10/processed/"
    "cams_residual_final_model_veri.csv"
)


# =========================================================
# VERİYİ OKU
# =========================================================
df = pd.read_csv(INPUT_FILE)

print("\n==============================")
print("GELEN SÜTUNLAR")
print("==============================")
print(list(df.columns))


# =========================================================
# TARİH
# =========================================================
if "tarih" not in df.columns:
    raise ValueError(
        "Beklenen 'tarih' sütunu bulunamadı."
    )

df["tarih"] = pd.to_datetime(
    df["tarih"]
)


# =========================================================
# GEREKLİ DEĞİŞKENLER
# =========================================================
required_cols = [
    "istasyon",
    "tarih",

    # Gerçek gözlem
    "pm10_gunluk",

    # CAMS
    "pm10_cams_gunluk",

    # ERA5-Land meteoroloji
    "sicaklik_ort_c",
    "bagil_nem_ort_yuzde",
    "yagis_toplam_mm",
    "basinc_ort_hpa",
    "ruzgar_u_ort_ms",
    "ruzgar_v_ort_ms",
]

missing = [
    c for c in required_cols
    if c not in df.columns
]

if missing:
    raise ValueError(
        f"Eksik gerekli sütunlar: {missing}"
    )


# =========================================================
# SADECE GEREKLİ KOLONLAR
# =========================================================
model_df = df[
    required_cols
].copy()


# =========================================================
# CAMS RESIDUAL
#
# Pozitif:
# SİM > CAMS
#
# Negatif:
# SİM < CAMS
# =========================================================
model_df["residual_sim_cams"] = (
    model_df["pm10_gunluk"]
    - model_df["pm10_cams_gunluk"]
)


# =========================================================
# MEVSİMSELLİK
#
# Gün-of-year'ı doğrudan 1...365 vermiyoruz.
# Döngüsel sin/cos kullanıyoruz.
#
# Böylece 31 Aralık ile 1 Ocak model açısından
# birbirinden çok uzak görünmüyor.
# =========================================================
model_df["gun_yil"] = (
    model_df["tarih"]
    .dt.dayofyear
)

angle = (
    2
    * np.pi
    * (model_df["gun_yil"] - 1)
    / 365.25
)

model_df["mevsim_sin"] = np.sin(angle)
model_df["mevsim_cos"] = np.cos(angle)


# =========================================================
# YIL / AY SADECE RAPORLAMA İÇİN
#
# Bunları predictor olarak kullanmayacağız.
# =========================================================
model_df["yil"] = (
    model_df["tarih"]
    .dt.year
)

model_df["donem"] = (
    model_df["tarih"]
    .dt.strftime("%Y-%m")
)


# =========================================================
# DUPLICATE KONTROLÜ
# =========================================================
duplicates = model_df.duplicated(
    subset=["istasyon", "tarih"]
).sum()

if duplicates != 0:
    raise RuntimeError(
        f"İstasyon-tarih duplicate bulundu: {duplicates}"
    )


# =========================================================
# EKSİK DEĞER KONTROLÜ
# =========================================================
predictor_cols = [
    "pm10_cams_gunluk",
    "sicaklik_ort_c",
    "bagil_nem_ort_yuzde",
    "yagis_toplam_mm",
    "basinc_ort_hpa",
    "ruzgar_u_ort_ms",
    "ruzgar_v_ort_ms",
    "mevsim_sin",
    "mevsim_cos",
]

critical_cols = (
    predictor_cols
    + [
        "pm10_gunluk",
        "residual_sim_cams"
    ]
)

missing_counts = (
    model_df[critical_cols]
    .isna()
    .sum()
)

if missing_counts.sum() != 0:

    print("\n[HATA] Eksik değerler:")
    print(
        missing_counts[
            missing_counts > 0
        ]
    )

    raise RuntimeError(
        "Final model veri setinde eksik değer var."
    )


# =========================================================
# İSTASYON BAŞINA KAYIT
# =========================================================
station_counts = (
    model_df
    .groupby("istasyon")
    .size()
    .sort_index()
)


# =========================================================
# RESIDUAL İSTASYON ÖZETİ
# =========================================================
residual_summary = (
    model_df
    .groupby("istasyon")
    ["residual_sim_cams"]
    .agg(
        [
            "count",
            "mean",
            "std",
            "median",
            "min",
            "max"
        ]
    )
)


# =========================================================
# KAYDET
# =========================================================
OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

model_df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)


# =========================================================
# SON KONTROLLER
# =========================================================
print("\n==============================")
print("FINAL RESIDUAL MODEL VERİSİ")
print("==============================")

print(
    f"Toplam kayıt       : {len(model_df)}"
)

print(
    f"İstasyon sayısı    : "
    f"{model_df['istasyon'].nunique()}"
)

print(
    f"Tarih başlangıcı   : "
    f"{model_df['tarih'].min()}"
)

print(
    f"Tarih bitişi       : "
    f"{model_df['tarih'].max()}"
)

print(
    f"Duplicate          : {duplicates}"
)

print(
    f"Eksik kritik değer : "
    f"{missing_counts.sum()}"
)

print("\nİstasyon başına kayıt:")
print(station_counts)

print("\nCAMS residual özeti:")
print(
    residual_summary.to_string(
        float_format=lambda x: f"{x:.3f}"
    )
)

print("\nPredictorlar:")
for col in predictor_cols:
    print(f" - {col}")

print(
    f"\n[OK] Kaydedildi: {OUTPUT_FILE}"
)