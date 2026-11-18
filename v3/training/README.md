# Laufmodell für Microban v3 neu trainieren

Grundlage: Rhobans [mjlab_microban](https://github.com/Rhoban/mjlab_microban), damit wurde `src/agents/walk.onnx`
trainiert (Geschwindigkeitsaufgabe, Servos mit BAM, Domain Randomization). Für v3 tauschen wir nur das
Robotermodell aus. Das macht `v3/tools/modell_v3.py`, dieselbe Datei wie im Simulator:

- Kopf mit AI Camera: 36,5 g statt 17 g, Schwerpunkt 8,5 mm vor der Achse
- Schienbein +15 mm (Knöchel tiefer)
- Sohle 80 × 40 mm, 4 mm tiefer unter der Rollachse
- Startposition des Rumpfs 19 mm höher

## Warum überhaupt?

Das alte `walk.onnx` läuft im Simulator auch auf v3 ohne Sturz (`v3/tools/lauftest_v3.py`). Aber:
- rückwärts kippt der Rumpf bis 23,5° (Original 16,2°)
- vorwärts voll braucht das Knie 19 % mehr Strom (0,93 statt 0,79 A)
- die neue Beweglichkeit im Knöchel (Spitze runter 95°) nutzt es nicht

## Voraussetzungen

- Linux mit NVIDIA-GPU und CUDA-Treiber (mjlab nutzt MuJoCo Warp), z. B. der HCR-Lab-Laptop.
  **Geteilter Rechner: vorher absprechen, ob die GPU frei ist** (dort läuft ggf. das Spot-Training).
- `uv`, `git`, Internet (für `uv sync`)
- optional ein Konto bei Weights & Biases (wandb) für die Trainingskurven

## Ablauf

```bash
git clone https://github.com/GabriellaCRoland/MicrobanTest   # oder: git pull im vorhandenen Klon
cd MicrobanTest
bash v3/training/einrichten.sh ~/mjlab_microban_v3
cd ~/mjlab_microban_v3
uv run play Mjlab-Velocity-Microban --agent zero               # Modell ansehen: langes Bein, neue Füße?
uv run train Mjlab-Velocity-Microban --env.scene.num-envs 4096 # Training
```

Das Ergebnis liegt in `logs/rsl_rl/mjlab_microban_velocity/<Datum>/`. Die ONNX-Datei wird beim Training mit
erzeugt (sonst `uv run python src/mjlab_microban/scripts/export_onnx.py --checkpoint …`).

Danach:
1. ONNX als `src/agents/walk_v3.onnx` ins MicrobanTest-Repo
2. Im Simulator testen: `v3/tools/lauftest_v3.py` (mit dem neuen Modell) und zuschauen mit `lauf_ansehen.py … v3`
3. Erst danach auf den echten Roboter

## Offen

- Gelenkgrenzen im Modell (Knöchel Nicken −90° … +35°, Rollen ±35°) noch wie beim Original. Für die neue
  Beweglichkeit vergrößern, sobald der echte Unterschenkel gebaut und vermessen ist.
- Massen von Schienbein (+ ca. 1,5 g) und Fuß (mit TPU ca. 18 g) sind noch nicht eingetragen.
