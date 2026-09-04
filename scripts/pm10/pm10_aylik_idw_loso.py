import pandas as pd
import numpy as np
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

# =========================================================
# DOSYA YOLLARI
# =========================================================
MONTHLY_FILE = Path(
    "data/pm10/processed/pm10_aylik_ozet.csv"
)

STATION_FILE = Path(
    "data/pm10/processed/pm10_istasyonlar.csv"
)

OUTPUT_FILE = Path(
    "outputs/pm10/pm10_aylik_idw_p2_loso_sonuclar.csv"
)

PREDICTION_FILE = Path(
    "outputs/pm10/pm10_aylik_idw_p2_loso_tahminler.csv"
)

IDW_POWER = 2.0


# =========================================================
# HAVERSINE MESAFESİ
# =========================================================
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return R * c


# =========================================================
# IDW
# =========================================================
def idw_predict(
    target_lat,
    target_lon,
    sources,
    power=2.0
):
    weighted_sum = 0.0
    weight_sum = 0.0

    for _, row in sources.iterrows():

        distance = haversine_km(
            target_lat,
            target_lon,
            row["enlem"],
            row["boylam"]
        )

        # İstasyonlar farklı fiziksel konumlarda.
        # Yine de sıfır mesafeye karşı koruma.
        if distance == 0:
            return row["pm10_ortalama"]

        weight = 1.0 / (distance ** power)

        weighted_sum += (
            weight * row["pm10_ortalama"]
        )

        weight_sum += weight

    if weight_sum == 0:
        return np.nan

    return weighted_sum / weight_sum


# =========================================================
# METRİKLER
# =========================================================
def calculate_metrics(group):
    actual = group["gercek_pm10"].to_numpy()
    predicted = group["tahmin_pm10"].to_numpy()

    error = predicted - actual

    mae = np.mean(np.abs(error))

    rmse = np.sqrt(
        np.mean(error ** 2)
    )

    bias = np.mean(error)

    ss_res = np.sum(
        (actual - predicted) ** 2
    )

    ss_tot = np.sum(
        (actual - np.mean(actual)) ** 2
    )

    if ss_tot == 0:
        r2 = np.nan
    else:
        r2 = 1 - (
            ss_res / ss_tot
        )

    return pd.Series({
        "n": len(group),
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2,
        "Bias": bias
    })


# =========================================================
# VERİLERİ OKU
# =========================================================
monthly = pd.read_csv(MONTHLY_FILE)

stations = pd.read_csv(STATION_FILE)


# Sadece aylık QC'den geçen kayıtlar
valid = monthly[
    (monthly["aylik_gecerli"] == True)
    & monthly["pm10_ortalama"].notna()
].copy()


# =========================================================
# KOORDİNATLARI EKLE
# =========================================================
valid = valid.merge(
    stations[
        [
            "istasyon",
            "enlem",
            "boylam"
        ]
    ],
    on="istasyon",
    how="left"
)

if valid[
    ["enlem", "boylam"]
].isna().any().any():

    raise ValueError(
        "Bazı istasyon koordinatları eşleşmedi."
    )


# =========================================================
# AYLIK LOSO IDW
# =========================================================
predictions = []

for _, target in valid.iterrows():

    same_month = valid[
        valid["donem"]
        == target["donem"]
    ].copy()

    # Test istasyonunu kaynaklardan çıkar
    sources = same_month[
        same_month["istasyon"]
        != target["istasyon"]
    ].copy()

    if len(sources) == 0:
        continue

    prediction = idw_predict(
        target_lat=target["enlem"],
        target_lon=target["boylam"],
        sources=sources,
        power=IDW_POWER
    )

    predictions.append({
        "donem": target["donem"],
        "istasyon": target["istasyon"],
        "gercek_pm10": target["pm10_ortalama"],
        "tahmin_pm10": prediction,
        "hata": prediction
        - target["pm10_ortalama"],
        "kaynak_istasyon_sayisi": len(sources)
    })


pred = pd.DataFrame(predictions)


# =========================================================
# İSTASYON BAZINDA METRİKLER
# =========================================================
station_results = (
    pred
    .groupby("istasyon")
    .apply(
        calculate_metrics,
        include_groups=False
    )
    .reset_index()
)


# =========================================================
# TÜM VERİ İÇİN POOLED METRİK
# =========================================================
pooled = calculate_metrics(pred)

pooled_row = pd.DataFrame([{
    "istasyon": "POOLED",
    "n": pooled["n"],
    "MAE": pooled["MAE"],
    "RMSE": pooled["RMSE"],
    "R2": pooled["R2"],
    "Bias": pooled["Bias"]
}])


results = pd.concat(
    [station_results, pooled_row],
    ignore_index=True
)


# =========================================================
# KAYDET
# =========================================================
OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

results.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

pred.to_csv(
    PREDICTION_FILE,
    index=False,
    encoding="utf-8-sig"
)


# =========================================================
# ÇIKTI
# =========================================================
print("\n==============================")
print("AYLIK IDW LOSO — p=2")
print("==============================")

print(
    results.to_string(
        index=False
    )
)

print("\nKaynak istasyon sayısı:")
print(
    pred["kaynak_istasyon_sayisi"]
    .value_counts()
    .sort_index()
)

print(
    f"\nToplam doğrulanan "
    f"istasyon-ay: {len(pred)}"
)

print(
    f"\n[OK] Sonuçlar: {OUTPUT_FILE}"
)

print(
    f"[OK] Tahminler: {PREDICTION_FILE}"
)