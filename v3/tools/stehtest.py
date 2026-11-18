"""Stehtest im MuJoCo-Modell: alter gegen neuen Kopf.

Der Roboter steht auf dem Boden, alle Gelenke werden mit einer PD-Regelung in der Standhaltung des Laufmodells
gehalten (Drehmoment begrenzt wie beim XL330). Gemessen werden:
  1. Reserve: Abstand des Schwerpunkts (senkrecht auf den Boden projiziert) zur Kante der Stützfläche beider Füße.
  2. Schubtest: Wie stark darf man den Rumpf 0,1 s lang nach vorn / hinten / zur Seite schieben, bis er umfällt?

Aufruf: uv run --no-project --python 3.12 --with mujoco --with scipy --with shapely python v3/tools/stehtest.py \
            robot.xml robot_v3.xml
"""
import sys

import mujoco
import numpy as np
from scipy.spatial import ConvexHull
from shapely.geometry import Point, Polygon

STAND = {"right_shoulder_roll": -0.175, "right_elbow": -0.349, "right_hip_roll": -0.087, "right_hip_pitch": -0.175,
         "right_ankle_roll": 0.087, "left_shoulder_roll": 0.175, "left_elbow": -0.349, "left_hip_roll": 0.087,
         "left_hip_pitch": -0.175, "left_ankle_roll": -0.087,
         "left_shoulder_pitch": np.pi / 2, "right_shoulder_pitch": np.pi / 2}
KP, KD, TAU_MAX = 2.0, 0.03, 0.52        # Nm/rad, Nm·s/rad, Nm (XL330-M288 Haltemoment ≈ 0,52 Nm bei 5 V)
SOHLEN = ("left_foot_collision_1", "right_foot_collision_1")


def lade(pfad):
    spec = mujoco.MjSpec.from_file(pfad)
    boden = spec.worldbody.add_geom()
    boden.type = mujoco.mjtGeom.mjGEOM_PLANE
    boden.size = [1, 1, 0.1]
    boden.friction = [0.8, 0.005, 0.0001]
    m = spec.compile()
    m.opt.timestep = 0.001
    return m


def start(m):
    d = mujoco.MjData(m)
    gelenke = {}
    for j in range(m.njnt):
        if m.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE:
            n = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j)
            gelenke[n] = (m.jnt_qposadr[j], m.jnt_dofadr[j], STAND.get(n, 0.0))
            d.qpos[m.jnt_qposadr[j]] = STAND.get(n, 0.0)
    mujoco.mj_forward(m, d)
    # Rumpf so anheben, dass die tiefste Sohlenecke knapp über dem Boden ist
    tief = min(ecken(m, d, s)[:, 2].min() for s in SOHLEN)
    d.qpos[2] -= tief - 0.0005
    mujoco.mj_forward(m, d)
    return d, gelenke


def ecken(m, d, name):
    g = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, name)
    s, R, p = m.geom_size[g], d.geom_xmat[g].reshape(3, 3), d.geom_xpos[g]
    return np.array([p + R @ (np.array([a, b, c]) * s) for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)])


def regeln(m, d, gelenke):
    d.qfrc_applied[:] = 0
    for qa, da, soll in gelenke.values():
        tau = KP * (soll - d.qpos[qa]) - KD * d.qvel[da]
        d.qfrc_applied[da] = np.clip(tau, -TAU_MAX, TAU_MAX)


def reserve(m, d):
    pkte = np.vstack([ecken(m, d, s)[:, :2] for s in SOHLEN])
    huelle = Polygon(pkte[ConvexHull(pkte).vertices])
    com = d.subtree_com[1][:2]
    p = Point(com)
    return (1 if huelle.contains(p) else -1) * huelle.exterior.distance(p), com, huelle


def umgefallen(d):
    return d.xmat[1].reshape(3, 3)[2, 2] < 0.7     # Rumpf mehr als ca. 45° geneigt


def steht_nach_schub(pfad, richtung, kraft):
    m = lade(pfad)
    d, gel = start(m)
    rumpf = 1
    for i in range(4000):                           # 1 s ruhig stehen, 0,1 s schieben, 2,9 s abwarten
        regeln(m, d, gel)
        if 1000 <= i < 1100:
            d.xfrc_applied[rumpf, :3] = np.array(richtung) * kraft
        else:
            d.xfrc_applied[rumpf, :3] = 0
        mujoco.mj_step(m, d)
        if umgefallen(d):
            return False
    return True


def max_schub(pfad, richtung):
    lo, hi = 0.0, 5.0                               # N
    for _ in range(12):
        mitte = (lo + hi) / 2
        if steht_nach_schub(pfad, richtung, mitte):
            lo = mitte
        else:
            hi = mitte
    return lo


for titel, pfad in (("alter Kopf", sys.argv[1]), ("neuer Kopf (v3)", sys.argv[2])):
    m = lade(pfad)
    d, gel = start(m)
    for _ in range(2000):
        regeln(m, d, gel)
        mujoco.mj_step(m, d)
    r, com, huelle = reserve(m, d)
    minx, miny, maxx, maxy = huelle.bounds
    print(f"\n{titel}: Masse {m.body_subtreemass[1] * 1000:.1f} g, steht: {'ja' if not umgefallen(d) else 'NEIN'}")
    print(f"  Schwerpunkt-Höhe {d.subtree_com[1][2] * 1000:.1f} mm, Stützfläche x {minx * 1000:.0f}…{maxx * 1000:.0f}, "
          f"Schwerpunkt x {com[0] * 1000:.1f}, y {com[1] * 1000:.1f} mm")
    print(f"  Reserve bis zur Kante: vorn {(maxx - com[0]) * 1000:.1f} mm, hinten {(com[0] - minx) * 1000:.1f} mm, "
          f"seitlich {min(maxy - com[1], com[1] - miny) * 1000:.1f} mm")
    for name, ri in (("nach vorn", (1, 0, 0)), ("nach hinten", (-1, 0, 0)), ("zur Seite", (0, 1, 0))):
        print(f"  Schubtest {name:11}: hält bis {max_schub(pfad, ri):.2f} N (0,1 s)")
