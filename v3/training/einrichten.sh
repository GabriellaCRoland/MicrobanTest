#!/usr/bin/env bash
# Richtet Rhobans Trainingsumgebung (mjlab_microban) für Microban v3 ein: Kopf mit AI Camera, Schienbein +15 mm,
# neue Sohle 80 × 40 (4 mm tiefer). Läuft auf Linux mit NVIDIA-GPU (mjlab nutzt MuJoCo Warp).
#
# Aufruf (aus dem MicrobanTest-Repo, auf dem Trainingsrechner):
#   bash v3/training/einrichten.sh ~/mjlab_microban_v3
# Danach: siehe v3/training/README.md
set -euo pipefail

ZIEL="${1:-$HOME/mjlab_microban_v3}"
HIER="$(cd "$(dirname "$0")/../.." && pwd)"

if [ ! -d "$ZIEL" ]; then
  git clone https://github.com/Rhoban/mjlab_microban "$ZIEL"
fi
cd "$ZIEL"

# BAM per https statt ssh (ohne GitHub-SSH-Schlüssel installierbar)
sed -i 's#ssh://git@github.com/rhoban/bam#https://github.com/Rhoban/bam#' pyproject.toml

# v3-Umbau des Modells neben die Roboter-Konstanten legen
cp "$HIER/v3/tools/modell_v3.py" src/mjlab_microban/robot/modell_v3.py

python3 - <<'PY'
from pathlib import Path
p = Path("src/mjlab_microban/robot/microban_constants.py")
t = p.read_text()
if "modell_v3" not in t:
    t = t.replace(
        "def get_spec() -> mujoco.MjSpec:\n    return mujoco.MjSpec.from_file(str(MICROBAN_XML))",
        "from .modell_v3 import v3_spec\n\n"
        "def get_spec() -> mujoco.MjSpec:\n"
        "    # Microban v3: Kopf mit AI Camera, Schienbein +15 mm, Sohle 80 x 40 (4 mm tiefer)\n"
        "    return v3_spec(mujoco.MjSpec.from_file(str(MICROBAN_XML)))")
    # Startposition: Rumpf 19 mm höher (Bein +15 mm, Sohle +4 mm)
    t = t.replace("pos=(0.0, 0.0, 0.168), #0.1676),", "pos=(0.0, 0.0, 0.187),  # v3: 0.168 + 0.019")
    assert "v3_spec" in t and "0.187" in t, "Anpassung fehlgeschlagen – microban_constants.py hat sich geändert?"
    p.write_text(t)
    print("microban_constants.py angepasst")
else:
    print("schon angepasst")
PY

uv sync
echo
echo "Fertig. Test (ohne Training, Fenster nötig):  uv run play Mjlab-Velocity-Microban --agent zero"
echo "Training:                                   uv run train Mjlab-Velocity-Microban --env.scene.num-envs 4096"
