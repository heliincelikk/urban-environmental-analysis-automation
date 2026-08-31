from pathlib import Path
import pandas as pd

# ==============================
# DOSYA YOLLARI
# ==============================

PROJECT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_DIR / "data" / "pm10" / "raw"

excel_dosyalari = sorted(RAW_DIR.glob("*.xlsx"))

tum_saatlik_veriler = []

print("Bulunan Excel dosyası:", len(excel_dosyalari))


# ==============================
# SAATLİK DOSYALARI BİRLEŞTİR
# ==============================

for dosya in excel_dosyalari:

    dosya_adi = dosya.stem

    yil_kisa = dosya_adi[-2:]
    yil = 2000 + int(yil_kisa)

    istasyon = dosya_adi[:-2]

    df = pd.read_excel(dosya)

    pm10_sutunu = [
        col for col in df.columns
        if col != "Tarih"
    ][0]

    df["Tarih"] = pd.to_datetime(
        df["Tarih"],
        errors="coerce"
    )

    df = df[
        df["Tarih"].notna()
    ].copy()

    df["pm10"] = (
        df[pm10_sutunu]
        .astype(str)
        .str.replace(",", ".", regex=False)
    )

    df["pm10"] = pd.to_numeric(
        df["pm10"],
        errors="coerce"
    )

    df["istasyon"] = istasyon
    df["yil"] = yil

    df = df[
        [
            "Tarih",
            "istasyon",
            "yil",
            "pm10"
        ]
    ]

    tum_saatlik_veriler.append(df)


tum_saatlik = pd.concat(
    tum_saatlik_veriler,
    ignore_index=True
)

print("\nToplam saatlik kayıt:", len(tum_saatlik))
print(
    "Geçerli PM10 kaydı:",
    tum_saatlik["pm10"].notna().sum()
)
print("\n==============================")
print("ŞÜPHELİ GÜNLERİN GÜNLÜK ETKİSİ")
print("==============================")

supheli_gunler = [
    ("serik", "2024-05-31"),
    ("kumluca", "2025-04-16")
]

for istasyon, tarih_str in supheli_gunler:

    tarih = pd.Timestamp(tarih_str)

    gun_verisi = tum_saatlik[
        (tum_saatlik["istasyon"] == istasyon)
        & (tum_saatlik["Tarih"].dt.date == tarih.date())
    ]

    gecerli_saat = gun_verisi["pm10"].notna().sum()

    print("\n--------------------------------")
    print(f"İstasyon: {istasyon.upper()}")
    print(f"Tarih: {tarih.date()}")
    print(f"Geçerli saat: {gecerli_saat}")

    if gecerli_saat >= 18:
        gunluk_ortalama = gun_verisi["pm10"].mean()

        print("Gün durumu: GEÇERLİ")
        print(f"Günlük PM10: {gunluk_ortalama:.2f}")

    else:
        print("Gün durumu: GEÇERSİZ")
        print("Günlük PM10: HESAPLANMADI")
        print("\n==============================")
print("EKSTREM DEĞERİN GÜNLÜK ORTALAMAYA ETKİSİ")
print("==============================")

supheli_gunler = [
    ("serik", "2024-05-31"),
    ("kumluca", "2025-04-16")
]

for istasyon, tarih_str in supheli_gunler:

    tarih = pd.Timestamp(tarih_str)

    gun_verisi = tum_saatlik[
        (tum_saatlik["istasyon"] == istasyon)
        & (tum_saatlik["Tarih"].dt.date == tarih.date())
    ].copy()

    gecerli = gun_verisi["pm10"].dropna()

    normal_ortalama = gecerli.mean()

    maksimum_deger = gecerli.max()

    maksimum_haric = gecerli[
        gecerli != maksimum_deger
    ]

    yeni_ortalama = maksimum_haric.mean()

    fark = normal_ortalama - yeni_ortalama

    print("\n--------------------------------")
    print(f"İstasyon: {istasyon.upper()}")
    print(f"Tarih: {tarih.date()}")
    print(f"Geçerli saat: {len(gecerli)}")
    print(f"En yüksek değer: {maksimum_deger:.2f}")
    print(f"Normal günlük ortalama: {normal_ortalama:.2f}")
    print(f"En yüksek değer çıkarılırsa: {yeni_ortalama:.2f}")
    print(f"Ortalamaya etkisi: +{fark:.2f}")
    print("\n==============================")
print("ÖZEL DEĞER KONTROLÜ")
print("==============================")

print(
    "995 kodu sayısı:",
    (tum_saatlik["pm10"] == 995).sum()
)

print(
    "0 değeri sayısı:",
    (tum_saatlik["pm10"] == 0).sum()
)

print(
    "Negatif değer sayısı:",
    (tum_saatlik["pm10"] < 0).sum()
)

print("\n0 OLAN KAYITLAR:")

sifirlar = tum_saatlik[
    tum_saatlik["pm10"] == 0
]

print(
    sifirlar[
        ["Tarih", "istasyon", "yil", "pm10"]
    ].to_string(index=False)
)
print("\n==============================")
print("TRAFİK 0 DEĞERİ KONTROLÜ")
print("==============================")

sifir_zamani = pd.Timestamp("2025-04-16 12:00:56")

# Aynı istasyonda ±3 saat
trafik_cevre = tum_saatlik[
    (tum_saatlik["istasyon"] == "trafik")
    & (tum_saatlik["Tarih"] >= sifir_zamani - pd.Timedelta("3h"))
    & (tum_saatlik["Tarih"] <= sifir_zamani + pd.Timedelta("3h"))
]

print("\nTRAFİK İSTASYONU ±3 SAAT:")
print(
    trafik_cevre[
        ["Tarih", "pm10"]
    ].to_string(index=False)
)

# Aynı saatte diğer istasyonlar
ayni_saat = tum_saatlik[
    tum_saatlik["Tarih"] == sifir_zamani
].sort_values("pm10", ascending=False)

print("\nAYNI SAATTE TÜM İSTASYONLAR:")
print(
    ayni_saat[
        ["istasyon", "pm10"]
    ].to_string(index=False)
)
print("\n==============================")
print("TRAFİK 0 DEĞERİNİN GÜNLÜK ETKİSİ")
print("==============================")

tarih = pd.Timestamp("2025-04-16")

gun = tum_saatlik[
    (tum_saatlik["istasyon"] == "trafik")
    & (tum_saatlik["Tarih"].dt.date == tarih.date())
].copy()

# Mevcut hali
mevcut = gun["pm10"].dropna()

print("0 dahil geçerli saat:", len(mevcut))
print("0 dahil günlük ortalama:", round(mevcut.mean(), 2))

# 0 değerini geçersiz kabul ediyoruz
duzeltilmis = gun["pm10"].replace(0, pd.NA)
duzeltilmis = pd.to_numeric(
    duzeltilmis,
    errors="coerce"
).dropna()

print("0 çıkarılmış geçerli saat:", len(duzeltilmis))

if len(duzeltilmis) >= 18:
    print("Gün durumu: GEÇERLİ")
    print(
        "0 çıkarılmış günlük ortalama:",
        round(duzeltilmis.mean(), 2)
    )
else:
    print("Gün durumu: GEÇERSİZ")
    print("Günlük PM10: HESAPLANMADI")