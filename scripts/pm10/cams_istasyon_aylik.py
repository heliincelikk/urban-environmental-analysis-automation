import pandas as pd
import xarray as xr
from pathlib import Path

# =========================================================
# DOSYALAR
# =========================================================
STATION_FILE = Path(
    "data/pm10/processed/pm10_istasyonlar.csv"
)

CAMS_BASE = Path(
    "data/pm10/raw/cams"
)

BUFFER_DIR = CAMS_BASE / "2023_12_buffer"

HOURLY_OUTPUT = Path(
    "data/pm10/processed/cams_istasyon_saatlik_2024_2025.csv"
)

DAILY_OUTPUT = Path(
    "data/pm10/processed/cams_istasyon_gunluk_2024_2025.csv"
)

MONTHLY_OUTPUT = Path(
    "data/pm10/processed/cams_istasyon_aylik_2024_2025.csv"
)


# =========================================================
# İSTASYONLAR
# =========================================================
stations = pd.read_csv(STATION_FILE)

required = {"istasyon", "enlem", "boylam"}

if not required.issubset(stations.columns):
    raise ValueError(
        f"Eksik istasyon sütunları: "
        f"{required - set(stations.columns)}"
    )


# =========================================================
# ANA CAMS DOSYALARI
# =========================================================
nc_files = sorted(
    CAMS_BASE.glob("20??_??/*.nc")
)

if len(nc_files) != 24:
    raise RuntimeError(
        f"24 ana NetCDF bekleniyordu, "
        f"{len(nc_files)} bulundu."
    )


# =========================================================
# BUFFER DOSYASI
# =========================================================
buffer_files = list(
    BUFFER_DIR.glob("*.nc")
)

if len(buffer_files) != 1:
    raise RuntimeError(
        f"1 buffer NetCDF bekleniyordu, "
        f"{len(buffer_files)} bulundu."
    )

buffer_file = buffer_files[0]


# =========================================================
# YARDIMCI FONKSİYON:
# CAMS -> İSTASYON BILINEAR INTERPOLATION
# =========================================================
def extract_station_values(ds, stations, selected_times=None):

    if "pm10" not in ds.data_vars:
        raise ValueError(
            "Dataset içinde pm10 değişkeni yok."
        )

    if selected_times is not None:
        ds = ds.sel(time=selected_times)

    rows = []

    for _, station in stations.iterrows():

        pm10_interp = (
            ds["pm10"]
            .interp(
                lat=float(station["enlem"]),
                lon=float(station["boylam"]),
                method="linear"
            )
        )

        temp = pd.DataFrame({
            "zaman_utc": pd.to_datetime(
                ds["time"].values
            ),
            "istasyon": station["istasyon"],
            "pm10_cams": pm10_interp.values
        })

        rows.append(temp)

    return rows


# =========================================================
# BUFFER:
# SADECE 31 ARALIK 2023 21-23 UTC
# =========================================================
print("[BUFFER] 2023-12-31 21:00-23:00 UTC")

ds_buffer = xr.open_dataset(
    buffer_file,
    engine="netcdf4"
)

buffer_times = pd.to_datetime(
    ds_buffer["time"].values
)

wanted_buffer = buffer_times[
    (buffer_times >= "2023-12-31 21:00:00")
    & (buffer_times <= "2023-12-31 23:00:00")
]

if len(wanted_buffer) != 3:
    raise RuntimeError(
        f"Buffer içinde 3 saat bekleniyordu, "
        f"{len(wanted_buffer)} bulundu."
    )

all_rows = extract_station_values(
    ds_buffer,
    stations,
    selected_times=wanted_buffer
)

ds_buffer.close()


# =========================================================
# 2024-2025 ANA VERİ
# =========================================================
for file in nc_files:

    print(f"[OKUYOR] {file.parent.name}")

    ds = xr.open_dataset(
        file,
        engine="netcdf4"
    )

    rows = extract_station_values(
        ds,
        stations
    )

    all_rows.extend(rows)

    ds.close()


# =========================================================
# BİRLEŞTİR
# =========================================================
hourly = pd.concat(
    all_rows,
    ignore_index=True
)


# =========================================================
# UTC -> TÜRKİYE
# =========================================================
hourly["zaman_utc"] = pd.to_datetime(
    hourly["zaman_utc"],
    utc=True
)

hourly["zaman_tr"] = (
    hourly["zaman_utc"]
    .dt.tz_convert("Europe/Istanbul")
)


# =========================================================
# SADECE HEDEF YEREL DÖNEM:
# 2024-01-01 -> 2025-12-31
# =========================================================
hourly["tarih_tr"] = (
    hourly["zaman_tr"]
    .dt.date
)

hourly["tarih_tr_dt"] = pd.to_datetime(
    hourly["tarih_tr"]
)

hourly = hourly[
    (hourly["tarih_tr_dt"] >= "2024-01-01")
    & (hourly["tarih_tr_dt"] <= "2025-12-31")
].copy()


# =========================================================
# SAATLİK KONTROLLER
# =========================================================
if hourly["pm10_cams"].isna().any():
    raise RuntimeError(
        "Saatlik CAMS içinde eksik PM10 bulundu."
    )

duplicate_count = hourly.duplicated(
    subset=["istasyon", "zaman_tr"]
).sum()

if duplicate_count != 0:
    raise RuntimeError(
        f"Saatlik duplicate bulundu: "
        f"{duplicate_count}"
    )


# =========================================================
# SAATLİK DOSYA
# =========================================================
HOURLY_OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

hourly.to_csv(
    HOURLY_OUTPUT,
    index=False,
    encoding="utf-8-sig"
)


# =========================================================
# GÜNLÜK CAMS
# =========================================================
daily = (
    hourly
    .groupby(
        ["istasyon", "tarih_tr_dt"],
        as_index=False
    )
    .agg(
        cams_saat_sayisi=("pm10_cams", "count"),
        pm10_cams_gunluk=("pm10_cams", "mean")
    )
)

daily = daily.rename(
    columns={
        "tarih_tr_dt": "tarih_tr"
    }
)

daily["donem"] = (
    daily["tarih_tr"]
    .dt.strftime("%Y-%m")
)


# =========================================================
# TÜM GÜNLER 24 SAAT Mİ?
# =========================================================
bad_days = daily[
    daily["cams_saat_sayisi"] != 24
].copy()

if len(bad_days) != 0:
    print("\n[HATA] 24 saat olmayan günler:")
    print(
        bad_days.to_string(index=False)
    )

    raise RuntimeError(
        "CAMS günlük zaman kapsaması tam değil."
    )


daily.to_csv(
    DAILY_OUTPUT,
    index=False,
    encoding="utf-8-sig"
)


# =========================================================
# AYLIK CAMS
# =========================================================
monthly = (
    daily
    .groupby(
        ["istasyon", "donem"],
        as_index=False
    )
    .agg(
        cams_gecerli_gun=(
            "pm10_cams_gunluk",
            "count"
        ),
        pm10_cams_aylik=(
            "pm10_cams_gunluk",
            "mean"
        )
    )
)

monthly.to_csv(
    MONTHLY_OUTPUT,
    index=False,
    encoding="utf-8-sig"
)


# =========================================================
# SON KONTROLLER
# =========================================================
print("\n==============================")
print("CAMS ZAMAN QC TAMAMLANDI")
print("==============================")

print(f"Saatlik kayıt : {len(hourly)}")
print(f"Günlük kayıt  : {len(daily)}")
print(f"Aylık kayıt   : {len(monthly)}")

print(
    f"İstasyon sayısı: "
    f"{monthly['istasyon'].nunique()}"
)

print(
    f"Dönem sayısı: "
    f"{monthly['donem'].nunique()}"
)

print(
    f"24 saat olmayan gün: "
    f"{len(bad_days)}"
)

print(
    f"Eksik PM10: "
    f"{hourly['pm10_cams'].isna().sum()}"
)

print("\nGün başına saat sayısı:")
print(
    daily["cams_saat_sayisi"]
    .value_counts()
    .sort_index()
)

print(
    f"\n[OK] Saatlik: {HOURLY_OUTPUT}"
)

print(
    f"[OK] Günlük : {DAILY_OUTPUT}"
)

print(
    f"[OK] Aylık  : {MONTHLY_OUTPUT}"
)