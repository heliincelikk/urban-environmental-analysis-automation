import cdsapi
import zipfile
from pathlib import Path

DATASET = "cams-europe-air-quality-reanalyses"

BASE_DIR = Path("data/pm10/raw/cams")
BASE_DIR.mkdir(parents=True, exist_ok=True)

AREA = [37.5, 29.5, 35.8, 32.8]

client = cdsapi.Client()

for year in [2024, 2025]:
    for month in range(1, 13):

        month_str = f"{month:02d}"

        extract_dir = BASE_DIR / f"{year}_{month_str}"

        # Zaten çıkarılmış NetCDF varsa tekrar indirme
        existing_nc = list(extract_dir.glob("*.nc"))

        if existing_nc:
            print(
                f"[SKIP] {year}-{month_str} zaten mevcut: "
                f"{existing_nc[0]}"
            )
            continue

        if year == 2024:
            reanalysis_type = "validated_reanalysis"
        else:
            reanalysis_type = "interim_reanalysis"

        zip_path = BASE_DIR / f"cams_pm10_{year}_{month_str}.zip"

        print("\n==============================")
        print(
            f"CAMS {year}-{month_str} "
            f"({reanalysis_type})"
        )
        print("==============================")

        request = {
            "variable": ["particulate_matter_10um"],
            "model": ["ensemble"],
            "level": ["0"],
            "type": [reanalysis_type],
            "year": [str(year)],
            "month": [month_str],
            "area": AREA,
        }

        client.retrieve(
            DATASET,
            request,
            str(zip_path)
        )

        print(f"[OK] ZIP indirildi: {zip_path}")

        extract_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)

        nc_files = list(extract_dir.glob("*.nc"))

        if len(nc_files) != 1:
            raise RuntimeError(
                f"{year}-{month_str} için "
                f"1 NetCDF bekleniyordu, "
                f"{len(nc_files)} bulundu."
            )

        print(f"[OK] NetCDF: {nc_files[0]}")

print("\n==============================")
print("CAMS 2024-2025 TAMAMLANDI")
print("==============================")