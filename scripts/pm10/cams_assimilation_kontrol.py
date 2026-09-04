import pandas as pd
import numpy as np
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2

# =========================================================
# DOSYALAR
# =========================================================
STATION_FILE = Path(
    "data/pm10/processed/pm10_istasyonlar.csv"
)

LIST_DIR = Path(
    "data/pm10/raw/cams_station_lists"
)

FILES = {
    "assimilation_2024":
        LIST_DIR / "assimilation_PM10_2024.csv",

    "evaluation_2024":
        LIST_DIR / "evaluation_PM10_2024.csv",

    "assimilation_2025":
        LIST_DIR / "assimilation_PM10_2025.csv",

    "evaluation_2025":
        LIST_DIR / "evaluation_PM10_2025.csv",
}

OUTPUT_FILE = Path(
    "outputs/pm10/cams_assimilation_kontrol.csv"
)

MATCH_THRESHOLD_KM = 10.0


# =========================================================
# HAVERSINE
# =========================================================
def haversine_km(lat1, lon1, lat2, lon2):

    R = 6371.0088

    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))
    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    return R * 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )


# =========================================================
# BİZİM İSTASYONLAR
# =========================================================
stations = pd.read_csv(STATION_FILE)

required_station_cols = {
    "istasyon",
    "enlem",
    "boylam"
}

missing = (
    required_station_cols
    - set(stations.columns)
)

if missing:
    raise ValueError(
        f"İstasyon dosyasında eksik sütunlar: {missing}"
    )


# =========================================================
# SONUÇLAR
# =========================================================
all_results = []


for label, file in FILES.items():

    print("\n==============================")
    print(label.upper())
    print("==============================")

    # KRİTİK DÜZELTME:
    # CAMS listeleri ; ile ayrılmış.
    df = pd.read_csv(
        file,
        sep=";"
    )

    print(f"Satır sayısı: {len(df)}")
    print("Sütunlar:")
    print(list(df.columns))

    required = {
        "CODE",
        "LAT",
        "LON"
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"{label}: Eksik sütunlar: {missing}"
        )

    df["LAT"] = pd.to_numeric(
        df["LAT"],
        errors="coerce"
    )

    df["LON"] = pd.to_numeric(
        df["LON"],
        errors="coerce"
    )

    valid = df[
        df["LAT"].notna()
        & df["LON"].notna()
    ].copy()

    # Antalya ve yakın çevresine daralt
    region = valid[
        (valid["LAT"] >= 35.5)
        & (valid["LAT"] <= 38.0)
        & (valid["LON"] >= 29.0)
        & (valid["LON"] <= 33.5)
    ].copy()

    print(
        f"Antalya çevresi CAMS istasyonu: "
        f"{len(region)}"
    )

    if len(region) > 0:
        print("\nBölgedeki CAMS istasyonları:")
        print(
            region[
                [
                    c for c in
                    ["CODE", "TYPE", "AREA", "LAT", "LON", "ALT"]
                    if c in region.columns
                ]
            ].to_string(index=False)
        )

    print("\nBizim istasyonlara en yakın CAMS noktaları:")

    for _, s in stations.iterrows():

        if len(region) == 0:
            print(
                f"{s['istasyon']:12s} -> "
                "bölgede CAMS istasyonu yok"
            )
            continue

        best_distance = None
        best_row = None

        for _, r in region.iterrows():

            distance = haversine_km(
                s["enlem"],
                s["boylam"],
                r["LAT"],
                r["LON"]
            )

            if (
                best_distance is None
                or distance < best_distance
            ):
                best_distance = distance
                best_row = r

        candidate_match = (
            best_distance <= MATCH_THRESHOLD_KM
        )

        result = {
            "liste": label,
            "bizim_istasyon":
                s["istasyon"],

            "bizim_lat":
                s["enlem"],

            "bizim_lon":
                s["boylam"],

            "cams_code":
                best_row["CODE"],

            "cams_type":
                best_row["TYPE"]
                if "TYPE" in best_row
                else None,

            "cams_area":
                best_row["AREA"]
                if "AREA" in best_row
                else None,

            "cams_lat":
                best_row["LAT"],

            "cams_lon":
                best_row["LON"],

            "mesafe_km":
                best_distance,

            "10km_icinde":
                candidate_match
        }

        all_results.append(result)

        flag = (
            "[ADAY EŞLEŞME]"
            if candidate_match
            else ""
        )

        print(
            f"{s['istasyon']:12s} -> "
            f"{best_row['CODE']} | "
            f"{best_distance:.3f} km "
            f"{flag}"
        )


# =========================================================
# SONUÇ
# =========================================================
results = pd.DataFrame(all_results)

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

results.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)


print("\n==============================")
print("10 KM İÇİNDEKİ ADAY EŞLEŞMELER")
print("==============================")

if (
    results.empty
    or "10km_icinde" not in results.columns
):
    print(
        "Aday eşleşme üretilemedi."
    )

else:

    matches = results[
        results["10km_icinde"] == True
    ].copy()

    if matches.empty:
        print(
            "10 km içinde aday eşleşme bulunmadı."
        )

    else:
        print(
            matches[
                [
                    "liste",
                    "bizim_istasyon",
                    "cams_code",
                    "cams_type",
                    "cams_area",
                    "mesafe_km",
                    "cams_lat",
                    "cams_lon"
                ]
            ].to_string(
                index=False,
                float_format=lambda x: f"{x:.4f}"
            )
        )


print(
    f"\n[OK] Detaylı çıktı: {OUTPUT_FILE}"
)