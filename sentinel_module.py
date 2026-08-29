import json
from pathlib import Path

import openeo


# ============================================================
# AYARLAR
# ============================================================

OPENEO_URL = "https://openeo.dataspace.copernicus.eu"


# ============================================================
# GEOJSON SINIRINDAN BBOX ÇIKAR
# ============================================================

def load_boundary_bbox(boundary_file):
    """
    GeoJSON sınırından bbox üretir.

    Çıktı:
    {
        "west": ...,
        "south": ...,
        "east": ...,
        "north": ...
    }
    """

    with open(
        boundary_file,
        "r",
        encoding="utf-8"
    ) as f:
        geojson = json.load(f)

    if geojson["type"] == "FeatureCollection":
        geometry = geojson["features"][0]["geometry"]

    elif geojson["type"] == "Feature":
        geometry = geojson["geometry"]

    else:
        geometry = geojson

    points = []

    def collect_points(obj):

        if (
            isinstance(obj, list)
            and len(obj) >= 2
            and isinstance(obj[0], (int, float))
            and isinstance(obj[1], (int, float))
        ):
            points.append(
                (
                    float(obj[0]),
                    float(obj[1])
                )
            )

        elif isinstance(obj, list):

            for item in obj:
                collect_points(item)

    collect_points(
        geometry["coordinates"]
    )

    if not points:
        raise ValueError(
            "GeoJSON içinden koordinat okunamadı."
        )

    lons = [
        point[0]
        for point in points
    ]

    lats = [
        point[1]
        for point in points
    ]

    bbox = {
        "west": min(lons),
        "south": min(lats),
        "east": max(lons),
        "north": max(lats)
    }

    return bbox


# ============================================================
# COPERNICUS OPENEO BAĞLANTISI
# ============================================================

def connect_openeo():
    """
    Copernicus Data Space openEO bağlantısı kurar.

    İlk çalıştırmada tarayıcı üzerinden
    Copernicus hesabıyla giriş gerekebilir.
    """

    print("\n========================================")
    print("COPERNICUS OPENEO")
    print("========================================")

    print("Sunucuya bağlanılıyor...")

    connection = openeo.connect(
        OPENEO_URL
    )

    print(
        "Kimlik doğrulama başlatılıyor..."
    )

    connection.authenticate_oidc()

    print(
        "[OK] Copernicus bağlantısı hazır."
    )

    return connection


# ============================================================
# SENTINEL-2 DÖNEMSEL NDVI
# ============================================================

def create_seasonal_ndvi(
    boundary_file,
    start_date,
    end_date,
    mahalle_name,
    year,
    season_name,
    max_cloud=30,
    output_folder="outputs"
):
    """
    Sentinel-2 L2A verilerinden:

    1) B04
    2) B08
    3) SCL

    kullanır.

    Bulut/gölge sınıflarını temizler.
    NDVI üretir.
    Dönemdeki görüntülerden medyan NDVI
    rasterı oluşturur.
    """

    # --------------------------------------------------------
    # ÇIKTI KLASÖRÜ
    # --------------------------------------------------------

    output_folder = (
        Path(output_folder)
        / mahalle_name.lower()
        / str(year)
        / season_name.lower()
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        output_folder
        / "ndvi_median.tif"
    )

    # Daha önce üretildiyse tekrar çalıştırma
    if output_file.exists():

        print("\n[SENTINEL] NDVI zaten mevcut:")
        print(output_file)

        return output_file

    # --------------------------------------------------------
    # SINIR
    # --------------------------------------------------------

    bbox = load_boundary_bbox(
        boundary_file
    )

    spatial_extent = {
        "west": bbox["west"],
        "south": bbox["south"],
        "east": bbox["east"],
        "north": bbox["north"],
        "crs": "EPSG:4326"
    }

    print("\n========================================")
    print("SENTINEL-2 NDVI")
    print("========================================")

    print(
        "Dönem:",
        start_date,
        "-",
        end_date
    )

    print(
        "Maksimum sahne bulutu:",
        f"%{max_cloud}"
    )

    print("Alan:")
    print(spatial_extent)

    # --------------------------------------------------------
    # OPENEO
    # --------------------------------------------------------

    connection = connect_openeo()

    # --------------------------------------------------------
    # SENTINEL-2 L2A YÜKLE
    # --------------------------------------------------------

    print(
        "\nSentinel-2 L2A veri kümesi hazırlanıyor..."
    )

    cube = connection.load_collection(
        "SENTINEL2_L2A",

        spatial_extent=
            spatial_extent,

        temporal_extent=[
            start_date,
            end_date
        ],

        bands=[
            "B04",
            "B08",
            "SCL"
        ],

        max_cloud_cover=
            max_cloud
    )

    # ========================================================
    # SCL BULUT MASKESİ
    # ========================================================

    scl = cube.band("SCL")

    # Sentinel-2 SCL sınıfları:
    #
    # 1  = saturated / defective
    # 3  = cloud shadow
    # 7  = unclassified / low probability cloud
    # 8  = medium probability cloud
    # 9  = high probability cloud
    # 10 = thin cirrus
    # 11 = snow / ice
    #
    # Bunları geçersiz kabul ediyoruz.

    invalid = (
        (scl == 1)
        | (scl == 3)
        | (scl == 7)
        | (scl == 8)
        | (scl == 9)
        | (scl == 10)
        | (scl == 11)
    )

    # ========================================================
    # B04 / B08
    # ========================================================

    red = cube.band("B04")

    nir = cube.band("B08")

    # L2A değerleri scale factor 10000 ile tutulur.
    # NDVI oran olduğu için ortak çarpan sadeleşir.
    #
    # Yine de matematiksel ifade doğrudan:
    #
    # (NIR - RED) / (NIR + RED)

    denominator = (
        nir + red
    )

    ndvi = (
        (nir - red)
        /
        denominator
    )

    # --------------------------------------------------------
    # BULUT MASKESİ
    # --------------------------------------------------------

    ndvi_clean = ndvi.mask(
        invalid
    )

    # --------------------------------------------------------
    # DÖNEMSEL MEDYAN
    # --------------------------------------------------------

    print(
        "Dönemsel medyan NDVI hazırlanıyor..."
    )

    ndvi_median = (
        ndvi_clean.reduce_temporal(
            "median"
        )
    )

    # ========================================================
    # BATCH JOB
    # ========================================================

    print(
        "\nCopernicus sunucusunda NDVI işi başlatılıyor."
    )

    print(
        "Bu işlem birkaç dakika sürebilir."
    )

    job = ndvi_median.create_job(
        title=(
            f"{mahalle_name}_"
            f"{year}_"
            f"{season_name}_NDVI"
        ),

        out_format="GTiff"
    )

    job.start_and_wait()

    # ========================================================
    # SONUCU İNDİR
    # ========================================================

    print(
        "\nNDVI sonucu indiriliyor..."
    )

    results = job.get_results()

    results.download_file(
        output_file
    )

    print(
        "\n[OK] Dönemsel NDVI oluşturuldu:"
    )

    print(
        output_file
    )

    return output_file