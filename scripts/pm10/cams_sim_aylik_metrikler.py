import pandas as pd
import numpy as np
from pathlib import Path

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

OUTPUT_FILE = Path(
    "outputs/pm10/cams_sim_aylik_metrikler.csv"
)


# =========================================================
# VERİ
# =========================================================
df = pd.read_csv(INPUT_FILE)

df = df[
    (df["aylik_gecerli"] == True)
    & df["pm10_sim_aylik"].notna()
    & df["pm10_cams_aylik"].notna()
].copy()

if len(df) != 181:
    print(
        f"[UYARI] 181 geçerli istasyon-ay "
        f"bekleniyordu, {len(df)} bulundu."
    )


# =========================================================
# METRİK FONKSİYONU
# =========================================================
def calculate_metrics(group):

    y_true = group["pm10_sim_aylik"]
    y_pred = group["pm10_cams_aylik"]

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
        "Bias": error.mean(),
        "SIM_ortalama": y_true.mean(),
        "CAMS_ortalama": y_pred.mean()
    })


# =========================================================
# İSTASYON BAZINDA
# =========================================================
station_results = (
    df
    .groupby("istasyon")
    .apply(
        calculate_metrics,
        include_groups=False
    )
    .reset_index()
)


# =========================================================
# POOLED
# =========================================================
pooled = calculate_metrics(df)

pooled_row = pd.DataFrame([{
    "istasyon": "POOLED",
    **pooled.to_dict()
}])


results = pd.concat(
    [
        station_results,
        pooled_row
    ],
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


# =========================================================
# ÇIKTI
# =========================================================
print("\n==============================")
print("CAMS -> SİM AYLIK METRİKLER")
print("==============================")

print(
    results.to_string(
        index=False,
        float_format=lambda x: f"{x:.3f}"
    )
)

print(
    f"\n[OK] Kaydedildi: {OUTPUT_FILE}"
)