import openeo

OPENEO_URL = "https://openeo.dataspace.copernicus.eu"

print("\n==============================")
print("OPENEO KOLEKSİYON KONTROLÜ")
print("==============================")

connection = openeo.connect(OPENEO_URL)

print("Copernicus bağlantısı kuruluyor...")

connection.authenticate_oidc()

print("[OK] Giriş yapıldı.")

print("\n==============================")
print("MEVCUT KOLEKSİYONLAR")
print("==============================")

collections = connection.list_collection_ids()

for collection_id in collections:
    print("-", collection_id)

print("\n==============================")
print("LANDSAT ARAMASI")
print("==============================")

landsat_collections = [
    collection_id
    for collection_id in collections
    if "LANDSAT" in collection_id.upper()
]

if landsat_collections:
    print("Landsat koleksiyonları bulundu:")

    for collection_id in landsat_collections:
        print("-", collection_id)

else:
    print(
        "Bu openEO backend'inde "
        "Landsat koleksiyonu bulunamadı."
    )

print("\n==============================")
print("KONTROL TAMAMLANDI")
print("==============================")