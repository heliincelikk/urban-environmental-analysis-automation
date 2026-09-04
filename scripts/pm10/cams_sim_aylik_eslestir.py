import pandas as pd
import numpy as np
from pathlib import Path

# =========================================================
# DOSYALAR
# =========================================================
SIM_FILE = Path(
    "data/pm10/processed/pm10_meteoroloji_birlestirilmis.csv"
)

CAMS_DAILY_FILE = Path(
    "data/pm10/processed/cams_istasyon_gunluk_2024_2025.csv"
)

OUTPUT_DAILY = Path(
    "data/pm10/processed/cams_sim_gunluk_eslestirilmis.csv"
)

OUTPUT_MONTHLY = Path(
    "data/pm10/processed/cams_sim_aylik_eslestirilmis.csv"
)


# =========================================================
# VERİLERİ OKU
# =========================================================
sim = pd.read_csv(SIM_FILE)
cams = pd.read_csv(CAMS_DAILY_FILE)

sim["tarih"] = pd.to_datetime(sim["tarih"])
cams["tarih_tr"] = pd.to_datetime(cams["tarih_tr"])


# =========================================================
# SADECE ÇALIŞMA DÖNEMİ
# =========================================================
sim = sim[
    (sim["tarih"] >= "2024-01-01")
    & (sim["tarih"] <= "2025-12-31")
].copy()

cams = cams[
    (cams["tarih_tr"] >= "2024-01-01")
    & (cams["tarih_tr"] <= "2025-12-31")
].copy()


# =========================================================
# SİM'DE GEÇERLİ GÜNLER
# =========================================================
sim_valid = sim[
    (sim["gecerli_gun"] == True)
    & (sim["pm10_gunluk"].notna())
].copy()


# =========================================================
# CAMS'TE YALNIZCA TAM 24 SAATLİK GÜNLER
# =========================================================
cams_valid = cams[
    (cams["cams_saat_sayisi"] == 24)
    & (cams["pm10_cams_gunluk"].notna())
].copy()


# =========================================================
# AYNI İSTASYON + AYNI GÜN EŞLEŞTİR
# =========================================================
merged = sim_valid.merge(
    cams_valid[
        [
            "istasyon",
            "tarih_tr",
            "cams_saat_sayisi",
            "pm10_cams_gunluk"
        ]
    ],
    left_on=["istasyon", "tarih"],
    right_on=["istasyon", "tarih_tr"],
    how="inner"
)


# =========================================================
# AY BİLGİSİ
# =========================================================
merged["donem"] = (
    merged["tarih"]
    .dt.strftime("%Y-%m")
)

merged["gun_sayisi_ay"] = (
    merged["tarih"]
    .dt.days_in_month
)


# =========================================================
# GÜNLÜK EŞLEŞMİŞ DOSYA
# =========================================================
OUTPUT_DAILY.parent.mkdir(
    parents=True,
    exist_ok=True
)

merged.to_csv(
    OUTPUT_DAILY,
    index=False,
    encoding="utf-8-sig"
)


# =========================================================
# AYLIK:
# SİM VE CAMS AYNI GÜNLER ÜZERİNDEN ORTALANIYOR
# =========================================================
monthly = (
    merged
    .groupby(
        ["istasyon", "donem"],
        as_index=False
    )
    .agg(
        eslesen_gun=("tarih", "count"),
        gun_sayisi_ay=("gun_sayisi_ay", "first"),
        pm10_sim_aylik=("pm10_gunluk", "mean"),
        pm10_cams_aylik=("pm10_cams_gunluk", "mean")
    )
)

monthly["kapsama_yuzde"] = (
    100
    * monthly["eslesen_gun"]
    / monthly["gun_sayisi_ay"]
)

# Aynı %75 aylık çalışma kriterimiz
monthly["aylik_gecerli"] = (
    monthly["kapsama_yuzde"] >= 75
)


# =========================================================
# HATA METRİKLERİ İÇİN FARK
# =========================================================
monthly["hata"] = (
    monthly["pm10_cams_aylik"]
    - monthly["pm10_sim_aylik"]
)

monthly["mutlak_hata"] = (
    monthly["hata"].abs()
)

monthly.to_csv(
    OUTPUT_MONTHLY,
    index=False,
    encoding="utf-8-sig"
)


# =========================================================
# KONTROLLER
# =========================================================
valid_monthly = monthly[
    monthly["aylik_gecerli"]
].copy()

print("\n==============================")
print("CAMS - SİM AYLIK EŞLEŞTİRME")
print("==============================")

print(f"SİM geçerli günlük kayıt : {len(sim_valid)}")
print(f"CAMS tam günlük kayıt     : {len(cams_valid)}")
print(f"Eşleşen günlük kayıt      : {len(merged)}")

print(f"\nToplam istasyon-ay        : {len(monthly)}")
print(
    f"Geçerli istasyon-ay       : "
    f"{len(valid_monthly)}"
)

print(
    f"İstasyon sayısı           : "
    f"{valid_monthly['istasyon'].nunique()}"
)

print(
    f"Dönem sayısı              : "
    f"{valid_monthly['donem'].nunique()}"
)

print("\nGeçersiz aylar:")
print(
    monthly.loc[
        ~monthly["aylik_gecerli"],
        [
            "istasyon",
            "donem",
            "eslesen_gun",
            "gun_sayisi_ay",
            "kapsama_yuzde"
        ]
    ].to_string(index=False)
)

print("\nCAMS aylık PM10 özeti:")
print(
    valid_monthly["pm10_cams_aylik"].describe()
)

print("\nSİM aylık PM10 özeti:")
print(
    valid_monthly["pm10_sim_aylik"].describe()
)

print(
    f"\n[OK] Günlük çıktı: {OUTPUT_DAILY}"
)

print(
    f"[OK] Aylık çıktı : {OUTPUT_MONTHLY}"
)