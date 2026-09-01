from pathlib import Path
import cdsapi

# Proje klasörü
PROJECT_DIR = Path(__file__).resolve().parents[2]

# Kayıt klasörü
OUT_DIR = PROJECT_DIR / "data" / "pm10" / "raw" / "era5"
OUT_DIR.mkdir(parents=True, exist_ok=True)

dataset = "reanalysis-era5-land"

variables = [
    "2m_temperature",
    "2m_dewpoint_temperature",
    "surface_pressure",
    "total_precipitation",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
]

# Daha önce kullandığımız alan
area = [37.2, 29.9, 36.0, 32.5]

client = cdsapi.Client()


def indir(year, month, day, hours, filename):
    target = OUT_DIR / filename

    if target.exists():
        print(f"[VAR] {target.name}")
        return

    request = {
        "variable": variables,
        "year": str(year),
        "month": f"{month:02d}",
        "day": f"{day:02d}",
        "time": hours,
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": area,
    }

    print(f"[INDIRILIYOR] {target.name}")

    client.retrieve(
        dataset,
        request,
        str(target)
    )

    print(f"[TAMAM] {target.name}")


# 1 Ocak 2024 Türkiye günü için gereken önceki UTC saatleri
indir(
    2023,
    12,
    31,
    ["21:00", "22:00", "23:00"],
    "era5_land_antalya_2023_12_31_buffer.nc"
)

# 31 Aralık 2025 Türkiye gününün son kısmı için
indir(
    2026,
    1,
    1,
    [f"{h:02d}:00" for h in range(0, 21)],
    "era5_land_antalya_2026_01_01_buffer.nc"
)

print("\nSinir saatleri indirildi.")