"""Baut eine interaktive 3D-Vorschau (eine HTML-Datei, im Browser öffnen) aus STL-Dateien in Einbaulage.

Aufruf: uv run --no-project --python 3.12 --with trimesh --with numpy --with scipy python v3/tools/vorschau.py \
            EINBAU_ORDNER_BAUGRUPPE v3/vorschau.html [kopf|fuss|unterschenkel]
EINBAU_ORDNER_BAUGRUPPE: Ordner mit den Teilen der Baugruppe als STL (erzeugt mit export_teile.py).
Die neuen v3-Teile kommen aus v3/cad/einbau/. Die HTML-Datei in Edge/Chrome öffnen (nicht in VS Code).

Gelenke sind verschachtelt: Gelenk 1 hängt an Gelenk 0 (wie Rollen am Nicken). Jedes Teil gehört zu einer Gruppe:
-1 = fest, 0 = dreht mit Gelenk 0, 1 = dreht mit Gelenk 0 und 1.
"""
import base64
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

alt, ziel = Path(sys.argv[1]), Path(sys.argv[2])
satz = sys.argv[3] if len(sys.argv) > 3 else "kopf"
neu = Path(__file__).resolve().parents[1] / "cad" / "einbau"

SAETZE = {
    "kopf": {
        "titel": "Microban v3 – Kopf &amp; Deckel",
        "gelenke": [{"punkt": [-2, 0, 0], "achse": [0, 0, 1], "min": -60, "max": 60, "text": "Kopfdrehung"}],
        "hinweis": "Genutzt werden ±46° (±0,8 rad), geprüft ist ±60°. Das Kabel ist hier fest gezeichnet, in echt hat "
                   "es oben eine Schlaufe.",
        "teile": [
            ("Kopf: Haube", neu / "kopf_haube.stl", "#4f9fd6", 0.45, 0),
            ("Kopf: Bodenplatte", neu / "kopf_basis.stl", "#2f6f9f", 1.0, 0),
            ("Kopf: Distanzring", neu / "kopf_ring.stl", "#f2b134", 1.0, 0),
            ("AI Camera (Platzhalter)", neu / "platzhalter_ai_camera.stl", "#3a3a3a", 1.0, 0),
            ("Kamerakabel (Platzhalter)", neu / "platzhalter_kabel.stl", "#e8743b", 1.0, -1),
            ("Deckel v3", neu / "deckel.stl", "#9bc27a", 0.55, -1),
            ("Ladeplatine (neue Lage)", neu / "platzhalter_ladeplatine.stl", "#c0392b", 1.0, -1),
            ("Motoren im Rumpf (XL330)", alt / "trunk_1_XL330_without_horn.stl", "#5a5a66", 1.0, -1),
            ("Schalter", alt / "trunk_1_switch.stl", "#d35400", 1.0, -1),
            ("Pi Zero 2 W", alt / "raspberry.stl", "#2e8b57", 1.0, -1),
            ("Pollen-Platine", alt / "trunk_1_hat.stl", "#1f5f3f", 1.0, -1),
            ("Akku 2 × 18650", alt / "trunk_1_battery.stl", "#8e44ad", 1.0, -1),
            ("BMS", alt / "trunk_1_BMS.stl", "#7f8c8d", 1.0, -1),
            ("Brust (chest)", alt / "trunk_1_chest.stl", "#d9d9d9", 0.25, -1),
            ("Becken (pelvis)", alt / "trunk_1_pelvis.stl", "#cfcfcf", 0.25, -1),
            ("Schulter links", alt / "shoulder_1_shoulder.stl", "#bdbdbd", 0.5, -1),
            ("Schulter rechts", alt / "shoulder_2_shoulder.stl", "#bdbdbd", 0.5, -1),
        ],
        "aus": {"Brust (chest)", "Becken (pelvis)", "Schulter links", "Schulter rechts"},
        "ziel": [0, 0, 105], "kamera": [260, -200, 220],
    },
    "fuss": {
        "titel": "Microban v3 – Fuß in Bewegung",
        # Bereiche: heute ohne Zusammenstoß möglich (v3/tools/gelenk_pruefen.py, 18.11.)
        "gelenke": [{"punkt": [15.5, -36, -144.62], "achse": [0, 1, 0], "min": -85, "max": 35,
                     "text": "Nicken (+ Spitze runter, − Spitze hoch)"},
                    {"punkt": [0, -36, -144.62], "achse": [1, 0, 0], "min": -40, "max": 40, "text": "Rollen (kippen)"}],
        "hinweis": "Bereiche wie sie heute ohne Anstoßen gehen: Spitze hoch bis 85°, Spitze runter bis 35°, Rollen ±40°. Beide Achsen schneiden "
                   "sich in einem Punkt (wie ein Kugelgelenk mit 2 angetriebenen Achsen). Beim Laufen werden nur "
                   "wenige Grad genutzt.",
        "teile": [
            ("Fuß v3 (PLA)", neu / "fuss.stl", "#4f9fd6", 1.0, 1),
            ("TPU-Sohle", neu / "fuss_sohle.stl", "#2b2b2b", 1.0, 1),
            ("alter Fuß (Original)", alt / "foot_1_foot.stl", "#e8743b", 0.35, 1),
            ("Knöchelblock", alt / "ankle_block_2_ankle_dbl_block.stl", "#9bc27a", 0.9, 0),
            ("Knöchelmotoren (XL330)", alt / "ankle_block_2_XL330.stl", "#5a5a66", 1.0, 0),
            ("Gegenlager (Idle Horn)", alt / "ankle_block_2_DC15.stl", "#f2b134", 1.0, 0),
            ("Schienbein (tibia)", alt / "tibia_1_tibia.stl", "#cfcfcf", 0.5, -1),
        ],
        "aus": {"alter Fuß (Original)"},
        "ziel": [14, -36, -145], "kamera": [150, -190, -100],
    },
    "unterschenkel": {
        "titel": "Microban v3 – Unterschenkel mit mehr Beweglichkeit",
        # geprüft mit v3/tools/gelenk_pruefen.py: Spitze runter frei bis 95°, hoch bis 110°, Rollen ±55°
        "gelenke": [{"punkt": [15.5, -36, -159.62], "achse": [0, 1, 0], "min": -110, "max": 95,
                     "text": "Nicken (+ Spitze runter, − Spitze hoch)"},
                    {"punkt": [0, -36, -159.62], "achse": [1, 0, 0], "min": -55, "max": 55, "text": "Rollen (kippen)"}],
        "hinweis": "Schienbein 15 mm länger, Sohle 4 mm tiefer, Motoren wie beim Original. Geprüft ohne Anstoßen: "
                   "Spitze runter bis 95° (vorher 35°), hoch bis 110° (vorher 85°), Rollen ±55° (vorher ±40°). "
                   "Alten Unterschenkel zum Vergleich einblenden (steht 15 mm höher).",
        "teile": [
            ("Fuß v3 (PLA)", neu / "fuss.stl", "#4f9fd6", 1.0, 1),
            ("TPU-Sohle", neu / "fuss_sohle.stl", "#2b2b2b", 1.0, 1),
            ("Gegenlager (Idle Horn)", neu / "knoechel_gegenlager.stl", "#f2b134", 1.0, 1),
            ("Knöchelblock", neu / "knoechel_block.stl", "#9bc27a", 0.9, 0),
            ("Knöchelmotoren (XL330)", neu / "knoechel_motoren.stl", "#5a5a66", 1.0, 0),
            ("Schienbein v3 (+15 mm)", neu / "schienbein.stl", "#cfcfcf", 0.6, -1),
            ("Kniemotor", alt / "tibia_1_XL330.stl", "#5a5a66", 1.0, -1),
            ("Oberschenkel (femur)", alt / "femur_1_femur.stl", "#bdbdbd", 0.35, -1),
            ("altes Schienbein", alt / "tibia_1_tibia.stl", "#e8743b", 0.3, -1),
            ("alter Fuß", alt / "foot_1_foot.stl", "#e8743b", 0.3, -1),
        ],
        "aus": {"altes Schienbein", "alter Fuß"},
        "ziel": [14, -36, -140], "kamera": [190, -230, -80],
    },
}
S = SAETZE[satz]

daten = []
for name, datei, farbe, deck, gruppe in S["teile"]:
    if not datei.exists():
        print("fehlt:", datei)
        continue
    m = trimesh.load_mesh(datei)
    m.merge_vertices()
    daten.append({"name": name, "farbe": farbe, "deck": deck, "gruppe": gruppe, "an": name not in S["aus"],
                  "v": base64.b64encode(m.vertices.astype(np.float32).tobytes()).decode(),
                  "f": base64.b64encode(m.faces.astype(np.uint32).tobytes()).decode()})
    print(f"{name:28} {len(m.faces):7d} Dreiecke")

HTML = """<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Microban v3 Vorschau</title>
<style>
:root{--bg:#f4f5f7;--panel:#ffffffee;--text:#1d1d1f;--muted:#666;--acc:#2f6f9f}
@media (prefers-color-scheme:dark){:root{--bg:#1b1c1f;--panel:#26282ccc;--text:#eee;--muted:#aaa;--acc:#6fb0e0}}
html,body{margin:0;height:100%;background:var(--bg);color:var(--text);font:14px system-ui,sans-serif;overflow:hidden}
#panel{position:absolute;top:12px;left:12px;background:var(--panel);padding:12px 14px;border-radius:10px;
 max-height:calc(100% - 48px);overflow:auto;box-shadow:0 2px 10px #0003;width:270px}
h1{font-size:15px;margin:0 0 8px} label{display:flex;gap:6px;align-items:center;margin:3px 0;cursor:pointer}
.sw{width:12px;height:12px;border-radius:3px;display:inline-block;flex:none}
.hint{color:var(--muted);font-size:12px;margin-top:8px;line-height:1.4} input[type=range]{width:100%}
.wert{font-variant-numeric:tabular-nums} button{margin:6px 0;padding:6px 12px;border-radius:6px;border:1px solid var(--acc);
 background:var(--acc);color:#fff;cursor:pointer;font:inherit}
</style></head><body>
<div id="panel"><h1>__TITEL__</h1><div id="regler"></div>
<button id="spiel">▶ Abspielen</button>
<label><input id="schnitt" type="checkbox"> Schnitt durch die Mitte (Blick ins Innere)</label>
<hr><div id="liste"></div>
<div class="hint">Linke Maustaste: drehen · Rechte: verschieben · Rad: zoomen<br>__HINWEIS__</div></div>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
"three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
<script type="module">
import * as THREE from "three";
import {OrbitControls} from "three/addons/controls/OrbitControls.js";
const TEILE = __DATEN__, GELENKE = __GELENKE__;
const dunkel = matchMedia("(prefers-color-scheme: dark)").matches;
const renderer = new THREE.WebGLRenderer({antialias:true}); renderer.setPixelRatio(devicePixelRatio);
renderer.setSize(innerWidth, innerHeight); renderer.localClippingEnabled = true; document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(dunkel ? 0x1b1c1f : 0xf4f5f7);
const cam = new THREE.PerspectiveCamera(35, innerWidth/innerHeight, 1, 5000); cam.up.set(0,0,1); cam.position.set(...__KAMERA__);
const ctl = new OrbitControls(cam, renderer.domElement); ctl.target.set(...__ZIEL__); ctl.update();
scene.add(new THREE.HemisphereLight(0xffffff, 0x555555, 1.6));
const sonne = new THREE.DirectionalLight(0xffffff, 1.4); sonne.position.set(150,-120,300); scene.add(sonne);
// verschachtelte Gelenk-Gruppen: Gruppe i liegt im Drehpunkt i, Gruppe i+1 hängt an Gruppe i
const gruppen = [], achsen = [];
GELENKE.forEach((g, i) => {
  const grp = new THREE.Group();
  const p = new THREE.Vector3(...g.punkt);
  if (i === 0) { grp.position.copy(p); scene.add(grp); }
  else { grp.position.copy(p.clone().sub(new THREE.Vector3(...GELENKE[i-1].punkt))); gruppen[i-1].add(grp); }
  gruppen.push(grp); achsen.push(new THREE.Vector3(...g.achse).normalize());
});
const mitte = new THREE.Vector3(...__ZIEL__);
const ebene = new THREE.Plane(new THREE.Vector3(0,-1,0), mitte.y); const ebenen = [];
const dec = s => Uint8Array.from(atob(s), c => c.charCodeAt(0)).buffer;
const liste = document.getElementById("liste");
for (const t of TEILE) {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(dec(t.v)), 3));
  g.setIndex(new THREE.BufferAttribute(new Uint32Array(dec(t.f)), 1)); g.computeVertexNormals();
  const mat = new THREE.MeshStandardMaterial({color:t.farbe, transparent:t.deck<1, opacity:t.deck, roughness:0.7,
    side:THREE.DoubleSide, depthWrite:t.deck>=1, clippingPlanes:ebenen});
  const mesh = new THREE.Mesh(g, mat); mesh.visible = t.an;
  if (t.gruppe >= 0) { mesh.position.set(...GELENKE[t.gruppe].punkt.map(v => -v)); gruppen[t.gruppe].add(mesh); }
  else scene.add(mesh);
  const l = document.createElement("label");
  l.innerHTML = `<input type="checkbox" ${t.an ? "checked" : ""}><span class="sw" style="background:${t.farbe}"></span>${t.name}`;
  l.querySelector("input").onchange = e => { mesh.visible = e.target.checked; };
  liste.appendChild(l);
}
const regler = document.getElementById("regler"), schieber = [];
GELENKE.forEach((g, i) => {
  const d = document.createElement("div");
  d.innerHTML = `<div>${g.text}: <b class="wert">0°</b></div><input type="range" min="${g.min}" max="${g.max}" value="0" step="1">`;
  const r = d.querySelector("input"), w = d.querySelector("b");
  r.oninput = () => { gruppen[i].quaternion.setFromAxisAngle(achsen[i], THREE.MathUtils.degToRad(+r.value)); w.textContent = r.value + "°"; };
  regler.appendChild(d); schieber.push(r);
});
let spielt = false, t0 = 0;
const knopf = document.getElementById("spiel");
knopf.onclick = () => { spielt = !spielt; knopf.textContent = spielt ? "⏸ Anhalten" : "▶ Abspielen"; t0 = performance.now(); };
document.getElementById("schnitt").onchange = e => { ebenen.length = 0; if (e.target.checked) ebenen.push(ebene); };
addEventListener("resize", () => { cam.aspect = innerWidth/innerHeight; cam.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });
renderer.setAnimationLoop(now => {
  if (spielt) {
    // jedes Gelenk schwingt zwischen seinen Grenzen, mit verschiedener Frequenz → alle Kombinationen kommen vor
    const t = (now - t0) / 1000;
    GELENKE.forEach((g, i) => {
      const m = (g.max + g.min) / 2, a = (g.max - g.min) / 2;
      schieber[i].value = Math.round(m + a * Math.sin(2 * Math.PI * t * (i === 0 ? 0.15 : 0.23)));
      schieber[i].oninput();
    });
  }
  ctl.update(); renderer.render(scene, cam);
});
</script></body></html>"""

ersatz = {"__DATEN__": json.dumps(daten), "__TITEL__": S["titel"], "__HINWEIS__": S["hinweis"],
          "__GELENKE__": json.dumps(S["gelenke"]), "__KAMERA__": json.dumps(S["kamera"]), "__ZIEL__": json.dumps(S["ziel"])}
html = HTML
for k, v in ersatz.items():
    html = html.replace(k, v)
ziel.write_text(html, encoding="utf-8")
print(f"gespeichert: {ziel} ({ziel.stat().st_size / 1e6:.1f} MB)")
