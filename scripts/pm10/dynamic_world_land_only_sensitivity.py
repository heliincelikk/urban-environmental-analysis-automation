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
    "dynamic_world_2024_q1_land_only_sensitivity.csv"
)

# Dynamic World label kodu:
# 0 = water
WATER_LABEL = 0

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
)

results = []

print("=" * 110)
print("DYNAMIC WORLD - 2024 Q1 - TUM BUFFER vs KARA-ONLY BUILT")
print("=" * 110)

print(
    f"{'Istasyon':<12}"
    f"{'Tip':<12}"
    f"{'Built All':>12}"
    f"{'Built Land':>13}"
    f"{'Fark':>10}"
    f"{'Su %':>10}"
    f"{'Gecerli km2':>14}"
)

print("-" * 110)

for _, row in stations.iterrows():

    station_name = row["istasyon"]
    station_type = row["tip"]

    lat = float(row["enlem"])
    lon = float(row["boylam"])

    point = ee.Geometry.Point([lon, lat])
    buffer_1km = point.buffer(BUFFER_M)

    # --------------------------------------------------
    # ISTASYONA AIT DYNAMIC WORLD KOLEKSIYONU
    # --------------------------------------------------

    dw = (
        dw_all
        .filterBounds(buffer_1km)
    )

    # --------------------------------------------------
    # 1) DONEMSEL ORTALAMA BUILT PROBABILITY
    # --------------------------------------------------

    built_mean = (
        dw
        .select("built")
        .mean()
    )

    # --------------------------------------------------
    # 2) DONEM BOYUNCA EN SIK GORULEN SINIF
    # --------------------------------------------------
    # label = her pikselde en olasi Dynamic World sinifi
    #
    # mode() = Q1 boyunca o pikselde en sik gorulen sinif
    #
    # Burada keyfi bir "water probability > 0.5" esigi
    # kullanmiyoruz.
    # --------------------------------------------------

    label_mode = (
        dw
        .select("label")
        .mode()
    )

    # Gecerli veri olan pikseller
    valid_mask = label_mode.mask()

    # Su ve kara maskeleri
    water_mask = label_mode.eq(WATER_LABEL)
    land_mask = label_mode.neq(WATER_LABEL)

    # --------------------------------------------------
    # 3) TUM GECERLI BUFFER UZERINDEN BUILT
    # --------------------------------------------------

    built_all_stats = built_mean.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=buffer_1km,
        scale=10,
        maxPixels=1_000_000
    ).getInfo()

    built_all = built_all_stats.get("built")

    # --------------------------------------------------
    # 4) SADECE KARA PIKSELLERI UZERINDEN BUILT
    # --------------------------------------------------

    built_land_image = built_mean.updateMask(
        land_mask
    )

    built_land_stats = built_land_image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=buffer_1km,
        scale=10,
        maxPixels=1_000_000
    ).getInfo()

    built_land = built_land_stats.get("built")

    # --------------------------------------------------
    # 5) ALAN HESAPLARI
    # --------------------------------------------------
    # Pixel saymak yerine pixelArea kullanıyoruz.
    # Böylece önceki projection/grid uyumsuzluğu
    # problemine düşmüyoruz.
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

    land_area_stats = (
        pixel_area
        .updateMask(land_mask)
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
    land_area_m2 = land_area_stats.get("area")

    # None guvenligi
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

    land_area_m2 = (
        land_area_m2
        if land_area_m2 is not None
        else 0
    )

    # --------------------------------------------------
    # 6) SU PAYI
    # --------------------------------------------------
    # Buradaki pay bütün geometrik buffer'a değil,
    # Dynamic World'de geçerli gözlemi olan alana göredir.
    # --------------------------------------------------

    if valid_area_m2 > 0:
        water_fraction = (
            water_area_m2 /
            valid_area_m2
        )
    else:
        water_fraction = None

    # --------------------------------------------------
    # 7) BUILT FARKI
    # --------------------------------------------------

    if (
        built_all is not None
        and built_land is not None
    ):
        built_difference = (
            built_land - built_all
        )
    else:
        built_difference = None

    # --------------------------------------------------
    # SONUCLARI KAYDET
    # --------------------------------------------------

    results.append(
        {
            "istasyon": station_name,
            "tip": station_type,
            "enlem": lat,
            "boylam": lon,
            "donem_baslangic": START_DATE,
            "donem_bitis": END_DATE,
            "buffer_m": BUFFER_M,
            "built_all_mean": built_all,
            "built_land_only_mean": built_land,
            "built_land_minus_all": built_difference,
            "water_fraction_valid_area": water_fraction,
            "valid_area_km2": valid_area_m2 / 1_000_000,
            "water_area_km2": water_area_m2 / 1_000_000,
            "land_area_km2": land_area_m2 / 1_000_000,
        }
    )

    # --------------------------------------------------
    # TERMINAL FORMAT
    # --------------------------------------------------

    built_all_text = (
        f"{built_all:.4f}"
        if built_all is not None
        else "NA"
    )

    built_land_text = (
        f"{built_land:.4f}"
        if built_land is not None
        else "NA"
    )

    diff_text = (
        f"{built_difference:+.4f}"
        if built_difference is not None
        else "NA"
    )

    water_text = (
        f"{water_fraction * 100:.2f}"
        if water_fraction is not None
        else "NA"
    )

    valid_area_text = (
        f"{valid_area_m2 / 1_000_000:.3f}"
    )

    print(
        f"{station_name:<12}"
        f"{station_type:<12}"
        f"{built_all_text:>12}"
        f"{built_land_text:>13}"
        f"{diff_text:>10}"
        f"{water_text:>10}"
        f"{valid_area_text:>14}"
    )

# --------------------------------------------------
# CSV
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
# EK OZET
# --------------------------------------------------

print()
print("=" * 110)
print("SU PAYINA GORE SIRALAMA")
print("=" * 110)

summary = result_df[
    [
        "istasyon",
        "water_fraction_valid_area",
        "built_all_mean",
        "built_land_only_mean",
        "built_land_minus_all"
    ]
].copy()

summary["water_percent"] = (
    summary["water_fraction_valid_area"] * 100
)

summary = summary.sort_values(
    "water_percent",
    ascending=False
)

print(
    summary[
        [
            "istasyon",
            "water_percent",
            "built_all_mean",
            "built_land_only_mean",
            "built_land_minus_all"
        ]
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)

print()
print("CSV kaydedildi:")
print(OUTPUT_FILE)