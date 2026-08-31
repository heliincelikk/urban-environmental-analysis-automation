import pandas as pd
from pathlib import Path

# Proje ana klasörü
PROJECT_DIR = Path(__file__).resolve().parents[2]

# Ham SİM verisi
dosya = PROJECT_DIR / "data" / "pm10" / "raw" / "alanya24.xlsx"

print("Dosya:", dosya)
print("Dosya var mı?:", dosya.exists())

# Excel dosyasını oku
df = pd.read_excel(dosya)

print("\n==============================")
print("SÜTUNLAR")
print("==============================")
print(df.columns.tolist())

print("\n==============================")
print("İLK 10 SATIR")
print("==============================")
print(df.head(10))

print("\n==============================")
print("VERİ BOYUTU")
print("==============================")
print("Satır:", len(df))
print("Sütun:", len(df.columns))

print("\n==============================")
print("VERİ TİPLERİ")
print("==============================")
print(df.dtypes)

print("\n==============================")
print("EKSİK DEĞERLER")
print("==============================")
print(df.isna().sum())