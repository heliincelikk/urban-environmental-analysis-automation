import ee
from datetime import datetime, timezone

# ============================================================
# DYNAMIC WORLD - KEPEZ PILOT KALITE KONTROLU
# ============================================================

PROJECT_ID = "antalya-environmental-analysis"

ee.Initialize(project=PROJECT_ID)


# ------------------------------------------------------------
# 1. KEPEZ ISTASYONU
# ------------------------------------------------------------

KEPEZ_LON = 30.700425
KEPEZ_LAT = 36.914883

kepez = ee.Geometry.Point([KEPEZ_LON, KEPEZ_LAT])
buffer_1km = kepez.buffer(1000)


# ------------------------------------------------------------
# 2. ANALIZ DONEMI
# ------------------------------------------------------------

START_DATE = "2024-01-01"
END_DATE = "2024-04-01"


# ------------------------------------------------------------
# 3. DYNAMIC WORLD KOLEKSIYONU
# ------------------------------------------------------------

dw = (
    ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
    .filterDate(START_DATE, END_DATE)
    .filterBounds(buffer_1km)
)

dw_built = dw.select("built")


# ------------------------------------------------------------
# 4. KOLEKSIYON GORUNTU SAYISI
# ------------------------------------------------------------

image_count = dw.size().getInfo()


# ------------------------------------------------------------
# 5. GORUNTU TARIHLERI
# ------------------------------------------------------------
# Aynı tarihte birden fazla Sentinel-2 granulu bulunabilir.
# Bu nedenle toplam image sayisi ile benzersiz gun sayisini
# ayri kontrol ediyoruz.

timestamps = dw.aggregate_array("system:time_start").getInfo()

dates = [
    datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    for ts in timestamps
]

unique_dates = sorted(set(dates))


# ------------------------------------------------------------
# 6. BUILT OLASILIGININ ZAMANSAL ORTALAMASI
# ------------------------------------------------------------

built_temporal_mean = dw_built.mean()


# ------------------------------------------------------------
# 7. 1 KM BUFFER ICIN ORTALAMA BUILT OLASILIGI
# ------------------------------------------------------------

mean_stats = built_temporal_mean.reduceRegion(
    reducer=ee.Reducer.mean(),
    geometry=buffer_1km,
    scale=10,
    maxPixels=1_000_000
).getInfo()

mean_built_probability = mean_stats.get("built")


# ------------------------------------------------------------
# 8. MEKANSAL DAGILIM
# ------------------------------------------------------------
# Buffer içindeki piksellerin temporal-mean built probability
# dagilimini inceliyoruz.
#
# Bu bize tek ortalama degerin arkasinda nasil bir dagilim
# oldugunu gosterecek.

percentile_stats = built_temporal_mean.reduceRegion(
    reducer=ee.Reducer.percentile([10, 25, 50, 75, 90]),
    geometry=buffer_1km,
    scale=10,
    maxPixels=1_000_000
).getInfo()


# ------------------------------------------------------------
# 9. GECERLI GOZLEM SAYISI
# ------------------------------------------------------------

observation_count = dw_built.count()

count_stats = observation_count.reduceRegion(
    reducer=ee.Reducer.mean().combine(
        reducer2=ee.Reducer.minMax(),
        sharedInputs=True
    ),
    geometry=buffer_1km,
    scale=10,
    maxPixels=1_000_000
).getInfo()


# ------------------------------------------------------------
# 10. ALTERNATIF KONTROL:
#     MODE LABEL COMPOSITE
# ------------------------------------------------------------
# Dynamic World label:
# 0 water
# 1 trees
# 2 grass
# 3 flooded_vegetation
# 4 crops
# 5 shrub_and_scrub
# 6 built
# 7 bare
# 8 snow_and_ice
#
# Burada her piksel icin donem boyunca en sik gorulen
# sinifi buluyoruz.

label_mode = dw.select("label").mode()

built_mode_mask = label_mode.eq(6)

mode_fraction_stats = built_mode_mask.reduceRegion(
    reducer=ee.Reducer.mean(),
    geometry=buffer_1km,
    scale=10,
    maxPixels=1_000_000
).getInfo()

mode_built_fraction = mode_fraction_stats.get("label")


# ------------------------------------------------------------
# 11. SONUCLAR
# ------------------------------------------------------------

print("=" * 65)
print("DYNAMIC WORLD - KEPEZ PILOT KALITE KONTROLU")
print("=" * 65)

print()
print("DONEM")
print("-----")
print(f"Baslangic            : {START_DATE}")
print(f"Bitis                : {END_DATE}")
print("Buffer               : 1 km")

print()
print("GORUNTU / TARIH KONTROLU")
print("------------------------")
print(f"Toplam image sayisi  : {image_count}")
print(f"Benzersiz tarih      : {len(unique_dates)}")

print()
print("Benzersiz tarihler:")
for date in unique_dates:
    print(f"  {date}")

print()
print("MEAN BUILT PROBABILITY")
print("----------------------")
print(
    f"Buffer ortalamasi     : "
    f"{mean_built_probability:.6f}"
)

print()
print("PIKSEL DAGILIMI")
print("---------------")
print(
    f"P10                   : "
    f"{percentile_stats.get('built_p10')}"
)
print(
    f"P25                   : "
    f"{percentile_stats.get('built_p25')}"
)
print(
    f"Median (P50)          : "
    f"{percentile_stats.get('built_p50')}"
)
print(
    f"P75                   : "
    f"{percentile_stats.get('built_p75')}"
)
print(
    f"P90                   : "
    f"{percentile_stats.get('built_p90')}"
)

print()
print("GECERLI GOZLEM SAYISI")
print("---------------------")
print(
    f"Piksel basi ortalama  : "
    f"{count_stats.get('built_mean')}"
)
print(
    f"Minimum               : "
    f"{count_stats.get('built_min')}"
)
print(
    f"Maksimum              : "
    f"{count_stats.get('built_max')}"
)

print()
print("MODE LABEL KONTROLU")
print("-------------------")
print(
    f"Mode composite built fraction : "
    f"{mode_built_fraction}"
)

print()
print("=" * 65)
print("UYARI")
print("=" * 65)

print(
    "Mean built probability yapili alan yuzdesi degildir."
)

print(
    "Mode built fraction ise yalnizca Dynamic World "
    "siniflandirmasindan turetilen yardimci bir karsilastirma "
    "gostergesidir; resmi veya hatasiz yapili alan orani "
    "olarak yorumlanmamalidir."
)