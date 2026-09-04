import ee
import pandas as pd
import os

PROJECT_ID = "antalya-environmental-analysis"

ee.Initialize(project=PROJECT_ID)

# --------------------------------------------------
# AYARLAR
# --------------------------------------------------

STATION_FILE = "data/pm10/processed/pm10_istasyonlar.csv"

START_DATE = "2024-01-01"
END_DATE = "2024-04-01"

BUFFER_M = 1000

OUTPUT_FILE = (
    "outputs/pm10/"
    "dynamic_world_2024_q1_8_istasyon.csv"
)

# --------------------------------------------------
# ISTASYONLARI OKU
# --------------------------------------------------

stations = pd.read_csv(STATION_FILE)

# --------------------------------------------------
# DYNAMIC WORLD
# --------------------------------------------------

dw_all = (
    ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
    .filterDate(START_DATE, END_DATE)
    .select("built")
)

results = []

print("=" * 88)
print("DYNAMIC WORLD - 8 ISTASYON - 2024 Q1")
print("=" * 88)

print()
print(
    f"{'Istasyon':<12}"
    f"{'Tip':<12}"
    f"{'Image':>8}"
    f"{'Built Mean':>14}"
    f"{'Obs Mean':>12}"
    f"{'Obs Min':>10}"
    f"{'Obs Max':>10}"
)

print("-" * 88)

for _, row in stations.iterrows():

    station_name = row["istasyon"]
    lat = float(row["enlem"])
    lon = float(row["boylam"])
    station_type = row["tip"]

    point = ee.Geometry.Point([lon, lat])
    buffer_1km = point.buffer(BUFFER_M)

    dw = (
        dw_all
        .filterBounds(buffer_1km)
    )

    image_count = dw.size().getInfo()

    # --------------------------------------------------
    # DONEMSEL ORTALAMA BUILT PROBABILITY
    # --------------------------------------------------

    built_mean_image = dw.mean()

    built_stats = built_mean_image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=buffer_1km,
        scale=10,
        maxPixels=1_000_000
    ).getInfo()

    mean_built_probability = built_stats.get("built")

    # --------------------------------------------------
    # PIKSEL BAZLI GOZLEM SAYISI
    # --------------------------------------------------

    observation_count = dw.count()

    count_stats = observation_count.reduceRegion(
        reducer=ee.Reducer.mean().combine(
            reducer2=ee.Reducer.minMax(),
            sharedInputs=True
        ),
        geometry=buffer_1km,
        scale=10,
        maxPixels=1_000_000
    ).getInfo()

    obs_mean = count_stats.get("built_mean")
    obs_min = count_stats.get("built_min")
    obs_max = count_stats.get("built_max")

    results.append(
        {
            "istasyon": station_name,
            "tip": station_type,
            "enlem": lat,
            "boylam": lon,
            "donem_baslangic": START_DATE,
            "donem_bitis": END_DATE,
            "buffer_m": BUFFER_M,
            "image_count": image_count,
            "built_probability_mean": mean_built_probability,
            "pixel_observation_mean": obs_mean,
            "pixel_observation_min": obs_min,
            "pixel_observation_max": obs_max,
        }
    )

    built_text = (
        f"{mean_built_probability:.4f}"
        if mean_built_probability is not None
        else "NA"
    )

    obs_mean_text = (
        f"{obs_mean:.2f}"
        if obs_mean is not None
        else "NA"
    )

    obs_min_text = (
        f"{obs_min:.0f}"
        if obs_min is not None
        else "NA"
    )

    obs_max_text = (
        f"{obs_max:.0f}"
        if obs_max is not None
        else "NA"
    )

    print(
        f"{station_name:<12}"
        f"{station_type:<12}"
        f"{image_count:>8}"
        f"{built_text:>14}"
        f"{obs_mean_text:>12}"
        f"{obs_min_text:>10}"
        f"{obs_max_text:>10}"
    )

# --------------------------------------------------
# CSV KAYDET
# --------------------------------------------------

result_df = pd.DataFrame(results)

os.makedirs(
    os.path.dirname(OUTPUT_FILE),
    exist_ok=True
)

result_df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

print()
print("=" * 88)
print("OZET")
print("=" * 88)

valid_built = result_df[
    "built_probability_mean"
].dropna()

if not valid_built.empty:

    print(
        f"Minimum built probability : "
        f"{valid_built.min():.4f}"
    )

    print(
        f"Maksimum built probability : "
        f"{valid_built.max():.4f}"
    )

    print(
        f"Aralik                     : "
        f"{valid_built.max() - valid_built.min():.4f}"
    )

print()
print(f"CSV kaydedildi:")
print(OUTPUT_FILE)