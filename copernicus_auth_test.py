import os
import requests
from dotenv import load_dotenv


# ============================================================
# .ENV YÜKLE
# ============================================================

load_dotenv()

client_id = os.getenv("COPERNICUS_CLIENT_ID")
client_secret = os.getenv("COPERNICUS_CLIENT_SECRET")


if not client_id or not client_secret:
    raise ValueError(
        ".env içinde COPERNICUS_CLIENT_ID "
        "veya COPERNICUS_CLIENT_SECRET bulunamadı."
    )


# ============================================================
# TOKEN AL
# ============================================================

token_url = (
    "https://identity.dataspace.copernicus.eu/"
    "auth/realms/CDSE/protocol/openid-connect/token"
)

data = {
    "grant_type": "client_credentials",
    "client_id": client_id,
    "client_secret": client_secret
}


print("\n==============================")
print("COPERNICUS AUTH TEST")
print("==============================")

print("Access token isteniyor...")


response = requests.post(
    token_url,
    data=data,
    timeout=60
)


print(
    "HTTP durum kodu:",
    response.status_code
)


if response.status_code != 200:

    print("\nHATA:")
    print(response.text)

    raise SystemExit


token_data = response.json()

access_token = token_data.get(
    "access_token"
)


if not access_token:
    raise ValueError(
        "Access token alınamadı."
    )


print("[OK] Access token başarıyla alındı.")

print(
    "Token tipi:",
    token_data.get("token_type")
)

print(
    "Geçerlilik süresi:",
    token_data.get("expires_in"),
    "saniye"
)

print("\n==============================")
print("TEST BAŞARILI")
print("==============================")