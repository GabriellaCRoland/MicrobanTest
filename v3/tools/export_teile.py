"""Exportiert Bauteile einer STEP-Baugruppe an ihrer Einbaulage als STL (eine Datei je Filter).

Aufruf: uv run --no-project --python 3.12 --with cadquery-ocp python v3/tools/export_teile.py cad/microban.step ZIELORDNER filter1 [filter2 ...]
"""
import re
import sys
from pathlib import Path

from OCP.BRep import BRep_Builder
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.IFSelect import IFSelect_RetDone
from OCP.StlAPI import StlAPI_Writer
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label
from OCP.TDocStd import TDocStd_Document
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Compound
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.collections import Sequence_TDF_Label

step, ziel, filter_ = sys.argv[1], Path(sys.argv[2]), sys.argv[3:]
ziel.mkdir(parents=True, exist_ok=True)
doc = TDocStd_Document(TCollection_ExtendedString("doc"))
reader = STEPCAFControl_Reader()
reader.SetNameMode(True)
if reader.ReadFile(step) != IFSelect_RetDone:
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

for f in filter_:
    b, comp = BRep_Builder(), TopoDS_Compound()
    b.MakeCompound(comp)
    n = 0
    for nm, form in teile:
        if f.lower() in nm.lower():
            b.Add(comp, form)
            n += 1
    BRepMesh_IncrementalMesh(comp, 0.05, False, 0.2, True)
    datei = ziel / (re.sub(r"[^a-zA-Z0-9]+", "_", f).strip("_") + ".stl")
    StlAPI_Writer().Write(comp, str(datei))
    print(f"{f}: {n} Teile -> {datei}")
