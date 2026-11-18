"""Prüft neue Teile, die sich um ein Gelenk drehen, gegen feste Teile der Baugruppe (Überschneidung in mm³).

Aufruf:
  uv run --no-project --python 3.12 --with cadquery-ocp python v3/tools/gelenk_pruefen.py cad/microban.step \
      --teile v3/cad/step/fuss.step v3/cad/step/fuss_sohle.step \
      --punkt 0 -36 -144.62 --richtung 1 0 0 --winkel -35 -20 0 20 35 \
      --hindernisse "ankle_block <2>" "tibia <1>"
--hindernisse: Teile der Baugruppe (Teil des Namens genügt), die sich NICHT mitdrehen.
"""
import argparse
import math

from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label
from OCP.TDocStd import TDocStd_Document
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.collections import Sequence_TDF_Label

p = argparse.ArgumentParser()
p.add_argument("step")
p.add_argument("--teile", nargs="*", default=[])
p.add_argument("--mitdrehen", nargs="*", default=[], help="Teile der Baugruppe, die sich mitdrehen")
p.add_argument("--punkt", nargs=3, type=float)
p.add_argument("--richtung", nargs=3, type=float)
p.add_argument("--winkel", nargs="+", type=float)
p.add_argument("--hindernisse", nargs="*", default=[])
p.add_argument("--feste-neu", nargs="*", default=[], help="neue feste Teile (STEP)")
a = p.parse_args()

doc = TDocStd_Document(TCollection_ExtendedString("doc"))
reader = STEPCAFControl_Reader()
reader.SetNameMode(True)
if reader.ReadFile(a.step) != IFSelect_RetDone:
    raise SystemExit("STEP konnte nicht gelesen werden")
reader.Transfer(doc)
st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())


def name(label):
    attr = TDataStd_Name()
    return attr.Get().ToExtString() if label.FindAttribute(TDataStd_Name.GetID_s(), attr) else "?"


feste = []
drehende_alt = []


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
        n = " / ".join(pfad[-2:])
        if any(h.lower() in n.lower() for h in a.mitdrehen):
            drehende_alt.append((n, st.GetShape_s(label).Moved(loc)))
        elif any(h.lower() in n.lower() for h in a.hindernisse):
            feste.append((n, st.GetShape_s(label).Moved(loc)))


wurzeln = Sequence_TDF_Label()
st.GetFreeShapes(wurzeln)
for w in wurzeln:
    gehe(w, TopLoc_Location(), [name(w)])


def lade(pfad):
    r = STEPControl_Reader()
    r.ReadFile(pfad)
    r.TransferRoots()
    return r.OneShape()


def volumen(x, y):
    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(BRepAlgoAPI_Common(x, y).Shape(), g)
    return g.Mass()


teile = [(t.replace("\\", "/").split("/")[-1], lade(t)) for t in a.teile] + drehende_alt
feste += [(t.replace("\\", "/").split("/")[-1], lade(t)) for t in a.feste_neu]
print(f"{len(feste)} feste Teile: {sorted({n for n, _ in feste})}")
for w in a.winkel:
    t = gp_Trsf()
    t.SetRotation(gp_Ax1(gp_Pnt(*a.punkt), gp_Dir(*a.richtung)), math.radians(w))
    treffer = []
    for tn, tf in teile:
        g = tf.Moved(TopLoc_Location(t))
        for fn, ff in feste:
            v = volumen(g, ff)
            if v > 0.5:
                treffer.append(f"{tn}↔{fn}: {v:.0f}")
    print(f"  {w:+6.1f}°: " + ("frei" if not treffer else "; ".join(treffer)))
