import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ============================================================
# DOSYA YOLLARI
# ============================================================

PM10_FILE = Path(
    "data/pm10/processed/pm10_meteoroloji_birlestirilmis.csv"
)

ELEVATION_FILE = Path(
    "outputs/pm10/copernicus_dem_istasyon_elevation.csv"
)

OUTPUT_DIR = Path("outputs/pm10")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# VERIYI OKU
# ============================================================

df = pd.read_csv(PM10_FILE)
elevation = pd.read_csv(ELEVATION_FILE)

# Sadece gerekli elevation bilgisi
elevation = elevation[
    ["istasyon", "elevation_m"]
].copy()

# PM10 + meteoroloji + elevation
df = df.merge(
    elevation,
    on="istasyon",
    how="left"
)

# Sadece geçerli PM10 günleri
df = df[
    (df["gecerli_gun"] == True)
    & df["pm10_gunluk"].notna()
].copy()


# ============================================================
# FEATURE / TARGET
# ============================================================

MET_FEATURES = [
    "sicaklik_ort_c",
    "bagil_nem_ort_yuzde",
    "yagis_toplam_mm",
    "basinc_ort_hpa",
    "ruzgar_u_ort_ms",
    "ruzgar_v_ort_ms",
    "ruzgar_hizi_ort_ms",
]

FEATURES = MET_FEATURES + [
    "elevation_m"
]

TARGET = "pm10_gunluk"

stations = sorted(df["istasyon"].unique())


# ============================================================
# VERI KONTROLU
# ============================================================

print("=" * 90)
print("VERI KONTROLU")
print("=" * 90)

print(f"Modelde kullanilacak satir sayisi: {len(df)}")
print(f"Istasyon sayisi: {len(stations)}")
print(f"Istasyonlar: {stations}")

print("\nEksik predictor sayilari:")
print(df[FEATURES].isna().sum())

print("\nIstasyon elevation degerleri:")
print(
    df.groupby("istasyon")["elevation_m"]
    .first()
    .sort_values()
    .round(2)
    .to_string()
)


# ============================================================
# METRIKLER
# ============================================================

def calculate_metrics(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    bias = np.mean(y_pred - y_true)

    return {
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "bias": bias
    }


# ============================================================
# LOSO
# ============================================================

def run_loso(model, model_name):

    station_results = []
    all_true = []
    all_pred = []

    print("\n" + "=" * 90)
    print(model_name)
    print("=" * 90)

    print(
        f"{'Test Istasyonu':<16}"
        f"{'N':>8}"
        f"{'MAE':>12}"
        f"{'RMSE':>12}"
        f"{'R2':>12}"
        f"{'Bias':>12}"
    )

    print("-" * 90)

    for test_station in stations:

        train = df[
            df["istasyon"] != test_station
        ].copy()

        test = df[
            df["istasyon"] == test_station
        ].copy()

        X_train = train[FEATURES]
        y_train = train[TARGET]

        X_test = test[FEATURES]
        y_test = test[TARGET]

        model.fit(X_train, y_train)

        pred = model.predict(X_test)

        metrics = calculate_metrics(
            y_test,
            pred
        )

        station_results.append({
            "istasyon": test_station,
            "n": len(test),
            **metrics
        })

        all_true.extend(y_test.values)
        all_pred.extend(pred)

        print(
            f"{test_station:<16}"
            f"{len(test):>8}"
            f"{metrics['mae']:>12.3f}"
            f"{metrics['rmse']:>12.3f}"
            f"{metrics['r2']:>12.3f}"
            f"{metrics['bias']:>12.3f}"
        )

    pooled = calculate_metrics(
        np.array(all_true),
        np.array(all_pred)
    )

    print("\nPOOLED SONUCLAR")
    print(f"MAE  : {pooled['mae']:.3f}")
    print(f"RMSE : {pooled['rmse']:.3f}")
    print(f"R2   : {pooled['r2']:.3f}")
    print(f"Bias : {pooled['bias']:.3f}")

    return (
        pd.DataFrame(station_results),
        pooled
    )


# ============================================================
# LINEAR
# ============================================================

linear_model = LinearRegression()

linear_results, linear_pooled = run_loso(
    linear_model,
    "Linear Met + Elevation"
)


# ============================================================
# RANDOM FOREST
# ============================================================

rf_model = RandomForestRegressor(
    n_estimators=500,
    random_state=42,
    n_jobs=-1
)

rf_results, rf_pooled = run_loso(
    rf_model,
    "RF Met + Elevation"
)


# ============================================================
# KAYDET
# ============================================================

linear_output = (
    OUTPUT_DIR
    / "pm10_loso_linear_met_elevation.csv"
)

rf_output = (
    OUTPUT_DIR
    / "pm10_loso_rf_met_elevation.csv"
)

linear_results.to_csv(
    linear_output,
    index=False
)

rf_results.to_csv(
    rf_output,
    index=False
)


# ============================================================
# POOLED KARSILASTIRMA
# ============================================================

comparison = pd.DataFrame([
    {
        "model": "Linear Met + Elevation",
        **linear_pooled
    },
    {
        "model": "RF Met + Elevation",
        **rf_pooled
    }
])

print("\n" + "=" * 90)
print("POOLED KARSILASTIRMA")
print("=" * 90)

print(
    comparison.round(3).to_string(
        index=False
    )
)

print("\nDosyalar kaydedildi:")
print(linear_output)
print(rf_output)