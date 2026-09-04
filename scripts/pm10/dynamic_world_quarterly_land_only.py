import ee
import pandas as pd
import os

PROJECT_ID = "antalya-environmental-analysis"

ee.Initialize(project=PROJECT_ID)

# --------------------------------------------------
# AYARLAR
# --------------------------------------------------

STATION_FILE = "data/pm10/processed/pm10_istasyonlar.csv"

BUFFER_M = 1000

OUTPUT_FILE = (
    "outputs/pm10/"
    "dynamic_world_quarterly_land_only_2024_2025.csv"
)

WATER_LABEL = 0

# --------------------------------------------------
# DONEMLER
# --------------------------------------------------

quarters = [
    ("2024_Q1", "2024-01-01", "2024-04-01"),
    ("2024_Q2", "2024-04-01", "2024-07-01"),
    ("2024_Q3", "2024-07-01", "2024-10-01"),
    ("2024_Q4", "2024-10-01", "2025-01-01"),
    ("2025_Q1", "2025-01-01", "2025-04-01"),
    ("2025_Q2", "2025-04-01", "2025-07-01"),
    ("2025_Q3", "2025-07-01", "2025-10-01"),
    ("2025_Q4", "2025-10-01", "2026-01-01"),
]

# --------------------------------------------------
# ISTASYONLARI OKU
# --------------------------------------------------

stations = pd.read_csv(STATION_FILE)

results = []

print("=" * 120)
print("DYNAMIC WORLD - QUARTERLY LAND-ONLY BUILT - 2024-2025")
print("=" * 120)

print(
    f"{'Donem':<10}"
    f"{'Istasyon':<12}"
    f"{'Tip':<12}"
    f"{'Image':>8}"
    f"{'Built Land':>13}"
    f"{'Su %':>10}"
    f"{'Obs Mean':>12}"
    f"{'Obs Min':>10}"
    f"{'Obs Max':>10}"
)

print("-" * 120)

# --------------------------------------------------
# ANA DONGU
# --------------------------------------------------

for quarter_name, start_date, end_date in quarters:

    dw_period = (
        ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
        .filterDate(start_date, end_date)
    )

    for _, row in stations.iterrows():

        station_name = row["istasyon"]
        station_type = row["tip"]

        lat = float(row["enlem"])
        lon = float(row["boylam"])

        point = ee.Geometry.Point([lon, lat])
        buffer_1km = point.buffer(BUFFER_M)

        dw = (
            dw_period
            .filterBounds(buffer_1km)
        )

        image_count = dw.size().getInfo()

        # --------------------------------------------------
        # BOS KOLEKSIYON KONTROLU
        # --------------------------------------------------

        if image_count == 0:

            results.append(
                {
                    "donem": quarter_name,
                    "donem_baslangic": start_date,
                    "donem_bitis": end_date,
                    "istasyon": station_name,
                    "tip": station_type,
                    "enlem": lat,
                    "boylam": lon,
                    "buffer_m": BUFFER_M,
                    "image_count": 0,
                    "built_land_only_mean": None,
                    "water_fraction_valid_area": None,
                    "pixel_observation_mean": None,
                    "pixel_observation_min": None,
                    "pixel_observation_max": None,
                }
            )

            print(
                f"{quarter_name:<10}"
                f"{station_name:<12}"
                f"{station_type:<12}"
                f"{0:>8}"
                f"{'NA':>13}"
                f"{'NA':>10}"
                f"{'NA':>12}"
                f"{'NA':>10}"
                f"{'NA':>10}"
            )

            continue

        # --------------------------------------------------
        # BUILT ORTALAMASI
        # --------------------------------------------------

        built_mean = (
            dw
            .select("built")
            .mean()
        )

        # --------------------------------------------------
        # DONEMSEL MODE LABEL
        # --------------------------------------------------

        label_mode = (
            dw
            .select("label")
            .mode()
        )

        valid_mask = label_mode.mask()
        water_mask = label_mode.eq(WATER_LABEL)
        land_mask = label_mode.neq(WATER_LABEL)

        # --------------------------------------------------
        # LAND-ONLY BUILT
        # --------------------------------------------------

        built_land_image = (
            built_mean
            .updateMask(land_mask)
        )

        built_land_stats = (
            built_land_image
            .reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=buffer_1km,
                scale=10,
                maxPixels=1_000_000
            )
            .getInfo()
        )

        built_land = built_land_stats.get("built")

        # --------------------------------------------------
        # SU PAYI
        # --------------------------------------------------

        pixel_area = ee.Image.pixelArea()

        valid_area_stats = (
            pixel_area
            .updateMask(valid_mask)
            .reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=buffer_1km,
                scale=10,
                maxPixels=1_000_000
            )
            .getInfo()
        )

        water_area_stats = (
            pixel_area
            .updateMask(water_mask)
            .reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=buffer_1km,
                scale=10,
                maxPixels=1_000_000
            )
            .getInfo()
        )

        valid_area_m2 = valid_area_stats.get("area")
        water_area_m2 = water_area_stats.get("area")

        valid_area_m2 = (
            valid_area_m2
            if valid_area_m2 is not None
            else 0
        )

        water_area_m2 = (
            water_area_m2
            if water_area_m2 is not None
            else 0
        )

        if valid_area_m2 > 0:
            water_fraction = (
                water_area_m2 /
                valid_area_m2
            )
        else:
            water_fraction = None

        # --------------------------------------------------
        # PIKSEL BAZLI GECERLI GOZLEM SAYISI
        # --------------------------------------------------

        observation_count = (
            dw
            .select("built")
            .count()
        )

        count_stats = (
            observation_count
            .reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.minMax(),
                    sharedInputs=True
                ),
                geometry=buffer_1km,
                scale=10,
                maxPixels=1_000_000
            )
            .getInfo()
        )

        obs_mean = count_stats.get("built_mean")
        obs_min = count_stats.get("built_min")
        obs_max = count_stats.get("built_max")

        # --------------------------------------------------
        # KAYDET
        # --------------------------------------------------

        results.append(
            {
                "donem": quarter_name,
                "donem_baslangic": start_date,
                "donem_bitis": end_date,
                "istasyon": station_name,
                "tip": station_type,
                "enlem": lat,
                "boylam": lon,
                "buffer_m": BUFFER_M,
                "image_count": image_count,
                "built_land_only_mean": built_land,
                "water_fraction_valid_area": water_fraction,
                "pixel_observation_mean": obs_mean,
                "pixel_observation_min": obs_min,
                "pixel_observation_max": obs_max,
            }
        )

        built_text = (
            f"{built_land:.4f}"
            if built_land is not None
            else "NA"
        )

        water_text = (
            f"{water_fraction * 100:.2f}"
            if water_fraction is not None
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
            f"{quarter_name:<10}"
            f"{station_name:<12}"
            f"{station_type:<12}"
            f"{image_count:>8}"
            f"{built_text:>13}"
            f"{water_text:>10}"
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

# --------------------------------------------------
# KONTROL
# --------------------------------------------------

print()
print("=" * 120)
print("KONTROL")
print("=" * 120)

print(f"Toplam satir: {len(result_df)}")
print(
    "Beklenen satir: "
    f"{len(quarters) * len(stations)}"
)

print(
    "Eksik built degeri: "
    f"{result_df['built_land_only_mean'].isna().sum()}"
)

print(
    "Duplicate donem-istasyon: "
    f"{result_df.duplicated(['donem', 'istasyon']).sum()}"
)

print()
print("Istasyon basina donem sayisi:")

print(
    result_df
    .groupby("istasyon")["donem"]
    .count()
    .to_string()
)

print()
print("=" * 120)
print("BUILT DEGISKENLIGI OZETI")
print("=" * 120)

summary = (
    result_df
    .groupby("istasyon")["built_land_only_mean"]
    .agg(
        ["min", "max", "mean", "std"]
    )
    .reset_index()
)

summary["range"] = (
    summary["max"] - summary["min"]
)

print(
    summary.to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)

print()
print("CSV kaydedildi:")
print(OUTPUT_FILE)