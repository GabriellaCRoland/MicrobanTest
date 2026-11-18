"""Waagerechte Schnitte (z = Werte) durch mehrere STL-Dateien übereinander, als PNG (Draufsicht).

Aufruf: uv run --no-project --python 3.12 --with trimesh --with matplotlib --with shapely --with networkx \
            --with rtree --with scipy python v3/tools/draufsicht.py bild.png "z1,z2,..." teil1.stl teil2.stl ...
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import trimesh
from matplotlib.patches import Patch, Polygon

png, hoehen, *dateien = sys.argv[1], [float(z) for z in sys.argv[2].split(",")], *sys.argv[3:]
FARBEN = ["#4c78a8", "#f58518", "#54a24b", "#e45756", "#72b7b2", "#b279a2", "#9d755d", "#bab0ac"]
netze = [trimesh.load_mesh(d) for d in dateien]
fig, axs = plt.subplots(1, len(hoehen), figsize=(5 * len(hoehen), 5.6), squeeze=False)
for ax, z in zip(axs[0], hoehen):
    for i, m in enumerate(netze):
        s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if s is None:
            continue
        for poly in s.to_2D(to_2D=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, -z], [0, 0, 0, 1]])[0].polygons_full:
            ax.add_patch(Polygon(list(poly.exterior.coords), closed=True, fc=FARBEN[i % 8], ec="k", lw=0.4, alpha=0.6))
            for loch in poly.interiors:
                ax.add_patch(Polygon(list(loch.coords), closed=True, fc="white", ec="k", lw=0.4))
    ax.set_xlim(-40, 40)
    ax.set_ylim(-58, 58)
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.set_title(f"z = {z}")
    ax.set_xlabel("x nach vorn")
    ax.set_ylabel("y nach links")
fig.legend(handles=[Patch(color=FARBEN[i % 8], label=Path(d).stem) for i, d in enumerate(dateien)], loc="lower center",
           ncol=min(len(dateien), 8))
fig.tight_layout(rect=(0, 0.06, 1, 1))
fig.savefig(png, dpi=90)
print("gespeichert:", png)
