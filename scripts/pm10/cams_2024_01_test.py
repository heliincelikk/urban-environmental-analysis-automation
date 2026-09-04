import cdsapi
from pathlib import Path

dataset = "cams-europe-air-quality-reanalyses"

request = {
    "variable": ["particulate_matter_10um"],
    "model": ["ensemble"],
    "level": ["0"],
    "type": ["validated_reanalysis"],
    "year": ["2024"],
    "month": ["01"],
    "area": [37.5, 29.5, 35.8, 32.8],
}

output = Path(
    "data/pm10/raw/cams/cams_pm10_2024_01.nc"
)

output.parent.mkdir(
    parents=True,
    exist_ok=True
)

client = cdsapi.Client()

client.retrieve(
    dataset,
    request,
    str(output)
)

print(f"\n[OK] İndirildi: {output}")