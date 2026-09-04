import pandas as pd
import numpy as np
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

INPUT = Path(
    "data/pm10/processed/cams_residual_final_model_veri.csv"
)

OUTPUT_PRED = Path(
    "outputs/pm10/cams_met_residual_idw_final_tahminler.csv"
)

OUTPUT_METRICS = Path(
    "outputs/pm10/cams_met_residual_idw_final_metrikler.csv"
)

STATIONS = Path(
    "data/pm10/processed/pm10_istasyonlar.csv"
)

FEATURES = [
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

P = 2


def haversine(lat1, lon1, lat2, lon2):

    R = 6371.0088

    lat1, lon1, lat2, lon2 = map(
        radians,
        [lat1, lon1, lat2, lon2]
    )

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


def idw(target_lat, target_lon, source_df, value_col):

    distances = np.array([
        haversine(
            target_lat,
            target_lon,
            row["enlem"],
            row["boylam"]
        )
        for _, row in source_df.iterrows()
    ])

    values = source_df[value_col].to_numpy()

    weights = 1 / (distances ** P)

    return np.sum(
        weights * values
    ) / np.sum(weights)


# =========================================================
# VERİ
# =========================================================
df = pd.read_csv(
    INPUT,
    parse_dates=["tarih"]
)

coords = pd.read_csv(STATIONS)[
    ["istasyon", "enlem", "boylam"]
]

df = df.merge(
    coords,
    on="istasyon",
    how="left"
)


# =========================================================
# OUTER LOSO
# =========================================================
predictions = []

for test_station in sorted(
    df["istasyon"].unique()
):

    print(f"[OUTER TEST] {test_station}")

    train = df[
        df["istasyon"] != test_station
    ].copy()

    test = df[
        df["istasyon"] == test_station
    ].copy()

    # -----------------------------------------------------
    # 1. METEOROLOJİK RESIDUAL MODEL
    # -----------------------------------------------------
    model = Pipeline([
        ("scale", StandardScaler()),
        ("model", LinearRegression())
    ])

    model.fit(
        train[FEATURES],
        train["residual_sim_cams"]
    )

    # Training istasyonlarında meteorolojinin açıklayamadığı
    # kalan residual
    train["residual_met_pred"] = model.predict(
        train[FEATURES]
    )

    train["residual_remaining"] = (
        train["residual_sim_cams"]
        - train["residual_met_pred"]
    )

    # Test istasyonunda yalnız predictorlar kullanılıyor
    test["residual_met_pred"] = model.predict(
        test[FEATURES]
    )

    # -----------------------------------------------------
    # 2. AYNI GÜN DİĞER TRAINING İSTASYONLARINDAN
    #    KALAN RESIDUALI IDW İLE DÜZELT
    # -----------------------------------------------------
    for _, row in test.iterrows():

        same_day_sources = train[
            train["tarih"] == row["tarih"]
        ].copy()

        if len(same_day_sources) == 0:
            continue

        spatial_residual = idw(
            row["enlem"],
            row["boylam"],
            same_day_sources,
            "residual_remaining"
        )

        final_daily = (
            row["pm10_cams_gunluk"]
            + row["residual_met_pred"]
            + spatial_residual
        )

        predictions.append({
            "istasyon": test_station,
            "tarih": row["tarih"],

            "pm10_sim":
                row["pm10_gunluk"],

            "pm10_cams":
                row["pm10_cams_gunluk"],

            "residual_met_pred":
                row["residual_met_pred"],

            "residual_spatial_pred":
                spatial_residual,

            "pm10_final":
                final_daily,

            "kaynak_istasyon_sayisi":
                len(same_day_sources)
        })


pred = pd.DataFrame(predictions)

pred["tarih"] = pd.to_datetime(
    pred["tarih"]
)

pred["donem"] = (
    pred["tarih"]
    .dt.strftime("%Y-%m")
)

pred.to_csv(
    OUTPUT_PRED,
    index=False,
    encoding="utf-8-sig"
)


# =========================================================
# AYLIK DEĞERLER
#
# Aynı valid SİM günlerinden aylık ortalama.
# >= %75 kapsama.
# =========================================================
pred["gun_sayisi_ay"] = (
    pred["tarih"].dt.days_in_month
)

monthly = (
    pred
    .groupby(
        ["istasyon", "donem"],
        as_index=False
    )
    .agg(
        eslesen_gun=("tarih", "count"),
        gun_sayisi_ay=("gun_sayisi_ay", "first"),
        pm10_sim=("pm10_sim", "mean"),
        pm10_final=("pm10_final", "mean")
    )
)

monthly["kapsama"] = (
    100
    * monthly["eslesen_gun"]
    / monthly["gun_sayisi_ay"]
)

monthly = monthly[
    monthly["kapsama"] >= 75
].copy()


# =========================================================
# METRİK
# =========================================================
def metrics(g):

    y = g["pm10_sim"]
    p = g["pm10_final"]

    return pd.Series({
        "n": len(g),
        "MAE": mean_absolute_error(y, p),
        "RMSE": np.sqrt(
            mean_squared_error(y, p)
        ),
        "R2": r2_score(y, p),
        "Bias": (p - y).mean()
    })


station_metrics = (
    monthly
    .groupby("istasyon")
    .apply(
        metrics,
        include_groups=False
    )
    .reset_index()
)

pooled = metrics(monthly)

results = pd.concat(
    [
        station_metrics,
        pd.DataFrame([{
            "istasyon": "POOLED",
            **pooled.to_dict()
        }])
    ],
    ignore_index=True
)

OUTPUT_METRICS.parent.mkdir(
    parents=True,
    exist_ok=True
)

results.to_csv(
    OUTPUT_METRICS,
    index=False,
    encoding="utf-8-sig"
)


print("\n==============================")
print("FINAL CAMS + MET + RESIDUAL IDW")
print("==============================")

print(
    results.to_string(
        index=False,
        float_format=lambda x: f"{x:.3f}"
    )
)

print("\nGeçerli aylık kayıt:")
print(len(monthly))

print("\nGünlük IDW kaynak sayıları:")
print(
    pred["kaynak_istasyon_sayisi"]
    .value_counts()
    .sort_index()
)

print(
    f"\n[OK] {OUTPUT_METRICS}"
)