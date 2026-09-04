import ee
from datetime import datetime, timezone

PROJECT_ID = "antalya-environmental-analysis"

ee.Initialize(project=PROJECT_ID)

# --------------------------------------------------
# KEPEZ
# --------------------------------------------------

KEPEZ_LON = 30.700425
KEPEZ_LAT = 36.914883

kepez = ee.Geometry.Point([KEPEZ_LON, KEPEZ_LAT])
buffer_1km = kepez.buffer(1000)

START_DATE = "2024-01-01"
END_DATE = "2024-04-01"

# --------------------------------------------------
# DYNAMIC WORLD
# --------------------------------------------------

dw = (
    ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
    .filterDate(START_DATE, END_DATE)
    .filterBounds(buffer_1km)
    .select("built")
    .sort("system:time_start")
)

images = dw.toList(dw.size())
image_count = dw.size().getInfo()

# --------------------------------------------------
# BUFFER ALANI
# --------------------------------------------------
# Eski sürümde piksel sayisi üzerinden kapsama hesapliyorduk.
# Bu, farklı projeksiyonlar nedeniyle hatali sonuç verebilir.
#
# Artik gerçek alan üzerinden hesap yapiyoruz.

buffer_area_m2 = buffer_1km.area(maxError=1).getInfo()

print("=" * 82)
print("DYNAMIC WORLD - KEPEZ TARIH BAZLI KAPSAMA KONTROLU")
print("=" * 82)

print(f"Donem               : {START_DATE} - {END_DATE}")
print("Buffer              : 1 km")
print(f"Toplam image sayisi : {image_count}")
print(f"Buffer alani        : {buffer_area_m2:.2f} m2")

print()
print(
    f"{'Tarih':<12}"
    f"{'Gecerli Alan m2':>20}"
    f"{'Kapsama %':>14}"
    f"{'Built Ort.':>14}"
)

print("-" * 60)

results = []

# --------------------------------------------------
# HER TARIH ICIN KAPSAMA VE BUILT ORTALAMASI
# --------------------------------------------------

for i in range(image_count):

    image = ee.Image(images.get(i))

    timestamp = image.get("system:time_start").getInfo()

    date = datetime.fromtimestamp(
        timestamp / 1000,
        tz=timezone.utc
    ).strftime("%Y-%m-%d")

    # --------------------------------------------------
    # GECERLI ALAN
    # --------------------------------------------------
    # pixelArea her pikselin alanini m2 olarak verir.
    #
    # updateMask(image.mask()) ile sadece o tarihte
    # Dynamic World 'built' verisinin gecerli oldugu
    # pikselleri tutuyoruz.

    valid_area_image = (
        ee.Image.pixelArea()
        .updateMask(image.mask())
    )

    valid_area_stats = valid_area_image.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=buffer_1km,
        scale=10,
        maxPixels=1_000_000
    ).getInfo()

    valid_area_m2 = valid_area_stats.get("area", 0)

    if valid_area_m2 is None:
        valid_area_m2 = 0

    if buffer_area_m2 > 0:
        coverage_percent = (
            valid_area_m2 / buffer_area_m2
        ) * 100
    else:
        coverage_percent = None

    # --------------------------------------------------
    # O TARIHTEKI BUILT ORTALAMASI
    # --------------------------------------------------

    mean_stats = image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=buffer_1km,
        scale=10,
        maxPixels=1_000_000
    ).getInfo()

    built_mean = mean_stats.get("built")

    # --------------------------------------------------
    # SONUCU KAYDET
    # --------------------------------------------------

    results.append(
        {
            "date": date,
            "valid_area_m2": valid_area_m2,
            "coverage_percent": coverage_percent,
            "built_mean": built_mean,
        }
    )

    coverage_text = (
        f"{coverage_percent:.2f}"
        if coverage_percent is not None
        else "NA"
    )

    built_text = (
        f"{built_mean:.4f}"
        if built_mean is not None
        else "NA"
    )

    print(
        f"{date:<12}"
        f"{valid_area_m2:>20.2f}"
        f"{coverage_text:>14}"
        f"{built_text:>14}"
    )

# --------------------------------------------------
# OZET
# --------------------------------------------------

valid_coverages = [
    r["coverage_percent"]
    for r in results
    if r["coverage_percent"] is not None
]

valid_built_means = [
    r["built_mean"]
    for r in results
    if r["built_mean"] is not None
]

nonzero_coverages = [
    r["coverage_percent"]
    for r in results
    if (
        r["coverage_percent"] is not None
        and r["coverage_percent"] > 0
    )
]

print()
print("=" * 82)
print("OZET")
print("=" * 82)

if valid_coverages:
    print(
        f"Tum tarihler min kapsama       : "
        f"{min(valid_coverages):.2f}%"
    )

    print(
        f"Tum tarihler max kapsama       : "
        f"{max(valid_coverages):.2f}%"
    )

    print(
        f"Tum tarihler ort. kapsama      : "
        f"{sum(valid_coverages) / len(valid_coverages):.2f}%"
    )

if nonzero_coverages:
    print(
        f"Veri olan tarihler min kapsama : "
        f"{min(nonzero_coverages):.2f}%"
    )

    print(
        f"Veri olan tarihler ort. kapsama: "
        f"{sum(nonzero_coverages) / len(nonzero_coverages):.2f}%"
    )

if valid_built_means:
    print(
        f"Minimum tarih built ort.       : "
        f"{min(valid_built_means):.4f}"
    )

    print(
        f"Maksimum tarih built ort.      : "
        f"{max(valid_built_means):.4f}"
    )

    print(
        f"Ortalama tarih built ort.      : "
        f"{sum(valid_built_means) / len(valid_built_means):.4f}"
    )

print()
print(
    "NOT: Kapsama yüzdesi artık piksel sayisindan degil, "
    "gecerli Dynamic World piksel alaninin 1 km buffer "
    "alanina oranindan hesaplanmaktadir."
)