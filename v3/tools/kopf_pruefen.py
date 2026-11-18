"""Prüft den neuen Kopf (v3/cad/step) gegen die Baugruppe: Zusammenstöße bei Kopfdrehung und Platz der Kamera.

Aufruf: uv run --no-project --python 3.12 --with cadquery-ocp python v3/tools/kopf_pruefen.py cad/microban.step
"""
import math
import sys
from pathlib import Path

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

ACHSE = (-2.0, 0.0)
WINKEL = [-60, -45, -30, 0, 30, 45, 60]
HINDERNISSE = ("trunk <1> / XL330_without_horn", "trunk <1> / trunk_top", "trunk <1> / switch",
               "shoulder", "humerus")

doc = TDocStd_Document(TCollection_ExtendedString("doc"))
reader = STEPCAFControl_Reader()
reader.SetNameMode(True)
if reader.ReadFile(sys.argv[1]) != IFSelect_RetDone:
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
hindernisse = [(n, f) for n, f in teile if any(h.lower() in n.lower() for h in HINDERNISSE)]


def lade(pfad):
    r = STEPControl_Reader()
    r.ReadFile(str(pfad))
    r.TransferRoots()
    return r.OneShape()


def volumen(a, b):
    s = BRepAlgoAPI_Common(a, b)
    p = GProp_GProps()
    BRepGProp.VolumeProperties_s(s.Shape(), p)
    return p.Mass()


ordner = Path(__file__).parent.parent / "cad" / "step"
kopf = {n: lade(ordner / f"{n}.step") for n in ("kopf_ring", "kopf_basis", "kopf_haube", "platzhalter_ai_camera")}

print("Kamera-Platzhalter gegen Haube/Basis (nur die Bolzen-Stirnflächen dürfen sich berühren):")
for n in ("kopf_haube", "kopf_basis"):
    print(f"  {n}: {volumen(kopf['platzhalter_ai_camera'], kopf[n]):.1f} mm³")

print("\nKopf gedreht gegen Motor, Deckel, Schalter, Schultern (mm³ Überschneidung):")
for w in WINKEL:
    t = gp_Trsf()
    t.SetRotation(gp_Ax1(gp_Pnt(*ACHSE, 0), gp_Dir(0, 0, 1)), math.radians(w))
    treffer = []
    for kn, kf in kopf.items():
        gedreht = kf.Moved(TopLoc_Location(t))
        for hn, hf in hindernisse:
            v = volumen(gedreht, hf)
            if v > 0.5:
                treffer.append(f"{kn}↔{hn}: {v:.0f}")
    print(f"  {w:+4d}°: " + ("frei" if not treffer else "; ".join(treffer)))
