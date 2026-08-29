import json
from pathlib import Path

import numpy as np
import rasterio
import pystac_client
import planetary_computer

from rasterio.mask import mask
from rasterio.warp import transform_geom, reproject, Resampling


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def load_geometry(boundary_file):

    with open(boundary_file, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    if geojson["type"] == "FeatureCollection":
        return geojson["features"][0]["geometry"]

    if geojson["type"] == "Feature":
        return geojson["geometry"]

    return geojson


def flatten_coordinates(values):

    result = []

    for item in values:

        if (
            isinstance(item, list)
            and len(item) >= 2
            and isinstance(item[0], (int, float))
            and isinstance(item[1], (int, float))
        ):
            result.append(item)

        else:
            result.extend(
                flatten_coordinates(item)
            )

    return result


def geometry_to_bbox(geometry):

    points = flatten_coordinates(
        geometry["coordinates"]
    )

    return [
        min(p[0] for p in points),
        min(p[1] for p in points),
        max(p[0] for p in points),
        max(p[1] for p in points)
    ]


# ============================================================
# QA_PIXEL MASK
# ============================================================

def build_clear_mask(qa):

    qa = qa.astype("uint16")

    # Landsat Collection 2 QA_PIXEL
    #
    # Bit 0 = Fill
    # Bit 1 = Dilated Cloud
    # Bit 2 = Cirrus
    # Bit 3 = Cloud
    # Bit 4 = Cloud Shadow
    # Bit 5 = Snow

    fill = (
        qa & (1 << 0)
    ) != 0

    dilated_cloud = (
        qa & (1 << 1)
    ) != 0

    cirrus = (
        qa & (1 << 2)
    ) != 0

    cloud = (
        qa & (1 << 3)
    ) != 0

    cloud_shadow = (
        qa & (1 << 4)
    ) != 0

    snow = (
        qa & (1 << 5)
    ) != 0

    invalid = (
        fill
        | dilated_cloud
        | cirrus
        | cloud
        | cloud_shadow
        | snow
    )

    return ~invalid


# ============================================================
# ANA FONKSİYON
# ============================================================

def create_seasonal_lst(
    boundary_file,
    start_date,
    end_date,
    mahalle_name,
    year,
    season_name,
    max_cloud=30
):

    print("\n========================================")
    print("LANDSAT DÖNEMSEL LST")
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


    # ========================================================
    # ÇIKTI KLASÖRÜ
    # ========================================================

    output_dir = (
        Path("outputs")
        / mahalle_name.lower()
        / str(year)
        / season_name
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        output_dir
        / "lst_median.tif"
    )


    # ========================================================
    # SINIR
    # ========================================================

    geometry = load_geometry(
        boundary_file
    )

    bbox = geometry_to_bbox(
        geometry
    )

    print(
        "BBOX:",
        bbox
    )


    # ========================================================
    # STAC
    # ========================================================

    print(
        "\nLandsat 8/9 Collection 2 Level-2 aranıyor..."
    )

    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace
    )


    search = catalog.search(
        collections=[
            "landsat-c2-l2"
        ],

        bbox=bbox,

        datetime=(
            f"{start_date}/"
            f"{end_date}"
        ),

        query={
            "eo:cloud_cover": {
                "lt": max_cloud
            }
        }
    )


    items = list(
        search.items()
    )


    if not items:
        raise ValueError(
            "Uygun Landsat sahnesi bulunamadı."
        )


    items = sorted(
        items,
        key=lambda item:
        item.datetime
    )


    print(
        "Bulunan sahne:",
        len(items)
    )


    # ========================================================
    # REFERANS GRID
    # ========================================================

    reference_transform = None
    reference_crs = None
    reference_shape = None
    output_profile = None

    lst_stack = []


    # ========================================================
    # HER LANDSAT SAHNESİNİ İŞLE
    # ========================================================

    for index, item in enumerate(
        items,
        start=1
    ):

        print("\n----------------------------------------")
        print(
            f"Sahne {index}/{len(items)}"
        )
        print("----------------------------------------")

        print(
            "ID:",
            item.id
        )

        print(
            "Tarih:",
            item.datetime
        )

        print(
            "Bulut:",
            item.properties.get(
                "eo:cloud_cover"
            )
        )


        # ----------------------------------------------------
        # ST_B10
        # ----------------------------------------------------

        if "lwir11" not in item.assets:

            print(
                "[ATLANDI] ST_B10 bulunamadı."
            )

            continue


        st_asset = item.assets[
            "lwir11"
        ]


        # ----------------------------------------------------
        # QA_PIXEL
        # ----------------------------------------------------

        qa_key = None

        for possible_key in [
            "qa_pixel",
            "qa"
        ]:

            if possible_key in item.assets:
                qa_key = possible_key
                break


        if qa_key is None:

            print(
                "[ATLANDI] QA_PIXEL bulunamadı."
            )

            continue


        qa_asset = item.assets[
            qa_key
        ]


        # ----------------------------------------------------
        # SCALE / OFFSET
        # ----------------------------------------------------

        raster_bands = (
            st_asset.extra_fields.get(
                "raster:bands",
                []
            )
        )

        scale = 0.00341802
        offset = 149.0

        if raster_bands:

            band_info = raster_bands[0]

            if band_info.get("scale") is not None:
                scale = band_info["scale"]

            if band_info.get("offset") is not None:
                offset = band_info["offset"]


        print(
            "Scale:",
            scale,
            "Offset:",
            offset
        )


        # ====================================================
        # ST_B10 OKU + SINIRA KIRP
        # ====================================================

        with rasterio.open(
            st_asset.href
        ) as st_src:

            geometry_projected = transform_geom(
                "EPSG:4326",
                st_src.crs,
                geometry,
                precision=6
            )

            st_clipped, st_transform = mask(
                st_src,
                [geometry_projected],
                crop=True,
                filled=False
            )

            dn = (
                st_clipped[0]
                .astype("float32")
            )

            if np.ma.isMaskedArray(
                dn
            ):
                dn = dn.filled(
                    np.nan
                )

            if st_src.nodata is not None:

                dn[
                    dn == st_src.nodata
                ] = np.nan


            current_crs = st_src.crs
            current_shape = dn.shape


            # ------------------------------------------------
            # REFERANS GRID
            # ------------------------------------------------

            if reference_transform is None:

                reference_transform = (
                    st_transform
                )

                reference_crs = (
                    current_crs
                )

                reference_shape = (
                    current_shape
                )

                output_profile = (
                    st_src.profile.copy()
                )

                output_profile.update({
                    "height": reference_shape[0],
                    "width": reference_shape[1],
                    "transform": reference_transform,
                    "crs": reference_crs,
                    "dtype": "float32",
                    "count": 1,
                    "nodata": -9999.0
                })


        # ====================================================
        # QA_PIXEL OKU + AYNI ALANA KIRP
        # ====================================================

        with rasterio.open(
            qa_asset.href
        ) as qa_src:

            geometry_projected_qa = transform_geom(
                "EPSG:4326",
                qa_src.crs,
                geometry,
                precision=6
            )

            qa_clipped, qa_transform = mask(
                qa_src,
                [geometry_projected_qa],
                crop=True,
                filled=False
            )

            qa = qa_clipped[0]

            if np.ma.isMaskedArray(
                qa
            ):

                qa = qa.filled(
                    0
                )

            qa_crs = qa_src.crs


        # ====================================================
        # QA GRIDİNİ ST GRIDİNE UYARLA
        # ====================================================

        if (
            qa.shape != dn.shape
            or qa_transform != st_transform
            or qa_crs != current_crs
        ):

            qa_reprojected = np.zeros(
                dn.shape,
                dtype="uint16"
            )

            reproject(
                source=qa,
                destination=qa_reprojected,

                src_transform=qa_transform,
                src_crs=qa_crs,

                dst_transform=st_transform,
                dst_crs=current_crs,

                resampling=Resampling.nearest
            )

            qa = qa_reprojected


        # ====================================================
        # BULUT MASKESİ
        # ====================================================

        clear_mask = build_clear_mask(
            qa
        )


        # ====================================================
        # DN -> KELVIN -> CELSIUS
        # ====================================================

        kelvin = (
            dn * scale
            + offset
        )

        celsius = (
            kelvin
            - 273.15
        )


        # ====================================================
        # BULUTLARI TEMİZLE
        # ====================================================

        celsius[
            ~clear_mask
        ] = np.nan


        # Fiziksel kontrol
        celsius[
            (celsius < -20)
            |
            (celsius > 70)
        ] = np.nan


        # ====================================================
        # REFERANS GRIDE EŞLE
        # ====================================================

        if (
            celsius.shape != reference_shape
            or st_transform != reference_transform
            or current_crs != reference_crs
        ):

            aligned = np.full(
                reference_shape,
                np.nan,
                dtype="float32"
            )

            reproject(
                source=celsius,
                destination=aligned,

                src_transform=st_transform,
                src_crs=current_crs,

                dst_transform=reference_transform,
                dst_crs=reference_crs,

                resampling=Resampling.bilinear,

                src_nodata=np.nan,
                dst_nodata=np.nan
            )

            celsius = aligned


        # ====================================================
        # SAHNE KONTROLÜ
        # ====================================================

        valid_count = int(
            np.sum(
                np.isfinite(
                    celsius
                )
            )
        )


        print(
            "Geçerli piksel:",
            valid_count
        )


        if valid_count == 0:

            print(
                "[ATLANDI] Geçerli piksel yok."
            )

            continue


        lst_stack.append(
            celsius.astype(
                "float32"
            )
        )


    # ========================================================
    # STACK KONTROLÜ
    # ========================================================

    if not lst_stack:

        raise ValueError(
            "Hiçbir Landsat sahnesinden "
            "geçerli LST üretilemedi."
        )


    print(
        "\n========================================"
    )

    print(
        "Kullanılan geçerli sahne:",
        len(lst_stack)
    )


    # ========================================================
    # DÖNEMSEL MEDYAN
    # ========================================================

    stack = np.stack(
        lst_stack,
        axis=0
    )


    with np.errstate(
        all="ignore"
    ):

        median_lst = np.nanmedian(
            stack,
            axis=0
        )


    valid = median_lst[
        np.isfinite(
            median_lst
        )
    ]


    if len(valid) == 0:

        raise ValueError(
            "Dönemsel medyan LST boş çıktı."
        )


    # ========================================================
    # İSTATİSTİK
    # ========================================================

    print(
        "\n========================================"
    )

    print(
        "DÖNEMSEL LST SONUÇLARI"
    )

    print(
        "========================================"
    )


    print(
        "Geçerli piksel:",
        len(valid)
    )

    print(
        "Ortalama °C:",
        round(
            float(
                np.mean(valid)
            ),
            2
        )
    )

    print(
        "Medyan °C:",
        round(
            float(
                np.median(valid)
            ),
            2
        )
    )

    print(
        "Minimum °C:",
        round(
            float(
                np.min(valid)
            ),
            2
        )
    )

    print(
        "Maksimum °C:",
        round(
            float(
                np.max(valid)
            ),
            2
        )
    )

    print(
        "%25:",
        round(
            float(
                np.percentile(
                    valid,
                    25
                )
            ),
            2
        )
    )

    print(
        "%75:",
        round(
            float(
                np.percentile(
                    valid,
                    75
                )
            ),
            2
        )
    )

    print(
        "%90:",
        round(
            float(
                np.percentile(
                    valid,
                    90
                )
            ),
            2
        )
    )


    # ========================================================
    # KAYDET
    # ========================================================

    save_array = np.where(
        np.isfinite(
            median_lst
        ),
        median_lst,
        -9999.0
    ).astype(
        "float32"
    )


    with rasterio.open(
        output_file,
        "w",
        **output_profile
    ) as dst:

        dst.write(
            save_array,
            1
        )


    print(
        "\n[OK] Dönemsel medyan LST kaydedildi:"
    )

    print(
        output_file
    )


    return str(
        output_file
    )