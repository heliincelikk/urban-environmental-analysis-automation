import pandas as pd
import numpy as np
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

# =========================================================
# DOSYALAR
# =========================================================
INPUT_FILE = Path(
    "data/pm10/processed/cams_sim_aylik_eslestirilmis.csv"
)

STATION_FILE = Path(
    "data/pm10/processed/pm10_istasyonlar.csv"
)

OUTPUT_PRED = Path(
    "outputs/pm10/cams_residual_idw_aylik_loso_tahminler.csv"
)

OUTPUT_METRICS = Path(
    "outputs/pm10/cams_residual_idw_aylik_loso_metrikler.csv"
)

IDW_POWER = 2


# =========================================================
# HAVERSINE
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

    return R * 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )


# =========================================================
# IDW
# =========================================================
def idw_predict(
    target_lat,
    target_lon,
    source_df,
    value_col,
    power=2
):

    distances = []
    values = []

    for _, row in source_df.iterrows():

        d = haversine_km(
            target_lat,
            target_lon,
            row["enlem"],
            row["boylam"]
        )

        # Aynı koordinat teorik olarak olmamalı
        if d == 0:
            return row[value_col]

        distances.append(d)
        values.append(row[value_col])

    distances = np.array(distances)
    values = np.array(values)

    weights = 1 / (distances ** power)

    return np.sum(
        weights * values
    ) / np.sum(weights)


# =========================================================
# VERİ
# =========================================================
df = pd.read_csv(INPUT_FILE)

stations = pd.read_csv(STATION_FILE)

df = df[
    (df["aylik_gecerli"] == True)
    & df["pm10_sim_aylik"].notna()
    & df["pm10_cams_aylik"].notna()
].copy()

df = df.merge(
    stations[
        ["istasyon", "enlem", "boylam"]
    ],
    on="istasyon",
    how="left"
)

if df[["enlem", "boylam"]].isna().any().any():
    raise RuntimeError(
        "Bazı istasyon koordinatları eşleşmedi."
    )


# =========================================================
# RESIDUAL
# =========================================================
df["residual"] = (
    df["pm10_sim_aylik"]
    - df["pm10_cams_aylik"]
)


# =========================================================
# LEAVE-ONE-STATION-OUT
# =========================================================
predictions = []

for test_station in sorted(
    df["istasyon"].unique()
):

    print(
        f"[TEST İSTASYONU] {test_station}"
    )

    test_rows = df[
        df["istasyon"] == test_station
    ].copy()

    for _, test in test_rows.iterrows():

        # Aynı ayın diğer istasyonları
        sources = df[
            (df["donem"] == test["donem"])
            & (df["istasyon"] != test_station)
        ].copy()

        # Kritik:
        # test istasyonunun hiçbir SİM değeri kaynakta yok.
        if len(sources) == 0:
            continue

        residual_pred = idw_predict(
            target_lat=test["enlem"],
            target_lon=test["boylam"],
            source_df=sources,
            value_col="residual",
            power=IDW_POWER
        )

        final_pred = (
            test["pm10_cams_aylik"]
            + residual_pred
        )

        predictions.append({
            "istasyon": test_station,
            "donem": test["donem"],

            "pm10_sim_aylik":
                test["pm10_sim_aylik"],

            "pm10_cams_aylik":
                test["pm10_cams_aylik"],

            "residual_gercek":
                test["residual"],

            "residual_idw_tahmin":
                residual_pred,

            "pm10_final":
                final_pred,

            "kaynak_istasyon_sayisi":
                len(sources)
        })


pred = pd.DataFrame(predictions)


# =========================================================
# METRİK
# =========================================================
def metrics(group):

    y_true = group["pm10_sim_aylik"]
    y_pred = group["pm10_final"]

    error = y_pred - y_true

    return pd.Series({
        "n": len(group),

        "MAE": mean_absolute_error(
            y_true,
            y_pred
        ),

        "RMSE": np.sqrt(
            mean_squared_error(
                y_true,
                y_pred
            )
        ),

        "R2": r2_score(
            y_true,
            y_pred
        ),

        "Bias": error.mean()
    })


station_metrics = (
    pred
    .groupby("istasyon")
    .apply(
        metrics,
        include_groups=False
    )
    .reset_index()
)

pooled = metrics(pred)

pooled_df = pd.DataFrame([{
    "istasyon": "POOLED",
    **pooled.to_dict()
}])

results = pd.concat(
    [
        station_metrics,
        pooled_df
    ],
    ignore_index=True
)


# =========================================================
# KAYDET
# =========================================================
OUTPUT_PRED.parent.mkdir(
    parents=True,
    exist_ok=True
)

pred.to_csv(
    OUTPUT_PRED,
    index=False,
    encoding="utf-8-sig"
)

results.to_csv(
    OUTPUT_METRICS,
    index=False,
    encoding="utf-8-sig"
)


# =========================================================
# ÇIKTI
# =========================================================
print("\n==============================")
print("CAMS + RESIDUAL IDW")
print("==============================")

print(
    results.to_string(
        index=False,
        float_format=lambda x: f"{x:.3f}"
    )
)

print("\nKaynak istasyon sayıları:")
print(
    pred["kaynak_istasyon_sayisi"]
    .value_counts()
    .sort_index()
)

print(
    f"\n[OK] Tahminler: {OUTPUT_PRED}"
)

print(
    f"[OK] Metrikler: {OUTPUT_METRICS}"
)