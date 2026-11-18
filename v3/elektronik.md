# Elektronik Microban v3 – Board-Vergleich

Stand 18.11.2026. Ziel: Bilderkennung im Kopf, Laufregelung mit 50 Hz bleibt, Akku 2 × 18650.

## Was das Board können muss (aus dem Code)

| Anforderung | Woher |
|---|---|
| UART mit 1 Mbit/s für 19 Dynamixel XL330 (Protokoll 2.0, Halbduplex über die Platine) | `src/constants.py:135`, `docs/dev/setup_rasp.md` |
| I2C für die IMU (heute BMI088, Bibliothek `pollen_bmi088_imu_library`) | `src/constants.py:136`, `pyproject.toml` |
| ONNX-Laufmodell mit 50 Hz (`onnxruntime`, aarch64, Python 3.12) | `pyproject.toml`, `src/agents/` |
| WLAN (Dashboard, Deploy über SSH) | `docs/usage.md` |
| neu: Kameraanschluss + Bilderkennung | ZIEL.md |

## Zwei Wege zur Bilderkennung

1. **Die Kamera rechnet selbst:** Raspberry Pi AI Camera (Sony IMX500). Das neuronale Netz läuft auf dem
   Kamerasensor, das Board bekommt nur das Ergebnis (Boxen, Klassen, Wahrscheinlichkeiten). So reicht auch ein
   kleines Board.
2. **Das Board rechnet:** normale Kamera und ein Board mit NPU (z. B. Rockchip RK3566 mit 0,8 TOPS). Das kostet mehr
   Software-Arbeit (RKNN-Toolkit) und belastet den Rechner, auf dem auch die Laufregelung läuft.

## Vergleich

| | Pi Zero 2 W | **Pi 3 Model A+** | Radxa Zero 3W | Radxa ROCK 3C | Pi 5 / CM5 |
|---|---|---|---|---|---|
| Größe | 65 × 30 mm (wie v1) | 65 × 56 mm | 65 × 30 mm | 85 × 56 mm | 85 × 56 mm / CM5 + Träger |
| Chip, RAM | BCM2837, 512 MB | **gleicher Chip** BCM2837, 512 MB, 1,4 GHz | RK3566, 1–8 GB | RK3566, bis 4 GB | BCM2712, bis 16 GB |
| Bilderkennung | AI Camera | AI Camera | NPU 0,8 TOPS (RKNN), normale Kamera | wie Zero 3W | AI Camera |
| AI Camera nutzbar | ja | ja (normaler 15-pol. Kameraanschluss) | nein (nur Raspberry Pi OS) | nein | ja |
| Code vorhanden | ja (v1) | fast (gleicher Chip, gleiches OS wie v1) | nein, gleicher Chip wie ROCK 3C | ja (v2) | nein |
| Pollen-Platine | ja | elektrisch ja (40-pol.), Befestigung zu prüfen | Pinbelegung zu prüfen | nein | nein |
| Strom | ca. 0,6–1,2 W | etwas mehr als Zero 2 W | höher | höher | ca. 3–9 W, 5 V/5 A |
| **Lieferbar (11/2026)** | **fast überall ausverkauft**, nur kleine Chargen | **ja**, ca. 46 € | nur Import, 2–4 Wochen | ja | ja |

Zum Pi Zero 2 W: Offiziell wird er weiter produziert (bis mind. 01/2030). Wegen knapper Substrate (Nachfrage durch KI)
ist er aber seit Monaten ausverkauft. Laut Raspberry-Pi-Forum ist in diesem Jahr kaum mit Ware zu rechnen.

## Empfehlung

**Pi 3 Model A+ + Pollen-Platine + Raspberry Pi AI Camera**, Rumpf so konstruiert, dass auch ein Pi Zero 2 W passt.

- Der Pi 3A+ hat **denselben Chip und RAM** wie der Pi Zero 2 W und läuft mit Raspberry Pi OS. Software und
  Einrichtung der v1 (`docs/dev/setup_rasp.md`) sollten fast unverändert passen, auch die AI Camera.
- Er ist lieferbar und hat den normalen Kameraanschluss. Das AI-Camera-Kabel passt direkt.
- Nachteil: 26 mm länger. Der Rumpf (`chest`/`trunk_top`) muss dafür umkonstruiert werden. Das wollten wir für
  Kamera und bessere Druckbarkeit ohnehin.
- Halterung mit Löchern für beide Boards: Die zwei Löcher an der Steckerleiste liegen bei beiden Boards im
  gleichen Abstand (58 mm, nachmessen). So passt später auch ein Pi Zero 2 W, wenn er wieder lieferbar ist.
- Die Erkennung (z. B. MobileNet SSD mit 30 Bildern/s) läuft auf der Kamera und belastet die Laufregelung kaum.
- Eigene Modelle lassen sich trainieren: PyTorch/TensorFlow → Sony Model Compression Toolkit → `imx500-package` → `.rpk`.

**Plan B:** Radxa Zero 3W (klein, stark, gleicher Chip wie die v2) mit normaler Kamera und Erkennung auf der NPU.
Mehr Software-Arbeit, dafür ohne AI Camera und mit viel mehr RAM.

## Vor dem Kauf prüfen (Risiken)

1. ~~**IMU auf der Pollen-Platine**~~ → geklärt (18.11.), siehe Abschnitt „Pollen-Platine: welche Revision?“ unten.
2. **Kamerakabel durch den drehenden Hals:** Flachbandkabel in passender Länge und eine Kabelschlaufe, damit der
   Kopf (Servo 51) drehen kann, ohne das Kabel zu knicken. Eventuell den Drehbereich des Kopfes begrenzen.
   (Pi 3A+: normaler 15-poliger Anschluss. Pi Zero 2 W: schmaler 22-poliger, eigenes Kabel.)
3. **Pollen-Platine auf dem Pi 3A+:** Steckt auf der 40-poligen Leiste. Prüfen, ob sie mit den zwei Löchern an der
   Leiste sicher hält und nichts auf dem 3A+ (USB-Buchse, Kameraanschluss) im Weg ist.
4. **RAM und CPU:** Laufregelung + `picamera2` gleichzeitig auf 512 MB. Erster Test: beides parallel laufen lassen
   und Takt der Regelschleife messen.
5. **Strom:** Stromaufnahme der AI Camera und ob der 5-V-Regler der Platine reicht (Angaben fehlen, messen).
6. **Software:** Die AI Camera braucht Raspberry Pi OS (`imx500-all`, `picamera2`). Prüfen, dass die v1-Installation
   (`docs/dev/setup_rasp.md`) dazu passt.

## Pollen-Platine: welche Revision? (geklärt 18.11.2026)

| Revision | Datum | IMU | passt zum Code | Fertigungsdateien |
|---|---|---|---|---|
| A1 | 03/2026 | BMI088 | nein (falsche I2C-Adresse) | `production/_old/…A1.zip` |
| B1 | 05/2026 | BMI088 (Acc 0x19, Gyro 0x68) | ja | `production/_old/…B1.zip` |
| **C1** | 07/2026 | **BMI088** (Acc 0x19, Gyro 0x68) | **ja, ohne Änderung** | `production/_old/` (Gerber, BOM, POS, STEP) |
| D1 | 10/2026 | LSM6DSV16X | nein, neuer Treiber nötig | `production/` (aktuell) |

Der Code setzt die BMI088-Adressen 0x19/0x68 fest (`src/imu_reader.py:17-18`). Genau die hat der Schaltplan ab B1.

**Empfehlung: Revision C1 bei JLCPCB fertigen lassen.** Die Software läuft dann unverändert, und das Laufmodell sieht
dieselbe IMU wie beim Training. Die BMI088 ist bei JLCPCB/LCSC vorrätig (C194919, 1.842 Stück, ca. 12,70 $ pro
Stück, Stand 18.11.). Die LSM6DSV16X aus D1 kostet ca. 3,60 $.

D1 ginge auch. Dann bräuchten wir eine eigene Klasse mit denselben Methoden wie die BMI088-Bibliothek
(`read_accelerometer()` in g, `read_gyroscope()` in rad/s, `get_quat(dt)`, Attribut `q`), eine neue
Einbaulage `IMU_MOUNT_QUAT` und Tests am echten Roboter. Das wären ca. 150 Zeilen. Es lohnt sich erst, wenn C1 nicht
mehr zu fertigen ist.

### Was der Schaltplan (C1) sonst zeigt

- **Pi 3A+ passt elektrisch genau wie der Pi Zero 2 W:** IMU an GPIO 2/3 (I2C1 = `IMU_I2C_BUS = 1`), Dynamixel an
  GPIO 14/15 (UART = `/dev/ttyAMA0`), IMU-Interrupt an GPIO 22. Beide Boards haben denselben Chip und dieselbe
  Pinbelegung, also bleibt `src/constants.py` für den Pi unverändert.
- **5-V-Regler:** AP63205, 2 A, Eingang aus dem Akku (`+BATT`). Das reicht für den Pi 3A+ (laut Pollen-Tabelle Pi 4 bis
  7,6 W, Zero 2 W 1,5 W) plus AI Camera. Messen wir trotzdem.
- **Dynamixel-Halbduplex:** 74LVC1G125/126 mit Richtung aus TX (Robotis-Schaltung), dazu RS-485 (SIT3088E) für andere Motoren.
- **Abschaltung erkennen:** GPIO 6 meldet, wenn die Akkuspannung wegfällt.
- Weitere I2C-Anschlüsse (Qwiic/Stemma QT, 3,3 V) für spätere Sensoren.

## Quellen

- Pollen RPI Robot Hat, Releases und Fertigungsdateien: https://github.com/pollen-robotics/elec_RPI_Robot_HAT
  (README-Tabelle „Releases“, Ordner `production/_old/`, Schaltplan `ASE01187-C1_elec_RPI_Robot_HAT_SCH.pdf`)
- LCSC/JLCPCB-Bestand (abgefragt über jlcsearch.tscircuit.com): BMI088 = C194919, LSM6DSV16XTR = C5267406

- Raspberry Pi AI Camera, Doku: https://www.raspberrypi.com/documentation/accessories/ai-camera.html
- Raspberry Pi AI Camera, Produktseite (25 × 24 × 11,9 mm, 78,3° Blickwinkel, Produktion bis mind. 01/2028):
  https://www.raspberrypi.com/products/ai-camera/
- Raspberry Pi Zero 2 W (Produktion bis mind. 01/2030): https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/
- Pollen RPI Robot Hat (Revision D1, IMU LSM6DSV16X, 5–28 V): https://github.com/pollen-robotics/elec_RPI_Robot_HAT
- Radxa Zero 3W (RK3566, 0,8 TOPS, 65 × 30 mm): https://electronics-lab.com/radxa-zero-3w-a-compact-rk3566-sbc-with-bluetooth-5-4-and-wi-fi-6
- Pi Zero 2 W ausverkauft, Alternativen (Stand 11.11.2026, Pi 3A+ ca. 46 €):
  https://raspberry.tips/en/raspberrypi-infos/raspberry-pi-zero-2-w-alternative-sold-out
- Lieferlage Pi Zero 2 W (Forum): https://forums.raspberrypi.com/viewtopic.php?t=398799&start=25
- Vergleich Zero-große Boards (09/2026): https://github.com/wr/macintosh-mini/issues/27
- Stromverbrauch Pi-Modelle: https://raspberry.tips/en/faq/raspberry-pi-power-consumption-update-2026-all-models-compared
