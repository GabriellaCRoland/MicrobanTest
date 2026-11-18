"""Senkrechter Schnitt (Ebene y = Wert) durch mehrere STL-Dateien, als PNG.

Aufruf: uv run --no-project --python 3.12 --with trimesh --with matplotlib --with shapely --with networkx --with rtree \
            python v3/tools/schnitt.py bild.png y_wert teil1.stl teil2.stl ...
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import trimesh
from matplotlib.patches import Polygon

png, y, *dateien = sys.argv[1], float(sys.argv[2]), *sys.argv[3:]
FARBEN = ["#4c78a8", "#f58518", "#54a24b", "#e45756", "#72b7b2", "#b279a2", "#9d755d"]
fig, ax = plt.subplots(figsize=(8, 7))
for i, d in enumerate(dateien):
    m = trimesh.load_mesh(d)
    s = m.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    if s is None:
        continue
    pfad, _ = s.to_2D(to_2D=[[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]])
    for poly in pfad.polygons_full:
        ax.add_patch(Polygon(list(poly.exterior.coords), closed=True, fc=FARBEN[i % 7], ec="k", lw=0.5, alpha=0.6,
                             label=Path(d).stem if poly is pfad.polygons_full[0] else None))
        for loch in poly.interiors:
            ax.add_patch(Polygon(list(loch.coords), closed=True, fc="white", ec="k", lw=0.5))
ax.autoscale()
ax.set_aspect("equal")
ax.grid(alpha=0.3)
ax.set_xlabel("x nach vorn (mm)")
ax.set_ylabel("z nach oben (mm)")
ax.set_title(f"Schnitt bei y = {y}")
ax.legend(loc="lower left", fontsize=8)
fig.tight_layout()
fig.savefig(png, dpi=100)
print("gespeichert:", png)
