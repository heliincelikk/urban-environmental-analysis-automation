import ee
import folium
import os
import webbrowser

# ============================================================
# EARTH ENGINE
# ============================================================

PROJECT_ID = "antalya-environmental-analysis"

ee.Initialize(project=PROJECT_ID)

# ============================================================
# KEPEZ
# ============================================================

KEPEZ_LON = 30.700425
KEPEZ_LAT = 36.914883

kepez = ee.Geometry.Point([KEPEZ_LON, KEPEZ_LAT])
buffer_1km = kepez.buffer(1000)

# ============================================================
# DONEM
# ============================================================

START_DATE = "2024-01-01"
END_DATE = "2024-04-01"

# Görsel kontrolde özellikle tam kapsama gördüğümüz
# tarihlerden birini kullanıyoruz.
QC_DATE_START = "2024-03-21"
QC_DATE_END = "2024-03-22"

# ============================================================
# DYNAMIC WORLD - Q1 ORTALAMA BUILT
# ============================================================

dw_q1 = (
    ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
    .filterDate(START_DATE, END_DATE)
    .filterBounds(buffer_1km)
    .select("built")
)

built_q1_mean = dw_q1.mean().clip(buffer_1km)

# ============================================================
# DYNAMIC WORLD - TEK TARIH
# ============================================================

dw_day = (
    ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
    .filterDate(QC_DATE_START, QC_DATE_END)
    .filterBounds(buffer_1km)
    .select("built")
    .mosaic()
    .clip(buffer_1km)
)

# ============================================================
# SENTINEL-2 - AYNI TARIH
# ============================================================
# Dynamic World Sentinel-2 goruntulerinden uretilir.
# Bu nedenle ayni gunun Sentinel-2 RGB goruntusunu
# karsilastirma icin kullaniyoruz.

s2_day = (
    ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
    .filterDate(QC_DATE_START, QC_DATE_END)
    .filterBounds(buffer_1km)
    .sort("CLOUDY_PIXEL_PERCENTAGE")
    .mosaic()
    .clip(buffer_1km)
)

# ============================================================
# FOLIUM ICIN EARTH ENGINE KATMAN FONKSIYONU
# ============================================================

def add_ee_layer(
    map_object,
    ee_image,
    vis_params,
    name,
    opacity=1.0
):
    map_id = ee.Image(ee_image).getMapId(vis_params)

    folium.raster_layers.TileLayer(
        tiles=map_id["tile_fetcher"].url_format,
        attr="Google Earth Engine",
        name=name,
        overlay=True,
        control=True,
        opacity=opacity
    ).add_to(map_object)

# ============================================================
# HARITA
# ============================================================

m = folium.Map(
    location=[KEPEZ_LAT, KEPEZ_LON],
    zoom_start=14,
    control_scale=True
)

# ------------------------------------------------------------
# SENTINEL-2 RGB
# ------------------------------------------------------------

s2_vis = {
    "bands": ["B4", "B3", "B2"],
    "min": 0,
    "max": 3000,
    "gamma": 1.1
}

add_ee_layer(
    m,
    s2_day,
    s2_vis,
    "Sentinel-2 RGB - 2024-03-21",
    opacity=1.0
)

# ------------------------------------------------------------
# DYNAMIC WORLD BUILT - AYNI TARIH
# ------------------------------------------------------------
# Renk skalasi:
# koyu = dusuk built olasiligi
# acik = yuksek built olasiligi
#
# Buradaki renkler sadece gorsel inceleme icindir.

built_vis = {
    "min": 0,
    "max": 1,
    "palette": [
        "000004",
        "3b0f70",
        "8c2981",
        "de4968",
        "fe9f6d",
        "fcfdbf"
    ]
}

add_ee_layer(
    m,
    dw_day,
    built_vis,
    "Dynamic World built - 2024-03-21",
    opacity=0.65
)

# ------------------------------------------------------------
# DYNAMIC WORLD Q1 MEAN
# ------------------------------------------------------------

add_ee_layer(
    m,
    built_q1_mean,
    built_vis,
    "Dynamic World built - 2024 Q1 mean",
    opacity=0.65
)

# ============================================================
# KEPEZ ISTASYONU
# ============================================================

folium.Marker(
    location=[KEPEZ_LAT, KEPEZ_LON],
    popup="Kepez PM10 Station",
    tooltip="Kepez PM10 Station"
).add_to(m)

# ============================================================
# 1 KM BUFFER
# ============================================================

buffer_geojson = buffer_1km.getInfo()

folium.GeoJson(
    buffer_geojson,
    name="1 km buffer",
    style_function=lambda feature: {
        "fillOpacity": 0,
        "weight": 3
    }
).add_to(m)

# ============================================================
# KATMAN KONTROLU
# ============================================================

folium.LayerControl(collapsed=False).add_to(m)

# ============================================================
# HTML KAYDET
# ============================================================

output_dir = os.path.join(
    "outputs",
    "pm10",
    "dynamic_world_qc"
)

os.makedirs(output_dir, exist_ok=True)

output_file = os.path.abspath(
    os.path.join(
        output_dir,
        "kepez_dynamic_world_visual_qc.html"
    )
)

m.save(output_file)

print("=" * 70)
print("DYNAMIC WORLD - KEPEZ GORSEL QC")
print("=" * 70)
print()
print(f"HTML olusturuldu:")
print(output_file)
print()
print("Harita tarayicida aciliyor...")

webbrowser.open(
    "file:///" + output_file.replace("\\", "/")
)