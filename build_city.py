import geopandas as gpd
import matplotlib.pyplot as plt

boundary = gpd.read_file("data/boundary.geojson")
roads = gpd.read_file("data/roads.geojson")
signals = gpd.read_file("data/signals.geojson")

roads = roads.to_crs(boundary.crs)
signals = signals.to_crs(boundary.crs)

roads = gpd.clip(roads, boundary)
signals = gpd.clip(signals, boundary)

fig, ax = plt.subplots(figsize=(10,10))
boundary.plot(ax=ax, facecolor="none", edgecolor="black")
roads.plot(ax=ax, linewidth=0.5)
signals.plot(ax=ax, color="red", markersize=4)

plt.title("DC Transport Model Check")
plt.show()