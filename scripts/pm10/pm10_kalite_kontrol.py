import pandas as pd
from pathlib import Path

# Projenin ana klasörünü bul
PROJECT_DIR = Path(__file__).resolve().parents[2]

# Kullanıcıdan kontrol edilecek dosya adını al
dosya_adi = input("Kontrol edilecek dosya (örn. alanya25.xlsx): ")

# Dosya yolu
dosya = PROJECT_DIR / "data" / "pm10" / "raw" / dosya_adi

print("\nDosya yolu:", dosya)
print("Dosya var mı?:", dosya.exists())

# Excel dosyasını oku
df = pd.read_excel(dosya)

# SİM'in ilk birim satırını kaldır
df = df[df["Tarih"].notna()].copy()

# PM10 sütununu bul
pm10_sutunu = [col for col in df.columns if col != "Tarih"][0]

print("PM10 sütunu:", pm10_sutunu)

# Sütun adını sadeleştir
df = df.rename(columns={pm10_sutunu: "pm10_raw"})

print("\n==============================")
print("1. TARİH ARALIĞI")
print("==============================")
print("İlk kayıt :", df["Tarih"].min())
print("Son kayıt :", df["Tarih"].max())
print("Toplam satır:", len(df))

print("\n==============================")
print("2. KOPYA TIMESTAMP")
print("==============================")

duplicate_count = df["Tarih"].duplicated().sum()

print("Kopya tarih-saat sayısı:", duplicate_count)

# PM10 değerlerini sayıya çevirmeye hazırla
temiz = (
    df["pm10_raw"]
    .astype(str)
    .str.strip()
    .str.replace(",", ".", regex=False)
)

df["pm10"] = pd.to_numeric(temiz, errors="coerce")

print("\n==============================")
print("3. SAYISALA DÖNÜŞMEYEN PM10")
print("==============================")

problem = df[df["pm10"].isna()]

print("Toplam:", len(problem))

print("\nHam değerlerin dağılımı:")
print(
    problem["pm10_raw"]
    .astype(str)
    .value_counts(dropna=False)
    .head(20)
)

print("\nİlk 20 problemli kayıt:")
print(
    problem[["Tarih", "pm10_raw"]]
    .head(20)
    .to_string(index=False)
)

print("\n==============================")
print("4. SAYISAL PM10 KONTROLÜ")
print("==============================")

print(df["pm10"].describe())

print("\nNegatif PM10 sayısı:", (df["pm10"] < 0).sum())
print("Sıfır PM10 sayısı:", (df["pm10"] == 0).sum())

# Her kaydın gününü oluştur
df["gun"] = df["Tarih"].dt.date

# Gün başına geçerli PM10 saat sayısı
gunluk_saat = df.groupby("gun")["pm10"].count()

print("\n==============================")
print("5. GEÇERSİZ GÜNLER (<18 SAAT)")
print("==============================")

gecersiz = gunluk_saat[gunluk_saat < 18]

print("Geçersiz gün sayısı:", len(gecersiz))

if len(gecersiz) > 0:
    print(gecersiz.to_string())
else:
    print("Geçersiz gün yok.")

print("\n==============================")
print("6. GENEL ÖZET")
print("==============================")

print("Toplam saat:", len(df))
print("Geçerli PM10 saati:", df["pm10"].notna().sum())
print("Eksik/geçersiz PM10 saati:", df["pm10"].isna().sum())
print("Toplam gün:", len(gunluk_saat))
print("Geçerli gün:", (gunluk_saat >= 18).sum())
print("Geçersiz gün:", (gunluk_saat < 18).sum())

print("\nKontrol tamamlandı.")