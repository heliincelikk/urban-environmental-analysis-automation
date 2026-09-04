import ee
import folium
import pandas as pd
import os
import webbrowser

PROJECT_ID = "antalya-environmental-analysis"

ee.Initialize(project=PROJECT_ID)

# --------------------------------------------------
# AYARLAR
# --------------------------------------------------

STATION_FILE = "data/pm10/processed/pm10_istasyonlar.csv"

START_DATE = "2024-01-01"
END_DATE = "2024-04-01"

BUFFER_M = 1000

OUTPUT_DIR = "outputs/pm10/dynamic_world_qc/all_stations"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --------------------------------------------------
# FOLIUM ICIN EARTH ENGINE KATMAN FONKSIYONU
# --------------------------------------------------

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


# --------------------------------------------------
# ISTASYONLARI OKU
# --------------------------------------------------

stations = pd.read_csv(STATION_FILE)

# --------------------------------------------------
# ORTAK DYNAMIC WORLD KOLEKSIYONU
# --------------------------------------------------

dw_all = (
    ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
    .filterDate(START_DATE, END_DATE)
)

# --------------------------------------------------
# HER ISTASYON ICIN HARITA
# --------------------------------------------------

created_files = []

for _, row in stations.iterrows():

    station_name = row["istasyon"]
    station_type = row["tip"]

    lat = float(row["enlem"])
    lon = float(row["boylam"])

    point = ee.Geometry.Point([lon, lat])
    buffer_1km = point.buffer(BUFFER_M)

    # --------------------------------------------------
    # DYNAMIC WORLD Q1 MEAN BUILT
    # --------------------------------------------------

    dw_station = (
        dw_all
        .filterBounds(buffer_1km)
        .select("built")
    )

    built_q1_mean = (
        dw_station
        .mean()
        .clip(buffer_1km)
    )

    # --------------------------------------------------
    # SENTINEL-2 Q1 MEDIAN RGB
    # --------------------------------------------------
    # Tek bir günü seçmek yerine bütün Q1 döneminin
    # Sentinel-2 median kompozitini kullanıyoruz.
    #
    # Amaç burada görsel arazi kontrolü yapmak,
    # atmosferik/temporal analiz yapmak değil.

    s2_q1 = (
        ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
        .filterDate(START_DATE, END_DATE)
        .filterBounds(buffer_1km)
        .filter(
            ee.Filter.lt(
                "CLOUDY_PIXEL_PERCENTAGE",
                35
            )
        )
        .median()
        .clip(buffer_1km)
    )

    # --------------------------------------------------
    # HARITA
    # --------------------------------------------------

    m = folium.Map(
        location=[lat, lon],
        zoom_start=14,
        control_scale=True
    )

    # --------------------------------------------------
    # SENTINEL-2 RGB
    # --------------------------------------------------

    s2_vis = {
        "bands": ["B4", "B3", "B2"],
        "min": 0,
        "max": 3000,
        "gamma": 1.1
    }

    add_ee_layer(
        m,
        s2_q1,
        s2_vis,
        "Sentinel-2 Q1 median RGB",
        opacity=1.0
    )

    # --------------------------------------------------
    # DYNAMIC WORLD BUILT
    # --------------------------------------------------

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
        built_q1_mean,
        built_vis,
        "Dynamic World built - 2024 Q1 mean",
        opacity=0.65
    )

    # --------------------------------------------------
    # ISTASYON NOKTASI
    # --------------------------------------------------

    folium.Marker(
        location=[lat, lon],
        popup=(
            f"{station_name}<br>"
            f"Type: {station_type}"
        ),
        tooltip=station_name
    ).add_to(m)

    # --------------------------------------------------
    # 1 KM BUFFER
    # --------------------------------------------------

    folium.GeoJson(
        buffer_1km.getInfo(),
        name="1 km buffer",
        style_function=lambda feature: {
            "fillOpacity": 0,
            "weight": 3
        }
    ).add_to(m)

    # --------------------------------------------------
    # KATMAN KONTROLU
    # --------------------------------------------------

    folium.LayerControl(
        collapsed=False
    ).add_to(m)

    # --------------------------------------------------
    # HTML KAYDET
    # --------------------------------------------------

    output_file = os.path.abspath(
        os.path.join(
            OUTPUT_DIR,
            f"{station_name}_dynamic_world_q1_qc.html"
        )
    )

    m.save(output_file)

    created_files.append(output_file)

    print(
        f"[OK] {station_name:<12} -> "
        f"{output_file}"
    )

# --------------------------------------------------
# SONUC
# --------------------------------------------------

print()
print("=" * 80)
print("8 ISTASYON ICIN GORSEL QC HARITALARI OLUSTURULDU")
print("=" * 80)

print()
print("Dosyalar:")

for file_path in created_files:
    print(file_path)

print()
print(
    "Ilk harita tarayicida aciliyor..."
)

if created_files:
    webbrowser.open(
        "file:///" +
        created_files[0].replace("\\", "/")
    )