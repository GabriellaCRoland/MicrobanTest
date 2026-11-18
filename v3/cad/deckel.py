"""Microban v3 – Deckel (trunk_top) für die Kopfkamera, auf Basis des Original-Deckels aus cad/microban.step.

Änderungen gegenüber dem Original (alles in Einbaulage, mm: x nach vorn, y nach links, z nach oben):
  1. Kabelschlitz hinter dem Kopfmotor für das Kamerakabel (passt zum Schlitz in v3/cad/kopf.py).
  2. Ladeplatine 4 mm nach rechts (−y), damit das Kabel daneben nach unten kann: USB-C-Öffnung in der Rückwand
     verschoben, alte Öffnung zu, neue Haltenase links.

Außerdem als Platzhalter zum Prüfen: Ladeplatine an der neuen Stelle und der Kabelweg bis zum Pi Zero 2 W
(Kameraanschluss oben, Pi um 180° gedreht eingebaut).

Aufruf (aus dem Repo-Ordner):
  uv run --no-project --python 3.12 --with build123d python v3/cad/deckel.py
"""
from pathlib import Path

from build123d import Box, Location, Pos, Solid, export_step, export_stl
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label
from OCP.TDocStd import TDocStd_Document
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.collections import Sequence_TDF_Label

REPO = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------- Maße
KABEL_Y = (-6.5, 9.5)            # Flachbandkabel 16 mm, 1,5 mm nach links versetzt (Platz zur Ladeplatine)
SCHLITZ_X = (-16.5, -12.7)       # vorn bleibt 1 mm Wand zur Motorschraube (x −11,7)
SCHLITZ_Y = (KABEL_Y[0] - 0.5, KABEL_Y[1] + 0.5)
LADER_VERSATZ = -4.0             # Ladeplatine in y
# USB-C-Buchse der Ladeplatine heute: x −32 … −25,5, y −16,9 … −7,9, z 92,5 … 96
USB_X, USB_Y, USB_Z = (-32.0, -25.5), (-16.9, -7.9), (92.5, 96.0)
SPIEL = 0.4


def quader(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


# ---------------------------------------------------------------- Original aus der Baugruppe lesen
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


teile = lade_baugruppe(REPO / "cad" / "microban.step")
_, form, lage = next(t for t in teile if t[0] == "trunk <1> / trunk_top")
_, lader_form, lader_lage = next(t for t in teile if t[0] == "trunk <1> / charger")
deckel = Solid(form.Moved(lage))
lader = Solid(lader_form.Moved(lader_lage))

# ---------------------------------------------------------------- 1. Kabelschlitz
deckel -= quader(*SCHLITZ_X, *SCHLITZ_Y, 88.0, 110.0)

# ---------------------------------------------------------------- 2. Ladeplatine versetzen
usb_neu_y = (USB_Y[0] + LADER_VERSATZ, USB_Y[1] + LADER_VERSATZ)
# alte Öffnung in der Rückwand schließen (der Teil, den die Buchse nicht mehr braucht)
LADER_UNTEN = 95.5                # Unterseite der Ladeplatine
deckel += quader(-33.0, USB_X[1], usb_neu_y[1] + SPIEL, USB_Y[1] + SPIEL, USB_Z[0] - 0.5, LADER_UNTEN - 0.1)
# neue Öffnung (Buchse + Spiel, nach hinten offen für den Stecker)
deckel -= quader(-34.0, USB_X[1] + SPIEL, usb_neu_y[0] - SPIEL, usb_neu_y[1] + SPIEL, USB_Z[0] - SPIEL, USB_Z[1] + SPIEL)
# Haltenase links neben der Buchse
deckel += quader(-31.0, USB_X[1], usb_neu_y[1] + SPIEL, usb_neu_y[1] + SPIEL + 2.0, USB_Z[0] - 0.5, LADER_UNTEN - 0.1)
# flache Tasche im Schraubendom rechts für den Platinenrand (Schraube sitzt bei z 85,8)
deckel -= quader(-31.5, -24.0, -21.5 + LADER_VERSATZ - SPIEL, -21.0, LADER_UNTEN - SPIEL, 97.5 + SPIEL)
lader = Pos(0, LADER_VERSATZ, 0) * lader

# ---------------------------------------------------------------- Platzhalter Kabelweg (0,3 mm dick)
d = 0.3
kabel = quader(SCHLITZ_X[0] + 1.5, SCHLITZ_X[0] + 1.5 + d, *KABEL_Y, 94.0, 129.0)     # senkrecht hinter dem Motor
kabel += quader(SCHLITZ_X[0] + 1.5, 24.0, *KABEL_Y, 94.0, 94.0 + d)                    # nach vorn über dem Akku
kabel += quader(24.0 - d, 24.0, -6.0, 6.0, 89.5, 94.3)                                 # hinunter in den Pi-Anschluss (22-pol.)

# ---------------------------------------------------------------- Ausgabe
ordner = Path(__file__).parent
for unter in ("step", "einbau", "stl"):
    (ordner / unter).mkdir(exist_ok=True)
export_step(deckel, str(ordner / "step" / "deckel.step"))
export_stl(deckel, str(ordner / "einbau" / "deckel.stl"), tolerance=0.02, angular_tolerance=0.1)
# Drucklage: wie das Original-STL (cad/stl/trunk_top.stl), also zurück in die Teilkoordinaten
lage_inv = Location(lage.Inverted())
export_stl(lage_inv * deckel, str(ordner / "stl" / "deckel.stl"), tolerance=0.02, angular_tolerance=0.1)
for name, teil in (("platzhalter_ladeplatine", lader), ("platzhalter_kabel", kabel)):
    export_step(teil, str(ordner / "step" / f"{name}.step"))
    export_stl(teil, str(ordner / "einbau" / f"{name}.stl"))
print(f"Deckel: Volumen {deckel.volume:.0f} mm³ (Original {Solid(form).volume:.0f} mm³)")
