from pathlib import Path
import json
import requests
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import transform_geom


# ============================================================
# WORLDPOP AYARLARI
# ============================================================

WORLDPOP_RELEASE = "R2025A"
WORLDPOP_VERSION = "v1"
COUNTRY_ISO3 = "TUR"


def worldpop_url(year: int) -> str:
    """
    WorldPop Global 2015-2030
    100 m constrained population raster URL'sini oluşturur.
    """

    filename = (
        f"tur_pop_{year}_CN_100m_"
        f"{WORLDPOP_RELEASE}_{WORLDPOP_VERSION}.tif"
    )

    url = (
        "https://data.worldpop.org/"
        "GIS/Population/Global_2015_2030/"
        f"{WORLDPOP_RELEASE}/"
        f"{year}/"
        f"{COUNTRY_ISO3}/"
        f"{WORLDPOP_VERSION}/"
        "100m/constrained/"
        f"{filename}"
    )

    return url


# ============================================================
# WORLDPOP İNDİR
# ============================================================

def download_worldpop(year: int, output_folder="data/population"):

    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    filename = (
        f"tur_pop_{year}_CN_100m_"
        f"{WORLDPOP_RELEASE}_{WORLDPOP_VERSION}.tif"
    )

    output_file = output_folder / filename

    # Daha önce indirildiyse tekrar indirme
    if output_file.exists():
        print("\n[WORLDPOP] Dosya zaten mevcut:")
        print(output_file)

        return output_file

    url = worldpop_url(year)

    print("\n========================================")
    print("WORLDPOP")
    print("========================================")

    print("WorldPop URL:")
    print(url)

    print("\nWorldPop indiriliyor...")
    print("Bu ilk seferde biraz sürebilir.")

    response = requests.get(
        url,
        stream=True,
        timeout=180
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"WorldPop indirilemedi. "
            f"HTTP kodu: {response.status_code}\n"
            f"URL: {url}"
        )

    total = int(
        response.headers.get(
            "content-length",
            0
        )
    )

    downloaded = 0

    with open(output_file, "wb") as f:

        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):

            if not chunk:
                continue

            f.write(chunk)

            downloaded += len(chunk)

            if total > 0:

                percent = (
                    downloaded /
                    total *
                    100
                )

                print(
                    f"\rİndiriliyor: %{percent:.1f}",
                    end=""
                )

    print("\n\n[OK] WorldPop indirildi:")
    print(output_file)

    return output_file


# ============================================================
# MAHALLEYE KIRP + TÜİK'E KALİBRE ET
# ============================================================

def prepare_population_grid(
    worldpop_file,
    boundary_file,
    tuik_population,
    mahalle_name,
    year,
    output_folder="outputs"
):

    output_folder = (
        Path(output_folder)
        / mahalle_name.lower()
        / str(year)
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # MAHALLE SINIRI
    # --------------------------------------------------------

    with open(
        boundary_file,
        "r",
        encoding="utf-8"
    ) as f:

        geojson = json.load(f)

    if geojson["type"] == "FeatureCollection":

        geometry = (
            geojson["features"][0]["geometry"]
        )

    elif geojson["type"] == "Feature":

        geometry = geojson["geometry"]

    else:

        geometry = geojson

    # --------------------------------------------------------
    # WORLDPOP AÇ
    # --------------------------------------------------------

    with rasterio.open(worldpop_file) as src:

        print("\nWorldPop CRS:")
        print(src.crs)

        # GeoJSON sınırımız EPSG:4326
        geometry_projected = transform_geom(
            "EPSG:4326",
            src.crs,
            geometry,
            precision=6
        )

        clipped, transform = mask(
            src,
            [geometry_projected],
            crop=True
        )

        profile = src.profile.copy()

        population = (
            clipped[0]
            .astype("float64")
        )

        if src.nodata is not None:

            population[
                population == src.nodata
            ] = np.nan

    # --------------------------------------------------------
    # GEÇERSİZ DEĞERLER
    # --------------------------------------------------------

    population[
        ~np.isfinite(population)
    ] = 0

    population[
        population < 0
    ] = 0

    raw_total = float(
        np.sum(population)
    )

    if raw_total <= 0:

        raise ValueError(
            "Mahalle içinde geçerli "
            "WorldPop nüfusu bulunamadı."
        )

    # --------------------------------------------------------
    # TÜİK KALİBRASYONU
    # --------------------------------------------------------

    scale_factor = (
        tuik_population /
        raw_total
    )

    calibrated_population = (
        population *
        scale_factor
    )

    calibrated_total = float(
        np.sum(
            calibrated_population
        )
    )

    positive = (
        calibrated_population > 0
    )

    positive_values = (
        calibrated_population[positive]
    )

    # --------------------------------------------------------
    # İSTATİSTİKLER
    # --------------------------------------------------------

    print("\n========================================")
    print("NÜFUS GRID SONUÇLARI")
    print("========================================")

    print(
        "WorldPop ham toplam:",
        round(raw_total, 2)
    )

    print(
        "TÜİK hedef nüfus:",
        tuik_population
    )

    print(
        "Kalibrasyon katsayısı:",
        round(scale_factor, 4)
    )

    print(
        "Kalibre toplam:",
        round(calibrated_total, 2)
    )

    print(
        "Pozitif nüfuslu grid:",
        int(np.sum(positive))
    )

    print(
        "Ortalama kişi/grid:",
        round(
            float(
                np.mean(positive_values)
            ),
            2
        )
    )

    print(
        "Medyan kişi/grid:",
        round(
            float(
                np.median(
                    positive_values
                )
            ),
            2
        )
    )

    print(
        "Maksimum kişi/grid:",
        round(
            float(
                np.max(
                    positive_values
                )
            ),
            2
        )
    )

    print(
        "%90 nüfus eşiği:",
        round(
            float(
                np.percentile(
                    positive_values,
                    90
                )
            ),
            2
        )
    )

    # --------------------------------------------------------
    # KAYDET
    # --------------------------------------------------------

    profile.update({
        "height":
            calibrated_population.shape[0],

        "width":
            calibrated_population.shape[1],

        "transform":
            transform,

        "count":
            1,

        "dtype":
            "float32",

        "nodata":
            -9999.0
    })

    output = np.where(
        np.isfinite(
            calibrated_population
        ),

        calibrated_population,

        -9999.0

    ).astype("float32")

    output_file = (
        output_folder /
        "population_100m_calibrated.tif"
    )

    with rasterio.open(
        output_file,
        "w",
        **profile
    ) as dst:

        dst.write(
            output,
            1
        )

    print("\n[OK] Nüfus grid kaydedildi:")
    print(output_file)

    return output_file