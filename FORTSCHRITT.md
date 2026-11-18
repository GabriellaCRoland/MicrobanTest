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

## Nächster Schritt

- Abstand USB-A ↔ Pollen-Platine mit dem STEP der Platine C1 prüfen.
- Kopf mit AI Camera und Kabelweg durch den Hals konstruieren (Code-CAD), danach `pelvis`/`trunk_top` anpassen.
- Offen aus `v3/elektronik.md`: Kamerakabel, RAM/CPU-Test, Strom messen, Raspberry Pi OS + `imx500-all`.

## Offene Fragen

- Welcher Prusa genau (Mini, MK4, Core One …)?
- Welches CAD-Programm: Onshape-Kopie des Originals oder Code-CAD (build123d) für neue Teile?
