"""Microban v3 – Fuß (technisch-clean) mit TPU-Sohle, Code-CAD (build123d).

Zwei Teile, beide flach auf dem Druckbett, ohne Stützmaterial:
  fuss        PLA: Sohlenplatte, Mittelrippe, zwei Arme an Servohorn (hinten) und Gegenlager (vorn) des Knöchel-Rollmotors
  fuss_sohle  TPU: Laufsohle mit Querrillen, bündig unter die flache Platte geklebt (Rillen oben drucken)
Beide Füße sind gleich (wie beim Original, 2 × drucken).

Anschluss wie beim Original (cad/stl/foot.stl), Koordinaten wie cad/microban.step für den linken Fuß „foot <1>“ (mm):
Rollachse parallel zu x bei y = −36, z = −144,62 − BEIN_LAENGER; Arme innen bei x = −23 (Horn) und x = 32,5 (Gegenlager), Lochbild
4 × ø2 auf 6 mm Radius + ø6 Mitte; Unterseite der Sohle 27 mm unter der Rollachse (Original 23).

Aufruf (aus dem Repo-Ordner):
  uv run --no-project --python 3.12 --with build123d python v3/cad/fuss.py
"""
import math
from pathlib import Path

from build123d import (Axis, Box, Cylinder, Polygon, Pos, Rot, chamfer, export_step, export_stl, extrude, Plane)

# ---------------------------------------------------------------- Anschluss (nicht ändern)
BEIN_LAENGER = 15.0             # Schienbein länger (v3/cad/unterschenkel.py) → Knöchel 15 mm tiefer
SOHLE_TIEFER = 4.0              # Sohle zusätzlich tiefer unter der Rollachse → mehr Luft beim Rollen
ACHSE_Y, ACHSE_Z = -36.0, -144.62 - BEIN_LAENGER
ARM_HINTEN_INNEN, ARM_VORN_INNEN = -23.0, 32.5
LOCHKREIS, LOCH, LOCH_MITTE = 6.0, 2.0, 6.0
Z_BODEN = -167.6 - BEIN_LAENGER - SOHLE_TIEFER

# ---------------------------------------------------------------- Gestaltung (frei, im Simulator geprüft)
SOHLE_X = (-26.0, 54.0)         # 80 mm, Ferse wie das Original, vorn 10 mm kürzer (Lauftest: Zehe ≥ x 54 nötig)
SOHLE_B = 40.0                  # Breite (Original 45)
FASE_VORN, FASE_HINTEN = 8.0, 4.0
TPU_D = 2.0                     # TPU-Sohle unter der Platte
TPU_RAND = 0.3                  # TPU-Sohle etwas kleiner als die Platte (Kleberand)
PLATTE_D = 3.0
KANTE = 1.0                     # Fase an allen oberen Kanten (einheitlich)
ARM_D, ARM_B = 3.0, 18.0
ARM_FASE = 5.0                  # 45° oben an den Armen (Material um die Löcher bleibt ≥ 1,5 mm)
SENKUNG_D, SENKUNG_T = 4.2, 1.2 # Schraubenköpfe STP39 2x6 (ø3,9 × 1,4) liegen versenkt
RIPPE_H, RIPPE_B = 4.0, 8.0     # Mittelrippe, 45°-Flanken; Spitze 18 mm unter der Rollachse (Knöchelblock bei 55° Rollen: 16,5)
RILLE_B, RILLE_T, RILLE_TEILUNG = 1.0, 0.8, 5.0

Z_PLATTE_UNTEN = Z_BODEN + TPU_D                # Unterseite PLA, ganz flach (liegt beim Druck auf dem Bett)
Z_PLATTE_OBEN = Z_PLATTE_UNTEN + PLATTE_D


def sohlen_umriss(rand=0.0):
    x0, x1 = SOHLE_X[0] + rand, SOHLE_X[1] - rand
    y0, y1 = ACHSE_Y - SOHLE_B / 2 + rand, ACHSE_Y + SOHLE_B / 2 - rand
    fv, fh = max(FASE_VORN - rand * 0.6, 1), max(FASE_HINTEN - rand * 0.6, 1)
    return Polygon((x0 + fh, y0), (x1 - fv, y0), (x1, y0 + fv), (x1, y1 - fv), (x1 - fv, y1), (x0 + fh, y1),
                   (x0, y1 - fh), (x0, y0 + fh), align=None)


def arm(x_innen, nach_aussen):
    """Arm als Achteck-Platte in der yz-Ebene, Dicke ARM_D in x (nach_aussen = +1 oder −1)."""
    h = ARM_B / 2
    oben = ACHSE_Z + h
    unten = Z_PLATTE_OBEN - 0.5
    pts = [(-h, unten), (h, unten), (h, oben - ARM_FASE), (h - ARM_FASE, oben), (-h + ARM_FASE, oben), (-h, oben - ARM_FASE)]
    platte = extrude(Plane.YZ.offset(0) * Polygon(*pts, align=None), amount=ARM_D)
    x0 = x_innen if nach_aussen > 0 else x_innen - ARM_D
    teil = Pos(x0, ACHSE_Y, 0) * platte
    # 45°-Zwickel unten zur Platte (seitlich), damit der Arm steif steht
    for s in (1, -1):
        punkte = [(0, 0), (s * 4.0, 0), (0, 4.0)]
        zw = Polygon(*(punkte if s > 0 else punkte[::-1]), align=None)   # immer gegen den Uhrzeigersinn
        teil += Pos(x0, ACHSE_Y + s * h, Z_PLATTE_OBEN - 0.01) * extrude(Plane.YZ * zw, amount=ARM_D)
    # Löcher (Achse parallel zu x) und Senkungen außen
    x_aussen = x0 + (ARM_D if nach_aussen > 0 else 0)
    for dy, dz in ((LOCHKREIS, 0), (-LOCHKREIS, 0), (0, LOCHKREIS), (0, -LOCHKREIS)):
        teil -= Pos(x0 + ARM_D / 2, ACHSE_Y + dy, ACHSE_Z + dz) * Rot(0, 90, 0) * Cylinder(LOCH / 2, ARM_D + 1)
        teil -= Pos(x_aussen, ACHSE_Y + dy, ACHSE_Z + dz) * Rot(0, 90, 0) * Cylinder(SENKUNG_D / 2, 2 * SENKUNG_T)
    # Mittelloch als Tropfen (45°-Spitze nach oben): druckt ohne Durchhängen, Platz für den Hornschlüssel bleibt
    r = LOCH_MITTE / 2
    teil -= Pos(x0 + ARM_D / 2, ACHSE_Y, ACHSE_Z) * Rot(0, 90, 0) * Cylinder(r, ARM_D + 1)
    spitze = Polygon((-r / math.sqrt(2), r / math.sqrt(2)), (r / math.sqrt(2), r / math.sqrt(2)), (0, r * math.sqrt(2)), align=None)
    teil -= Pos(x0 - 0.5, ACHSE_Y, ACHSE_Z) * extrude(Plane.YZ * spitze, amount=ARM_D + 1)
    return teil


# ---------------------------------------------------------------- PLA-Fuß
platte = Pos(0, 0, Z_PLATTE_UNTEN) * extrude(sohlen_umriss(), amount=PLATTE_D)
platte = chamfer(platte.edges().group_by(Axis.Z)[-1], KANTE)
# Mittelrippe (Dreieck mit 45°-Flanken) entlang x zwischen den Armen, vorn flach auslaufend
rippe_profil = Polygon((-RIPPE_B / 2, 0), (RIPPE_B / 2, 0), (0, RIPPE_H), align=None)
rippe = Pos(ARM_HINTEN_INNEN, ACHSE_Y, Z_PLATTE_OBEN - 0.01) * extrude(Plane.YZ * rippe_profil, amount=ARM_VORN_INNEN - ARM_HINTEN_INNEN)
fuss = platte + rippe
fuss += arm(ARM_HINTEN_INNEN, -1)
fuss += arm(ARM_VORN_INNEN, +1)

# ---------------------------------------------------------------- TPU-Sohle
sohle = Pos(0, 0, Z_BODEN) * extrude(sohlen_umriss(TPU_RAND), amount=TPU_D)
n = int((SOHLE_X[1] - SOHLE_X[0]) / RILLE_TEILUNG)
for i in range(1, n):
    x = SOHLE_X[0] + i * RILLE_TEILUNG
    sohle -= Pos(x, ACHSE_Y, Z_BODEN + RILLE_T / 2 - 0.01) * Box(RILLE_B, SOHLE_B, RILLE_T)

# ---------------------------------------------------------------- Ausgabe
ordner = Path(__file__).parent
for unter in ("step", "einbau", "stl"):
    (ordner / unter).mkdir(exist_ok=True)
for name, teil, dichte in (("fuss", fuss, 1.24), ("fuss_sohle", sohle, 1.21)):
    export_step(teil, str(ordner / "step" / f"{name}.step"))
    export_stl(teil, str(ordner / "einbau" / f"{name}.stl"), tolerance=0.02, angular_tolerance=0.1)
    if name == "fuss_sohle":                                      # Klebefläche aufs Bett, Rillen oben
        druck = Pos(0, 0, teil.bounding_box().max.Z) * Rot(180, 0, 0) * teil
    else:
        druck = Pos(0, 0, -teil.bounding_box().min.Z) * teil      # Unterseite aufs Bett
    export_stl(druck, str(ordner / "stl" / f"{name}.stl"), tolerance=0.02, angular_tolerance=0.1)
    bb = teil.bounding_box()
    print(f"{name:10} {teil.volume:7.0f} mm³ (massiv {teil.volume * dichte / 1000:4.1f} g)  "
          f"x {bb.min.X:.1f}..{bb.max.X:.1f}  y {bb.min.Y:.1f}..{bb.max.Y:.1f}  z {bb.min.Z:.2f}..{bb.max.Z:.2f}")
print(f"Spitze Mittelrippe {ACHSE_Z - Z_PLATTE_OBEN - RIPPE_H:.1f} mm unter der Rollachse (Knöchelblock bei 55° Rollen: 16,5 mm)")
