from pathlib import Path
import pandas as pd

# ==============================
# PROJE YOLLARI
# ==============================

PROJECT_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_DIR / "data" / "pm10" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "pm10" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

excel_dosyalari = sorted(RAW_DIR.glob("*.xlsx"))

tum_gunluk_veriler = []

print("Bulunan Excel dosyası:", len(excel_dosyalari))


# ==============================
# HER EXCEL DOSYASINI İŞLE
# ==============================

for dosya in excel_dosyalari:

    dosya_adi = dosya.stem

    # Örnek:
    # alanya24 -> istasyon = alanya
    # alanya24 -> yil = 2024

    yil_kisa = dosya_adi[-2:]
    yil = 2000 + int(yil_kisa)

    istasyon = dosya_adi[:-2]

    # Excel'i oku
    df = pd.read_excel(dosya)

    # Tarih dışındaki sütunu PM10 sütunu kabul ediyoruz
    pm10_sutunu = [
        col for col in df.columns
        if col != "Tarih"
    ][0]

    # ==============================
    # TARİH TEMİZLİĞİ
    # ==============================

    df["Tarih"] = pd.to_datetime(
        df["Tarih"],
        errors="coerce"
    )

    # Tarih olmayan satırları çıkar
    # Örneğin birim satırı gibi
    df = df[
        df["Tarih"].notna()
    ].copy()


    # ==============================
    # PM10 SAYISAL DÖNÜŞÜM
    # ==============================

    df["pm10"] = (
        df[pm10_sutunu]
        .astype(str)
        .str.replace(",", ".", regex=False)
    )

    df["pm10"] = pd.to_numeric(
        df["pm10"],
        errors="coerce"
    )


    # ==============================
    # PM10 KALİTE KONTROLÜ
    # ==============================

    # Resmî geçersiz kod
    df.loc[
        df["pm10"] == 995,
        "pm10"
    ] = pd.NA

    # Negatif PM10 değerlerini geçersiz kabul et
    df.loc[
        df["pm10"] < 0,
        "pm10"
    ] = pd.NA

    # QC sırasında incelenen özel anomali:
    # Antalya Trafik
    # 16.04.2025 12:00:56
    # PM10 = 0.00
    #
    # Sadece bu tek kayıt geçersiz kabul ediliyor.
    # Bütün 0 değerlerini otomatik silmiyoruz.

    anomali_maskesi = (
        (istasyon == "trafik")
        & (
            df["Tarih"]
            == pd.Timestamp("2025-04-16 12:00:56")
        )
    )

    df.loc[
        anomali_maskesi,
        "pm10"
    ] = pd.NA


    # ==============================
    # GÜNLÜK TOPLULAŞTIRMA
    # ==============================

    # Saat bilgisinden günü çıkar
    df["gun"] = df["Tarih"].dt.normalize()

    # Her gün için:
    # - kaç geçerli PM10 saati var?
    # - günlük ortalama nedir?
    gunluk = (
        df.groupby("gun")
        .agg(
            gecerli_saat=("pm10", "count"),
            pm10_gunluk=("pm10", "mean")
        )
    )


    # ==============================
    # EKSİK GÜNLERİ TAMAMLA
    # ==============================

    # O yılın bütün günlerini oluştur
    tam_tarih_araligi = pd.date_range(
        start=f"{yil}-01-01",
        end=f"{yil}-12-31",
        freq="D"
    )

    # Dosyada hiç bulunmayan günleri de tabloya ekle
    gunluk = gunluk.reindex(
        tam_tarih_araligi
    )

    gunluk.index.name = "tarih"

    # Hiç ölçüm olmayan günlerde
    # geçerli saat sayısı = 0
    gunluk["gecerli_saat"] = (
        gunluk["gecerli_saat"]
        .fillna(0)
        .astype(int)
    )


    # ==============================
    # 18 SAAT KALİTE KURALI
    # ==============================

    gunluk["gecerli_gun"] = (
        gunluk["gecerli_saat"] >= 18
    )

    # 18 saatten az geçerli ölçüm varsa
    # günlük PM10 kullanılmayacak
    gunluk.loc[
        ~gunluk["gecerli_gun"],
        "pm10_gunluk"
    ] = pd.NA


    # ==============================
    # İSTASYON VE YIL BİLGİSİ
    # ==============================

    gunluk["istasyon"] = istasyon
    gunluk["yil"] = yil

    gunluk = gunluk.reset_index()

    tum_gunluk_veriler.append(
        gunluk
    )


    # ==============================
    # DOSYA ÖZETİ
    # ==============================

    print(
        f"{dosya.name} | "
        f"Geçerli gün: "
        f"{gunluk['gecerli_gun'].sum()} | "
        f"Geçersiz gün: "
        f"{(~gunluk['gecerli_gun']).sum()}"
    )


# ==============================
# BÜTÜN İSTASYONLARI BİRLEŞTİR
# ==============================

tum_gunluk = pd.concat(
    tum_gunluk_veriler,
    ignore_index=True
)


# ==============================
# SÜTUN SIRASI
# ==============================

tum_gunluk = tum_gunluk[
    [
        "tarih",
        "istasyon",
        "yil",
        "pm10_gunluk",
        "gecerli_saat",
        "gecerli_gun"
    ]
]


# ==============================
# CSV KAYDET
# ==============================

cikti_dosyasi = (
    PROCESSED_DIR
    / "pm10_gunluk_tum.csv"
)

tum_gunluk.to_csv(
    cikti_dosyasi,
    index=False,
    encoding="utf-8-sig"
)


# ==============================
# TOPLAM ÖZET
# ==============================

print("\n==============================")
print("TOPLAM ÖZET")
print("==============================")

print(
    "Toplam satır:",
    len(tum_gunluk)
)

print(
    "Geçerli station-day:",
    tum_gunluk["gecerli_gun"].sum()
)

print(
    "Geçersiz station-day:",
    (~tum_gunluk["gecerli_gun"]).sum()
)

print(
    "Kaydedildi:",
    cikti_dosyasi
)


# ==============================
# ÖZEL QC DOĞRULAMASI
# ==============================

print("\n==============================")
print("QC DOĞRULAMA")
print("==============================")

kontrol = tum_gunluk[
    (
        (tum_gunluk["istasyon"] == "trafik")
        & (
            tum_gunluk["tarih"]
            == pd.Timestamp("2025-04-16")
        )
    )
]

print(
    kontrol[
        [
            "tarih",
            "istasyon",
            "pm10_gunluk",
            "gecerli_saat",
            "gecerli_gun"
        ]
    ].to_string(index=False)
)