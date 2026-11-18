"""Macht aus dem Rhoban-Modell (microban_model, im Simulator: microban_sim.build_spec) das Microban-v3-Modell.

Änderungen (alle auch einzeln abschaltbar):
  kopf    Masse, Schwerpunkt, Trägheit des neuen Kopfes (aus v3/tools/schwerpunkt.py, Werte unten)
  bein    Schienbein 15 mm länger: der Knöchel (Körper mit dem Gelenk *_ankle_pitch) sitzt 15 mm tiefer
  sohle   Kontaktflächen des neuen Fußes (v3/cad/fuss.py): 80 × 40 mm, 4 mm tiefer unter der Rollachse
  formen  die neuen Teile (Kopf, Schienbein, Fuß) als sichtbare Formen (nur fürs Zuschauen)

Im CAD (cad/microban.step) und im Modell liegen die Beine in der Nullstellung gleich (Knie z −83,4, Knöchel −144,62,
rechtes Bein bei y −36). Darum lassen sich CAD-Punkte direkt in die Körper-Koordinaten umrechnen.

Als Bibliothek: from modell_v3 import v3_spec;  spec = v3_spec(build_spec("classic"))
Als Programm schreibt es das Modell als XML (z. B. für das Training):
  uv run --no-project --python 3.12 --with "microban-sim @ git+https://github.com/Rhoban/microban_sim" --with trimesh \
      python v3/tools/modell_v3.py v3/modell/robot_v3.xml
"""
import sys
from pathlib import Path

import mujoco
import numpy as np

EINBAU = Path(__file__).resolve().parents[1] / "cad" / "einbau"
BEIN_LAENGER = 0.015
SOHLE_TIEFER = 0.004
# neuer Kopf (v3/tools/schwerpunkt.py, 18.11.2026): Masse kg, Schwerpunkt im Kopf-KS (m), Trägheitsfaktor
KOPF_MASSE = 0.0365
KOPF_IPOS = [0.0, -0.0085, 0.0182]
KOPF_TRAEGHEIT_FAKTOR = 2.15
SOHLE_MITTE_Y = -0.02175          # Sohlenebene im Fuß-KS (Original)


def _koerper_mit_gelenk(spec, gelenk):
    for b in spec.bodies:
        if any(j.name == gelenk for j in b.joints):
            return b
    raise KeyError(gelenk)


def _nullstellung(spec):
    """Weltlage aller Körper in der Nullstellung (Rumpf im Ursprung, aufrecht, alle Gelenke 0)."""
    m = spec.compile()
    d = mujoco.MjData(m)
    d.qpos[:] = 0
    d.qpos[3] = 1
    mujoco.mj_kinematics(m, d)
    lage = {}
    for i in range(m.nbody):
        lage[mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, i)] = (d.xpos[i].copy(), d.xmat[i].reshape(3, 3).copy())
    return lage


def _form(spec, koerper, lage, stl, farbe, spiegeln_y=False):
    import trimesh

    m = trimesh.load_mesh(stl)
    v = m.vertices / 1000.0
    f = m.faces
    if spiegeln_y:
        v = v * np.array([1, -1, 1])
        f = f[:, ::-1]
    p, R = lage[koerper.name]
    lokal = (v - p) @ R                      # = R^T (v − p) für jede Zeile
    netz = spec.add_mesh()
    netz.name = f"v3_{koerper.name}_{Path(stl).stem}"
    netz.uservert = lokal.astype(np.float32).ravel().tolist()
    netz.userface = f.astype(np.int32).ravel().tolist()
    g = koerper.add_geom()
    g.type = mujoco.mjtGeom.mjGEOM_MESH
    g.meshname = netz.name
    g.contype = g.conaffinity = 0
    g.group = 2
    g.mass = 0
    g.rgba = farbe


def _alte_formen_aus(koerper):
    for g in koerper.geoms:
        if g.classname.name == "visual":
            g.rgba = [0, 0, 0, 0]
            g.material = ""


def v3_spec(spec, kopf=True, bein=True, sohle=True, formen=False):
    lage = _nullstellung(spec) if (bein or formen) else None
    if kopf:
        # Trägheit aus dem kompilierten Modell (im XML steht sie mal als diaginertia, mal als fullinertia)
        m0 = spec.compile()
        i = mujoco.mj_name2id(m0, mujoco.mjtObj.mjOBJ_BODY, "head")
        k = spec.body("head")
        k.mass = KOPF_MASSE
        k.ipos = KOPF_IPOS
        k.inertia = m0.body_inertia[i] * KOPF_TRAEGHEIT_FAKTOR
        k.iquat = m0.body_iquat[i]
        k.fullinertia = [np.nan] * 6
        k.explicitinertial = True
    for seite in ("left", "right"):
        knoechel = _koerper_mit_gelenk(spec, f"{seite}_ankle_pitch")
        fuss = _koerper_mit_gelenk(spec, f"{seite}_ankle_roll")
        schien = knoechel.parent
        if bein:
            _, R = lage[schien.name]
            knoechel.pos = np.array(knoechel.pos) + R.T @ np.array([0.0, 0.0, -BEIN_LAENGER])
        if sohle:
            y = SOHLE_MITTE_Y - SOHLE_TIEFER
            a, b = spec.geom(f"{seite}_foot_collision_1"), spec.geom(f"{seite}_foot_collision_2")
            a.pos, a.size = [0.0, y, 0.0365], [0.020, 0.0345, 0.00125]
            b.pos, b.size = [0.0, y, 0.037], [0.014, 0.040, 0.00125]
            for i, (dx, dz) in zip(range(3, 7), ((-0.0165, -0.0015), (0.0165, -0.0015), (-0.0135, 0.0755), (0.0135, 0.0755))):
                spec.geom(f"{seite}_foot_collision_{i}").pos = [dx, y, dz]
            for s in spec.sites:
                if s.name == f"{seite}_foot":
                    s.pos = np.array(s.pos) + np.array([0.0, -SOHLE_TIEFER, 0.0])
        if formen:
            spiegeln = seite == "left"               # die CAD-Teile sind die des rechten Beins (y −36)
            # Lage nach der Verlängerung: Körper unterhalb des Knies 15 mm tiefer → CAD-Teile in v3-Lage passen dazu
            lage_neu = _nullstellung(spec)
            _alte_formen_aus(schien)
            _form(spec, schien, lage_neu, EINBAU / "schienbein.stl", [0.8, 0.8, 0.8, 1], spiegeln)
            _alte_formen_aus(fuss)
            _form(spec, fuss, lage_neu, EINBAU / "fuss.stl", [0.31, 0.62, 0.84, 1], spiegeln)
            _form(spec, fuss, lage_neu, EINBAU / "fuss_sohle.stl", [0.15, 0.15, 0.15, 1], spiegeln)
    if formen and kopf:
        kopfk = spec.body("head")
        lage_neu = _nullstellung(spec)
        _alte_formen_aus(kopfk)
        # Kopfteile: CAD-Drehachse x −2 mm, Modell +1,96 mm (v1-CAD gegen v2-Modell) → um 3,96 mm nach vorn schieben
        p, R = lage_neu["head"]
        for datei, farbe in (("kopf_haube.stl", [0.31, 0.62, 0.84, 1]), ("kopf_basis.stl", [0.18, 0.44, 0.62, 1]),
                             ("kopf_ring.stl", [0.95, 0.69, 0.2, 1]), ("platzhalter_ai_camera.stl", [0.15, 0.15, 0.15, 1])):
            import trimesh
            m = trimesh.load_mesh(EINBAU / datei)
            v = m.vertices / 1000.0 + np.array([0.00396, 0.0, 0.0])
            lokal = (v - p) @ R
            netz = spec.add_mesh()
            netz.name = f"v3_kopf_{Path(datei).stem}"
            netz.uservert = lokal.astype(np.float32).ravel().tolist()
            netz.userface = m.faces.astype(np.int32).ravel().tolist()
            g = kopfk.add_geom()
            g.type = mujoco.mjtGeom.mjGEOM_MESH
            g.meshname = netz.name
            g.contype = g.conaffinity = 0
            g.group = 2
            g.mass = 0
            g.rgba = farbe
    return spec


if __name__ == "__main__":
    from microban_sim.scene import build_spec

    ziel = Path(sys.argv[1])
    ziel.parent.mkdir(parents=True, exist_ok=True)
    s = v3_spec(build_spec("classic"))
    m = s.compile()
    ziel.write_text(s.to_xml(), encoding="utf-8")
    d = mujoco.MjData(m)
    d.qpos[3] = 1
    mujoco.mj_kinematics(m, d)
    print(f"geschrieben: {ziel}, Masse {sum(m.body_mass) * 1000:.1f} g")
