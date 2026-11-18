"""Liest die Bauteile der Original-Baugruppe (cad/microban.step) mit Namen, Form und Lage (für v3/cad/*.py)."""
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label
from OCP.TDocStd import TDocStd_Document
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.collections import Sequence_TDF_Label


def lade_baugruppe(datei):
    doc = TDocStd_Document(TCollection_ExtendedString("doc"))
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    if reader.ReadFile(str(datei)) != IFSelect_RetDone:
        raise SystemExit(f"{datei} konnte nicht gelesen werden")
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
            teile.append((" / ".join(pfad[-2:]), st.GetShape_s(label), loc))

    wurzeln = Sequence_TDF_Label()
    st.GetFreeShapes(wurzeln)
    for w in wurzeln:
        gehe(w, TopLoc_Location(), [name(w)])
    return teile
