"""Zuschauen: das Laufmodell (walk.onnx) im Rhoban-Simulator mit MuJoCo-Fenster, mit altem oder neuem Kopf.

Beim neuen Kopf werden Masse, Schwerpunkt und Trägheit aus robot_v3.xml übernommen und die neuen Kopfteile
(v3/cad/einbau/kopf_*.stl, AI-Camera-Platzhalter) als Form angezeigt.

Aufruf (aus dem Repo-Ordner):
  uv run --no-project --python 3.12 --with "microban-sim @ git+https://github.com/Rhoban/microban_sim" \
      --with onnxruntime --with ahrs --with trimesh python v3/tools/lauf_ansehen.py PFAD/robot_v3.xml [alt|neu]
Das Programm läuft in Schleife: stehen → vorwärts → drehen → rückwärts → seitwärts → vorwärts mit Kopfschwenken.
Fenster schließen zum Beenden. Im Fenster: Maus drehen/zoomen, Leertaste = Pause.
"""
import math
import sys
from pathlib import Path

import mujoco
import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lauftest as lt                              # noqa: E402  (Platzhalter für den IMU-Treiber, spec_mit_kopf …)

v3_xml, welcher = Path(sys.argv[1]), (sys.argv[2] if len(sys.argv) > 2 else "neu")
EINBAU = Path(__file__).resolve().parents[1] / "cad" / "einbau"
ACHSE = np.array([-2.0, 0.0, 126.0])               # Kopfgelenk in CAD-Koordinaten (mm)
PROGRAMM = [                                       # (Sekunden, Befehl normiert, Kopf schwenken, Text)
    (3, {"vx": 0.0, "vy": 0.0, "vtheta": 0.0}, False, "stehen"),
    (6, {"vx": 0.6, "vy": 0.0, "vtheta": 0.0}, False, "vorwärts"),
    (4, {"vx": 0.0, "vy": 0.0, "vtheta": 0.6}, False, "auf der Stelle drehen"),
    (4, {"vx": -0.8, "vy": 0.0, "vtheta": 0.0}, False, "rückwärts"),
    (4, {"vx": 0.0, "vy": 0.8, "vtheta": 0.0}, False, "seitwärts"),
    (8, {"vx": 0.5, "vy": 0.0, "vtheta": 0.0}, True, "vorwärts, Kopf schwenkt ±46°"),
]


def neue_kopfform(spec):
    kopf = spec.body("head")
    for g in list(kopf.geoms):                    # alte Kopfform unsichtbar machen
        if g.classname.name == "visual":
            g.rgba = [0, 0, 0, 0]
            g.material = ""
    for datei, farbe in (("kopf_haube.stl", [0.31, 0.62, 0.84, 1]), ("kopf_basis.stl", [0.18, 0.44, 0.62, 1]),
                         ("kopf_ring.stl", [0.95, 0.69, 0.2, 1]), ("platzhalter_ai_camera.stl", [0.15, 0.15, 0.15, 1])):
        m = trimesh.load_mesh(EINBAU / datei)
        rel = m.vertices - ACHSE
        im_kopf = np.column_stack([rel[:, 1], -rel[:, 0], rel[:, 2]]) / 1000   # Kopf-KS: 90° um z gedreht
        netz = spec.add_mesh()
        netz.name = "v3_" + datei[:-4]
        netz.uservert = im_kopf.astype(np.float32).ravel().tolist()
        netz.userface = m.faces.astype(np.int32).ravel().tolist()
        g = kopf.add_geom()
        g.type = mujoco.mjtGeom.mjGEOM_MESH
        g.meshname = netz.name
        g.contype = g.conaffinity = 0
        g.group = 2
        g.mass = 0
        g.rgba = farbe


spec = lt.spec_mit_kopf(v3_xml if welcher == "neu" else None)
if welcher == "neu":
    neue_kopfform(spec)
sim = lt.MicrobanSim("classic", spec=spec, seed=1)
viewer = sim.view(realtime=True)
print(f"Kopf: {welcher}. Fenster schließen zum Beenden.")
while viewer.is_running():
    obs = sim.reset()
    move = lt.WalkMove()
    move.robot = lt.Roboter(sim)
    move.pressed, move.slider, move.options = set(), {"speed": 0.5}, {}
    sim.servos.kp = lt.KP_RL
    move.velocity = lt.scale_velocity(PROGRAMM[0][1])
    move.start(obs)
    for sekunden, befehl, schwenk, text in PROGRAMM:
        print(f"  {text}")
        move.velocity = lt.scale_velocity(befehl)
        for n in range(int(sekunden / 0.02)):
            if not viewer.is_running():
                break
            ziel = move.step(obs)
            if isinstance(ziel, dict):
                q = list(obs["q"])
                for name, w in ziel.items():
                    q[lt.JOINTS.index(name)] = w
                ziel = q
            ziel = list(ziel)
            if schwenk:
                ziel[lt.KOPF] = 0.8 * math.sin(2 * math.pi * 0.35 * n * 0.02)
            obs = sim.step(ziel)
            # Kamera folgt dem Rumpf
            p, _ = sim.trunk_pose()
            viewer.cam.lookat[:] = p
sim.close()
