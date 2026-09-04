import pandas as pd
from pathlib import Path

INPUT_FILE = Path("data/pm10/processed/pm10_gunluk_tum.csv")
OUTPUT_FILE = Path("data/pm10/processed/pm10_aylik_ozet.csv")

MIN_COVERAGE = 75.0


# ==============================
# VERİYİ OKU
# ==============================
df = pd.read_csv(INPUT_FILE)

df["tarih"] = pd.to_datetime(df["tarih"])

# İstasyon isimleri
stations = sorted(df["istasyon"].dropna().unique())

# Çalışma dönemi
periods = pd.period_range(
    start="2024-01",
    end="2025-12",
    freq="M"
)


# ==============================
# TAM İSTASYON × AY TABLOSU
# ==============================
calendar = pd.MultiIndex.from_product(
    [stations, periods],
    names=["istasyon", "period"]
).to_frame(index=False)

calendar["yil"] = calendar["period"].dt.year
calendar["ay"] = calendar["period"].dt.month
calendar["donem"] = calendar["period"].astype(str)

calendar["aydaki_gun"] = (
    calendar["period"]
    .dt.to_timestamp()
    .dt.days_in_month
)


# ==============================
# GEÇERLİ GÜNLER
# ==============================
valid = df[
    (df["gecerli_gun"] == True) &
    (df["pm10_gunluk"].notna())
].copy()

valid["yil"] = valid["tarih"].dt.year
valid["ay"] = valid["tarih"].dt.month


# ==============================
# AYLIK PM10 İSTATİSTİKLERİ
# ==============================
monthly_stats = (
    valid
    .groupby(
        ["istasyon", "yil", "ay"],
        as_index=False
    )
    .agg(
        gecerli_gun=("pm10_gunluk", "count"),
        pm10_ortalama=("pm10_gunluk", "mean"),
        pm10_medyan=("pm10_gunluk", "median"),
        pm10_min=("pm10_gunluk", "min"),
        pm10_max=("pm10_gunluk", "max")
    )
)


# ==============================
# TAM TAKVİMLE BİRLEŞTİR
# ==============================
monthly = calendar.merge(
    monthly_stats,
    on=["istasyon", "yil", "ay"],
    how="left"
)

# Hiç geçerli günü olmayan ay → 0
monthly["gecerli_gun"] = (
    monthly["gecerli_gun"]
    .fillna(0)
    .astype(int)
)

monthly["kapsama_yuzde"] = (
    monthly["gecerli_gun"]
    / monthly["aydaki_gun"]
    * 100
)

# %75 QC eşiği
monthly["aylik_gecerli"] = (
    monthly["kapsama_yuzde"] >= MIN_COVERAGE
)

monthly = monthly[
    [
        "donem",
        "istasyon",
        "yil",
        "ay",
        "gecerli_gun",
        "aydaki_gun",
        "kapsama_yuzde",
        "aylik_gecerli",
        "pm10_ortalama",
        "pm10_medyan",
        "pm10_min",
        "pm10_max"
    ]
]

monthly = monthly.sort_values(
    ["yil", "ay", "istasyon"]
).reset_index(drop=True)


# ==============================
# KAYDET
# ==============================
OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

monthly.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)


# ==============================
# KONTROLLER
# ==============================
print("\n==============================")
print("AYLIK PM10 QC")
print("==============================")

print(f"Toplam beklenen kayıt: {len(stations) * len(periods)}")
print(f"Toplam oluşan kayıt:   {len(monthly)}")
print(f"İstasyon sayısı:       {monthly['istasyon'].nunique()}")
print(f"Dönem sayısı:          {monthly['donem'].nunique()}")

print("\nGeçerli aylık kayıt:")
print(monthly["aylik_gecerli"].value_counts())

print("\n%75 altında kalan istasyon-aylar:")
print(
    monthly.loc[
        ~monthly["aylik_gecerli"],
        [
            "donem",
            "istasyon",
            "gecerli_gun",
            "aydaki_gun",
            "kapsama_yuzde"
        ]
    ]
    .sort_values(
        ["kapsama_yuzde", "donem"]
    )
    .to_string(index=False)
)

print(f"\n[OK] Kaydedildi: {OUTPUT_FILE}")