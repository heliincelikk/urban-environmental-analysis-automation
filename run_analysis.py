import argparse
from pathlib import Path

from worldpop_module import (
    download_worldpop,
    prepare_population_grid
)


# ============================================================
# MAHALLE BİLGİLERİ
# Şimdilik test için Oba
# ============================================================

MAHALLELER = {
    "oba": {
        "name": "Oba",
        "boundary": "data/boundaries/oba_pilot_sinir.geojson",
        "tuik_population": 32496,
        "tuik_year": 2025
    }
}


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="Alanya çevresel maruziyet analiz pipeline"
    )

    parser.add_argument(
        "--mahalle",
        required=True,
        help="Analiz edilecek mahalle"
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Analiz yılı"
    )

    parser.add_argument(
        "--start",
        required=True,
        help="Başlangıç tarihi YYYY-MM-DD"
    )

    parser.add_argument(
        "--end",
        required=True,
        help="Bitiş tarihi YYYY-MM-DD"
    )

    args = parser.parse_args()

    # ========================================================
    # MAHALLE KONTROLÜ
    # ========================================================

    key = args.mahalle.lower()

    if key not in MAHALLELER:
        raise ValueError(
            f"Mahalle bulunamadı: {args.mahalle}"
        )

    mahalle = MAHALLELER[key]

    boundary = Path(
        mahalle["boundary"]
    )

    print("\n========================================")
    print("OTOMATİK ANALİZ PIPELINE")
    print("========================================")

    print(
        "Mahalle:",
        mahalle["name"]
    )

    print(
        "Analiz yılı:",
        args.year
    )

    print(
        "Dönem:",
        args.start,
        "-",
        args.end
    )

    print(
        "TÜİK nüfusu:",
        mahalle["tuik_population"]
    )

    print(
        "TÜİK nüfus yılı:",
        mahalle["tuik_year"]
    )

    print(
        "Sınır dosyası:",
        mahalle["boundary"]
    )

    # ========================================================
    # SINIR DOSYASI KONTROLÜ
    # ========================================================

    if not boundary.exists():

        raise FileNotFoundError(
            f"Mahalle sınırı bulunamadı: {boundary}"
        )

    print(
        "\n[OK] Mahalle sınırı bulundu."
    )

    # ========================================================
    # WORLDPOP
    # ========================================================

    print("\n========================================")
    print("WORLDPOP MODÜLÜ BAŞLATILIYOR")
    print("========================================")

    worldpop_file = download_worldpop(
        year=args.year
    )

    population_grid = prepare_population_grid(

        worldpop_file=worldpop_file,

        boundary_file=mahalle["boundary"],

        tuik_population=
        mahalle["tuik_population"],

        mahalle_name=
        mahalle["name"],

        year=args.year
    )

    print(
        "\n[OK] WorldPop modülü tamamlandı."
    )

    print(
        "Nüfus grid dosyası:",
        population_grid
    )

    # ========================================================
    # PIPELINE DURUMU
    # ========================================================

    print("\n========================================")
    print("PIPELINE DURUMU")
    print("========================================")

    print("[OK] Mahalle sınırı")
    print("[OK] WorldPop")
    print("[ ] Sentinel-2 / NDVI")
    print("[ ] Landsat / LST")
    print("[ ] Nüfus-ağırlıklı analiz")
    print("[ ] Harita / sonuç dosyaları")

    print("\n========================================")
    print("İŞLEM TAMAMLANDI")
    print("========================================")


# ============================================================
# ÇALIŞTIR
# ============================================================

if __name__ == "__main__":
    main()