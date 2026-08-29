from pathlib import Path

import numpy as np
import rasterio


# ============================================================
# AYARLAR
# ============================================================

MAHALLE = "Oba"
YIL = 2026
DONEM = "İlkbahar"
DONEM_KLASORU = "ilkbahar"

population_file = (
    "outputs/oba/2026/"
    "population_100m_calibrated.tif"
)

ndvi_file = (
    "outputs/oba/2026/ilkbahar/"
    "ndvi_100m.tif"
)

lst_file = (
    "outputs/oba/2026/ilkbahar/"
    "lst_100m.tif"
)

output_file = (
    "outputs/oba/2026/ilkbahar/"
    "analiz_raporu.txt"
)


# ============================================================
# RASTER OKUMA
# ============================================================

def read_raster(file_path):

    with rasterio.open(file_path) as src:

        data = (
            src.read(1)
            .astype("float32")
        )

        nodata = src.nodata

        if nodata is not None:

            if np.isnan(nodata):
                pass

            else:
                data[
                    data == nodata
                ] = np.nan

        return data


population = read_raster(
    population_file
)

ndvi = read_raster(
    ndvi_file
)

lst = read_raster(
    lst_file
)


# ============================================================
# NÜFUS
# ============================================================

population[
    ~np.isfinite(population)
] = 0

population[
    population < 0
] = 0


population_mask = (
    population > 0
)

total_population = float(
    np.sum(
        population[
            population_mask
        ]
    )
)

population_grid_count = int(
    np.sum(
        population_mask
    )
)

mean_population_per_grid = float(
    np.mean(
        population[
            population_mask
        ]
    )
)

median_population_per_grid = float(
    np.median(
        population[
            population_mask
        ]
    )
)


# ============================================================
# NDVI
# ============================================================

ndvi_valid = (
    population_mask
    &
    np.isfinite(ndvi)
    &
    (ndvi >= -1)
    &
    (ndvi <= 1)
)

ndvi_population = population[
    ndvi_valid
]

ndvi_values = ndvi[
    ndvi_valid
]

ndvi_total_population = float(
    np.sum(
        ndvi_population
    )
)


# Ağırlıksız ve nüfus-ağırlıklı NDVI

unweighted_ndvi = float(
    np.mean(
        ndvi_values
    )
)

weighted_ndvi = float(
    np.sum(
        ndvi_values
        *
        ndvi_population
    )
    /
    ndvi_total_population
)


# ============================================================
# NDVI SINIFLARI
# ============================================================

ndvi_classes = [

    (
        "Düşük yeşillik maruziyeti (NDVI < 0.20)",
        ndvi_values < 0.20
    ),

    (
        "Düşük-orta yeşillik maruziyeti (0.20–0.30)",
        (
            (ndvi_values >= 0.20)
            &
            (ndvi_values < 0.30)
        )
    ),

    (
        "Orta yeşillik maruziyeti (0.30–0.50)",
        (
            (ndvi_values >= 0.30)
            &
            (ndvi_values < 0.50)
        )
    ),

    (
        "Yüksek yeşillik maruziyeti (NDVI ≥ 0.50)",
        ndvi_values >= 0.50
    )
]


ndvi_results = []

for name, mask in ndvi_classes:

    class_population = float(
        np.sum(
            ndvi_population[
                mask
            ]
        )
    )

    percentage = (
        class_population
        /
        ndvi_total_population
        *
        100
    )

    ndvi_results.append(
        (
            name,
            class_population,
            percentage
        )
    )


# ============================================================
# YÜKSEK NÜFUS + DÜŞÜK YEŞİLLİK
# ============================================================

population_p90_ndvi = float(
    np.percentile(
        ndvi_population,
        90
    )
)

critical_green_mask = (
    ndvi_valid
    &
    (population >= population_p90_ndvi)
    &
    (ndvi < 0.20)
)

critical_green_population = float(
    np.sum(
        population[
            critical_green_mask
        ]
    )
)

critical_green_grid_count = int(
    np.sum(
        critical_green_mask
    )
)

critical_green_percentage = (
    critical_green_population
    /
    ndvi_total_population
    *
    100
)


# ============================================================
# LST
# ============================================================

lst_valid = (
    population_mask
    &
    np.isfinite(lst)
    &
    (lst > -20)
    &
    (lst < 70)
)

lst_population = population[
    lst_valid
]

lst_values = lst[
    lst_valid
]

lst_total_population = float(
    np.sum(
        lst_population
    )
)


# ============================================================
# AĞIRLIKLI / AĞIRLIKSIZ LST
# ============================================================

unweighted_lst = float(
    np.mean(
        lst_values
    )
)

weighted_lst = float(
    np.sum(
        lst_values
        *
        lst_population
    )
    /
    lst_total_population
)

lst_difference = (
    weighted_lst
    -
    unweighted_lst
)


# ============================================================
# LST EŞİKLERİ
# ============================================================

lst_median = float(
    np.percentile(
        lst_values,
        50
    )
)

lst_p75 = float(
    np.percentile(
        lst_values,
        75
    )
)

lst_p90 = float(
    np.percentile(
        lst_values,
        90
    )
)


thermal_classes = [

    (
        "Göreli olarak daha düşük termal yük (< medyan)",
        lst_values < lst_median
    ),

    (
        "Orta termal yük (medyan–%75)",
        (
            (lst_values >= lst_median)
            &
            (lst_values < lst_p75)
        )
    ),

    (
        "Yüksek termal yük (%75–%90)",
        (
            (lst_values >= lst_p75)
            &
            (lst_values < lst_p90)
        )
    ),

    (
        "En yüksek termal yük dilimi (≥ %90)",
        lst_values >= lst_p90
    )
]


thermal_results = []

for name, mask in thermal_classes:

    class_population = float(
        np.sum(
            lst_population[
                mask
            ]
        )
    )

    percentage = (
        class_population
        /
        lst_total_population
        *
        100
    )

    thermal_results.append(
        (
            name,
            class_population,
            percentage
        )
    )


# ============================================================
# YÜKSEK NÜFUS + YÜKSEK TERMAL YÜK
# ============================================================

population_p90_lst = float(
    np.percentile(
        lst_population,
        90
    )
)

critical_heat_mask = (
    lst_valid
    &
    (population >= population_p90_lst)
    &
    (lst >= lst_p90)
)

critical_heat_population = float(
    np.sum(
        population[
            critical_heat_mask
        ]
    )
)

critical_heat_grid_count = int(
    np.sum(
        critical_heat_mask
    )
)

critical_heat_percentage = (
    critical_heat_population
    /
    lst_total_population
    *
    100
)


# ============================================================
# RAPOR OLUŞTUR
# ============================================================

lines = []

lines.append(
    "=" * 70
)

lines.append(
    f"{MAHALLE.upper()} MAHALLESİ "
    f"{YIL} {DONEM.upper()} ÇEVRESEL MARUZİYET RAPORU"
)

lines.append(
    "=" * 70
)


# ------------------------------------------------------------
# NÜFUS
# ------------------------------------------------------------

lines.append("")
lines.append("1. NÜFUS VE ANALİZ GRIDİ")
lines.append("-" * 70)

lines.append(
    f"{MAHALLE} Mahallesi için analizde kullanılan "
    f"kalibre edilmiş toplam nüfus yaklaşık "
    f"{total_population:,.0f} kişidir."
)

lines.append(
    f"Nüfus bulunan toplam {population_grid_count:,} adet "
    f"yaklaşık 100 m çözünürlüklü grid hücresi analiz edilmiştir."
)

lines.append(
    f"Nüfus bulunan gridlerde ortalama "
    f"{mean_population_per_grid:.2f} kişi/grid, "
    f"medyan ise {median_population_per_grid:.2f} kişi/grid'dir."
)


# ------------------------------------------------------------
# YEŞİLLİK
# ------------------------------------------------------------

lines.append("")
lines.append("2. YEŞİLLİK MARUZİYETİ — NDVI")
lines.append("-" * 70)

lines.append(
    f"{DONEM} döneminde nüfus bulunan gridlerin "
    f"ağırlıksız ortalama NDVI değeri "
    f"{unweighted_ndvi:.4f}'tür."
)

lines.append(
    f"Nüfus-ağırlıklı NDVI değeri ise "
    f"{weighted_ndvi:.4f}'tür."
)

lines.append(
    f"Nüfus-ağırlıklı değerin daha düşük olması, "
    f"nüfusun daha az yeşil gridlerde yoğunlaşma "
    f"eğilimi gösterdiğini belirtmektedir."
)

lines.append("")

for (
    name,
    class_population,
    percentage
) in ndvi_results:

    lines.append(
        f"- {name}: "
        f"yaklaşık {class_population:,.0f} kişi "
        f"(%{percentage:.2f})"
    )


lines.append("")

lines.append(
    f"Yüksek nüfus yoğunluğuna sahip ve NDVI < 0.20 olan "
    f"{critical_green_grid_count} gridde yaklaşık "
    f"{critical_green_population:,.0f} kişi yaşamaktadır. "
    f"Bu değer analiz edilen nüfusun "
    f"%{critical_green_percentage:.2f}'sine karşılık gelmektedir."
)


# ------------------------------------------------------------
# TERMAL YÜK
# ------------------------------------------------------------

lines.append("")
lines.append("3. TERMAL YÜK — LANDSAT LST")
lines.append("-" * 70)

lines.append(
    f"{DONEM} döneminde nüfus bulunan gridlerde "
    f"ağırlıksız ortalama arazi yüzey sıcaklığı "
    f"{unweighted_lst:.2f} °C'dir."
)

lines.append(
    f"Nüfus-ağırlıklı arazi yüzey sıcaklığı ise "
    f"{weighted_lst:.2f} °C'dir."
)

lines.append(
    f"Nüfus-ağırlıklı sıcaklık, ağırlıksız değerden "
    f"{lst_difference:+.2f} °C farklıdır."
)

if lst_difference > 0:

    lines.append(
        "Bu sonuç, nüfusun göreli olarak daha sıcak "
        "yüzey sıcaklığına sahip gridlerde yoğunlaştığını "
        "göstermektedir."
    )

elif lst_difference < 0:

    lines.append(
        "Bu sonuç, nüfusun göreli olarak daha serin "
        "gridlerde yoğunlaştığını göstermektedir."
    )

else:

    lines.append(
        "Nüfus dağılımı ile ortalama yüzey sıcaklığı "
        "arasında belirgin bir ağırlık farkı görülmemektedir."
    )


lines.append("")

lines.append(
    f"Yerel termal dağılım eşikleri: "
    f"medyan {lst_median:.2f} °C, "
    f"%75 eşiği {lst_p75:.2f} °C ve "
    f"%90 eşiği {lst_p90:.2f} °C'dir."
)

lines.append("")

for (
    name,
    class_population,
    percentage
) in thermal_results:

    lines.append(
        f"- {name}: "
        f"yaklaşık {class_population:,.0f} kişi "
        f"(%{percentage:.2f})"
    )


lines.append("")

lines.append(
    f"Yüksek nüfus yoğunluğu ile yerel LST dağılımının "
    f"en sıcak %10'luk diliminin kesiştiği "
    f"{critical_heat_grid_count} gridde yaklaşık "
    f"{critical_heat_population:,.0f} kişi yaşamaktadır. "
    f"Bu değer toplam nüfusun "
    f"%{critical_heat_percentage:.2f}'sidir."
)


# ------------------------------------------------------------
# BİLİMSEL NOT
# ------------------------------------------------------------

lines.append("")
lines.append("4. YÖNTEMSEL NOT")
lines.append("-" * 70)

lines.append(
    "NDVI sonuçları yeşil alanın doğrudan kullanımını veya "
    "kamusal erişilebilirliğini değil, nüfusun yaşadığı "
    "gridlerdeki bitkisel yeşillik maruziyetini temsil eder."
)

lines.append(
    "LST değerleri hava sıcaklığı değil, Landsat 8/9 "
    "Collection 2 Level-2 verisinden elde edilen arazi "
    "yüzey sıcaklığıdır."
)

lines.append(
    "NDVI < 0.20 ve %90 LST eşikleri bu aşamada "
    "pilot/göreli sınıflandırmalardır; sağlık veya evrensel "
    "risk eşikleri olarak yorumlanmamalıdır."
)

lines.append(
    "Yeşillik ve termal yük birbirinden bağımsız "
    "çevresel bileşenler olarak raporlanmıştır."
)

lines.append(
    "=" * 70
)


# ============================================================
# EKRANA YAZ
# ============================================================

report = "\n".join(
    lines
)

print(
    "\n"
    + report
)


# ============================================================
# DOSYAYA KAYDET
# ============================================================

output_path = Path(
    output_file
)

output_path.parent.mkdir(
    parents=True,
    exist_ok=True
)

with open(
    output_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        report
    )


print(
    "\n[OK] Rapor kaydedildi:"
)

print(
    output_file
)