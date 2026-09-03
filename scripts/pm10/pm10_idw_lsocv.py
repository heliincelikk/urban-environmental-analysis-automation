import os
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ==============================
# DOSYA YOLLARI
# ==============================

ISTASYON_DOSYA = "data/pm10/processed/pm10_istasyonlar.csv"
PM10_DOSYA = "data/pm10/processed/pm10_gunluk_tum.csv"

CIKTI_KLASOR = "outputs/pm10"

ANA_SONUC_DOSYA = os.path.join(
    CIKTI_KLASOR,
    "pm10_idw_p2_lsocv_sonuclar.csv"
)

ANA_TAHMIN_DOSYA = os.path.join(
    CIKTI_KLASOR,
    "pm10_idw_p2_lsocv_tahminler.csv"
)

DUYARLILIK_DOSYA = os.path.join(
    CIKTI_KLASOR,
    "pm10_idw_power_duyarlilik.csv"
)


# ==============================
# HAVERSINE MESAFESI
# ==============================

def haversine_km(lat1, lon1, lat2, lon2):
    """
    Iki enlem-boylam noktasi arasindaki
    kusbakisi yuzey mesafesini kilometre cinsinden hesaplar.
    """

    R = 6371.0

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    c = 2 * np.arcsin(np.sqrt(a))

    return R * c


# ==============================
# TEK BIR IDW TAHMINI
# ==============================

def idw_tahmin(
    test_lat,
    test_lon,
    kaynak_df,
    power=2.0
):
    """
    Kaynak istasyonlarin PM10 degerlerinden
    test konumu icin IDW tahmini uretir.
    """

    mesafeler = haversine_km(
        test_lat,
        test_lon,
        kaynak_df["enlem"].to_numpy(),
        kaynak_df["boylam"].to_numpy()
    )

    # Guvenlik kontrolu:
    # test istasyonu kaynaklar arasinda olmamali.
    if np.any(mesafeler == 0):
        raise ValueError(
            "Kaynak istasyonlar arasinda test istasyonu olabilir. "
            "Mesafe 0 bulundu."
        )

    agirliklar = 1.0 / (mesafeler ** power)

    pm10_degerleri = kaynak_df["pm10_gunluk"].to_numpy()

    tahmin = np.sum(
        agirliklar * pm10_degerleri
    ) / np.sum(agirliklar)

    return tahmin, len(kaynak_df)


# ==============================
# TEK POWER DEGERI ICIN LOSO
# ==============================

def loso_idw_calistir(
    pm10_df,
    istasyon_df,
    power
):

    tum_tahminler = []

    test_istasyonlari = istasyon_df["istasyon"].tolist()

    for test_istasyon in test_istasyonlari:

        test_bilgi = istasyon_df[
            istasyon_df["istasyon"] == test_istasyon
        ].iloc[0]

        test_lat = test_bilgi["enlem"]
        test_lon = test_bilgi["boylam"]

        test_gunleri = pm10_df[
            (pm10_df["istasyon"] == test_istasyon)
            & (pm10_df["gecerli_gun"] == True)
            & (pm10_df["pm10_gunluk"].notna())
        ].copy()

        for _, test_satir in test_gunleri.iterrows():

            tarih = test_satir["tarih"]
            gercek_pm10 = test_satir["pm10_gunluk"]

            # O gun mevcut olan diger istasyonlari al.
            kaynak = pm10_df[
                (pm10_df["tarih"] == tarih)
                & (pm10_df["istasyon"] != test_istasyon)
                & (pm10_df["gecerli_gun"] == True)
                & (pm10_df["pm10_gunluk"].notna())
            ].copy()

            # Koordinatlari ekle.
            kaynak = kaynak.merge(
                istasyon_df[
                    ["istasyon", "enlem", "boylam"]
                ],
                on="istasyon",
                how="left",
                validate="many_to_one"
            )

            # Teorik olarak veri yapimizda
            # birden fazla kaynak olacak.
            # Yine de guvenlik kontrolu koyuyoruz.
            if len(kaynak) < 1:
                continue

            tahmin, kaynak_sayisi = idw_tahmin(
                test_lat=test_lat,
                test_lon=test_lon,
                kaynak_df=kaynak,
                power=power
            )

            tum_tahminler.append(
                {
                    "tarih": tarih,
                    "test_istasyon": test_istasyon,
                    "gercek_pm10": gercek_pm10,
                    "tahmin_pm10": tahmin,
                    "hata": tahmin - gercek_pm10,
                    "kullanilan_kaynak_sayisi": kaynak_sayisi,
                    "power": power
                }
            )

    tahmin_df = pd.DataFrame(tum_tahminler)

    return tahmin_df


# ==============================
# METRIK HESAPLAMA
# ==============================

def metrik_hesapla(tahmin_df):

    sonuclar = []

    for istasyon, grup in tahmin_df.groupby(
        "test_istasyon"
    ):

        y_true = grup["gercek_pm10"]
        y_pred = grup["tahmin_pm10"]

        mae = mean_absolute_error(
            y_true,
            y_pred
        )

        rmse = np.sqrt(
            mean_squared_error(
                y_true,
                y_pred
            )
        )

        r2 = r2_score(
            y_true,
            y_pred
        )

        bias = (
            y_pred - y_true
        ).mean()

        sonuclar.append(
            {
                "test_istasyon": istasyon,
                "n": len(grup),
                "MAE": mae,
                "RMSE": rmse,
                "R2": r2,
                "Bias": bias,
                "ortalama_kaynak_sayisi":
                    grup[
                        "kullanilan_kaynak_sayisi"
                    ].mean()
            }
        )

    sonuc_df = pd.DataFrame(sonuclar)

    return sonuc_df


# ==============================
# ANA PROGRAM
# ==============================

os.makedirs(
    CIKTI_KLASOR,
    exist_ok=True
)

istasyon_df = pd.read_csv(
    ISTASYON_DOSYA
)

pm10_df = pd.read_csv(
    PM10_DOSYA
)

pm10_df["tarih"] = pd.to_datetime(
    pm10_df["tarih"]
)

print(
    "\n=============================="
)
print(
    "IDW LOSO ANALIZI"
)
print(
    "=============================="
)

print(
    "\nIstasyon sayisi:",
    istasyon_df["istasyon"].nunique()
)

print(
    "PM10 satir sayisi:",
    len(pm10_df)
)


# ==============================
# ANA BASELINE: POWER = 2
# ==============================

print(
    "\nAna IDW baseline calisiyor..."
)
print(
    "Power = 2"
)

ana_tahmin_df = loso_idw_calistir(
    pm10_df=pm10_df,
    istasyon_df=istasyon_df,
    power=2.0
)

ana_sonuc_df = metrik_hesapla(
    ana_tahmin_df
)

ana_tahmin_df.to_csv(
    ANA_TAHMIN_DOSYA,
    index=False
)

ana_sonuc_df.to_csv(
    ANA_SONUC_DOSYA,
    index=False
)


print(
    "\n=============================="
)
print(
    "ISTASYON BAZLI SONUCLAR"
)
print(
    "=============================="
)

print(
    ana_sonuc_df.to_string(
        index=False
    )
)


# ==============================
# POOLED SONUC
# ==============================

y_true = ana_tahmin_df[
    "gercek_pm10"
]

y_pred = ana_tahmin_df[
    "tahmin_pm10"
]

pooled_mae = mean_absolute_error(
    y_true,
    y_pred
)

pooled_rmse = np.sqrt(
    mean_squared_error(
        y_true,
        y_pred
    )
)

pooled_r2 = r2_score(
    y_true,
    y_pred
)

pooled_bias = (
    y_pred - y_true
).mean()


print(
    "\n=============================="
)
print(
    "POOLED IDW SONUCU"
)
print(
    "=============================="
)

print(
    "MAE :",
    round(pooled_mae, 3)
)

print(
    "RMSE:",
    round(pooled_rmse, 3)
)

print(
    "R2  :",
    round(pooled_r2, 3)
)

print(
    "Bias:",
    round(pooled_bias, 3)
)


# ==============================
# POWER DUYARLILIK ANALIZI
# ==============================

power_degerleri = [
    1.0,
    1.5,
    2.0,
    2.5,
    3.0
]

duyarlilik_sonuclari = []

print(
    "\n=============================="
)
print(
    "POWER DUYARLILIK ANALIZI"
)
print(
    "=============================="
)

for power in power_degerleri:

    tahmin_df = loso_idw_calistir(
        pm10_df=pm10_df,
        istasyon_df=istasyon_df,
        power=power
    )

    y_true = tahmin_df[
        "gercek_pm10"
    ]

    y_pred = tahmin_df[
        "tahmin_pm10"
    ]

    mae = mean_absolute_error(
        y_true,
        y_pred
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_true,
            y_pred
        )
    )

    r2 = r2_score(
        y_true,
        y_pred
    )

    bias = (
        y_pred - y_true
    ).mean()

    duyarlilik_sonuclari.append(
        {
            "power": power,
            "n": len(tahmin_df),
            "MAE": mae,
            "RMSE": rmse,
            "R2": r2,
            "Bias": bias
        }
    )


duyarlilik_df = pd.DataFrame(
    duyarlilik_sonuclari
)

duyarlilik_df.to_csv(
    DUYARLILIK_DOSYA,
    index=False
)


print(
    duyarlilik_df.to_string(
        index=False
    )
)


# ==============================
# KAYNAK SAYISI KONTROLU
# ==============================

print(
    "\n=============================="
)
print(
    "KULLANILAN KAYNAK SAYISI"
)
print(
    "=============================="
)

print(
    ana_tahmin_df[
        "kullanilan_kaynak_sayisi"
    ]
    .value_counts()
    .sort_index()
    .to_string()
)


print(
    "\nDosyalar kaydedildi:"
)

print(
    ANA_SONUC_DOSYA
)

print(
    ANA_TAHMIN_DOSYA
)

print(
    DUYARLILIK_DOSYA
)