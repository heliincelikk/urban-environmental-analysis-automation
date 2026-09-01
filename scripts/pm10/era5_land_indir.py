import cdsapi
from pathlib import Path

# Proje ana klasörü
PROJECT_DIR = Path(__file__).resolve().parents[2]

# ERA5 dosyalarının kaydedileceği klasör
OUT_DIR = PROJECT_DIR / "data" / "pm10" / "raw" / "era5"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# CDS veri seti
dataset = "reanalysis-era5-land"

# İndireceğimiz yıl
year = "2025"

# Aylar
months = [
    "01", "02", "03", "04", "05", "06",
    "07", "08", "09", "10", "11", "12"
]

# Günler
days = [
    "01", "02", "03", "04", "05", "06", "07",
    "08", "09", "10", "11", "12", "13", "14",
    "15", "16", "17", "18", "19", "20", "21",
    "22", "23", "24", "25", "26", "27", "28",
    "29", "30", "31"
]

# Saatler
times = [
    "00:00", "01:00", "02:00", "03:00",
    "04:00", "05:00", "06:00", "07:00",
    "08:00", "09:00", "10:00", "11:00",
    "12:00", "13:00", "14:00", "15:00",
    "16:00", "17:00", "18:00", "19:00",
    "20:00", "21:00", "22:00", "23:00"
]

# CDS istemcisi
client = cdsapi.Client()

for month in months:

    output_file = OUT_DIR / f"era5_land_antalya_{year}_{month}.nc"

    # Dosya zaten varsa tekrar indirme
    if output_file.exists():
        print(f"[SKIP] Zaten var: {output_file.name}")
        continue

    print(f"[INDIRILIYOR] {year}-{month}")

    request = {
        "variable": [
            "2m_temperature",
            "2m_dewpoint_temperature",
            "surface_pressure",
            "total_precipitation",
            "10m_u_component_of_wind",
            "10m_v_component_of_wind",
        ],

        "year": year,
        "month": month,
        "day": days,
        "time": times,

        # Antalya ve 8 PM10 istasyonunu kapsayan çalışma alanı
        # [North, West, South, East]
        "area": [
            37.2,
            29.9,
            36.0,
            32.5
        ],

        "data_format": "netcdf",
        "download_format": "unarchived"
    }

    client.retrieve(
        dataset,
        request,
        str(output_file)
    )

    print(f"[OK] Tamamlandi: {output_file.name}")

print(f"[BITTI] {year} ERA5-Land indirmeleri tamamlandi.")