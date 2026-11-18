"""Wie empfindlich ist das Laufmodell (walk.onnx) auf die Fußsohle? Lauftest mit veränderten Sohlen im Simulator.

Die Kontaktflächen der Füße (Kollisionsquader *_foot_collision_*) werden in Länge und Breite skaliert und ggf. vorn
oder hinten gekürzt. Masse und Gelenke bleiben gleich.

Aufruf (aus dem Repo-Ordner):
  uv run --no-project --python 3.12 --with "microban-sim @ git+https://github.com/Rhoban/microban_sim" \
      --with onnxruntime --with ahrs python v3/tools/fuss_test.py
"""
import sys
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lauftest as lt                              # noqa: E402

FUSS_GEOMS = [f"{s}_foot_collision_{i}" for s in ("left", "right") for i in range(1, 7)]
MITTE_FUSS = np.array([0.0, -0.02175, 0.042])     # Sohlenmitte im Fuß-KS (Länge entlang z, Breite entlang x)

# (Name, Faktor Länge, Faktor Breite, Verschiebung der Sohlenmitte entlang der Länge in mm (+ = Richtung z))
VARIANTEN = [
    ("Original 80 × 45", 1.0, 1.0, 0.0),
    ("Länge 72 (−10 %)", 0.9, 1.0, 0.0),
    ("Länge 64 (−20 %)", 0.8, 1.0, 0.0),
    ("Breite 40 (−10 %)", 1.0, 0.9, 0.0),
    ("Breite 36 (−20 %)", 1.0, 0.8, 0.0),
    ("70 × 40", 0.875, 0.89, 0.0),
    ("70 × 40, Ende +z gekürzt", 0.875, 0.89, -5.0),
    ("70 × 40, Ende −z gekürzt", 0.875, 0.89, +5.0),
    ("64 × 36", 0.8, 0.8, 0.0),
]
FAELLE = [f for f in lt.FAELLE if f[0] in ("stehen", "vorwärts voll", "rückwärts", "seitwärts", "drehen")]


def sohle_aendern(spec, laenge, breite, versatz_mm):
    for name in FUSS_GEOMS:
        g = spec.geom(name)
        rel = np.array(g.pos) - MITTE_FUSS
        neu = MITTE_FUSS + rel * np.array([breite, 1.0, laenge]) + np.array([0.0, 0.0, versatz_mm / 1000])
        g.pos = neu
        # Größe: lokale Achsen des Quaders auf die Fuß-Achsen abbilden
        R = np.zeros(9)
        mujoco.mju_quat2Mat(R, np.array(g.quat, float))
        R = R.reshape(3, 3)
        faktor = np.array([breite, 1.0, laenge])
        g.size = [g.size[i] * float(np.abs(R[:, i]) @ faktor / np.abs(R[:, i]).sum()) for i in range(3)]
    return spec


def ende_vorn(spec):
    """Welches Ende der Sohle (+z oder −z im Fuß-KS) zeigt in Laufrichtung (Welt +x)?"""
    m = spec.compile()
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    a = d.geom_xpos[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "left_foot_collision_5")][0]   # z = 0,082
    b = d.geom_xpos[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "left_foot_collision_3")][0]   # z = 0,002
    return "+z" if a > b else "−z"




def sohle_v3(spec):
    """Kontaktflächen des neuen Fußes (v3/cad/fuss.py): 80 × 40 mm, Ferse wie das Original, Fasen vorn 8 / hinten 4.
    Fuß-KS: Länge entlang z mit z_mm = x_CAD + 23 (Ferse x −26 → z −3), Breite entlang x, Sohlenebene y = −0,02175."""
    y = MITTE_FUSS[1]
    for s in ("left", "right"):
        a, b = spec.geom(f"{s}_foot_collision_1"), spec.geom(f"{s}_foot_collision_2")
        a.pos, a.size = [0.0, y, 0.0365], [0.020, 0.0345, 0.00125]     # voll breit, ohne Fasen-Ecken (x −22 … 46)
        b.pos, b.size = [0.0, y, 0.037], [0.014, 0.040, 0.00125]       # voll lang (x −26 … 54), schmaler
        for i, (dx, dz) in zip(range(3, 7), ((-0.0165, -0.0015), (0.0165, -0.0015), (-0.0135, 0.0755), (0.0135, 0.0755))):
            spec.geom(f"{s}_foot_collision_{i}").pos = [dx, y, dz]
    return spec


basis = lt.spec_mit_kopf
if "--v3" in sys.argv:                            # nur Original gegen neuen Fuß, alle Fälle aus lauftest.py
    print(f"{'Sohle':16} {'Fall':22} {'gefallen':8} {'Strecke m':>9} {'Neigung max °':>13} {'Strom Fuß A':>11}")
    for name, umbau in (("Original", lambda q: basis(q)), ("v3 80 × 40", lambda q: sohle_v3(basis(q)))):
        lt.spec_mit_kopf = umbau
        for fall, befehl, schwenk in lt.FAELLE:
            r = [lt.lauf(None, befehl, schwenk, s) for s in lt.SEEDS]
            fallz = sum(x["gefallen"] is not None for x in r)
            print(f"{name:16} {fall:22} {f'{fallz}/{len(r)}':8} {np.mean([np.hypot(x['vor'], x['seit']) for x in r]):9.2f} "
                  f"{np.mean([x['neig_max'] for x in r]):13.1f} {np.mean([x['strom_fuss'] for x in r]):11.3f}")
        print()
    sys.exit()
print(f"Ende +z der Sohle zeigt {'nach vorn (Zehen)' if ende_vorn(basis(None)) == '+z' else 'nach hinten (Ferse)'}\n")
print(f"{'Sohle':28} {'Fall':14} {'gefallen':8} {'Strecke m':>9} {'Neigung max °':>13}")
for name, laenge, breite, versatz in VARIANTEN:
    lt.spec_mit_kopf = lambda q, l=laenge, b=breite, v=versatz: sohle_aendern(basis(q), l, b, v)
    for fall, befehl, schwenk in FAELLE:
        r = [lt.lauf(None, befehl, schwenk, s) for s in lt.SEEDS]
        fallz = sum(x["gefallen"] is not None for x in r)
        strecke = np.mean([np.hypot(x["vor"], x["seit"]) for x in r])
        print(f"{name:28} {fall:14} {f'{fallz}/{len(r)}':8} {strecke:9.2f} {np.mean([x['neig_max'] for x in r]):13.1f}")
    print()
