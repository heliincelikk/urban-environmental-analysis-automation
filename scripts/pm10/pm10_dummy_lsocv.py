from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.dummy import DummyRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


# =========================================================
# PROJE YOLLARI
# =========================================================

PROJECT_DIR = Path(__file__).resolve().parents[2]

input_file = (
    PROJECT_DIR
    / "data"
    / "pm10"
    / "processed"
    / "pm10_meteoroloji_birlestirilmis.csv"
)

output_dir = (
    PROJECT_DIR
    / "outputs"
    / "pm10"
)

output_dir.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# 1. VERİYİ OKU
# =========================================================

df = pd.read_csv(input_file)

df["tarih"] = pd.to_datetime(
    df["tarih"]
)


# =========================================================
# 2. SADECE GEÇERLİ PM10 GÜNLERİ
# =========================================================

df = df[
    (df["gecerli_gun"] == True)
    &
    (df["pm10_gunluk"].notna())
].copy()


target = "pm10_gunluk"


print("\n==============================")
print("DUMMY MEAN BASELINE")
print("LEAVE-ONE-STATION-OUT CV")
print("==============================")

print("\nToplam kullanilan satir:")
print(len(df))


# =========================================================
# 3. İSTASYONLAR
# =========================================================

stations = sorted(
    df["istasyon"].unique()
)


results = []
all_predictions = []


# =========================================================
# 4. LEAVE-ONE-STATION-OUT
# =========================================================

for test_station in stations:

    train_df = df[
        df["istasyon"] != test_station
    ].copy()

    test_df = df[
        df["istasyon"] == test_station
    ].copy()


    y_train = train_df[target]
    y_test = test_df[target]


    # DummyRegressor için bir X gerekiyor,
    # fakat predictor bilgisi gerçekten kullanılmıyor.
    X_train = np.zeros(
        (len(train_df), 1)
    )

    X_test = np.zeros(
        (len(test_df), 1)
    )


    model = DummyRegressor(
        strategy="mean"
    )


    model.fit(
        X_train,
        y_train
    )


    predictions = model.predict(
        X_test
    )


    mae = mean_absolute_error(
        y_test,
        predictions
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_test,
            predictions
        )
    )

    r2 = r2_score(
        y_test,
        predictions
    )

    bias = np.mean(
        predictions
        - y_test.to_numpy()
    )


    print("\n==============================")
    print(f"TEST ISTASYONU: {test_station.upper()}")
    print("==============================")

    print(
        f"Egitim ortalama PM10 : {y_train.mean():.3f}"
    )

    print(
        f"Test gercek ortalama : {y_test.mean():.3f}"
    )

    print(
        f"MAE  : {mae:.3f}"
    )

    print(
        f"RMSE : {rmse:.3f}"
    )

    print(
        f"R2   : {r2:.3f}"
    )

    print(
        f"Bias : {bias:.3f}"
    )


    results.append({

        "test_istasyonu":
            test_station,

        "egitim_ortalama_pm10":
            y_train.mean(),

        "test_ortalama_pm10":
            y_test.mean(),

        "MAE":
            mae,

        "RMSE":
            rmse,

        "R2":
            r2,

        "Bias":
            bias

    })


    prediction_df = pd.DataFrame({

        "tarih":
            test_df["tarih"].values,

        "istasyon":
            test_station,

        "gercek_pm10":
            y_test.values,

        "tahmin_pm10":
            predictions

    })


    all_predictions.append(
        prediction_df
    )


# =========================================================
# 5. SONUÇLAR
# =========================================================

results_df = pd.DataFrame(
    results
)

predictions_df = pd.concat(
    all_predictions,
    ignore_index=True
)


overall_mae = mean_absolute_error(
    predictions_df["gercek_pm10"],
    predictions_df["tahmin_pm10"]
)

overall_rmse = np.sqrt(
    mean_squared_error(
        predictions_df["gercek_pm10"],
        predictions_df["tahmin_pm10"]
    )
)

overall_r2 = r2_score(
    predictions_df["gercek_pm10"],
    predictions_df["tahmin_pm10"]
)

overall_bias = np.mean(
    predictions_df["tahmin_pm10"]
    -
    predictions_df["gercek_pm10"]
)


print("\n==============================")
print("ISTASYON BAZINDA SONUCLAR")
print("==============================")

print(
    results_df.round(3)
)


print("\n==============================")
print("TUM OUT-OF-STATION TAHMINLER")
print("==============================")

print(
    f"MAE  : {overall_mae:.3f}"
)

print(
    f"RMSE : {overall_rmse:.3f}"
)

print(
    f"R2   : {overall_r2:.3f}"
)

print(
    f"Bias : {overall_bias:.3f}"
)


# =========================================================
# 6. KAYDET
# =========================================================

output_file = (
    output_dir
    / "pm10_dummy_lsocv_sonuclar.csv"
)

results_df.to_csv(
    output_file,
    index=False
)


print("\nKaydedildi:")
print(output_file)