import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm


# ==============================
# AYARLAR
# ==============================
MAHALLE = "oba"
YEAR = "2026"
SEASON = "yaz"

population_path = Path(f"outputs/{MAHALLE}/{YEAR}/population_100m_calibrated.tif")
ndvi_path = Path(f"outputs/{MAHALLE}/{YEAR}/{SEASON}/ndvi_100m.tif")
lst_path = Path(f"outputs/{MAHALLE}/{YEAR}/{SEASON}/lst_100m.tif")
boundary_path = Path(f"data/boundaries/{MAHALLE}_pilot_sinir.geojson")

output_dir = Path(f"outputs/{MAHALLE}/{YEAR}/{SEASON}")
output_dir.mkdir(parents=True, exist_ok=True)

figure_path = output_dir / f"{MAHALLE}_{YEAR}_{SEASON}_harita_ozet.png"


# ==============================
# YARDIMCI FONKSİYONLAR
# ==============================
def load_geometry(geojson_path):
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if data["type"] == "FeatureCollection":
        return data["features"][0]["geometry"]
    elif data["type"] == "Feature":
        return data["geometry"]
    else:
        return data


def draw_geometry(ax, geometry, color="black", linewidth=1.2):
    """
    Polygon / MultiPolygon sınırını matplotlib eksenine çizer.
    """
    gtype = geometry["type"]
    coords = geometry["coordinates"]

    if gtype == "Polygon":
        for ring in coords:
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            ax.plot(xs, ys, color=color, linewidth=linewidth)

    elif gtype == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                xs = [p[0] for p in ring]
                ys = [p[1] for p in ring]
                ax.plot(xs, ys, color=color, linewidth=linewidth)


def masked_for_plot(arr, mask_condition):
    arr = arr.astype(float)
    return np.ma.array(arr, mask=~mask_condition)


# ==============================
# VERİLERİ OKU
# ==============================
geometry = load_geometry(boundary_path)

with rasterio.open(population_path) as pop_src:
    population = pop_src.read(1).astype(float)
    transform = pop_src.transform
    bounds = pop_src.bounds
    shape = population.shape

with rasterio.open(ndvi_path) as ndvi_src:
    ndvi = ndvi_src.read(1).astype(float)

with rasterio.open(lst_path) as lst_src:
    lst = lst_src.read(1).astype(float)


# ==============================
# SINIR MASKESİ
# ==============================
boundary_mask = rasterize(
    [(geometry, 1)],
    out_shape=shape,
    transform=transform,
    fill=0,
    dtype="uint8"
).astype(bool)

valid_pop = boundary_mask & (population > 0)
valid_ndvi = boundary_mask & np.isfinite(ndvi)
valid_lst = boundary_mask & np.isfinite(lst)

valid_all = valid_pop & valid_ndvi & valid_lst

if valid_all.sum() == 0:
    raise ValueError("Geçerli ortak grid bulunamadı.")


# ==============================
# EŞİKLER
# ==============================
pop_90 = np.percentile(population[valid_pop], 90)
lst_90 = np.percentile(lst[valid_all], 90)
ndvi_low_threshold = 0.20

critical_ndvi = valid_all & (population >= pop_90) & (ndvi < ndvi_low_threshold)
critical_lst = valid_all & (population >= pop_90) & (lst >= lst_90)

# 0 = yok
# 1 = düşük NDVI kritik
# 2 = yüksek LST kritik
# 3 = ikisi birden
critical_map = np.zeros(shape, dtype=np.uint8)
critical_map[critical_ndvi] = 1
critical_map[critical_lst] = 2
critical_map[critical_ndvi & critical_lst] = 3


# ==============================
# İSTATİSTİK ÖZET
# ==============================
total_population = population[valid_pop].sum()
ndvi_critical_population = population[critical_ndvi].sum()
lst_critical_population = population[critical_lst].sum()
both_critical_population = population[critical_map == 3].sum()

print("\n====================================")
print("HARİTA ÖZETİ")
print("====================================")
print(f"Toplam nüfus: {total_population:.0f}")
print(f"Yüksek nüfus eşiği (%90): {pop_90:.2f} kişi/grid")
print(f"Düşük NDVI eşiği: {ndvi_low_threshold}")
print(f"Yüksek LST eşiği (%90): {lst_90:.2f} °C")
print(f"Kritik düşük NDVI grid sayısı: {critical_ndvi.sum()}")
print(f"Kritik yüksek LST grid sayısı: {critical_lst.sum()}")
print(f"Her iki açıdan kritik grid sayısı: {(critical_map == 3).sum()}")
print(f"Düşük NDVI kritik nüfus: {ndvi_critical_population:.0f}")
print(f"Yüksek LST kritik nüfus: {lst_critical_population:.0f}")
print(f"Her iki açıdan kritik nüfus: {both_critical_population:.0f}")


# ==============================
# ÇİZİM İÇİN MASKELİ ARRAYLER
# ==============================
pop_plot = masked_for_plot(population, valid_pop)
ndvi_plot = masked_for_plot(ndvi, valid_ndvi)
lst_plot = masked_for_plot(lst, valid_lst)
critical_plot = np.ma.array(critical_map, mask=~boundary_mask)

extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]


# ==============================
# HARİTA ÇİZ
# ==============================
fig, axes = plt.subplots(2, 2, figsize=(15, 12))
fig.suptitle(
    f"{MAHALLE.title()} Mahallesi {YEAR} {SEASON.title()} - Çevresel Maruziyet Harita Özeti",
    fontsize=15,
    fontweight="bold"
)

# 1) Nüfus
im0 = axes[0, 0].imshow(pop_plot, extent=extent, origin="upper", cmap="viridis")
draw_geometry(axes[0, 0], geometry)
axes[0, 0].set_title("Nüfus Yoğunluğu (100 m grid)")
axes[0, 0].set_xlabel("Boylam")
axes[0, 0].set_ylabel("Enlem")
cbar0 = plt.colorbar(im0, ax=axes[0, 0], fraction=0.046, pad=0.04)
cbar0.set_label("Kişi / grid")

# 2) NDVI
im1 = axes[0, 1].imshow(ndvi_plot, extent=extent, origin="upper", cmap="YlGn")
draw_geometry(axes[0, 1], geometry)
axes[0, 1].set_title("NDVI (Yeşillik)")
axes[0, 1].set_xlabel("Boylam")
axes[0, 1].set_ylabel("Enlem")
cbar1 = plt.colorbar(im1, ax=axes[0, 1], fraction=0.046, pad=0.04)
cbar1.set_label("NDVI")

# 3) LST
im2 = axes[1, 0].imshow(lst_plot, extent=extent, origin="upper", cmap="hot")
draw_geometry(axes[1, 0], geometry)
axes[1, 0].set_title("LST (Arazi Yüzey Sıcaklığı)")
axes[1, 0].set_xlabel("Boylam")
axes[1, 0].set_ylabel("Enlem")
cbar2 = plt.colorbar(im2, ax=axes[1, 0], fraction=0.046, pad=0.04)
cbar2.set_label("°C")

# 4) Kritik alanlar
crit_cmap = ListedColormap([
    "white",      # 0
    "#3cb44b",    # 1 düşük NDVI kritik
    "#e6194b",    # 2 yüksek LST kritik
    "#911eb4"     # 3 ikisi birden
])
crit_norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5], crit_cmap.N)

im3 = axes[1, 1].imshow(
    critical_plot,
    extent=extent,
    origin="upper",
    cmap=crit_cmap,
    norm=crit_norm
)
draw_geometry(axes[1, 1], geometry)
axes[1, 1].set_title("Kritik Alanlar")
axes[1, 1].set_xlabel("Boylam")
axes[1, 1].set_ylabel("Enlem")

from matplotlib.patches import Patch
legend_items = [
    Patch(facecolor="#3cb44b", edgecolor="black", label="Yoğun nüfus + düşük NDVI"),
    Patch(facecolor="#e6194b", edgecolor="black", label="Yoğun nüfus + yüksek LST"),
    Patch(facecolor="#911eb4", edgecolor="black", label="Her ikisi birden")
]
axes[1, 1].legend(handles=legend_items, loc="lower left", fontsize=9)

plt.tight_layout()
plt.savefig(figure_path, dpi=300, bbox_inches="tight")
plt.show()

print("\n[OK] Harita kaydedildi:")
print(figure_path)