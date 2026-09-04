import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ============================================================
# AYARLAR
# ============================================================

DATA_FILE = Path(
    "data/pm10/processed/pm10_meteoroloji_birlestirilmis.csv"
)

STATION_FILE = Path(
    "data/pm10/processed/pm10_istasyonlar.csv"
)

OUTPUT_DIR = Path("outputs/pm10")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

IDW_POWER = 2.0


MET_FEATURES = [
    "sicaklik_ort_c",
    "bagil_nem_ort_yuzde",
    "yagis_toplam_mm",
    "basinc_ort_hpa",
    "ruzgar_u_ort_ms",
    "ruzgar_v_ort_ms",
    "ruzgar_hizi_ort_ms",
]

TARGET = "pm10_gunluk"


# ============================================================
# VERI
# ============================================================

df = pd.read_csv(DATA_FILE)

stations_df = pd.read_csv(STATION_FILE)

df = df[
    (df["gecerli_gun"] == True)
    & df[TARGET].notna()
].copy()

df["tarih"] = pd.to_datetime(df["tarih"])

station_coordinates = (
    stations_df
    .set_index("istasyon")[["enlem", "boylam"]]
    .to_dict("index")
)

stations = sorted(df["istasyon"].unique())


# ============================================================
# HAVERSINE MESAFESI
# ============================================================

def haversine_km(lat1, lon1, lat2, lon2):

    R = 6371.0088

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    c = 2 * np.arctan2(
        np.sqrt(a),
        np.sqrt(1 - a)
    )

    return R * c


# ============================================================
# MESAFE MATRISI
# ============================================================

distance_matrix = {}

for station_a in stations:

    distance_matrix[station_a] = {}

    lat1 = station_coordinates[station_a]["enlem"]
    lon1 = station_coordinates[station_a]["boylam"]

    for station_b in stations:

        lat2 = station_coordinates[station_b]["enlem"]
        lon2 = station_coordinates[station_b]["boylam"]

        distance_matrix[station_a][station_b] = haversine_km(
            lat1,
            lon1,
            lat2,
            lon2
        )


# ============================================================
# IDW
# ============================================================

def idw_prediction(
    target_station,
    date,
    available_df,
    power=2.0
):

    day_df = available_df[
        available_df["tarih"] == date
    ]

    # Hedef istasyon kesinlikle kaynak olamaz
    day_df = day_df[
        day_df["istasyon"] != target_station
    ]

    if len(day_df) == 0:
        return np.nan, 0

    values = []
    weights = []

    for _, row in day_df.iterrows():

        source_station = row["istasyon"]

        distance = distance_matrix[
            target_station
        ][source_station]

        if distance <= 0:
            continue

        weight = 1.0 / (distance ** power)

        values.append(row[TARGET])
        weights.append(weight)

    if len(values) == 0:
        return np.nan, 0

    values = np.array(values)
    weights = np.array(weights)

    prediction = np.sum(
        weights * values
    ) / np.sum(weights)

    return prediction, len(values)


# ============================================================
# METRIKLER
# ============================================================

def calculate_metrics(y_true, y_pred):

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    return {
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": np.sqrt(
            mean_squared_error(y_true, y_pred)
        ),
        "r2": r2_score(y_true, y_pred),
        "bias": np.mean(y_pred - y_true)
    }


# ============================================================
# OUTER LOSO
# ============================================================

def run_residual_loso(
    model,
    model_name
):

    station_results = []

    all_true = []
    all_idw = []
    all_final = []

    prediction_rows = []

    print("\n" + "=" * 100)
    print(model_name)
    print("=" * 100)

    print(
        f"{'Test Istasyonu':<15}"
        f"{'N':>7}"
        f"{'IDW MAE':>12}"
        f"{'Final MAE':>12}"
        f"{'Final RMSE':>13}"
        f"{'Final R2':>11}"
        f"{'Bias':>11}"
    )

    print("-" * 100)

    for test_station in stations:

        # ----------------------------------------------------
        # OUTER TRAIN / TEST
        # ----------------------------------------------------

        outer_train = df[
            df["istasyon"] != test_station
        ].copy()

        outer_test = df[
            df["istasyon"] == test_station
        ].copy()


        # ----------------------------------------------------
        # TRAINING RESIDUAL'LARI
        #
        # Çok önemli:
        # Test istasyonu outer_train içinde bulunmuyor.
        #
        # Her train satırının IDW tahmininde de kendi
        # istasyonu kaynaklardan çıkarılıyor.
        #
        # Böylece leakage oluşmuyor.
        # ----------------------------------------------------

        train_rows = []

        for _, row in outer_train.iterrows():

            target_station = row["istasyon"]
            date = row["tarih"]

            idw_pred, source_count = idw_prediction(
                target_station=target_station,
                date=date,
                available_df=outer_train,
                power=IDW_POWER
            )

            if np.isnan(idw_pred):
                continue

            residual = (
                row[TARGET] - idw_pred
            )

            new_row = {
                feature: row[feature]
                for feature in MET_FEATURES
            }

            new_row["residual"] = residual
            new_row["idw_pred"] = idw_pred
            new_row["source_count"] = source_count

            train_rows.append(new_row)

        train_residual_df = pd.DataFrame(
            train_rows
        )


        # ----------------------------------------------------
        # RESIDUAL MODELI
        # ----------------------------------------------------

        X_train = train_residual_df[
            MET_FEATURES
        ]

        y_train = train_residual_df[
            "residual"
        ]

        model.fit(
            X_train,
            y_train
        )


        # ----------------------------------------------------
        # TEST ISTASYONU
        #
        # IDW yalnızca diğer 7 istasyondan oluşturuluyor.
        # ----------------------------------------------------

        test_true = []
        test_idw = []
        test_final = []

        for _, row in outer_test.iterrows():

            date = row["tarih"]

            idw_pred, source_count = idw_prediction(
                target_station=test_station,
                date=date,
                available_df=outer_train,
                power=IDW_POWER
            )

            if np.isnan(idw_pred):
                continue

            X_test = pd.DataFrame(
                [{
                    feature: row[feature]
                    for feature in MET_FEATURES
                }]
            )

            predicted_residual = model.predict(
                X_test
            )[0]

            final_prediction = (
                idw_pred
                + predicted_residual
            )

            test_true.append(
                row[TARGET]
            )

            test_idw.append(
                idw_pred
            )

            test_final.append(
                final_prediction
            )

            prediction_rows.append({
                "tarih": date,
                "istasyon": test_station,
                "gercek_pm10": row[TARGET],
                "idw_pm10": idw_pred,
                "tahmin_residual": predicted_residual,
                "final_pm10": final_prediction,
                "kaynak_istasyon_sayisi": source_count
            })


        # ----------------------------------------------------
        # FOLD METRIKLERI
        # ----------------------------------------------------

        idw_metrics = calculate_metrics(
            test_true,
            test_idw
        )

        final_metrics = calculate_metrics(
            test_true,
            test_final
        )

        station_results.append({
            "istasyon": test_station,
            "n": len(test_true),

            "idw_mae": idw_metrics["mae"],
            "idw_rmse": idw_metrics["rmse"],
            "idw_r2": idw_metrics["r2"],
            "idw_bias": idw_metrics["bias"],

            "final_mae": final_metrics["mae"],
            "final_rmse": final_metrics["rmse"],
            "final_r2": final_metrics["r2"],
            "final_bias": final_metrics["bias"],
        })

        all_true.extend(test_true)
        all_idw.extend(test_idw)
        all_final.extend(test_final)

        print(
            f"{test_station:<15}"
            f"{len(test_true):>7}"
            f"{idw_metrics['mae']:>12.3f}"
            f"{final_metrics['mae']:>12.3f}"
            f"{final_metrics['rmse']:>13.3f}"
            f"{final_metrics['r2']:>11.3f}"
            f"{final_metrics['bias']:>11.3f}"
        )


    # ========================================================
    # POOLED
    # ========================================================

    pooled_idw = calculate_metrics(
        all_true,
        all_idw
    )

    pooled_final = calculate_metrics(
        all_true,
        all_final
    )

    print("\nPOOLED IDW")
    print(
        f"MAE  : {pooled_idw['mae']:.3f}"
    )
    print(
        f"RMSE : {pooled_idw['rmse']:.3f}"
    )
    print(
        f"R2   : {pooled_idw['r2']:.3f}"
    )
    print(
        f"Bias : {pooled_idw['bias']:.3f}"
    )

    print("\nPOOLED FINAL")
    print(
        f"MAE  : {pooled_final['mae']:.3f}"
    )
    print(
        f"RMSE : {pooled_final['rmse']:.3f}"
    )
    print(
        f"R2   : {pooled_final['r2']:.3f}"
    )
    print(
        f"Bias : {pooled_final['bias']:.3f}"
    )

    return (
        pd.DataFrame(station_results),
        pd.DataFrame(prediction_rows),
        pooled_idw,
        pooled_final
    )


# ============================================================
# VERI KONTROLU
# ============================================================

print("=" * 100)
print("VERI KONTROLU")
print("=" * 100)

print(
    f"Gecerli PM10 satiri: {len(df)}"
)

print(
    f"Istasyon sayisi: {len(stations)}"
)

print(
    f"Istasyonlar: {stations}"
)

print("\nMeteoroloji eksikleri:")

print(
    df[MET_FEATURES]
    .isna()
    .sum()
)


# ============================================================
# LINEAR RESIDUAL
# ============================================================

linear = LinearRegression()

(
    linear_station,
    linear_predictions,
    linear_idw,
    linear_final
) = run_residual_loso(
    linear,
    "IDW + Linear Meteoroloji Residual"
)


# ============================================================
# RANDOM FOREST RESIDUAL
# ============================================================

rf = RandomForestRegressor(
    n_estimators=500,
    random_state=42,
    n_jobs=-1
)

(
    rf_station,
    rf_predictions,
    rf_idw,
    rf_final
) = run_residual_loso(
    rf,
    "IDW + RF Meteoroloji Residual"
)


# ============================================================
# KAYDET
# ============================================================

linear_station.to_csv(
    OUTPUT_DIR
    / "pm10_idw_linear_residual_loso.csv",
    index=False
)

linear_predictions.to_csv(
    OUTPUT_DIR
    / "pm10_idw_linear_residual_predictions.csv",
    index=False
)

rf_station.to_csv(
    OUTPUT_DIR
    / "pm10_idw_rf_residual_loso.csv",
    index=False
)

rf_predictions.to_csv(
    OUTPUT_DIR
    / "pm10_idw_rf_residual_predictions.csv",
    index=False
)


# ============================================================
# FINAL KARSILASTIRMA
# ============================================================

comparison = pd.DataFrame([
    {
        "model": "IDW p=2",
        **linear_idw
    },
    {
        "model": "IDW + Linear Met Residual",
        **linear_final
    },
    {
        "model": "IDW + RF Met Residual",
        **rf_final
    }
])

print("\n" + "=" * 100)
print("FINAL POOLED KARSILASTIRMA")
print("=" * 100)

print(
    comparison
    .round(3)
    .to_string(index=False)
)