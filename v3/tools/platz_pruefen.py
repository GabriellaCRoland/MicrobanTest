"""Prüft, ob Quader (z. B. der Platzbedarf eines neuen Boards) mit Bauteilen der STEP-Baugruppe zusammenstoßen.

Aufruf: uv run --no-project --python 3.12 --with cadquery-ocp python v3/tools/platz_pruefen.py cad/microban.step
Die Quader stehen unten in KANDIDATEN (Koordinaten wie in step_bauteile.py: x nach vorn, y nach links, z nach oben, mm).
"""
import sys

from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepGProp import BRepGProp
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Pnt
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label
from OCP.collections import Sequence_TDF_Label
from OCP.TDocStd import TDocStd_Document
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFDoc import XCAFDoc_DocumentTool

# Bauteile, die beim Umbau wegfallen, zählen nicht als Hindernis
IGNORIEREN = ("raspberry_pi_zero_2W", "hat", "washer")

# name: (x0, x1, y0, y1, z0, z1)
KANDIDATEN = {
    "Pi Zero 2W + Hat heute (Kontrolle)": (14.8, 26.5, -15.0, 15.6, 26.5, 91.5),
    "Pi 3A+ hochkant, mittig": (14.8, 26.5, -28.0, 28.0, 26.5, 91.5),
    "Pi 3A+ hochkant, nach links": (14.8, 26.5, -15.0, 41.0, 26.5, 91.5),
    "Pi 3A+ hochkant, nach rechts": (14.8, 26.5, -41.0, 15.0, 26.5, 91.5),
    "Pi 3A+ quer, mittig": (14.8, 26.5, -32.5, 32.5, 35.5, 91.5),
    "Pi 3A+ mittig, unterer Streifen": (14.8, 26.5, -28.0, 28.0, 26.5, 33.0),
    "Pi 3A+ mittig, mittlerer Teil": (14.8, 26.5, -28.0, 28.0, 33.0, 82.0),
    "Pi 3A+ mittig, oberer Streifen": (14.8, 26.5, -28.0, 28.0, 82.0, 91.5),
    "USB-A steht 3 mm unten über": (14.8, 26.5, -28.0, 28.0, 23.5, 26.5),
    "USB-A steht 3 mm oben über": (14.8, 26.5, -28.0, 28.0, 91.5, 94.5),
}

doc = TDocStd_Document(TCollection_ExtendedString("doc"))
reader = STEPCAFControl_Reader()
reader.SetNameMode(True)
if reader.ReadFile(sys.argv[1]) != IFSelect_RetDone:
    sys.exit("STEP konnte nicht gelesen werden")
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


def volumen(form):
    p = GProp_GProps()
    BRepGProp.VolumeProperties_s(form, p)
    return p.Mass()


for titel, (x0, x1, y0, y1, z0, z1) in KANDIDATEN.items():
    quader = BRepPrimAPI_MakeBox(gp_Pnt(x0, y0, z0), gp_Pnt(x1, y1, z1)).Shape()
    treffer = []
    for n, form in teile:
        if any(i.lower() in n.lower() for i in IGNORIEREN):
            continue
        schnitt = BRepAlgoAPI_Common(form, quader)
        if schnitt.IsDone():
            v = volumen(schnitt.Shape())
            if v > 1.0:   # mm³; kleiner ist Rundungsrauschen
                treffer.append((n, v))
    print(f"\n{titel}: x {x0}..{x1}  y {y0}..{y1}  z {z0}..{z1}")
    if not treffer:
        print("  frei")
    for n, v in sorted(treffer, key=lambda t: -t[1]):
        print(f"  stößt an {n}: {v:.0f} mm³")
