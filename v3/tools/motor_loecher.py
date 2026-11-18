"""Findet die Schraubenlöcher (kleine Zylinderflächen) eines Bauteils der Baugruppe, z. B. des XL330.

Aufruf: uv run --no-project --python 3.12 --with cadquery-ocp python v3/tools/motor_loecher.py cad/microban.step "ankle_block <2> / XL330"
Ausgabe: Lage der Löcher in Einbaulage und relativ zur Mitte des Bauteils (mm), Achsrichtung, Durchmesser.
"""
import sys
from collections import defaultdict

from OCP.Bnd import Bnd_Box
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBndLib import BRepBndLib
from OCP.GeomAbs import GeomAbs_Cylinder
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.collections import Sequence_TDF_Label

datei, gesucht = sys.argv[1], sys.argv[2]
doc = TDocStd_Document(TCollection_ExtendedString("doc"))
reader = STEPCAFControl_Reader()
reader.SetNameMode(True)
if reader.ReadFile(datei) != IFSelect_RetDone:
    raise SystemExit("STEP konnte nicht gelesen werden")
reader.Transfer(doc)
st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())


def name(label):
    attr = TDataStd_Name()
    return attr.Get().ToExtString() if label.FindAttribute(TDataStd_Name.GetID_s(), attr) else "?"


treffer = []


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
    elif " / ".join(pfad[-2:]) == gesucht:
        treffer.append(st.GetShape_s(label).Moved(loc))


wurzeln = Sequence_TDF_Label()
st.GetFreeShapes(wurzeln)
for w in wurzeln:
    gehe(w, TopLoc_Location(), [name(w)])
if not treffer:
    raise SystemExit(f"nicht gefunden: {gesucht}")
form = treffer[0]
b = Bnd_Box()
BRepBndLib.Add_s(form, b)
lo, hi = b.CornerMin(), b.CornerMax()
mitte = ((lo.X() + hi.X()) / 2, (lo.Y() + hi.Y()) / 2, (lo.Z() + hi.Z()) / 2)
print(f"{gesucht}: {len(treffer)} Stück, erstes: x {lo.X():.1f}..{hi.X():.1f} y {lo.Y():.1f}..{hi.Y():.1f} "
      f"z {lo.Z():.1f}..{hi.Z():.1f}, Mitte {tuple(round(v, 2) for v in mitte)}")
loecher = defaultdict(list)
exp = TopExp_Explorer(form, TopAbs_FACE)
while exp.More():
    f = TopoDS.Face(exp.Current())
    s = BRepAdaptor_Surface(f)
    if s.GetType() == GeomAbs_Cylinder:
        c = s.Cylinder()
        r = c.Radius()
        if r < 2.6:
            a, p = c.Axis().Direction(), c.Axis().Location()
            d = (round(abs(a.X()), 2), round(abs(a.Y()), 2), round(abs(a.Z()), 2))
            # Lochmitte: Achspunkt auf die Mitte projizieren (Koordinate entlang der Achse egal)
            key = (d, round(2 * r, 2), tuple(round(v, 1) for v, ax in zip((p.X(), p.Y(), p.Z()), d) if ax < 0.5))
            fb = Bnd_Box()
            BRepBndLib.Add_s(f, fb)
            loecher[key].append((fb.CornerMin(), fb.CornerMax()))
    exp.Next()
print(f"{'Achse':>16} {'ø':>5}  Lage (quer zur Achse, absolut)      relativ zur Mitte    Tiefe entlang Achse")
for (d, dm, quer), boxen in sorted(loecher.items(), key=lambda k: (k[0][0], k[0][2])):
    ax = max(range(3), key=lambda i: d[i])
    z0 = min(bb[0].Coord(ax + 1) for bb in boxen)
    z1 = max(bb[1].Coord(ax + 1) for bb in boxen)
    quer_ach = [i for i in range(3) if i != ax]
    relativ = tuple(round(q - mitte[i], 2) for q, i in zip(quer, quer_ach))
    print(f"{'xyz'[ax]:>16} {dm:5.2f}  {'xyz'[quer_ach[0]]}={quer[0]:7.1f} {'xyz'[quer_ach[1]]}={quer[1]:7.1f}      "
          f"{relativ}        {'xyz'[ax]} {z0:.1f}..{z1:.1f}")
