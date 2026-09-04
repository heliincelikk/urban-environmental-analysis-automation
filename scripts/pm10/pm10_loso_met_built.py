import pandas as pd
import numpy as np
import os

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

# --------------------------------------------------
# DOSYALAR
# --------------------------------------------------

INPUT_FILE = (
    "data/pm10/processed/"
    "pm10_meteoroloji_built_birlestirilmis.csv"
)

OUTPUT_DIR = "outputs/pm10"

LINEAR_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "pm10_loso_linear_met_built.csv"
)

RF_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "pm10_loso_rf_met_built.csv"
)

# --------------------------------------------------
# VERIYI OKU
# --------------------------------------------------

df = pd.read_csv(INPUT_FILE)

# Sadece gecerli gunler ve PM10 degeri olan satirlar
df = df[
    (df["gecerli_gun"] == True)
    & (df["pm10_gunluk"].notna())
].copy()

# --------------------------------------------------
# PREDICTORLAR
# --------------------------------------------------

met_features = [
    "sicaklik_ort_c",
    "bagil_nem_ort_yuzde",
    "yagis_toplam_mm",
    "basinc_ort_hpa",
    "ruzgar_u_ort_ms",
    "ruzgar_v_ort_ms",
    "ruzgar_hizi_ort_ms",
]

features = (
    met_features
    + ["built_static_median"]
)

target = "pm10_gunluk"

stations = sorted(
    df["istasyon"].unique()
)

# --------------------------------------------------
# ILK KONTROLLER
# --------------------------------------------------

print("=" * 90)
print("VERI KONTROLU")
print("=" * 90)

print(f"Modelde kullanilacak satir sayisi: {len(df)}")
print(f"Istasyon sayisi: {len(stations)}")
print(f"Istasyonlar: {stations}")

print()
print("Eksik predictor sayilari:")

print(
    df[features]
    .isna()
    .sum()
    .to_string()
)

print()

# --------------------------------------------------
# METRIK FONKSIYONU
# --------------------------------------------------

def calculate_metrics(y_true, y_pred):

    mae = mean_absolute_error(
        y_true,
        y_pred
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_true,
            y_pred
        )
    )

    r2 = r2_score(
        y_true,
        y_pred
    )

    bias = np.mean(
        y_pred - y_true
    )

    return mae, rmse, r2, bias


# --------------------------------------------------
# LOSO CALISTIRICI
# --------------------------------------------------

def run_loso(
    model_name,
    model_factory
):

    station_results = []
    all_predictions = []

    print()
    print("=" * 90)
    print(model_name)
    print("=" * 90)

    print(
        f"{'Test Istasyonu':<15}"
        f"{'N':>8}"
        f"{'MAE':>12}"
        f"{'RMSE':>12}"
        f"{'R2':>12}"
        f"{'Bias':>12}"
    )

    print("-" * 90)

    for test_station in stations:

        train = df[
            df["istasyon"]
            != test_station
        ].copy()

        test = df[
            df["istasyon"]
            == test_station
        ].copy()

        X_train = train[features]
        y_train = train[target]

        X_test = test[features]
        y_test = test[target]

        model = model_factory()

        model.fit(
            X_train,
            y_train
        )

        y_pred = model.predict(
            X_test
        )

        mae, rmse, r2, bias = (
            calculate_metrics(
                y_test,
                y_pred
            )
        )

        station_results.append(
            {
                "model": model_name,
                "test_istasyonu": test_station,
                "n": len(test),
                "mae": mae,
                "rmse": rmse,
                "r2": r2,
                "bias": bias,
            }
        )

        prediction_df = pd.DataFrame(
            {
                "istasyon": test_station,
                "gercek_pm10": y_test.values,
                "tahmin_pm10": y_pred,
            }
        )

        all_predictions.append(
            prediction_df
        )

        print(
            f"{test_station:<15}"
            f"{len(test):>8}"
            f"{mae:>12.3f}"
            f"{rmse:>12.3f}"
            f"{r2:>12.3f}"
            f"{bias:>12.3f}"
        )

    # --------------------------------------------------
    # POOLED METRIKLER
    # --------------------------------------------------

    prediction_all = pd.concat(
        all_predictions,
        ignore_index=True
    )

    pooled_mae, pooled_rmse, pooled_r2, pooled_bias = (
        calculate_metrics(
            prediction_all["gercek_pm10"],
            prediction_all["tahmin_pm10"]
        )
    )

    print()
    print("POOLED SONUCLAR")

    print(
        f"MAE  : {pooled_mae:.3f}"
    )

    print(
        f"RMSE : {pooled_rmse:.3f}"
    )

    print(
        f"R2   : {pooled_r2:.3f}"
    )

    print(
        f"Bias : {pooled_bias:.3f}"
    )

    return (
        pd.DataFrame(
            station_results
        ),
        prediction_all,
        {
            "mae": pooled_mae,
            "rmse": pooled_rmse,
            "r2": pooled_r2,
            "bias": pooled_bias,
        }
    )


# --------------------------------------------------
# LINEAR REGRESSION
# --------------------------------------------------

linear_results, linear_predictions, linear_pooled = (
    run_loso(
        model_name="Linear Met + Built",
        model_factory=lambda: LinearRegression()
    )
)

# --------------------------------------------------
# RANDOM FOREST
# --------------------------------------------------

rf_results, rf_predictions, rf_pooled = (
    run_loso(
        model_name="RF Met + Built",
        model_factory=lambda: RandomForestRegressor(
            n_estimators=500,
            random_state=42,
            n_jobs=-1
        )
    )
)

# --------------------------------------------------
# KAYDET
# --------------------------------------------------

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

linear_results.to_csv(
    LINEAR_OUTPUT,
    index=False,
    encoding="utf-8-sig"
)

rf_results.to_csv(
    RF_OUTPUT,
    index=False,
    encoding="utf-8-sig"
)

# --------------------------------------------------
# KARSILASTIRMA
# --------------------------------------------------

print()
print("=" * 90)
print("POOLED KARSILASTIRMA")
print("=" * 90)

comparison = pd.DataFrame(
    [
        {
            "model":
            "Linear Met + Built",
            **linear_pooled
        },
        {
            "model":
            "RF Met + Built",
            **rf_pooled
        },
    ]
)

print(
    comparison.to_string(
        index=False,
        float_format=lambda x: f"{x:.3f}"
    )
)

print()
print("Dosyalar kaydedildi:")
print(LINEAR_OUTPUT)
print(RF_OUTPUT)