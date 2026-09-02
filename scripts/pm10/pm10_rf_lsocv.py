from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
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


print("\n==============================")
print("METEOROLOJI-ONLY RANDOM FOREST")
print("LEAVE-ONE-STATION-OUT CV")
print("==============================")

print("\nToplam kullanilan satir:")
print(len(df))


# =========================================================
# 3. FEATURE VE TARGET
# =========================================================

features = [
    "sicaklik_ort_c",
    "bagil_nem_ort_yuzde",
    "yagis_toplam_mm",
    "basinc_ort_hpa",
    "ruzgar_u_ort_ms",
    "ruzgar_v_ort_ms",
    "ruzgar_hizi_ort_ms"
]

target = "pm10_gunluk"


# =========================================================
# 4. VERİ KONTROLÜ
# =========================================================

feature_nan = (
    df[features]
    .isna()
    .sum()
)

print("\nFeature NaN kontrolu:")
print(feature_nan)


if feature_nan.sum() != 0:

    raise ValueError(
        "Model feature'larinda NaN bulundu."
    )


# =========================================================
# 5. LEAVE-ONE-STATION-OUT
# =========================================================

stations = sorted(
    df["istasyon"].unique()
)

results = []

all_predictions = []


for test_station in stations:

    print("\n==============================")
    print(f"TEST ISTASYONU: {test_station.upper()}")
    print("==============================")


    # -----------------------------------------------------
    # Eğitim / test ayrımı
    # -----------------------------------------------------

    train_df = df[
        df["istasyon"] != test_station
    ].copy()

    test_df = df[
        df["istasyon"] == test_station
    ].copy()


    X_train = train_df[features]

    y_train = train_df[target]


    X_test = test_df[features]

    y_test = test_df[target]


    print(
        f"Egitim satiri: {len(train_df)}"
    )

    print(
        f"Test satiri: {len(test_df)}"
    )


    # =====================================================
    # 6. RANDOM FOREST
    # =====================================================
    #
    # Şimdilik hyperparameter tuning YOK.
    #
    # n_estimators=500:
    # Sonuçların tek bir küçük forest'a göre
    # daha kararlı olması için.
    #
    # Diğer temel ayarlar sklearn varsayılanlarında.
    #
    # =====================================================

    model = RandomForestRegressor(

        n_estimators=500,

        random_state=42,

        n_jobs=-1
    )


    model.fit(
        X_train,
        y_train
    )


    predictions = model.predict(
        X_test
    )


    # =====================================================
    # 7. METRİKLER
    # =====================================================

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
        -
        y_test.to_numpy()
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

        "egitim_satiri":
            len(train_df),

        "test_satiri":
            len(test_df),

        "MAE":
            mae,

        "RMSE":
            rmse,

        "R2":
            r2,

        "Bias":
            bias

    })


    # =====================================================
    # 8. OUT-OF-STATION TAHMİNLER
    # =====================================================

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


    prediction_df["hata"] = (
        prediction_df["tahmin_pm10"]
        -
        prediction_df["gercek_pm10"]
    )


    all_predictions.append(
        prediction_df
    )


# =========================================================
# 9. FOLD SONUÇLARI
# =========================================================

results_df = pd.DataFrame(
    results
)


print("\n==============================")
print("ISTASYON BAZINDA SONUCLAR")
print("==============================")

print(
    results_df.round(3)
)


# =========================================================
# 10. ORTALAMA FOLD PERFORMANSI
# =========================================================

print("\n==============================")
print("ORTALAMA FOLD PERFORMANSI")
print("==============================")

print(
    results_df[
        [
            "MAE",
            "RMSE",
            "R2",
            "Bias"
        ]
    ]
    .mean()
    .round(3)
)


# =========================================================
# 11. TÜM OUT-OF-STATION TAHMİNLER
# =========================================================

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
# 12. FEATURE IMPORTANCE
# =========================================================
#
# DİKKAT:
# Bunları şimdilik bilimsel sonuç diye
# yorumlamıyoruz.
#
# Çünkü her fold'da model farklı ve
# impurity importance bias içerebilir.
#
# Sadece teknik kontrol amacıyla tutuluyor.
# =========================================================

feature_importance = pd.DataFrame({

    "degisken":
        features,

    "importance":
        model.feature_importances_

}).sort_values(

    "importance",
    ascending=False
)


print("\n==============================")
print("SON FOLD FEATURE IMPORTANCE")
print("(SADECE TEKNIK KONTROL)")
print("==============================")

print(
    feature_importance.round(4)
)


# =========================================================
# 13. KAYDET
# =========================================================

results_file = (
    output_dir
    / "pm10_rf_lsocv_sonuclar.csv"
)

predictions_file = (
    output_dir
    / "pm10_rf_lsocv_tahminler.csv"
)


results_df.to_csv(
    results_file,
    index=False
)

predictions_df.to_csv(
    predictions_file,
    index=False
)


print("\n==============================")
print("RANDOM FOREST TAMAMLANDI")
print("==============================")

print("\nSonuclar:")
print(results_file)

print("\nTahminler:")
print(predictions_file)