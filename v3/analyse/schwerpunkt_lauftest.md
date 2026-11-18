# Schwerpunkt und Lauftest mit dem neuen Kopf (18.11.2026)

Modell: `microban_model` von Rhoban (MuJoCo, Microban v2, 769,8 g). Das Laufmodell `src/agents/walk.onnx` wurde auf
der v1 trainiert (Schulter-Grundstellung 0).

Werkzeuge in `v3/tools/`:
- `schwerpunkt.py`: Massen, Schwerpunkt, schreibt `robot_v3.xml` (Modell mit neuem Kopf)
- `stehtest.py`: Stehen mit PD-Regelung, Reserve zur Fußkante, Schubtest
- `lauftest.py`: echtes Laufmodell im Rhoban-Simulator (Servos mit BAM), alter gegen neuer Kopf
- `lauf_ansehen.py`: dasselbe mit MuJoCo-Fenster zum Zuschauen

## Massen

| | alt | neu |
|---|---|---|
| Kopf | 17,0 g | 36,5 g (Haube 18, Basis 6,2, Ring 0,9, AI Camera 10, Schrauben 0,9, Kabel 0,5) |
| Schwerpunkt Kopf über der Achse | ca. 21 mm | 18 mm, 8,5 mm vor der Achse |
| Roboter gesamt | 769,8 g | 789,3 g (+2,5 %) |

Unsicher: Gewicht der AI Camera (Händlerangabe 10 g, ggf. bis 15 g) und die Füllung der Druckteile → nach dem
Druck wiegen und in `schwerpunkt.py` eintragen.

## Stehen (PD-Regelung, Standhaltung des Laufmodells)

| | alt | neu |
|---|---|---|
| Schwerpunkthöhe | 161,5 mm | 165,2 mm (+3,7 mm) |
| Reserve zur Fußkante hinten / vorn | 28,6 / 51,8 mm | 29,7 / 50,6 mm |
| Schubtest (0,1 s): vorn / hinten / Seite | 3,18 / 1,85 / 4,69 N | 3,20 / 1,95 / 4,79 N |

## Laufen (walk.onnx, 12 s je Fall, 3 Durchläufe)

| Fall | gefallen alt / neu | Strecke alt / neu | Rumpfneigung max alt / neu | Strom Fuß alt / neu |
|---|---|---|---|---|
| stehen | 0/3 / 0/3 | – | 14,3° / 15,0° | 0,070 / 0,076 A |
| vorwärts halb | 0/3 / 0/3 | 3,79 / 4,07 m | 11,4° / 11,6° | 0,389 / 0,390 A |
| vorwärts voll | 0/3 / 0/3 | 6,44 / 6,22 m | 11,6° / 11,7° | 0,530 / 0,533 A |
| rückwärts | 0/3 / 0/3 | 4,78 / 4,27 m | 16,2° / 17,3° | 0,500 / 0,500 A |
| seitwärts | 0/3 / 0/3 | 0,96 / 0,90 m | 12,6° / 13,2° | 0,241 / 0,237 A |
| drehen | 0/3 / 0/3 | – | 12,1° / 12,6° | 0,287 / 0,291 A |
| vorwärts + Kopf ±46° | 0/3 / 0/3 | 3,88 / 3,97 m | 11,5° / 11,6° | 0,389 / 0,388 A |

## Bewertung

- **Laufen geht mit dem neuen Kopf genauso gut:** kein Sturz, Strecken und Ströme fast gleich, Rumpf neigt sich
  0,5–1° mehr.
- Am knappsten ist **rückwärts** (max. Neigung 17,3°) und **nach hinten schieben** (Schwerpunkt liegt eher hinten).
  Der neue Kopf liegt etwas weiter vorn, das hilft dort sogar.
- Strom in Füßen und Knien steigt kaum (< 1 %). Die Erwärmung der Knöchel (beim Klettern bis 60 °C) wird beim Laufen
  durch den Kopf nicht spürbar schlimmer.
- Der Kopfmotor schafft die schwerere Last leicht (Trägheit noch sehr klein gegenüber 0,52 Nm Haltemoment).

## Grenzen

- Simuliert ist die v2-Masseverteilung (Radxa). Die v3 mit Pi Zero hat die Elektronik wie die v1 verteilt.
- Das Laufmodell ist nicht neu trainiert. Es kommt mit +2,5 % Masse zurecht, aber nach dem Bau trotzdem am echten
  Roboter prüfen (erst stehen, dann langsam laufen).
- Für die Kletterversion (später) gesondert testen: Dort hängt der Roboter, und der schwerere Kopf ist ein Hebel.
