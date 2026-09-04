import cdsapi
import zipfile
from pathlib import Path

DATASET = "cams-europe-air-quality-reanalyses"

BASE_DIR = Path("data/pm10/raw/cams")
EXTRACT_DIR = BASE_DIR / "2023_12_buffer"
ZIP_PATH = BASE_DIR / "cams_pm10_2023_12_buffer.zip"

AREA = [37.5, 29.5, 35.8, 32.8]

EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

request = {
    "variable": ["particulate_matter_10um"],
    "model": ["ensemble"],
    "level": ["0"],
    "type": ["validated_reanalysis"],
    "year": ["2023"],
    "month": ["12"],
    "area": AREA,
}

client = cdsapi.Client()

print("CAMS 2023-12 buffer indiriliyor...")

client.retrieve(
    DATASET,
    request,
    str(ZIP_PATH)
)

with zipfile.ZipFile(ZIP_PATH, "r") as z:
    z.extractall(EXTRACT_DIR)

nc_files = list(EXTRACT_DIR.glob("*.nc"))

if len(nc_files) != 1:
    raise RuntimeError(
        f"1 NetCDF bekleniyordu, {len(nc_files)} bulundu."
    )

print(f"[OK] Buffer NetCDF: {nc_files[0]}")