"""Lauftest im Rhoban-Simulator (microban_sim, Servos mit BAM): das echte Laufmodell (src/moves/walk.py, walk.onnx)
mit dem alten und dem neuen Kopf, ohne Fenster.

Aufruf (aus dem Repo-Ordner):
  uv run --no-project --python 3.12 --with "microban-sim @ git+https://github.com/Rhoban/microban_sim" \
      --with onnxruntime --with ahrs python v3/tools/lauftest.py PFAD/robot_v3.xml
robot_v3.xml: von schwerpunkt.py geschrieben; daraus werden nur Masse, Schwerpunkt und Trägheit des Kopfes übernommen.
"""
import math
import sys
from pathlib import Path

import mujoco
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
# Der IMU-Chip-Treiber des echten Roboters (I2C) wird im Simulator nicht gebraucht: leerer Platzhalter
import types  # noqa: E402

_bmi = types.ModuleType("bmi088")
_bmi.BMI088 = object
_bmi.bmi088 = types.ModuleType("bmi088.bmi088")
sys.modules.setdefault("bmi088", _bmi)
sys.modules.setdefault("bmi088.bmi088", _bmi.bmi088)
from constants import KP_RL                      # noqa: E402
from input.input_source import scale_velocity    # noqa: E402
from microban_sim import JOINTS, MicrobanSim     # noqa: E402
from microban_sim.scene import build_spec        # noqa: E402
from moves.walk import WalkMove                  # noqa: E402

SEKUNDEN = 12.0
SEEDS = (1, 2, 3)
# (Name, Befehl normiert −1…1, Kopf schwenken?)
FAELLE = [
    ("stehen", {"vx": 0.0, "vy": 0.0, "vtheta": 0.0}, False),
    ("vorwärts halb", {"vx": 0.5, "vy": 0.0, "vtheta": 0.0}, False),
    ("vorwärts voll", {"vx": 1.0, "vy": 0.0, "vtheta": 0.0}, False),
    ("rückwärts", {"vx": -1.0, "vy": 0.0, "vtheta": 0.0}, False),
    ("seitwärts", {"vx": 0.0, "vy": 1.0, "vtheta": 0.0}, False),
    ("drehen", {"vx": 0.0, "vy": 0.0, "vtheta": 0.5}, False),
    ("vorwärts + Kopf ±46°", {"vx": 0.5, "vy": 0.0, "vtheta": 0.0}, True),
]
KOPF = JOINTS.index("head")
FUSS = [JOINTS.index(n) for n in ("left_ankle_pitch", "right_ankle_pitch", "left_ankle_roll", "right_ankle_roll")]
KNIE = [JOINTS.index(n) for n in ("left_knee", "right_knee")]


class Roboter:                                   # was ein Move über self.robot erreicht
    variant = "classic"

    def __init__(self, sim):
        self.sim = sim

    def set_torque(self, on, joints=None):
        self.sim.set_torque(on)

    def set_kp(self, kp):
        self.sim.servos.kp = kp


def spec_mit_kopf(quelle):
    spec = build_spec("classic")
    if quelle is not None:
        k_neu = mujoco.MjSpec.from_file(str(quelle)).compile()
        i = mujoco.mj_name2id(k_neu, mujoco.mjtObj.mjOBJ_BODY, "head")
        kopf = spec.body("head")
        kopf.mass = float(k_neu.body_mass[i])
        kopf.ipos = k_neu.body_ipos[i].copy()
        kopf.iquat = k_neu.body_iquat[i].copy()
        kopf.inertia = k_neu.body_inertia[i].copy()
        kopf.fullinertia = [np.nan] * 6
    return spec


def lauf(spec_quelle, befehl, kopf_schwenk, seed):
    sim = MicrobanSim("classic", spec=spec_mit_kopf(spec_quelle), seed=seed)
    obs = sim.reset()
    move = WalkMove()
    move.robot = Roboter(sim)
    move.pressed, move.slider, move.options = set(), {"speed": 0.5}, {}
    move.velocity = scale_velocity(befehl)
    sim.servos.kp = KP_RL
    move.start(obs)
    p0, q0 = sim.trunk_pose()
    yaw0 = math.atan2(2 * (q0[0] * q0[3] + q0[1] * q0[2]), 1 - 2 * (q0[2] ** 2 + q0[3] ** 2))
    neigung, strom_fuss, strom_knie = [], [], []
    gefallen = None
    schritte = int(SEKUNDEN / 0.02)
    for n in range(schritte):
        ziel = move.step(obs)
        if isinstance(ziel, dict):
            q = list(obs["q"])
            for name, w in ziel.items():
                q[JOINTS.index(name)] = w
            ziel = q
        ziel = list(ziel)
        if kopf_schwenk:
            ziel[KOPF] = 0.8 * math.sin(2 * math.pi * 0.35 * n * 0.02)
        obs = sim.step(ziel)
        g = np.asarray(obs["gravity"])
        kipp = math.degrees(math.acos(max(-1.0, min(1.0, -g[2] / np.linalg.norm(g)))))
        neigung.append(kipp)
        strom = np.abs(np.asarray(obs["current"]))
        strom_fuss.append(strom[FUSS].mean())
        strom_knie.append(strom[KNIE].mean())
        if kipp > 45 and gefallen is None:
            gefallen = n * 0.02
            break
    p1, _ = sim.trunk_pose()
    d = np.asarray(p1[:2]) - np.asarray(p0[:2])
    c, s = math.cos(-yaw0), math.sin(-yaw0)
    vor, seit = c * d[0] - s * d[1], s * d[0] + c * d[1]
    return {"gefallen": gefallen, "vor": vor, "seit": seit, "neig_mittel": float(np.mean(neigung)),
            "neig_max": float(np.max(neigung)), "strom_fuss": float(np.mean(strom_fuss)),
            "strom_knie": float(np.mean(strom_knie))}


if __name__ == "__main__":
    v3_xml = Path(sys.argv[1])
    if "--probe" in sys.argv:                       # ein einzelner kurzer Lauf zum Ausprobieren
        import time
        t0 = time.time()
        print(lauf(None, {"vx": 0.5, "vy": 0.0, "vtheta": 0.0}, False, 1), f"{time.time() - t0:.1f} s")
        sys.exit()
    print(f"Lauftest: {SEKUNDEN:.0f} s je Fall, Seeds {SEEDS}, kp {KP_RL}. Werte: Mittel über die Seeds.\n")
    print(f"{'Fall':22} {'Kopf':4} {'gefallen':9} {'vor m':>6} {'seit m':>6} {'Neigung ø/max °':>16} {'Strom Fuß/Knie A':>17}")
    for name, befehl, schwenk in FAELLE:
        for kopf_name, quelle in (("alt", None), ("neu", v3_xml)):
            r = [lauf(quelle, befehl, schwenk, s) for s in SEEDS]
            fall = sum(x["gefallen"] is not None for x in r)
            mittel = {k: np.mean([x[k] for x in r]) for k in ("vor", "seit", "neig_mittel", "neig_max", "strom_fuss", "strom_knie")}
            print(f"{name:22} {kopf_name:4} {f'{fall}/{len(SEEDS)}':9} {mittel['vor']:6.2f} {mittel['seit']:6.2f} "
                  f"{mittel['neig_mittel']:7.1f} / {mittel['neig_max']:5.1f} {mittel['strom_fuss']:8.3f} / {mittel['strom_knie']:.3f}")
