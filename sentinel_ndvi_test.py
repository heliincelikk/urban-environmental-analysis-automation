from sentinel_module import create_seasonal_ndvi


ndvi_file = create_seasonal_ndvi(

    boundary_file=
        "data/boundaries/oba_pilot_sinir.geojson",

    start_date=
        "2026-03-01",

    end_date=
        "2026-05-31",

    mahalle_name=
        "Oba",

    year=
        2026,

    season_name=
        "ilkbahar",

    max_cloud=
        30
)

print(
    "\nSONUÇ:",
    ndvi_file
)