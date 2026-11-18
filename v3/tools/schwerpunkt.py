"""Masse und Schwerpunkt des neuen Kopfes und ihre Wirkung auf den ganzen Roboter (MuJoCo-Modell von Rhoban).

Aufruf (aus dem Repo-Ordner):
  uv run --no-project --python 3.12 --with build123d --with mujoco --with trimesh python v3/tools/schwerpunkt.py \
      PFAD/zu/microban_model/src/microban_model/mjcf/robot.xml PFAD/zu/head_1_head.stl [modell_v3.xml]
head_1_head.stl: der alte Kopf in Einbaulage (export_teile.py "head <1> / head").
Mit dem dritten Argument wird eine Kopie des Modells mit dem neuen Kopf geschrieben (für den Simulator).

Koordinaten der CAD-Teile: x nach vorn, y nach links, z nach oben (mm), Kopf-Drehachse bei x = −2, y = 0.
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np
import trimesh
from build123d import import_step

modell, alter_kopf_stl = Path(sys.argv[1]), Path(sys.argv[2])
v3_xml = Path(sys.argv[3]) if len(sys.argv) > 3 else None
CAD = Path(__file__).resolve().parents[1] / "cad"
ACHSE = np.array([-2.0, 0.0, 126.0])                # Kopfgelenk in CAD-Koordinaten (mm)

# ---------------------------------------------------------------- Massen (g)
# Druckteile: Schätzung aus stl_analyse.py (2 Wände, 15 % Füllung). Beim alten Kopf ergibt die Schätzung 15,1 g,
# das Modell sagt 17,0 g (mit Schrauben) → derselbe Faktor für die neuen Teile.
GESCHAETZT_ALT = 15.1
druck = {"kopf_ring": 0.8, "kopf_basis": 5.5, "kopf_haube": 16.0}
KAMERA_G = 10.0          # Raspberry Pi AI Camera (Händlerangabe, Farnell: 0,01 kg)
SCHRAUBEN_G = 6 * 0.15   # 4 × Kamera + 2 × Haube (M2x6)
KABEL_IM_KOPF_G = 0.5

# Standhaltung des Laufmodells (walk.onnx, v1-Schulter + pi/2 wie src/moves/walk.py)
STAND = {"right_shoulder_roll": -0.175, "right_elbow": -0.349, "right_hip_roll": -0.087, "right_hip_pitch": -0.175,
         "right_ankle_roll": 0.087, "left_shoulder_roll": 0.175, "left_elbow": -0.349, "left_hip_roll": 0.087,
         "left_hip_pitch": -0.175, "left_ankle_roll": -0.087,
         "left_shoulder_pitch": np.pi / 2, "right_shoulder_pitch": np.pi / 2}


def schwerpunkt_teil(name):
    teil = import_step(str(CAD / "step" / f"{name}.step"))
    c = teil.center()
    return np.array([c.X, c.Y, c.Z])


# ---------------------------------------------------------------- alter Kopf: Lage aus dem STL, Masse aus dem Modell
m = trimesh.load_mesh(alter_kopf_stl)
alt_cad = m.center_mass                              # Kopfteil allein (gleichmäßige Dichte angenommen)

spec = mujoco.MjSpec.from_file(str(modell))
mj = spec.compile()
kopf_id = mujoco.mj_name2id(mj, mujoco.mjtObj.mjOBJ_BODY, "head")
alt_masse = mj.body_mass[kopf_id] * 1000
alt_ipos = mj.body_ipos[kopf_id] * 1000              # Schwerpunkt im Kopf-Koordinatensystem (mm)
# Kopf-KS ist um 90° um z gedreht: Kopf (x, y) = CAD (y, −x) relativ zur Achse → Probe mit dem alten Kopf
alt_rel = alt_cad - ACHSE
alt_im_kopf_ks = np.array([alt_rel[1], -alt_rel[0], alt_rel[2]])

# ---------------------------------------------------------------- neuer Kopf
faktor = mj.body_mass[kopf_id] * 1000 / GESCHAETZT_ALT
teile = [(n, g * faktor, schwerpunkt_teil(n)) for n, g in druck.items()]
cam_bb = import_step(str(CAD / "step" / "platzhalter_ai_camera.step")).bounding_box()
cam_mitte = np.array([(cam_bb.min.X + cam_bb.max.X) / 2, 0.0, (cam_bb.min.Z + cam_bb.max.Z) / 2])
teile += [("AI Camera", KAMERA_G, cam_mitte), ("Schrauben", SCHRAUBEN_G, cam_mitte),
          ("Kabel im Kopf", KABEL_IM_KOPF_G, np.array([0.0, 0.0, 133.0]))]
neu_masse = sum(g for _, g, _ in teile)
neu_cad = sum(g * p for _, g, p in teile) / neu_masse
neu_rel = neu_cad - ACHSE
neu_im_kopf_ks = np.array([neu_rel[1], -neu_rel[0], neu_rel[2]])

print("Kopf                     Masse     Schwerpunkt relativ zur Kopfachse (CAD: x vorn, z hoch, mm)")
print(f"  alt (Modell)          {alt_masse:5.1f} g   Modell: Kopf-KS {np.round(alt_ipos, 1)}")
print(f"  alt (aus CAD-Form)            x {alt_rel[0]:+5.1f}  y {alt_rel[1]:+5.1f}  z {alt_rel[2]:+5.1f}   "
      f"(im Kopf-KS {np.round(alt_im_kopf_ks, 1)} – passt zum Modell?)")
for n, g, p in teile:
    r = p - ACHSE
    print(f"    {n:20} {g:5.1f} g   x {r[0]:+5.1f}  y {r[1]:+5.1f}  z {r[2]:+5.1f}")
print(f"  neu gesamt            {neu_masse:5.1f} g   x {neu_rel[0]:+5.1f}  y {neu_rel[1]:+5.1f}  z {neu_rel[2]:+5.1f}")

# ---------------------------------------------------------------- ganzer Roboter in der Standhaltung


def roboter(spec_):
    mj_ = spec_.compile()
    d = mujoco.MjData(mj_)
    for n, w in STAND.items():
        d.qpos[mj_.jnt_qposadr[mujoco.mj_name2id(mj_, mujoco.mjtObj.mjOBJ_JOINT, n)]] = w
    mujoco.mj_forward(mj_, d)
    masse = mj_.body_subtreemass[1]
    com = d.subtree_com[1].copy()
    fuesse = [d.geom_xpos[mujoco.mj_name2id(mj_, mujoco.mjtObj.mjOBJ_GEOM, g)].copy()   # Sohlenmitte
              for g in ("left_foot_collision_1", "right_foot_collision_1")]
    mitte = (fuesse[0] + fuesse[1]) / 2
    return masse, com, mitte, mj_, d


m0, com0, mitte0, mj0, d0 = roboter(spec)
spec_v3 = mujoco.MjSpec.from_file(str(modell))
kopf = spec_v3.body("head")
# Trägheit grob: alte Trägheit mit dem Massenverhältnis skaliert, dazu Steiner-Anteil der Kamera vorn
skala = neu_masse / alt_masse
kopf.mass = neu_masse / 1000
kopf.ipos = neu_im_kopf_ks / 1000
kopf.fullinertia = [np.nan] * 6
kopf.inertia = np.array(mj.body_inertia[kopf_id]) * skala
kopf.iquat = mj.body_iquat[kopf_id]
m1, com1, mitte1, mj1, d1 = roboter(spec_v3)

print("\nGanzer Roboter (Standhaltung des Laufmodells, Füße auf dem Boden)")
print(f"  Masse: {m0 * 1000:6.1f} g → {m1 * 1000:6.1f} g  ({(m1 - m0) * 1000:+.1f} g, {(m1 / m0 - 1) * 100:+.1f} %)")
for t, c0, c1 in (("x (vorn)", com0[0], com1[0]), ("y (links)", com0[1], com1[1]), ("z (Höhe)", com0[2], com1[2])):
    print(f"  Schwerpunkt {t:9}: {(c0 - mitte0[0 if t[0] == 'x' else 1 if t[0] == 'y' else 2]) * 1000:+6.2f} mm → "
          f"{(c1 - mitte1[0 if t[0] == 'x' else 1 if t[0] == 'y' else 2]) * 1000:+6.2f} mm   (relativ zur Mitte zwischen den Füßen)")
kz0 = mj0.body_inertia[kopf_id]
cam_r = np.linalg.norm((cam_mitte - ACHSE)[:2])          # mm
print(f"  Kopf-Trägheit um die Drehachse: Teile ×{skala:.2f}, dazu Kamera {KAMERA_G * cam_r ** 2 / 100:.0f} g·cm² "
      f"(Abstand {cam_r:.0f} mm; alter Kopf gesamt ≈ {kz0.max() * 1e7:.0f} g·cm²)")

if v3_xml:
    v3_xml.write_text(spec_v3.to_xml(), encoding="utf-8")
    print(f"\nModell mit neuem Kopf geschrieben: {v3_xml}")

# ---------------------------------------------------------------- Stützfläche und Kipp-Reserve
sohle = mj0.geom_size[mujoco.mj_name2id(mj0, mujoco.mjtObj.mjOBJ_GEOM, "left_foot_collision_1")] * 1000
print(f"\nSohlenplatte (Modell): {2 * sohle[0]:.0f} × {2 * sohle[1]:.0f} mm (halbe Länge {sohle.max():.0f} mm)")
print(f"Fußabstand (Mitte–Mitte, y): {abs(mitte0[1] - d0.geom_xpos[mujoco.mj_name2id(mj0, mujoco.mjtObj.mjOBJ_GEOM, 'left_foot_collision_1')][1]) * 2000:.0f} mm")
# statisch: wie weit darf sich der Oberkörper neigen, bis der Schwerpunkt über die Sohlenkante (vorn/hinten) wandert?
for t, h, dx in (("alt", com0[2] - mitte0[2], com0[0] - mitte0[0]), ("neu", com1[2] - mitte1[2], com1[0] - mitte1[0])):
    vor = np.degrees(np.arctan2(sohle.max() - dx, h))
    print(f"  {t}: Schwerpunkt {h * 1000:.1f} mm über der Sohle, Kippwinkel nach vorn ≈ {vor:.1f}° (statisch)")
