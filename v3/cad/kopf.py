"""Microban v3 – Kopf mit Raspberry Pi AI Camera (Code-CAD, build123d).

Drei Teile, alle ohne Stützmaterial druckbar:
  kopf_ring   Distanzring ø18 × 3 auf dem Kopfmotor (ID 51), ersetzt die Nabe des alten Kopfes
  kopf_basis  Bodenplatte: mit 4 × M2x8 durch Platte und Ring auf den Motor geschraubt, Kabelschlitz hinten
  kopf_haube  Haube mit Kamerahalter und Sichtfenster, seitlich mit 2 × M2x6 an der Bodenplatte

Koordinaten wie in cad/microban.step (mm): x nach vorn, y nach links, z nach oben. Drehachse des Kopfes bei
x = −2, y = 0. Die Oberkante des Motors liegt bei z = 126.

Aufruf (aus dem Repo-Ordner):
  uv run --no-project --python 3.12 --with build123d python v3/cad/kopf.py
Ergebnis: v3/cad/step/*.step und v3/cad/einbau/*.stl (Einbaulage), v3/cad/stl/*.stl (Drucklage).
"""
from pathlib import Path

from build123d import (Axis, Box, Plane, Cylinder, Cone, Pos, Rot, RectangleRounded, chamfer, export_step, export_stl,
                       extrude)

# ---------------------------------------------------------------- Maße, die sich ändern lassen
ACHSE = (-2.0, 0.0)            # Drehachse Kopfmotor (aus der Baugruppe)
Z_MOTOR = 126.0                # Oberkante Motor
HORN_SCHRAUBEN = [(4.0, 0.0), (-8.0, 0.0), (-2.0, 6.0), (-2.0, -6.0)]   # Lochbild wie der alte Kopf

RING_D, RING_H = 18.0, 3.0
PLATTE_D = 2.5                 # Dicke Bodenplatte
X_HINTEN, X_VORN = -17.5, 24.0 # Außenmaß Kopf in x (alt: −17.5 … 22.5)
BREITE = 48.0                  # Außenmaß Kopf in y (alt: 50)
ECKE = 5.0                     # Eckenradius senkrecht
WAND = 2.0
Z_OBEN = 160.5                 # Oberkante Haube (alt: 159)
FASE = 3.0                     # 45°-Fase oben (druckt kopfüber ohne Stütze)

LOCH_M2 = 2.2                  # Durchgang M2
KERN_M2 = 1.8                  # Kernloch M2 selbstschneidend (STP39)
SENK_D, SENK_T = 4.2, 1.5      # Senkung Schraubenkopf in der Bodenplatte

# AI Camera (Produktdatenblatt, Lochbild wie Camera Module 3): Platine 25 × 23,862, Kabel unten
CAM_B, CAM_H = 25.0, 23.862
CAM_UNTEN = 134.0              # Unterkante Kameraplatine (Platz, damit das Kabel nach hinten umbiegen kann)
CAM_X_RUECKSEITE = 12.0        # Rückseite Kameraplatine
CAM_LOECHER_Y = 10.5           # ±, Löcher 2,0 vom Rand
CAM_LOECHER_Z = (CAM_H - 2.0, CAM_H - 14.5)   # von der Unterkante (Kabelseite)
CAM_LINSE_Z = 9.462            # Linsenmitte von der Unterkante
ABSTAND = 3.5                  # Abstandsbolzen hinter der Platine (Bauteile auf der Rückseite ca. 3,2 mm)
HALTER_D = 2.0

FENSTER_INNEN, FENSTER_AUSSEN = 8.0, 12.0     # kegeliges Sichtfenster (66° waagerecht)

KABEL_B = 19.0                 # Flachbandkabel 16 mm + Spiel
SCHLITZ_X = (-15.3, -12.3)     # hinter dem Motor (Motorrückseite x = −11,6), innerhalb der Haubenwand

SEITEN_SCHRAUBE_X, SEITEN_SCHRAUBE_Z = 2.0, 134.5

# ---------------------------------------------------------------- abgeleitete Werte
Z_RING_OBEN = Z_MOTOR + RING_H
Z_PLATTE_OBEN = Z_RING_OBEN + PLATTE_D
X_MITTE, LAENGE = (X_HINTEN + X_VORN) / 2, X_VORN - X_HINTEN
CAM_X_VORN = CAM_X_RUECKSEITE + 1.0
X_HALTER = CAM_X_RUECKSEITE - ABSTAND           # Vorderseite Halter
LINSE_Z = CAM_UNTEN + CAM_LINSE_Z


def quader(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def zylinder_z(x, y, z0, z1, d):
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(d / 2, z1 - z0)


def zylinder_x(x0, x1, y, z, d):
    return Pos((x0 + x1) / 2, y, z) * Rot(0, 90, 0) * Cylinder(d / 2, x1 - x0)


def zylinder_y(y0, y1, x, z, d):
    return Pos(x, (y0 + y1) / 2, z) * Rot(90, 0, 0) * Cylinder(d / 2, abs(y1 - y0))


def umriss(z0, z1, rand=0.0):
    """Kopfumriss (abgerundetes Rechteck) als Körper, nach innen versetzt um 'rand'."""
    flaeche = RectangleRounded(LAENGE - 2 * rand, BREITE - 2 * rand, max(ECKE - rand, 0.5))
    return Pos(X_MITTE, 0, z0) * extrude(flaeche, amount=z1 - z0)


# ---------------------------------------------------------------- Distanzring
ring = zylinder_z(*ACHSE, Z_MOTOR, Z_RING_OBEN, RING_D)
for x, y in HORN_SCHRAUBEN:
    ring -= zylinder_z(x, y, Z_MOTOR - 1, Z_RING_OBEN + 1, LOCH_M2)

# ---------------------------------------------------------------- Bodenplatte
basis = umriss(Z_RING_OBEN, Z_PLATTE_OBEN)
for x, y in HORN_SCHRAUBEN:
    basis -= zylinder_z(x, y, Z_RING_OBEN - 1, Z_PLATTE_OBEN + 1, LOCH_M2)
    basis -= zylinder_z(x, y, Z_PLATTE_OBEN - SENK_T, Z_PLATTE_OBEN + 1, SENK_D)
basis -= quader(*SCHLITZ_X, -KABEL_B / 2, KABEL_B / 2, Z_RING_OBEN - 1, Z_PLATTE_OBEN + 1)
y_innen = BREITE / 2 - WAND - 0.2
for s in (1, -1):   # Laschen für die Seitenschrauben
    lasche = quader(SEITEN_SCHRAUBE_X - 3, SEITEN_SCHRAUBE_X + 3, y_innen - 5.5, y_innen,
                    Z_PLATTE_OBEN, SEITEN_SCHRAUBE_Z + 3)
    lasche -= zylinder_y(y_innen - 6, y_innen + 1, SEITEN_SCHRAUBE_X, SEITEN_SCHRAUBE_Z, KERN_M2)
    basis += lasche if s == 1 else lasche.mirror(Plane.XZ)   # an der XZ-Ebene spiegeln: y -> -y

# ---------------------------------------------------------------- Haube
aussen = umriss(Z_PLATTE_OBEN, Z_OBEN)
aussen = chamfer(aussen.edges().group_by(Axis.Z)[-1], FASE)
innen = umriss(Z_PLATTE_OBEN - 1, Z_OBEN - WAND, rand=WAND)
haube = aussen - innen
# Kamerahalter hängt am Dach (beim Druck kopfüber steht er senkrecht)
z_halter_unten = CAM_UNTEN + 4.0                 # darunter läuft das Kabel nach hinten
haube += quader(X_HALTER - HALTER_D, X_HALTER, -CAM_B / 2 - 0.5, CAM_B / 2 + 0.5, z_halter_unten, Z_OBEN - WAND + 0.1)
for y in (CAM_LOECHER_Y, -CAM_LOECHER_Y):
    for dz in CAM_LOECHER_Z:
        z = CAM_UNTEN + dz
        haube += zylinder_x(X_HALTER - 0.1, CAM_X_RUECKSEITE, y, z, 5.0)
        haube -= zylinder_x(X_HALTER - HALTER_D - 1, CAM_X_RUECKSEITE + 1, y, z, KERN_M2)
# Sichtfenster, kegelig nach außen
fenster = Pos(X_VORN - WAND / 2, 0, LINSE_Z) * Rot(0, 90, 0) * Cone(FENSTER_INNEN / 2, FENSTER_AUSSEN / 2, WAND + 0.02)
haube -= fenster
haube -= zylinder_x(X_VORN - WAND - 1.0, X_VORN - WAND + 0.01, 0, LINSE_Z, FENSTER_INNEN)
# Löcher für die Seitenschrauben
for s in (1, -1):
    haube -= zylinder_y(s * (BREITE / 2 - WAND - 1), s * (BREITE / 2 + 1), SEITEN_SCHRAUBE_X, SEITEN_SCHRAUBE_Z, LOCH_M2)

# ---------------------------------------------------------------- Platzhalter Kamera (nur zum Prüfen)
kamera = quader(CAM_X_RUECKSEITE - 3.2, CAM_X_VORN, -CAM_B / 2, CAM_B / 2, CAM_UNTEN, CAM_UNTEN + CAM_H)
kamera += zylinder_x(CAM_X_VORN, CAM_X_VORN + 6.6, 0, LINSE_Z, 12.8)     # Objektivblock, vereinfacht rund

# ---------------------------------------------------------------- Ausgabe
ordner = Path(__file__).parent
for unter in ("step", "einbau", "stl"):
    (ordner / unter).mkdir(exist_ok=True)

teile = {"kopf_ring": ring, "kopf_basis": basis, "kopf_haube": haube}
drucklage = {
    "kopf_ring": Pos(0, 0, -Z_MOTOR) * ring,
    "kopf_basis": Pos(0, 0, -Z_RING_OBEN) * basis,
    "kopf_haube": Pos(0, 0, Z_OBEN) * Rot(180, 0, 0) * haube,      # kopfüber, Dach auf dem Druckbett
}
for name, teil in teile.items():
    export_step(teil, str(ordner / "step" / f"{name}.step"))
    export_stl(teil, str(ordner / "einbau" / f"{name}.stl"), tolerance=0.02, angular_tolerance=0.1)
    export_stl(drucklage[name], str(ordner / "stl" / f"{name}.stl"), tolerance=0.02, angular_tolerance=0.1)
    bb = teil.bounding_box()
    print(f"{name:11} Volumen {teil.volume:7.0f} mm³ ≈ {teil.volume * 1.24e-3:4.1f} g PLA (massiv)   "
          f"x {bb.min.X:6.1f}..{bb.max.X:6.1f}  y {bb.min.Y:6.1f}..{bb.max.Y:6.1f}  z {bb.min.Z:6.1f}..{bb.max.Z:6.1f}")
export_stl(kamera, str(ordner / "einbau" / "platzhalter_ai_camera.stl"))
export_step(kamera, str(ordner / "step" / "platzhalter_ai_camera.step"))
print(f"Linsenmitte: x {CAM_X_VORN + 6.6:.1f}, z {LINSE_Z:.2f}; Abstand Objektiv–Fenster innen: "
      f"{X_VORN - WAND - (CAM_X_VORN + 6.6):.1f} mm")
