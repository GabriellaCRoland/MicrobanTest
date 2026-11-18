"""Wertet alle STL-Teile aus: Maße, Volumen, geschätztes Gewicht, Stützmaterial je Ausrichtung."""
import sys
from pathlib import Path

import numpy as np
import trimesh

STL_DIR = Path(sys.argv[1])
ANZAHL = {  # Stückzahl laut docs/printing.md
    "foot": 2, "tibia_left": 1, "tibia_right": 1, "femur_left": 1, "femur_right": 1, "hip": 2,
    "ankle_dbl_block": 2, "hip_dbl_block_left": 1, "hip_dbl_block_right": 1, "spacer": 4, "pelvis": 1,
    "chest": 1, "trunk_top": 1, "head": 1, "arm_bearing_support": 2, "shoulder": 2, "humerus": 2,
    "radius": 2, "idle_horn": 4, "idle_cap": 6, "board_spacer": 4,
}
PLA = 1.24e-3        # g/mm³
WAND = 0.9           # mm Außenwand (2 Perimeter à 0.45)
FUELLUNG = 0.15
MINI = 180.0         # Prusa Mini Druckraum (kleinster Prusa)
WINKEL = np.cos(np.radians(45))

RICHTUNGEN = {"+Z unten": [0, 0, -1], "-Z unten": [0, 0, 1], "+X unten": [-1, 0, 0],
              "-X unten": [1, 0, 0], "+Y unten": [0, -1, 0], "-Y unten": [0, 1, 0]}


def stuetz_flaeche(mesh, unten):
    """Fläche (mm²), die mehr als 45° überhängt, wenn 'unten' Richtung Druckbett zeigt."""
    unten = np.array(unten, float)
    hoehe = -(mesh.triangles_center @ unten)            # Höhe über dem Bett (bis auf Verschiebung)
    hoehe -= hoehe.min()
    nach_unten = mesh.face_normals @ unten               # 1 = Fläche zeigt genau zum Bett
    ueberhang = (nach_unten > WINKEL) & (hoehe > 0.3)    # nicht die Auflagefläche selbst
    return float(mesh.area_faces[ueberhang].sum())


zeilen = []
gesamt_g = 0.0
for datei in sorted(STL_DIR.glob("*.stl")):
    m = trimesh.load_mesh(datei)
    name = datei.stem
    n = ANZAHL.get(name, 1)
    groesse = np.sort(m.extents)[::-1]
    vol = abs(m.volume) if m.is_volume else float("nan")
    kern = max(vol - m.area * WAND, 0) if m.is_volume else float("nan")
    gramm = (vol - kern + kern * FUELLUNG) * PLA if m.is_volume else float("nan")
    stuetz = {k: stuetz_flaeche(m, v) for k, v in RICHTUNGEN.items()}
    beste = min(stuetz, key=stuetz.get)
    passt = "ja" if groesse[0] <= MINI else "NEIN"
    gesamt_g += gramm * n
    zeilen.append((name, n, groesse, gramm, beste, stuetz[beste], m.is_watertight, passt))

print(f"{'Teil':22} {'Stk':>3} {'Maße mm (L×B×H)':>20} {'g/Stk':>6} {'Stütze mm²':>10} {'beste Lage':>9} dicht Mini")
for name, n, g, gramm, beste, flaeche, dicht, passt in sorted(zeilen, key=lambda z: -z[5]):
    print(f"{name:22} {n:>3} {g[0]:6.1f}×{g[1]:5.1f}×{g[2]:5.1f} {gramm:6.1f} {flaeche:10.0f} {beste:>9} {str(dicht):5} {passt}")
print(f"\nGesamt (alle Stückzahlen): ca. {gesamt_g:.0f} g PLA (ohne Stützmaterial)")
