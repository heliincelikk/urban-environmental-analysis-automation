from sentinel_module import create_seasonal_ndvi


ndvi_file = create_seasonal_ndvi(
    boundary_file=(
        "data/boundaries/"
        "mahmutlar_belediye_sinir_DUZELTILMIS.geojson"
    ),
    start_date="2026-06-01",
    end_date="2026-08-30",
    mahalle_name="Mahmutlar",
    year=2026,
    season_name="yaz",
    max_cloud=30
)


print("\nSONUÇ:", ndvi_file)