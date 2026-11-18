"""Lauftest: altes Laufmodell (walk.onnx) auf dem Original gegen das v3-Modell (Kopf + Bein +15 mm + neue Sohle).

Aufruf: uv run --no-project --python 3.12 --with "microban-sim @ git+https://github.com/Rhoban/microban_sim" \
            --with onnxruntime --with ahrs --with trimesh --with scipy python v3/tools/lauftest_v3.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lauftest as lt                      # noqa: E402
from microban_sim.scene import build_spec  # noqa: E402
from modell_v3 import v3_spec              # noqa: E402

VARIANTEN = [
    ("Original", lambda q: build_spec("classic")),
    ("nur Kopf v3", lambda q: v3_spec(build_spec("classic"), bein=False, sohle=False)),
    ("v3 komplett", lambda q: v3_spec(build_spec("classic"))),
]
print(f"{'Modell':14} {'Fall':22} {'gefallen':8} {'Strecke m':>9} {'Neigung max °':>13} {'Strom Fuß/Knie A':>17}")
for name, bau in VARIANTEN:
    lt.spec_mit_kopf = bau
    for fall, befehl, schwenk in lt.FAELLE:
        r = [lt.lauf(None, befehl, schwenk, s) for s in lt.SEEDS]
        fz = sum(x["gefallen"] is not None for x in r)
        print(f"{name:14} {fall:22} {f'{fz}/{len(r)}':8} {np.mean([np.hypot(x['vor'], x['seit']) for x in r]):9.2f} "
              f"{np.mean([x['neig_max'] for x in r]):13.1f} {np.mean([x['strom_fuss'] for x in r]):8.3f} / "
              f"{np.mean([x['strom_knie'] for x in r]):.3f}")
    print()
