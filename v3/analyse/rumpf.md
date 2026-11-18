# Rumpf ausgemessen (18.11.2026)

Quelle: Gesamtbaugruppe `cad/microban.step`, ausgelesen mit `v3/tools/step_bauteile.py`, Platz geprüft mit
`v3/tools/platz_pruefen.py`. Koordinaten in mm: **x nach vorn** (Richtung Zehen), **y nach links**, **z nach oben**.

## So sitzt die Elektronik heute (v1)

| Bauteil | x | y | z | Bemerkung |
|---|---|---|---|---|
| Pi Zero 2 W | 21,4..26,5 | −15..15,6 | 26,5..91,5 | **hochkant vorn im Rumpf**, 65 mm senkrecht |
| Pollen-Platine | 14,8..16,9 | −15..15 | 26,5..91,5 | dahinter, 8 mm Abstandshalter |
| Akku 2 × 18650 | −30,5..−10 | −20,5..20,5 | 13..89 | hinten, senkrecht |
| BMS | −10..−5 | −8..8 | 42,6..83,7 | zwischen Akku und Motoren |
| Ladeplatine USB-C | −32..6,5 | −21,5..−3,3 | 92,5..97,5 | unter dem Deckel |
| Schalter | −24,5..−3,5 | 12,5..27,5 | 97,5..113,5 | im Deckel |
| Schultermotoren | −10..10 | ±24,5..50,5 | 56,5..90,5 | Mitte |
| Hüft-Gier-Motoren | −10..10 | ±11,5..45,5 | 0..26 | im Becken |
| Kopfmotor (ID 51) | −11,6..22,5 | −10..10 | 100..126 | auf dem Deckel |
| Kopf | −17,6..22,5 | −25..25 | 126..159 | |

Rumpf außen: `chest` 66 × 108 × 71,5, `pelvis` 66 × 108 × 34,5, `trunk_top` 66 × 101 × 25,2.

## Passt der Pi 3A+ (65 × 56 mm)?

Prüfung: Pi 3A+ an derselben Stelle wie der Pi Zero, ebenfalls hochkant (65 mm senkrecht, 56 mm quer), gleiche
Tiefe wie Pi Zero + Platine heute (x 14,8..26,5).

| Lage | Ergebnis |
|---|---|
| mittig (y −28..28), z 33..82 | **frei** |
| mittig, unterer Streifen z 26,5..33 | stößt an `pelvis` (118 mm³, oberer Rand/Befestigung) |
| mittig, oberer Streifen z 82..91,5 | stößt leicht an `trunk_top` (17 mm³) |
| nach links oder rechts verschoben | stößt an `chest` (1.822 mm³) → schlecht |
| quer (65 mm waagerecht) | stößt leicht an `chest` und `trunk_top` |
| USB-A steht 3 mm unten/oben über | stößt an `pelvis` (58 mm³) bzw. `trunk_top` (53 mm³) |

**Ergebnis:** Mittig und hochkant passt der Pi 3A+ fast in den heutigen Platz. Ändern müssen wir nur
den oberen Rand von `pelvis` (Befestigung) und die Unterkante von `trunk_top`. Die Teile bauen wir ohnehin um.
`chest` kann voraussichtlich bleiben.

## Maße Pi 3A+ (offizielle Maßzeichnung)

- Platine 65 × 56 mm, Ecken R3, Löcher 58 × 49 mm, je 3,5 mm vom Rand.
- Stiftleiste am langen Rand, Höhe 8,5 mm. Die Pollen-Platine (65 × 30) deckt die Hälfte an der Stiftleiste ab.
- USB-A am kurzen Rand, 7,0 mm hoch, steht über den Rand. Bei hochkant liegt sie **oben oder unten** → Richtung wählen.
- HDMI (6,5 mm), Klinke (6 mm), Micro-USB am langen Rand gegenüber der Stiftleiste. Die brauchen wir im Roboter
  nicht. Sie dürfen aber nicht an der Wand anstoßen.
- **Kameraanschluss (CSI)**: 45 mm vom kurzen Rand, nah am Rand gegenüber der Stiftleiste, 5,5 mm hoch.

## Offen für die Konstruktion

1. **Abstand USB-A ↔ Pollen-Platine:** Die USB-A-Buchse (7,0 mm) liegt teilweise unter der Platine, Abstand
   8,5 mm (Stiftleiste). Es bleiben ca. 1,5 mm, wenn auf der Unterseite der Platine nichts sitzt.
   → Mit dem STEP der Platine prüfen (`production/_old/ASE01187-C1_…_STEP.zip`).
2. **Befestigung:** Zwei Löcher an der Stiftleiste wie beim Zero (gleicher Abstand 58 mm), dazu zwei neue unten.
   Halter für beide Boards vorsehen.
3. **Kamerakabel:** Vom CSI-Anschluss nach oben durch `trunk_top`, am Kopfmotor (ID 51) vorbei in den Kopf.
   Dreht sich der Kopf, braucht das Flachbandkabel eine Schlaufe → Platz im Deckel einplanen.
4. **Kopf:** 40 × 50 × 33 mm. Die AI Camera (25 × 24 × 11,9 mm) passt hinein, der Kopf muss dafür aber
   neu konstruiert werden.
