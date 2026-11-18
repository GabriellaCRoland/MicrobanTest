# Ziel: Microban v3 (Arbeitstitel)

- Art: Privat

Eigene Weiterentwicklung des Microban **zum Laufen** (Version `classic`, normale Füße). Die Kletterversion kommt
danach als zweiter Schritt auf derselben Basis.

> Name „v3“, weil Rhoban selbst schon v1 (Raspberry Pi Zero 2 W + Pollen-Hat) und v2 (Radxa ROCK 3C) hat.
> Die CAD-Dateien in `cad/` sind die v1.

## Was besser werden soll

1. **Bilderkennung:** Der Roboter erkennt mit der Kamera Dinge, während der Regelkreis mit 50 Hz weiterläuft.
   Die Erkennung läuft auf einer KI-Kamera (z. B. Raspberry Pi AI Camera) oder einem Board mit NPU
   (Vergleich: `v3/elektronik.md`).
2. **Kamera im Kopf:** Kamera im Kopf (dreht mit Servo ID 51), Kabel sicher durch den Hals.
3. **Besser druckbar (Prusa):** weniger Stützmaterial, vor allem bei Rumpf (`chest`, `pelvis`, `trunk_top`),
   Oberschenkeln und Kopf. Alle Teile passen in den Druckraum des Prusa Mini (180 × 180 × 180 mm).
4. **Einfacher Aufbau:** weniger Teile und Schrauben, wo es geht, leichtere Kabelführung.
5. **Eigenes Erscheinungsbild (Entscheidung 18.11.):** alle Strukturteile neu konstruiert, Stil **technisch-clean**
   (kantig mit einheitlichen Fasen, aufgeräumt, Kabel versteckt, gleiche Linien überall). Druckoptimiert für den
   **Prusa MK4/MK4S** (25 × 21 cm, eine Farbe): flache Seite aufs Bett, Überhänge ≤ 45°, keine langen Brücken.
6. **Neue Füße:** andere Größe/Form, schöner, besserer Halt (TPU-Sohle als eigenes Teil). Ändert sich die Sohle so
   stark, dass `walk.onnx` nicht mehr läuft, muss das Laufmodell neu trainiert werden.

## Was gleich bleibt

- 19 × Dynamixel XL330-M288-T, gleiche IDs und Gelenke, damit Laufmodell (`walk`) und Simulator weiter passen.
- Akku 2 × 18650, Laden über USB-C.
- Rhoban-Code nur ändern, wo nötig; eigene Teile liegen in `v3/`.

## Fertig, wenn …

- [ ] Board, Adapterplatine und Kamera sind ausgewählt und begründet (`v3/elektronik.md`).
- [ ] Neue Teile (mindestens Rumpf und Kopf) liegen als STEP + STL in `v3/cad/`.
- [ ] Alle Teile drucken auf dem Prusa, die Rumpfteile mit deutlich weniger Stützmaterial als v1
      (Vergleich mit `v3/analyse/stl_v1.txt`).
- [ ] Der Code erkennt das neue Board (`src/constants.py`), Motoren und IMU laufen.
- [ ] Das Kamerabild ist im Dashboard zu sehen, und ein einfaches Erkennungsbeispiel läuft auf dem Roboter.
- [ ] Der Roboter läuft mit `walk` mindestens so gut wie die v2.
