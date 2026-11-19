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

## Schnittstellen-Sicherheit

Maßstab: `~/.claude/pruefung/SCHNITTSTELLEN-SICHERHEIT.md`. Eigene Sicherheitsänderungen im Rhoban-Code sind mit
`# Sicherheit (Gabriella)` markiert.

### Dashboard-Link – UDP 7350 auf dem Roboter (`src/humanoid_dashboard/link.py`, `src/telemetry.py`)
Wer darf aufrufen: nur ein PC mit dem gemeinsamen Schlüssel (`~/.config/humanoid_dashboard/key`, nie im Repo;
`make deploy` kopiert ihn auf den Roboter). Geprüft per HMAC-SHA256 über Sitzungs-Zufallszahl + steigende Nummer + Inhalt.
Ohne Schlüssel auf dem Roboter: nur Messdaten, alle Befehle abgelehnt.

| S-Nr | Missbrauch / falsche Eingabe | Erwartetes Verhalten | Test |
|------|------------------------------|----------------------|------|
| S1 | Befehl ohne oder mit falscher Signatur (fremder Rechner im WLAN) | verworfen, nicht ausgeführt, gezählt/protokolliert | `test_s1_befehl_ohne_signatur_wird_verworfen` |
| S2 | Mitgeschnittener gültiger Befehl wird erneut gesendet (Replay) | verworfen (Nummer nicht größer als die letzte) | `test_s2_wiederholter_befehl_wird_verworfen` |
| S3 | Gültiger Befehl aus einer früheren Sitzung (Roboter neu gestartet) | verworfen (andere Sitzungs-Zufallszahl) | `test_s3_befehl_alter_sitzung_wird_verworfen` |
| S4 | Kaputtes Paket: kein JSON, JSON-Liste/Zahl, `args` als Liste, `name` als Liste, riesige Werte, tiefe Verschachtelung mit gültiger Sitzung; jede unerwartete Ausnahme im Dashboard-Teil | ignoriert; jedes Paket und `Telemetry.tick()` als Ganzes abgefangen, Regelschleife läuft weiter | `test_s4_kaputte_pakete_stoppen_die_schleife_nicht`, `test_s4_tiefe_verschachtelung_mit_sitzung`, `test_s4_fehler_im_link_stoppt_tick_nicht` |
| S5 | Unsigniertes `hello` (Daten abgreifen, Roboter als Verstärker gegen fremde Adresse) | mit Schlüssel: keine Daten, kein Abo; nur eine kleine `challenge` (Sitzungsnummer, etwa so groß wie das `hello` → keine Verstärkung) | `test_s5_hello_ohne_signatur_bekommt_keine_daten` |
| S6 | Viele `hello` von gefälschten Absendern | höchstens 4 Abonnenten gleichzeitig, Abo läuft nach 3 s ab | `test_s6_abonnenten_sind_begrenzt` |
| S7 | Flut von `reboot`/`torque` (jeder `reboot` hält die Schleife bis 1,5 s an) | `reboot` höchstens 1 je 2 s, `torque` 1 je 0,3 s, Rest mit „too fast“ abgelehnt; `em` nie begrenzt | `test_s7_reboot_flut_wird_begrenzt` |
| S8 | Kein Schlüssel auf dem Roboter | Messdaten ja, jeder Befehl abgelehnt mit „kein Schlüssel“ | `test_s8_ohne_schluessel_nur_anzeigen` |
| S9 | Slider-Wert NaN/Inf/1e30, unbekannter Slider | auf Bereich begrenzt bzw. ignoriert | schon im Rhoban-Code (`telemetry.py`), Test `test_s9_slider_wird_begrenzt` |
| S10 | `move_option` mit riesigem Wert (z. B. Schrittweite 1e9) | **offen:** Optionen haben keine Grenzen; erst Grenzen je Option festlegen | – |
| S11 | Schlüsseldatei für andere lesbar / im Repo | Datei nur für den Besitzer (0600), in `.gitignore` nicht nötig (liegt außerhalb) | `test_s11_schluessel_wird_privat_angelegt` |

Tests: `PYTHONPATH=src uv run --no-project --python 3.12 --with pytest pytest -q tests/test_dashboard_sicherheit.py`
(laufen unter Windows ohne Roboter-Bibliotheken; `constants`/`moves.move` werden dort durch kleine Platzhalter ersetzt).
Bekannte Grenzen: Messdaten gehen unverschlüsselt durchs WLAN (nur lesbar, nicht steuerbar); wer den Schlüssel
vom PC oder Roboter kopiert, kann steuern – Schlüssel dann löschen, `make dashboard-key` erzeugt/verteilt ihn neu.
Die Befehlsnummer des PCs startet bei der PC-Uhrzeit (ms): wird die Uhr zurückgestellt und das Dashboard neu
gestartet, lehnt der Roboter den PC bis zu seinem eigenen Neustart ab (Meldung „refuses this PC's key“) – dann den
Roboter-Dienst neu starten. Unter Windows schützt 0600 nichts, dort schützen die Rechte des Benutzerordners.
Ohne Schlüssel auf dem Roboter können 4 gefälschte `hello` die Anzeige belegen (nur Anzeige, keine Steuerung).

PC-Seite (`app.py`, HTTP/WebSocket 8780): lauscht nur auf `127.0.0.1`, Host-/Origin-Prüfung gegen DNS-Rebinding –
bereits im Rhoban-Code, unverändert.
