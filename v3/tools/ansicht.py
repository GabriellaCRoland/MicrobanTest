"""Rendert ausgewählte Bauteile einer STEP-Baugruppe (und optional STL-Dateien) als PNG in drei Ansichten.

Aufruf:
  uv run --no-project --python 3.12 --with cadquery-ocp --with matplotlib --with numpy \
      python v3/tools/ansicht.py cad/microban.step bild.png --teile head trunk_top "trunk <1> / XL330" \
      [--stl v3/cad/kopf.stl] [--zmin 90]
Koordinaten: x nach vorn, y nach links, z nach oben (mm).
"""
import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.collections import Sequence_TDF_Label

p = argparse.ArgumentParser()
p.add_argument("step")
p.add_argument("png")
p.add_argument("--teile", nargs="+", default=[])
p.add_argument("--stl", nargs="*", default=[])
p.add_argument("--zmin", type=float, default=None)
args = p.parse_args()

doc = TDocStd_Document(TCollection_ExtendedString("doc"))
reader = STEPCAFControl_Reader()
reader.SetNameMode(True)
if reader.ReadFile(args.step) != IFSelect_RetDone:
    raise SystemExit("STEP konnte nicht gelesen werden")
reader.Transfer(doc)
st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())


def name(label):
    attr = TDataStd_Name()
    return attr.Get().ToExtString() if label.FindAttribute(TDataStd_Name.GetID_s(), attr) else "?"


teile = []


def gehe(label, loc, pfad):
    if st.IsReference_s(label):
        ref = TDF_Label()
        st.GetReferredShape_s(label, ref)
        gehe(ref, loc.Multiplied(st.GetLocation_s(label)), pfad + [name(label)])
    elif st.IsAssembly_s(label):
        kinder = Sequence_TDF_Label()
        st.GetComponents_s(label, kinder)
        for k in kinder:
            gehe(k, loc, pfad)
    else:
        teile.append((" / ".join(pfad[-2:]), st.GetShape_s(label).Moved(loc)))


wurzeln = Sequence_TDF_Label()
st.GetFreeShapes(wurzeln)
for w in wurzeln:
    gehe(w, TopLoc_Location(), [name(w)])


def dreiecke(form):
    BRepMesh_IncrementalMesh(form, 0.3, False, 0.3, True)
    tris = []
    exp = TopExp_Explorer(form, TopAbs_FACE)
    while exp.More():
        face = TopoDS.Face(exp.Current())
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        if tri is not None:
            trsf = loc.Transformation()
            pts = [tri.Node(i).Transformed(trsf) for i in range(1, tri.NbNodes() + 1)]
            pts = np.array([[q.X(), q.Y(), q.Z()] for q in pts])
            for i in range(1, tri.NbTriangles() + 1):
                a, b, c = tri.Triangle(i).Get()
                t = pts[[a - 1, b - 1, c - 1]]
                if face.Orientation() == TopAbs_REVERSED:
                    t = t[[0, 2, 1]]
                tris.append(t)
        exp.Next()
    return np.array(tris).reshape(-1, 3, 3)


FARBEN = ["#4c78a8", "#f58518", "#54a24b", "#e45756", "#72b7b2", "#b279a2", "#ff9da6", "#9d755d", "#bab0ac"]
gruppen = []
for i, muster in enumerate(args.teile):
    tris = [dreiecke(f) for n, f in teile if muster.lower() in n.lower()]
    tris = [t for t in tris if len(t)]
    if tris:
        gruppen.append((muster, np.concatenate(tris), FARBEN[i % len(FARBEN)]))
for j, pfad in enumerate(args.stl):
    import trimesh

    m = trimesh.load_mesh(pfad)
    gruppen.append((pfad.split("/")[-1], m.triangles, FARBEN[(len(args.teile) + j) % len(FARBEN)]))

if args.zmin is not None:
    gruppen = [(n, t[t[:, :, 2].max(axis=1) >= args.zmin], c) for n, t, c in gruppen]

alle = np.concatenate([t.reshape(-1, 3) for _, t, _ in gruppen])
mitte, halb = (alle.max(0) + alle.min(0)) / 2, (alle.max(0) - alle.min(0)).max() / 2 + 2

fig = plt.figure(figsize=(15, 5.5))
for k, (titel, elev, azim) in enumerate([("von vorn (Blick gegen x)", 0, 0), ("von links (Blick gegen y)", 0, 90),
                                         ("schräg von hinten oben", 25, 215)]):
    ax = fig.add_subplot(1, 3, k + 1, projection="3d")
    for n, t, c in gruppen:
        ax.add_collection3d(Poly3DCollection(t, facecolor=c, edgecolor="none", alpha=0.55, label=n))
    for d, s in zip(range(3), "xyz"):
        getattr(ax, f"set_{s}lim")(mitte[d] - halb, mitte[d] + halb)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_xlabel("x vorn")
    ax.set_ylabel("y links")
    ax.set_zlabel("z oben")
    ax.set_title(titel)
fig.legend(handles=[matplotlib.patches.Patch(color=c, label=n) for n, _, c in gruppen], loc="lower center",
           ncol=len(gruppen))
fig.tight_layout()
fig.savefig(args.png, dpi=110)
print("gespeichert:", args.png)
