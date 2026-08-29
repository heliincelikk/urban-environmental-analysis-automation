from sentinel_module import search_sentinel2

results = search_sentinel2(
    boundary_file="data/boundaries/oba_pilot_sinir.geojson",
    start_date="2026-03-01",
    end_date="2026-05-31",
    max_cloud=30
)

print("\nToplam uygun görüntü:", len(results))