import pandas as pd
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]

girdi = PROJECT_DIR / "data" / "pm10" / "raw" / "alanya24.xlsx"
cikti = PROJECT_DIR / "data" / "pm10" / "processed" / "alanya24_gunluk.csv"

df = pd.read_excel(girdi)

# İlk sahte başlık satırını kaldır
df = df[df["Tarih"].notna()].copy()

# Sütun adını sadeleştir
df = df.rename(columns={"Antalya - Alanya": "pm10"})

# Virgüllü ondalıkları sayıya çevir
df["pm10"] = (
    df["pm10"]
    .astype(str)
    .str.replace(",", ".", regex=False)
)

df["pm10"] = pd.to_numeric(df["pm10"], errors="coerce")

print("\n==============================")
print("TEMİZLENMİŞ SAATLİK VERİ")
print("==============================")
print(df.head())

print("\nSatır sayısı:", len(df))
print("Eksik PM10:", df["pm10"].isna().sum())
print("Minimum PM10:", df["pm10"].min())
print("Maksimum PM10:", df["pm10"].max())

# Türkiye yerel tarihine göre gün oluştur
df["gun"] = df["Tarih"].dt.date

# Her gün için:
# - geçerli saat sayısı
# - günlük ortalama PM10
gunluk = (
    df.groupby("gun")
    .agg(
        gecerli_saat=("pm10", "count"),
        pm10_gunluk=("pm10", "mean")
    )
    .reset_index()
)

# Literatürde dayandırdığımız >=18 saat kuralı
gunluk["gecerli_gun"] = gunluk["gecerli_saat"] >= 18

print("\n==============================")
print("GÜNLÜK VERİ ÖZETİ")
print("==============================")
print(gunluk.head(10))

print("\nToplam gün:", len(gunluk))
print("Geçerli gün:", gunluk["gecerli_gun"].sum())
print("Geçersiz gün:", (~gunluk["gecerli_gun"]).sum())

# Sadece geçerli günleri kaydet
gunluk_gecerli = gunluk[gunluk["gecerli_gun"]].copy()

gunluk_gecerli.to_csv(cikti, index=False, encoding="utf-8-sig")

print("\nKaydedildi:", cikti)