"""Liest eine STEP-Baugruppe und gibt für jedes Bauteil die Lage (Bounding Box im Gesamtkoordinatensystem) aus.

Aufruf: uv run --no-project --python 3.12 --with cadquery-ocp python v3/tools/step_bauteile.py cad/microban.step [Filter]
"""
import sys

from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label
from OCP.collections import Sequence_TDF_Label as TDF_LabelSequence

from OCP.TDocStd import TDocStd_Document
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFDoc import XCAFDoc_DocumentTool

datei = sys.argv[1]
filt = [f.lower() for f in sys.argv[2:]]

doc = TDocStd_Document(TCollection_ExtendedString("doc"))
reader = STEPCAFControl_Reader()
reader.SetNameMode(True)
if reader.ReadFile(datei) != IFSelect_RetDone:
    sys.exit("STEP konnte nicht gelesen werden")
reader.Transfer(doc)
st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())


def name(label):
    attr = TDataStd_Name()
    if label.FindAttribute(TDataStd_Name.GetID_s(), attr):
        return attr.Get().ToExtString()
    return "?"


zeilen = []


def gehe(label, loc, pfad):
    if st.IsReference_s(label):
        ref = TDF_Label()
        st.GetReferredShape_s(label, ref)
        neu = loc.Multiplied(st.GetLocation_s(label))
        gehe(ref, neu, pfad + [name(label)])
        return
    if st.IsAssembly_s(label):
        kinder = TDF_LabelSequence()
        st.GetComponents_s(label, kinder)
        for kind in kinder:
            gehe(kind, loc, pfad)
        return
    form = st.GetShape_s(label).Moved(loc)
    box = Bnd_Box()
    BRepBndLib.Add_s(form, box)
    if box.IsVoid():
        return
    lo, hi = box.CornerMin(), box.CornerMax()
    x0, y0, z0, x1, y1, z1 = lo.X(), lo.Y(), lo.Z(), hi.X(), hi.Y(), hi.Z()
    zeilen.append((" / ".join(pfad[-2:]) or name(label), x0, y0, z0, x1, y1, z1))


wurzeln = TDF_LabelSequence()
st.GetFreeShapes(wurzeln)
for w in wurzeln:
    gehe(w, TopLoc_Location(), [name(w)])

print(f"{'Bauteil':45} {'x von..bis':>17} {'y von..bis':>17} {'z von..bis':>17}   Maße")
for n, x0, y0, z0, x1, y1, z1 in sorted(zeilen, key=lambda z: -z[6]):
    if filt and not any(f in n.lower() for f in filt):
        continue
    print(f"{n[:45]:45} {x0:7.1f}..{x1:7.1f} {y0:7.1f}..{y1:7.1f} {z0:7.1f}..{z1:7.1f}"
          f"   {x1 - x0:5.1f}×{y1 - y0:5.1f}×{z1 - z0:5.1f}")
