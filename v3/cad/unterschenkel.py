"""Microban v3 – Unterschenkel mit mehr Beweglichkeit im Knöchel.

  schienbein   Original-Schienbein (tibia, aus cad/microban.step) um BEIN_LAENGER verlängert: unterhalb eines
               Schnitts wird alles nach unten geschoben und die Lücke mit dem Querschnitt gefüllt. Alle Anschlüsse
               (Kniemotor oben, Nickachse unten) bleiben exakt wie beim Original.
Der Knöchelblock bleibt das Original (nur tiefer eingebaut). Der Fuß kommt aus v3/cad/fuss.py (BEIN_LAENGER und
SOHLE_TIEFER sind dort genauso eingetragen).

Warum (v3/analyse/knoechel.md): Beim Nicken (Spitze runter) schwenkt der Rollmotor hinten oben in den Kniemotor. Mit
15 mm Abstand ist dort Platz. Die 4 mm tiefere Sohle gibt beim Rollen Luft unter den Schienbein-Armen.

Aufruf (aus dem Repo-Ordner):
  uv run --no-project --python 3.12 --with build123d python v3/cad/unterschenkel.py
Ergebnis: v3/cad/step/schienbein.step, einbau/schienbein.stl, stl/schienbein.stl (Drucklage wie das Original),
dazu Knöchelblock & Motoren in der neuen Lage als einbau/knoechel_*.step/.stl (zum Prüfen und für die Ansicht).
"""
import sys
from pathlib import Path

from build123d import Box, Keep, Location, Plane, Pos, Solid, export_step, export_stl, extrude, section, split

sys.path.insert(0, str(Path(__file__).resolve().parent))
from baugruppe import lade_baugruppe                 # noqa: E402  (liest Teile + Lage aus cad/microban.step)

REPO = Path(__file__).resolve().parents[2]
BEIN_LAENGER = 15.0        # mm, Abstand Knie – Knöchel länger
Z_SCHNITT = -125.0         # Schnitt durch die beiden Seitenarme (unterhalb der Querplatte, oberhalb der Nickachse)

teile = lade_baugruppe(REPO / "cad" / "microban.step")


def teil(name):
    t = [x for x in teile if x[0] == name]
    if not t:
        raise SystemExit(f"nicht gefunden: {name}")
    return t


_, form, lage = teil("tibia <1> / tibia")[0]
original = Solid(form.Moved(lage))

oben = split(original, bisect_by=Plane.XY.offset(Z_SCHNITT), keep=Keep.TOP)
unten = split(original, bisect_by=Plane.XY.offset(Z_SCHNITT), keep=Keep.BOTTOM)
querschnitt = section(original, section_by=Plane.XY.offset(Z_SCHNITT))
fuellung = Pos(0, 0, Z_SCHNITT - BEIN_LAENGER) * extrude(Pos(0, 0, -Z_SCHNITT) * querschnitt, amount=BEIN_LAENGER)
schienbein = oben + fuellung + Pos(0, 0, -BEIN_LAENGER) * unten

ordner = Path(__file__).parent
for unter in ("step", "einbau", "stl"):
    (ordner / unter).mkdir(exist_ok=True)
export_step(schienbein, str(ordner / "step" / "schienbein.step"))
export_stl(schienbein, str(ordner / "einbau" / "schienbein.stl"), tolerance=0.02, angular_tolerance=0.1)
export_stl(Location(lage.Inverted()) * schienbein, str(ordner / "stl" / "schienbein.stl"), tolerance=0.02,
           angular_tolerance=0.1)
bb = schienbein.bounding_box()
print(f"Schienbein: {schienbein.volume:.0f} mm³ (Original {original.volume:.0f}), "
      f"z {bb.min.Z:.1f}..{bb.max.Z:.1f} (Original {original.bounding_box().min.Z:.1f}..{original.bounding_box().max.Z:.1f})")

# Knöchelblock, Motoren, Gegenlager, Schrauben in der neuen (tieferen) Lage – nur zum Prüfen / Anzeigen
for gruppe, datei in (("ankle_block <2> / ankle_dbl_block", "knoechel_block"),
                      ("ankle_block <2> / XL330", "knoechel_motoren"),
                      ("ankle_block <2> / DC15", "knoechel_gegenlager"),
                      ("ankle_block <2> / spacer", "knoechel_spacer")):
    stuecke = [Pos(0, 0, -BEIN_LAENGER) * Solid(f.Moved(l)) for n, f, l in teile if n.startswith(gruppe)]
    ganz = stuecke[0]
    for s in stuecke[1:]:
        ganz += s
    export_step(ganz, str(ordner / "step" / f"{datei}.step"))
    export_stl(ganz, str(ordner / "einbau" / f"{datei}.stl"))
    print(f"{datei}: {len(stuecke)} Teile, 15 mm tiefer")
