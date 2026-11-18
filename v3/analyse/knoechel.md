# Knöchel: beste Lösung für mehr Beweglichkeit (18.11.2026)

Werkzeuge: `v3/tools/gelenk_pruefen.py` (heutige Grenzen mit den echten Teilen), `v3/tools/knoechel_suche.py`
(Grenzen, wenn nur noch die Motoren mit 2 mm Wand + 1 mm Spiel begrenzen).

## Heute

Der Knöchel ist schon ein **Kardangelenk**: Nick- und Rollachse schneiden sich in einem Punkt (x 15,5, y −36,
z −144,62). Funktional ist er also ein angetriebenes Kugelgelenk mit 2 Achsen.
Vorzeichen Nicken: **+ = Spitze runter**, − = Spitze hoch.

| | Mensch | heute | Grenze |
|---|---|---|---|
| Spitze hoch | ~20° | 85° | Fuß an Schienbein |
| Spitze runter | ~50° | 35–40° | **Rollmotor (hinter der Nickachse, lange Seite oben) schwenkt in den Kniemotor** |
| Rollen | ~35° / 20° | ±40° | Fußarme an Schienbein |

Die Schwäche ist „Spitze runter“. Das braucht man fürs Abdrücken, den Zehenstand und das Klettern. Grund dafür ist
die Anordnung der Motoren, nicht die Form der Druckteile.

## Durchgerechnete Varianten (nur Motoren als Grenze)

| Variante | Spitze runter | Rollen | Überstand seitlich | Bein länger |
|---|---|---|---|---|
| heute, Sohle 4 mm tiefer | 31° | frei (≥ 90°) | 0 | 4 mm |
| Rollmotor liegend (90°), Sohle 4 mm tiefer | 61° | 90° / **22°** | 6,5 mm | 4 mm |
| Rollmotor schräg (75°), Sohle 4 mm tiefer | 49° | 90° / 37° | 8,7 mm | 4 mm |
| **heute + Schienbein 10 mm länger, Sohle 4 mm tiefer** | **46,5°** | **frei** | **0** | **14 mm** |
| heute + Schienbein 15 mm länger, Sohle 4 mm tiefer | nicht mehr durch Motoren begrenzt | frei | 0 | 19 mm |

## Empfehlung

**Motoranordnung wie heute lassen, Schienbein 10–15 mm länger, Sohle 4 mm tiefer.** Dazu Schienbein, Knöchelblock
und Fuß so neu gestalten, dass nur noch die Motoren begrenzen (Schienbein unten als schmale Gabel, nichts in den
Ebenen der Fußarme, Fußplatte mit Luft unter den Motoren).

- Spitze runter: 35° → ca. 47° (10 mm) bzw. so weit, bis der Fuß das Schienbein berührt (15 mm)
- Rollen: ±40° → deutlich mehr (Grenze sind dann Fußarme/Gabel, Ziel ±55°)
- Spitze hoch: bleibt bei ca. 85°
- Kein seitlicher Überstand, keine zusätzlichen Teile, gleiche Motoren
- Kosten: Bein 14–19 mm länger (Roboter etwas größer, Schwerpunkt höher) → **Laufmodell neu trainieren**
  (`Rhoban/mjlab_microban`, NVIDIA-GPU). Das Knie muss bei längerem Schienbein etwas mehr Moment liefern
  (Strom heute 0,6–0,8 A von 1,75 A).

Verworfen: Parallelknöchel (schlanker, aber typisch nur ±30–45°), liegender Rollmotor (Rollen nach einer Seite nur
22°, Knöchel steht seitlich über), dritter Servo am Knöchel (+18 g ganz unten, Drehen macht schon die Hüfte).

## Umgesetzt (18.11.2026): Unterschenkel v3

Entscheidung: **+15 mm** (sinnvoller: Neutraining ist sowieso nötig, dann begrenzen die Motoren gar nicht mehr).

- `v3/cad/unterschenkel.py`: Original-Schienbein bei z = −125 geschnitten, unten 15 mm tiefer gesetzt, Lücke mit dem
  Querschnitt gefüllt → alle Anschlüsse exakt wie beim Original. Knöchelblock unverändert (nur 15 mm tiefer).
- `v3/cad/fuss.py`: Rollachse 15 mm tiefer, Sohle 27 mm unter der Achse (Original 23), Mittelrippe 4 mm hoch.

Geprüft mit `v3/tools/gelenk_pruefen.py` (echte Teile):

| | Original | v3 | frei bis | erster Anstoß |
|---|---|---|---|---|
| Spitze runter | 35° | **95°** | 95° | 100° (Fuß an Schienbein) |
| Spitze hoch | 85° | **110°** | 110° | 115° (Fuß an Schienbein) |
| Rollen | ±40° | **±55°** | 55° | 60° (Fuß an Schienbein, 5 mm³) |

(Gegenlager ↔ Knöchelblock 1 mm³ in jeder Stellung = Lagerzapfen im Sitz, kein Anstoß.)

Noch zu tun: Kabel der Knöchelmotoren lang genug für die großen Winkel, Simulator-Modell anpassen, Laufmodell neu
trainieren, Gestaltung des Schienbeins im technisch-clean-Stil.
