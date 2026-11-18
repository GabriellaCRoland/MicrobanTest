"""Prüft neue Teile (STEP) gegen die Baugruppe und gegeneinander auf Überschneidungen.

Aufruf:
  uv run --no-project --python 3.12 --with cadquery-ocp python v3/tools/teile_pruefen.py cad/microban.step \
      --ohne "trunk <1> / trunk_top" "trunk <1> / charger" \
      --neu v3/cad/step/deckel.step v3/cad/step/platzhalter_ladeplatine.step ... \
      --pruefe v3/cad/step/platzhalter_kabel.step v3/cad/step/platzhalter_ladeplatine.step
--ohne: Bauteile der Baugruppe, die durch neue ersetzt werden (Teil des Namens genügt).
--neu: neue Teile, die als Hindernis mitzählen. --pruefe: Teile, deren Überschneidungen ausgegeben werden.
"""
import argparse
from pathlib import Path

from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
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
p.add_argument("--ohne", nargs="*", default=[])
p.add_argument("--neu", nargs="*", default=[])
p.add_argument("--pruefe", nargs="+")
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
teile = [(n, f) for n, f in teile if not any(o.lower() in n.lower() for o in args.ohne)]


def lade(pfad):
    r = STEPControl_Reader()
    r.ReadFile(str(pfad))
    r.TransferRoots()
    return r.OneShape()


neu = [(Path(d).stem + " (neu)", lade(d)) for d in args.neu]


def volumen(a, b):
    p = GProp_GProps()
    BRepGProp.VolumeProperties_s(BRepAlgoAPI_Common(a, b).Shape(), p)
    return p.Mass()


for d in args.pruefe:
    n0, f0 = Path(d).stem, lade(d)
    treffer = [(n, volumen(f0, f)) for n, f in teile + neu if n != n0 + " (neu)"]
    treffer = [(n, v) for n, v in treffer if v > 0.5]
    print(f"\n{n0}:")
    print("  frei" if not treffer else "\n".join(f"  stößt an {n}: {v:.1f} mm³" for n, v in sorted(treffer, key=lambda t: -t[1])))
