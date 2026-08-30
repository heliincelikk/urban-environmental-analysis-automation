import argparse

from worldpop_module import (
    download_worldpop,
    prepare_population_grid
)


# ============================================================
# MAHALLE TANIMLARI
# ============================================================

MAHALLELER = {

    "Oba": {
        "boundary": (
            "data/boundaries/"
            "oba_pilot_sinir.geojson"
        ),

        # TÜİK / ADNKS 2025
        "official_population": 32496
    },

    "Mahmutlar": {
        "boundary": (
            "data/boundaries/"
            "mahmutlar_belediye_sinir_DUZELTILMIS.geojson"
        ),

        # TÜİK / ADNKS 2025
        "official_population": 51222
    }
}


# ============================================================
# ARGÜMANLAR
# ============================================================

parser = argparse.ArgumentParser(
    description=(
        "Mahalle bazlı kentsel çevresel "
        "maruziyet analiz pipeline'ı"
    )
)


parser.add_argument(
    "--mahalle",
    required=True,
    choices=MAHALLELER.keys(),
    help="Analiz edilecek mahalle"
)


parser.add_argument(
    "--year",
    required=True,
    type=int,
    help="WorldPop veri yılı"
)


parser.add_argument(
    "--start",
    required=True,
    help="Analiz başlangıç tarihi YYYY-MM-DD"
)


parser.add_argument(
    "--end",
    required=True,
    help="Analiz bitiş tarihi YYYY-MM-DD"
)


args = parser.parse_args()


# ============================================================
# SEÇİLEN MAHALLE
# ============================================================

config = MAHALLELER[
    args.mahalle
]


boundary_file = config[
    "boundary"
]

official_population = config[
    "official_population"
]


print("\n========================================")
print("ANALİZ PIPELINE")
print("========================================")

print(
    "Mahalle:",
    args.mahalle
)

print(
    "Yıl:",
    args.year
)

print(
    "Dönem:",
    args.start,
    "-",
    args.end
)

print(
    "Resmi nüfus hedefi:",
    official_population
)

print(
    "Sınır dosyası:",
    boundary_file
)


# ============================================================
# 1. WORLDPOP İNDİR
# ============================================================

print("\n========================================")
print("1. WORLDPOP")
print("========================================")


worldpop_file = download_worldpop(
    year=args.year
)


print(
    "[OK] WorldPop dosyası:",
    worldpop_file
)


# ============================================================
# 2. NÜFUS GRIDİNİ HAZIRLA
# ============================================================

print("\n========================================")
print("2. NÜFUS GRIDİ")
print("========================================")


population_output = prepare_population_grid(
    worldpop_file=worldpop_file,
    boundary_file=boundary_file,
    tuik_population=official_population,
    mahalle_name=args.mahalle,
    year=args.year
)


print(
    "\n[OK] Nüfus grid çıktısı:"
)

print(
    population_output
)


# ============================================================
# ÖZET
# ============================================================

print("\n========================================")
print("PIPELINE TAMAMLANDI")
print("========================================")

print(
    "Mahalle:",
    args.mahalle
)

print(
    "Dönem:",
    args.start,
    "-",
    args.end
)

print(
    "Nüfus grid:",
    population_output
)

print(
    "\nNot:"
)

print(
    "Bu aşamada nüfus katmanı üretildi."
)

print(
    "NDVI ve LST otomasyonu sonraki "
    "adımlarda aynı pipeline'a bağlanacak."
)