from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import folium
import rasterio
import geopandas as gpd

from rasterio.features import shapes
from shapely.geometry import shape
from streamlit_folium import st_folium


# ============================================================
# SAYFA
# ============================================================

st.set_page_config(
    page_title="Kentsel Çevresel Maruziyet",
    page_icon="🌍",
    layout="wide"
)

BASE_DIR = Path(__file__).parent


# ============================================================
# ANALİZ SENARYOLARI
# ============================================================

SCENARIOS = {
    "Oba": {
        "boundary": (
            BASE_DIR
            / "data"
            / "boundaries"
            / "oba_pilot_sinir.geojson"
        ),

        "population": (
            BASE_DIR
            / "outputs"
            / "oba"
            / "2026"
            / "population_100m_calibrated.tif"
        ),

        "periods": {
            "İlkbahar": {
                "folder": "ilkbahar",
                "dates": "1 Mart – 31 Mayıs 2026"
            },

            "Yaz": {
                "folder": "yaz",
                "dates": "1 Haziran – 30 Ağustos 2026"
            }
        }
    },

    "Mahmutlar": {
        "boundary": (
            BASE_DIR
            / "data"
            / "boundaries"
            / "mahmutlar_belediye_sinir_DUZELTILMIS.geojson"
        ),

        "population": (
            BASE_DIR
            / "outputs"
            / "mahmutlar"
            / "2026"
            / "population_100m_calibrated.tif"
        ),

        "periods": {
            "İlkbahar": {
                "folder": "ilkbahar",
                "dates": "1 Mart – 31 Mayıs 2026"
            },

            "Yaz": {
                "folder": "yaz",
                "dates": "1 Haziran – 30 Ağustos 2026"
            }
        }
    }
}


# ============================================================
# OKUMA FONKSİYONLARI
# ============================================================

def read_raster(path):

    with rasterio.open(path) as src:

        data = (
            src.read(1)
            .astype("float32")
        )

        nodata = src.nodata

        if nodata is not None:

            if not np.isnan(nodata):
                data[
                    data == nodata
                ] = np.nan

        return {
            "data": data,
            "transform": src.transform,
            "crs": src.crs
        }


def read_boundary(path):

    gdf = gpd.read_file(path)

    return gdf.to_crs(
        "EPSG:4326"
    )


# ============================================================
# RASTER -> HARİTA HÜCRELERİ
# ============================================================

def raster_to_cells(
    population_path,
    value_path
):

    with rasterio.open(
        population_path
    ) as pop_src:

        pop = (
            pop_src.read(1)
            .astype("float32")
        )

        transform = pop_src.transform
        crs = pop_src.crs

        if pop_src.nodata is not None:

            pop[
                pop == pop_src.nodata
            ] = np.nan


    with rasterio.open(
        value_path
    ) as value_src:

        values = (
            value_src.read(1)
            .astype("float32")
        )

        if value_src.nodata is not None:

            values[
                values == value_src.nodata
            ] = np.nan


    valid = (
        np.isfinite(pop)
        &
        (pop > 0)
        &
        np.isfinite(values)
    )


    rows = []


    for geometry, _ in shapes(
        values,
        mask=valid,
        transform=transform
    ):

        polygon = shape(
            geometry
        )

        centroid = (
            polygon.centroid
        )

        row, col = rasterio.transform.rowcol(
            transform,
            centroid.x,
            centroid.y
        )


        if (
            row < 0
            or col < 0
            or row >= pop.shape[0]
            or col >= pop.shape[1]
        ):
            continue


        rows.append({
            "geometry": polygon,

            "population": float(
                pop[
                    row,
                    col
                ]
            ),

            "value": float(
                values[
                    row,
                    col
                ]
            )
        })


    gdf = gpd.GeoDataFrame(
        rows,
        crs=crs
    )

    return gdf.to_crs(
        "EPSG:4326"
    )


# ============================================================
# SINIFLANDIRMALAR
# ============================================================

def ndvi_category(value):

    if value < 0.20:
        return (
            "Çok düşük yeşillik",
            "#d73027"
        )

    if value < 0.30:
        return (
            "Düşük yeşillik",
            "#fc8d59"
        )

    if value < 0.50:
        return (
            "Orta yeşillik",
            "#fee08b"
        )

    return (
        "Yüksek yeşillik",
        "#1a9850"
    )


def lst_category(
    value,
    median,
    p75,
    p90
):

    if value < median:
        return (
            "Göreli olarak daha düşük termal yük",
            "#ffffcc"
        )

    if value < p75:
        return (
            "Orta termal yük",
            "#feb24c"
        )

    if value < p90:
        return (
            "Yüksek termal yük",
            "#fd8d3c"
        )

    return (
        "En yüksek termal yük grubu",
        "#bd0026"
    )


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "🌍 Analiz Seçimi"
)

mahalle = st.sidebar.selectbox(
    "Mahalle",
    list(
        SCENARIOS.keys()
    )
)

year = st.sidebar.selectbox(
    "Yıl",
    [2026]
)

period = st.sidebar.selectbox(
    "Dönem",
    list(
        SCENARIOS[
            mahalle
        ][
            "periods"
        ].keys()
    )
)

component = st.sidebar.radio(
    "Ne görmek istiyorsunuz?",
    [
        "🌿 Yeşillik Durumu",
        "🌡️ Termal Yük",
        "🌫️ Hava Kirliliği / PM10",
        "🚗 Ulaşım Kaynaklı Baskı"
    ]
)


# ============================================================
# DOSYA YOLLARI
# ============================================================

scenario = (
    SCENARIOS[
        mahalle
    ]
)

period_info = (
    scenario[
        "periods"
    ][
        period
    ]
)

season_folder = (
    period_info[
        "folder"
    ]
)

date_text = (
    period_info[
        "dates"
    ]
)


BOUNDARY_FILE = (
    scenario[
        "boundary"
    ]
)

POPULATION_FILE = (
    scenario[
        "population"
    ]
)

NDVI_FILE = (
    BASE_DIR
    / "outputs"
    / mahalle.lower()
    / str(year)
    / season_folder
    / "ndvi_100m.tif"
)

LST_FILE = (
    BASE_DIR
    / "outputs"
    / mahalle.lower()
    / str(year)
    / season_folder
    / "lst_100m.tif"
)


# ============================================================
# DOSYA KONTROLÜ
# ============================================================

required_files = [
    POPULATION_FILE,
    NDVI_FILE,
    LST_FILE,
    BOUNDARY_FILE
]

missing = [
    str(path)
    for path in required_files
    if not path.exists()
]

if missing:

    st.error(
        "Bazı analiz dosyaları bulunamadı."
    )

    st.code(
        "\n".join(
            missing
        )
    )

    st.stop()


# ============================================================
# VERİLER
# ============================================================

population = read_raster(
    POPULATION_FILE
)["data"]

ndvi = read_raster(
    NDVI_FILE
)["data"]

lst = read_raster(
    LST_FILE
)["data"]

boundary = read_boundary(
    BOUNDARY_FILE
)


population[
    ~np.isfinite(
        population
    )
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

grid_count = int(
    np.sum(
        population_mask
    )
)


# ============================================================
# NDVI
# ============================================================

ndvi_valid = (
    population_mask
    &
    np.isfinite(
        ndvi
    )
)

ndvi_population = (
    population[
        ndvi_valid
    ]
)

ndvi_values = (
    ndvi[
        ndvi_valid
    ]
)


weighted_ndvi = float(
    np.sum(
        ndvi_population
        *
        ndvi_values
    )
    /
    np.sum(
        ndvi_population
    )
)


low_green_population = float(
    np.sum(
        population[
            ndvi_valid
            &
            (ndvi < 0.20)
        ]
    )
)


low_green_ratio = (
    low_green_population
    /
    total_population
    *
    100
)


high_green_population = float(
    np.sum(
        population[
            ndvi_valid
            &
            (ndvi >= 0.50)
        ]
    )
)


high_green_ratio = (
    high_green_population
    /
    total_population
    *
    100
)


# ============================================================
# LST
# ============================================================

lst_valid = (
    population_mask
    &
    np.isfinite(
        lst
    )
)

lst_population = (
    population[
        lst_valid
    ]
)

lst_values = (
    lst[
        lst_valid
    ]
)


weighted_lst = float(
    np.sum(
        lst_population
        *
        lst_values
    )
    /
    np.sum(
        lst_population
    )
)


unweighted_lst = float(
    np.mean(
        lst_values
    )
)


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


hot_population = float(
    np.sum(
        population[
            lst_valid
            &
            (lst >= lst_p90)
        ]
    )
)


hot_ratio = (
    hot_population
    /
    total_population
    *
    100
)


# ============================================================
# BAŞLIK
# ============================================================

st.title(
    "🌍 Kentsel Çevresel Maruziyet Analizi"
)

st.write(
    """
    Mahallede yaşayan nüfusun farklı çevresel
    koşullarla mekânsal ilişkisini inceleyen
    interaktif araştırma prototipi.
    """
)


st.markdown(
    f"""
    **📍 {mahalle} Mahallesi**  
    **📅 {period} {year}**  
    **🗓️ Analiz aralığı: {date_text}**
    """
)


# ============================================================
# GENEL KARTLAR
# ============================================================

c1, c2, c3 = st.columns(
    3
)

c1.metric(
    "Tahmini Toplam Nüfus",
    f"{total_population:,.0f} kişi"
)

c2.metric(
    "Nüfus Bulunan Analiz Bölgesi",
    f"{grid_count:,}"
)

c3.metric(
    "Analiz Çözünürlüğü",
    "≈ 100 m"
)


st.info(
    """
    💡 Haritadaki renkli alanların üzerine gelin.
    Seçtiğiniz bölgede yaklaşık kaç kişinin yaşadığını
    ve o bölgenin çevresel durumunu görebilirsiniz.
    """
)


# ============================================================
# HARİTA + SONUÇ
# ============================================================

map_col, result_col = st.columns(
    [2.2, 1]
)


with map_col:

    st.subheader(
        "🗺️ İnteraktif Harita"
    )


    if component == "🌿 Yeşillik Durumu":

        st.markdown(
            """
            **Renkler:**  
            🔴 Çok düşük → 🟠 Düşük →
            🟡 Orta → 🟢 Yüksek yeşillik
            """
        )


    elif component == "🌡️ Termal Yük":

        st.markdown(
            """
            **Renkler:**  
            🟡 Daha düşük → 🟠 Orta →
            🟥 Yüksek → 🔴 En yüksek termal yük
            """
        )


    center = (
        boundary.geometry
        .union_all()
        .centroid
    )


    m = folium.Map(
        location=[
            center.y,
            center.x
        ],
        zoom_start=13,
        tiles="OpenStreetMap"
    )


    # Mahalle sınırı
    folium.GeoJson(
        boundary.__geo_interface__,
        name="Mahalle sınırı",

        style_function=lambda x: {
            "fillOpacity": 0,
            "color": "black",
            "weight": 3
        }
    ).add_to(
        m
    )


    # ========================================================
    # NDVI
    # ========================================================

    if component == "🌿 Yeşillik Durumu":

        cells = raster_to_cells(
            str(
                POPULATION_FILE
            ),
            str(
                NDVI_FILE
            )
        )


        for _, row in cells.iterrows():

            value = row[
                "value"
            ]

            pop_value = row[
                "population"
            ]

            category, color = (
                ndvi_category(
                    value
                )
            )


            tooltip = (
                f"<b>Bu bölgede yaklaşık "
                f"{pop_value:.0f} kişi yaşıyor.</b>"
                f"<br><br>"
                f"Yeşillik durumu: "
                f"<b>{category}</b>"
                f"<br>"
                f"NDVI: {value:.3f}"
            )


            folium.GeoJson(
                row.geometry,

                style_function=(
                    lambda x,
                    color=color: {
                        "fillColor": color,
                        "color": color,
                        "weight": 0.2,
                        "fillOpacity": 0.70
                    }
                ),

                tooltip=folium.Tooltip(
                    tooltip
                )
            ).add_to(
                m
            )


    # ========================================================
    # LST
    # ========================================================

    elif component == "🌡️ Termal Yük":

        cells = raster_to_cells(
            str(
                POPULATION_FILE
            ),
            str(
                LST_FILE
            )
        )


        for _, row in cells.iterrows():

            value = row[
                "value"
            ]

            pop_value = row[
                "population"
            ]


            category, color = (
                lst_category(
                    value,
                    lst_median,
                    lst_p75,
                    lst_p90
                )
            )


            tooltip = (
                f"<b>Bu bölgede yaklaşık "
                f"{pop_value:.0f} kişi yaşıyor.</b>"
                f"<br><br>"
                f"Yüzey sıcaklığı: "
                f"<b>{value:.1f} °C</b>"
                f"<br>"
                f"Termal durum: "
                f"<b>{category}</b>"
            )


            folium.GeoJson(
                row.geometry,

                style_function=(
                    lambda x,
                    color=color: {
                        "fillColor": color,
                        "color": color,
                        "weight": 0.2,
                        "fillOpacity": 0.70
                    }
                ),

                tooltip=folium.Tooltip(
                    tooltip
                )
            ).add_to(
                m
            )


    elif component == "🌫️ Hava Kirliliği / PM10":

        st.info(
            """
            PM10 bileşeni için mekânsal analiz
            yöntemi geliştirilme aşamasındadır.
            """
        )


    elif component == "🚗 Ulaşım Kaynaklı Baskı":

        st.info(
            """
            Ulaşım kaynaklı çevresel baskı
            bileşeni geliştirilme aşamasındadır.
            """
        )


    st_folium(
        m,
        height=650,
        use_container_width=True
    )


# ============================================================
# SAĞ SONUÇ PANELİ
# ============================================================

with result_col:

    st.subheader(
        "📊 Bu Dönemde Ne Görüyoruz?"
    )


    if component == "🌿 Yeşillik Durumu":

        st.metric(
            "Düşük yeşillikli bölgelerde yaşayanlar",
            f"%{low_green_ratio:.1f}"
        )

        st.metric(
            "Yaklaşık kişi sayısı",
            f"{low_green_population:,.0f}"
        )


        st.write(
            f"""
            **{mahalle} Mahallesi'nde**
            {period.lower()} döneminde yaklaşık
            **{low_green_population:,.0f} kişi**,
            NDVI değeri 0.20'nin altında kalan
            bölgelerde yaşamaktadır.
            """
        )


        st.metric(
            "Yüksek yeşillikli bölgelerde yaşayanlar",
            f"%{high_green_ratio:.1f}"
        )


        with st.expander(
            "Teknik NDVI değerini göster"
        ):

            st.write(
                f"""
                Nüfus-ağırlıklı NDVI:
                **{weighted_ndvi:.4f}**
                """
            )


    elif component == "🌡️ Termal Yük":

        st.metric(
            "En sıcak %10'luk bölgelerde yaşayanlar",
            f"%{hot_ratio:.1f}"
        )

        st.metric(
            "Yaklaşık kişi sayısı",
            f"{hot_population:,.0f}"
        )


        st.write(
            f"""
            Yerel LST dağılımının en sıcak
            %10'luk grubunda yer alan bölgelerde
            yaklaşık **{hot_population:,.0f} kişi**
            yaşamaktadır.
            """
        )


        st.metric(
            "Nüfus-ağırlıklı yüzey sıcaklığı",
            f"{weighted_lst:.1f} °C"
        )


        with st.expander(
            "Teknik LST ayrıntıları"
        ):

            st.write(
                f"""
                Ağırlıksız ortalama:
                **{unweighted_lst:.2f} °C**

                Nüfus-ağırlıklı:
                **{weighted_lst:.2f} °C**

                Yerel %90 eşiği:
                **{lst_p90:.2f} °C**
                """
            )


    elif component == "🌫️ Hava Kirliliği / PM10":

        st.info(
            "PM10 sonuçları daha sonra eklenecek."
        )


    elif component == "🚗 Ulaşım Kaynaklı Baskı":

        st.info(
            "Ulaşım sonuçları daha sonra eklenecek."
        )


# ============================================================
# MEVSİMSEL KARŞILAŞTIRMA
# ============================================================

st.divider()

if mahalle == "Oba":

    st.subheader(
        "📈 Oba 2026 Mevsimsel Karşılaştırma"
    )

    comparison = pd.DataFrame(
        {
            "Gösterge": [
                "Nüfus-ağırlıklı NDVI",
                "Düşük yeşillikte yaşayan nüfus",
                "Nüfus-ağırlıklı LST"
            ],

            "İlkbahar": [
                "0.2266",
                "%54.42",
                "31.68 °C"
            ],

            "Yaz": [
                "0.2061",
                "%61.42",
                "39.27 °C"
            ]
        }
    )

    st.dataframe(
        comparison,
        hide_index=True,
        use_container_width=True
    )

    st.caption(
        """
        Not: Yaz 2026 analizi 1 Haziran–30 Ağustos
        arasındaki mevcut verileri kapsamaktadır.
        """
    )

elif mahalle == "Mahmutlar":

    st.subheader(
        "📈 Mahmutlar 2026 Mevsimsel Karşılaştırma"
    )

    comparison = pd.DataFrame(
        {
            "Gösterge": [
                "Nüfus-ağırlıklı NDVI",
                "Düşük yeşillikte yaşayan nüfus",
                "Nüfus-ağırlıklı LST",
                "En sıcak %10'luk bölgelerde yaşayan nüfus"
            ],

            "İlkbahar": [
                "0.2188",
                "%59.17",
                "29.68 °C",
                "%11.96"
            ],

            "Yaz": [
                "0.2122",
                "%63.12",
                "38.25 °C",
                "%17.47"
            ]
        }
    )

    st.dataframe(
        comparison,
        hide_index=True,
        use_container_width=True
    )

    st.caption(
        """
        Not: Yaz 2026 analizi 1 Haziran–30 Ağustos
        arasındaki mevcut verileri kapsamaktadır.
        """
    )


# ============================================================
# YÖNTEM
# ============================================================

with st.expander(
    "🔬 Bu sonuçlar nasıl hesaplandı?"
):

    st.markdown(
        """
        **Nüfus:** WorldPop yaklaşık 100 m nüfus
        dağılımı resmi nüfus toplamına kalibre edilmiştir.

        **Yeşillik:** Sentinel-2 L2A görüntülerinden
        dönemsel medyan NDVI üretilmiştir.

        **Termal yük:** Landsat 8/9 Collection 2
        Level-2 Surface Temperature verileri kullanılmıştır.

        **Yaklaşım:** Nüfus ortak mekânsal referans
        katmanıdır. Yeşillik, termal yük, PM10 ve
        ulaşım kaynaklı baskı birbirinden ayrı
        değerlendirilir.

        Tek bir birleşik çevre skoru oluşturulmaz.
        """
    )