import json
import folium
import geopandas as gpd


boundary_file = (
    "data/boundaries/"
    "mahmutlar_belediye_sinir_DUZELTILMIS.geojson"
)


gdf = gpd.read_file(boundary_file)

print("\n==============================")
print("MAHMUTLAR SINIR KONTROLÜ")
print("==============================")

print("CRS:", gdf.crs)
print("Feature sayısı:", len(gdf))
print("Geometri tipi:", gdf.geometry.iloc[0].geom_type)


gdf = gdf.to_crs("EPSG:4326")

centroid = gdf.geometry.union_all().centroid

m = folium.Map(
    location=[
        centroid.y,
        centroid.x
    ],
    zoom_start=13,
    tiles="OpenStreetMap"
)


folium.GeoJson(
    gdf,
    name="Mahmutlar Belediye Sınırı",
    style_function=lambda feature: {
        "color": "red",
        "weight": 3,
        "fillColor": "red",
        "fillOpacity": 0.15
    },
    tooltip="Mahmutlar Belediye Sınırı"
).add_to(m)


folium.LayerControl().add_to(m)


output_file = "mahmutlar_sinir_kontrol.html"

m.save(output_file)


print("\n[OK] Harita oluşturuldu:")
print(output_file)