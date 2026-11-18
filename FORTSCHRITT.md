# Fortschritt Microban v3

## 18.11.2026 – Start

- Ziel festgelegt (`ZIEL.md`): Laufversion zuerst, Kamera mit Bilderkennung, Prusa-Druck, neues Board.
- STL-Auswertung der v1-Teile: `v3/tools/stl_analyse.py` → `v3/analyse/stl_v1.txt`.
  - Alles passt in den Prusa Mini. Ca. 295 g PLA ohne Stützmaterial.
  - Am meisten Stützmaterial: `chest`, `pelvis`, `trunk_top` (Rumpf), dann `femur_*` und `head`.
    Den Rumpf bauen wir für das neue Board ohnehin um. Das passt gut zusammen.
  - Wichtig: `hip`, `pelvis`, `shoulder` und `arm_bearing_support` müssen wegen der Gleitlager in fester Lage gedruckt
    werden (`docs/printing.md`). Dort ist der Stützbedarf vom Lager vorgegeben.

- Board-Vergleich `v3/elektronik.md`. Pi Zero 2 W ist praktisch nicht lieferbar. Empfehlung jetzt:
  Pi 3 Model A+ (gleicher Chip, lieferbar) + Pollen-Platine + Raspberry Pi AI Camera (Erkennung läuft auf der Kamera),
  Rumpf passend für 3A+ und Zero 2 W. Plan B: Radxa Zero 3W mit NPU. Wichtigstes Risiko: Die aktuelle Pollen-Platine (Rev. D1) hat eine andere IMU
  (LSM6DSV16X) als der Code (BMI088).

- Board bestätigt: Pi 3A+.
- IMU geklärt: Pollen-Platine **Revision C1** (BMI088, Dateien in `production/_old/`) läuft ohne Codeänderung.
  D1 hat eine LSM6DSV16X und bräuchte einen neuen Treiber. Laut Schaltplan ist der Pi 3A+ pinkompatibel
  (I2C1, UART an GPIO 14/15).

- Rumpf ausgemessen (`v3/analyse/rumpf.md`, Werkzeuge `v3/tools/step_bauteile.py`, `platz_pruefen.py`):
  Pi 3A+ passt mittig hochkant an die Stelle des Pi Zero. Nur `pelvis` (oberer Rand) und `trunk_top` (Unterkante)
  müssen geändert werden, `chest` kann voraussichtlich bleiben.

- Kopf v0.1 mit AI Camera (`v3/kopf.md`, Code-CAD `v3/cad/kopf.py`): Distanzring, Bodenplatte und Haube, alle
  ohne nennenswertes Stützmaterial. Bei ±60° Kopfdrehung keine Zusammenstöße (`v3/tools/kopf_pruefen.py`).
  Weitere Werkzeuge: `ansicht.py` (3D-Bild), `schnitt.py` (Schnittbild), `export_teile.py` (Teile in Einbaulage als STL).

- Deckel/Rumpf für Pi 3A+ untersucht (`v3/analyse/rumpf.md`, Nachtrag): Der Pi passt quer, aber die
  Pollen-Platine auf seiner Stiftleiste stößt an die Schultermotoren und ihre Halterung → Brust müsste neu.
  Mit Pi Zero 2 W bleibt der Rumpf, und das Kamerakabel hat einen kurzen Weg.
- Entscheidung: **beides vorbereiten**, zuerst Pi Zero 2 W, danach Brust für Pi 3A+.
- Deckel v3 für Pi Zero 2 W (`v3/deckel.md`, `v3/cad/deckel.py`): Kabelschlitz hinter dem Kopfmotor, Ladeplatine
  4 mm nach rechts. Kabelweg Kopf → Pi geprüft und frei. Pi Zero dafür um 180° gedreht einbauen.

- Schwerpunkt + Lauftest (`v3/analyse/schwerpunkt_lauftest.md`): Kopf 17 → 36,5 g, Roboter +2,5 %, Schwerpunkt
  +3,7 mm höher. Im Rhoban-Simulator mit `walk.onnx` kein Sturz in 7 Fällen, Werte fast gleich wie mit altem Kopf.
  Zuschauen: `v3/tools/lauf_ansehen.py`.

- Gestaltung festgelegt: alles neu, technisch-clean, Prusa MK4/MK4S (siehe ZIEL.md Punkt 5/6).
- **Neuer Fuß** (`v3/cad/fuss.py`): PLA-Fuß + TPU-Sohle mit Querrillen, Sohle 80 × 40 (Original 90 × 45),
  achteckige Arme mit versenkten Schrauben, Mittelrippe, Tropfen-Mittelloch. Überhang 72 mm² (Original 66), TPU 0.
  Rollen ±35° frei (`v3/tools/gelenk_pruefen.py`). Sohlen-Studie (`v3/tools/fuss_test.py`): `walk.onnx` läuft ohne
  Neutraining. Die Zehe muss bis x = 54 reichen, sonst wird Rückwärtslaufen wackelig (72 mm: Neigung 22° statt 16°).

- Fuß soll komplett neu, Ziel **mehr Beweglichkeit**, Neutraining ist ok. Knöchel-Analyse (`v3/analyse/knoechel.md`):
  Der Knöchel ist schon ein Kardangelenk. „Spitze runter“ (35°) begrenzt der Rollmotor, der in den Kniemotor
  schwenkt. Empfehlung: Motoranordnung lassen, Schienbein 10–15 mm länger, Sohle 4 mm tiefer, Schienbein/Block/Fuß neu.
  Fuß-Ansicht mit Nicken + Rollen + Abspielen: `v3/tools/vorschau.py … fuss`.

- **Unterschenkel v3** (+15 mm Schienbein, Sohle 4 mm tiefer): Spitze runter 35° → 95°, hoch 85° → 110°,
  Rollen ±40° → ±55°, mit echten Teilen geprüft. `v3/cad/unterschenkel.py`, Ansicht `vorschau.py … unterschenkel`.

- **v3-Simulator-Modell** (`v3/tools/modell_v3.py`): Kopf, Schienbein +15 mm, Sohle 80 × 40 / 4 mm tiefer – passt
  exakt zum CAD, funktioniert mit microban_model (Simulator) und mjlab_microban (Training). Altes walk.onnx läuft
  darauf ohne Sturz (`lauftest_v3.py`), aber rückwärts 23,5° Neigung und Kniestrom +19 % → Neutraining sinnvoll.
  Zuschauen: `lauf_ansehen.py … v3`. Training vorbereitet: `v3/training/` (einrichten.sh + README).

## Nächster Schritt

- Training auf einem Rechner mit NVIDIA-GPU (HCR-Lab-Laptop: vorher absprechen, ob frei).
- Danach: walk_v3.onnx im Simulator testen; Schienbein im technisch-clean-Stil; Rumpf.
- Rumpf im selben Stil (Brust, Becken, Deckel neu; Brust mit Platz für Pi 3A+).

- Neue Brust (`chest`) für Pi 3A+ + Pollen-Platine (Schultermotor-Halterung), dabei weniger Stützmaterial.
- Probedruck Kopf + Deckel, Maße der echten AI Camera nachmessen.
- Abstand USB-A ↔ Pollen-Platine mit dem STEP der Platine C1 prüfen (nur für Pi 3A+).
- Offen aus `v3/elektronik.md`: Kamerakabel, RAM/CPU-Test, Strom messen, Raspberry Pi OS + `imx500-all`.

## Offene Fragen

- Welcher Prusa genau (Mini, MK4, Core One …)?
- Welches CAD-Programm: Onshape-Kopie des Originals oder Code-CAD (build123d) für neue Teile?
