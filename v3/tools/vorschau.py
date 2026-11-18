"""Baut eine interaktive 3D-Vorschau (eine HTML-Datei, im Browser öffnen) aus STL-Dateien in Einbaulage.

Aufruf: uv run --no-project --python 3.12 --with trimesh --with numpy --with scipy python v3/tools/vorschau.py \
            EINBAU_ORDNER_BAUGRUPPE v3/vorschau.html
EINBAU_ORDNER_BAUGRUPPE: Ordner mit den Teilen der Baugruppe als STL (erzeugt mit export_teile.py).
Die neuen v3-Teile kommen aus v3/cad/einbau/.
"""
import base64
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

alt, ziel = Path(sys.argv[1]), Path(sys.argv[2])
neu = Path(__file__).resolve().parents[1] / "cad" / "einbau"

# (Anzeigename, Datei, Farbe, Deckkraft, Gruppe)  Gruppe "kopf" dreht sich mit dem Regler
TEILE = [
    ("Kopf: Haube", neu / "kopf_haube.stl", "#4f9fd6", 0.45, "kopf"),
    ("Kopf: Bodenplatte", neu / "kopf_basis.stl", "#2f6f9f", 1.0, "kopf"),
    ("Kopf: Distanzring", neu / "kopf_ring.stl", "#f2b134", 1.0, "kopf"),
    ("AI Camera (Platzhalter)", neu / "platzhalter_ai_camera.stl", "#3a3a3a", 1.0, "kopf"),
    ("Kamerakabel (Platzhalter)", neu / "platzhalter_kabel.stl", "#e8743b", 1.0, "fest"),
    ("Deckel v3", neu / "deckel.stl", "#9bc27a", 0.55, "fest"),
    ("Ladeplatine (neue Lage)", neu / "platzhalter_ladeplatine.stl", "#c0392b", 1.0, "fest"),
    ("Motoren im Rumpf (XL330)", alt / "trunk_1_XL330_without_horn.stl", "#5a5a66", 1.0, "fest"),
    ("Schalter", alt / "trunk_1_switch.stl", "#d35400", 1.0, "fest"),
    ("Pi Zero 2 W", alt / "raspberry.stl", "#2e8b57", 1.0, "fest"),
    ("Pollen-Platine", alt / "trunk_1_hat.stl", "#1f5f3f", 1.0, "fest"),
    ("Akku 2 × 18650", alt / "trunk_1_battery.stl", "#8e44ad", 1.0, "fest"),
    ("BMS", alt / "trunk_1_BMS.stl", "#7f8c8d", 1.0, "fest"),
    ("Brust (chest)", alt / "trunk_1_chest.stl", "#d9d9d9", 0.25, "fest"),
    ("Becken (pelvis)", alt / "trunk_1_pelvis.stl", "#cfcfcf", 0.25, "fest"),
    ("Schulter links", alt / "shoulder_1_shoulder.stl", "#bdbdbd", 0.5, "fest"),
    ("Schulter rechts", alt / "shoulder_2_shoulder.stl", "#bdbdbd", 0.5, "fest"),
]
AUS = {"Brust (chest)", "Becken (pelvis)", "Schulter links", "Schulter rechts"}   # anfangs ausgeblendet

daten = []
for name, datei, farbe, deck, gruppe in TEILE:
    if not datei.exists():
        print("fehlt:", datei)
        continue
    m = trimesh.load_mesh(datei)
    m.merge_vertices()
    v = m.vertices.astype(np.float32)
    f = m.faces.astype(np.uint32)
    daten.append({"name": name, "farbe": farbe, "deck": deck, "gruppe": gruppe, "an": name not in AUS,
                  "v": base64.b64encode(v.tobytes()).decode(), "f": base64.b64encode(f.tobytes()).decode()})
    print(f"{name:28} {len(f):7d} Dreiecke")

HTML = """<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Microban v3 Vorschau</title>
<style>
:root{--bg:#f4f5f7;--panel:#ffffffee;--text:#1d1d1f;--muted:#666}
@media (prefers-color-scheme:dark){:root{--bg:#1b1c1f;--panel:#26282ccc;--text:#eee;--muted:#aaa}}
html,body{margin:0;height:100%;background:var(--bg);color:var(--text);font:14px system-ui,sans-serif;overflow:hidden}
#panel{position:absolute;top:12px;left:12px;background:var(--panel);padding:12px 14px;border-radius:10px;
 max-height:calc(100% - 48px);overflow:auto;box-shadow:0 2px 10px #0003;width:250px}
h1{font-size:15px;margin:0 0 8px} label{display:flex;gap:6px;align-items:center;margin:3px 0;cursor:pointer}
.sw{width:12px;height:12px;border-radius:3px;display:inline-block;flex:none}
.hint{color:var(--muted);font-size:12px;margin-top:8px;line-height:1.4} input[type=range]{width:100%}
#winkel{font-variant-numeric:tabular-nums}
</style></head><body>
<div id="panel"><h1>Microban v3 – Kopf &amp; Deckel</h1>
<div>Kopfdrehung: <b id="winkel">0°</b></div>
<input id="dreh" type="range" min="-60" max="60" value="0" step="1">
<label><input id="schnitt" type="checkbox"> Schnitt bei y = 0 (Blick ins Innere)</label>
<hr><div id="liste"></div>
<div class="hint">Linke Maustaste: drehen · Rechte: verschieben · Rad: zoomen<br>
Genutzt werden ±46° (±0,8 rad), geprüft ist ±60°. Das Kabel ist hier fest gezeichnet, in echt hat es oben eine Schlaufe.</div></div>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
"three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
<script type="module">
import * as THREE from "three";
import {OrbitControls} from "three/addons/controls/OrbitControls.js";
const TEILE = __DATEN__;
const ACHSE = [-2, 0];
const dunkel = matchMedia("(prefers-color-scheme: dark)").matches;
const renderer = new THREE.WebGLRenderer({antialias:true}); renderer.setPixelRatio(devicePixelRatio);
renderer.setSize(innerWidth, innerHeight); renderer.localClippingEnabled = true; document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(dunkel ? 0x1b1c1f : 0xf4f5f7);
const cam = new THREE.PerspectiveCamera(35, innerWidth/innerHeight, 1, 5000); cam.up.set(0,0,1); cam.position.set(260,-200,220);
const ctl = new OrbitControls(cam, renderer.domElement); ctl.target.set(0,0,105); ctl.update();
scene.add(new THREE.HemisphereLight(0xffffff, 0x555555, 1.6));
const sonne = new THREE.DirectionalLight(0xffffff, 1.4); sonne.position.set(150,-120,300); scene.add(sonne);
const kopf = new THREE.Group(); kopf.position.set(ACHSE[0], ACHSE[1], 0); scene.add(kopf);
const ebene = new THREE.Plane(new THREE.Vector3(0,-1,0), 0); const ebenen = [];
const dec = s => Uint8Array.from(atob(s), c => c.charCodeAt(0)).buffer;
const liste = document.getElementById("liste");
for (const t of TEILE) {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(dec(t.v)), 3));
  g.setIndex(new THREE.BufferAttribute(new Uint32Array(dec(t.f)), 1)); g.computeVertexNormals();
  const mat = new THREE.MeshStandardMaterial({color:t.farbe, transparent:t.deck<1, opacity:t.deck, roughness:0.7,
    side:THREE.DoubleSide, depthWrite:t.deck>=1, clippingPlanes:ebenen});
  const mesh = new THREE.Mesh(g, mat); mesh.visible = t.an;
  if (t.gruppe === "kopf") { mesh.position.set(-ACHSE[0], -ACHSE[1], 0); kopf.add(mesh); } else scene.add(mesh);
  const l = document.createElement("label");
  l.innerHTML = `<input type="checkbox" ${t.an ? "checked" : ""}><span class="sw" style="background:${t.farbe}"></span>${t.name}`;
  l.querySelector("input").onchange = e => { mesh.visible = e.target.checked; };
  liste.appendChild(l);
}
const dreh = document.getElementById("dreh"), w = document.getElementById("winkel");
dreh.oninput = () => { kopf.rotation.z = THREE.MathUtils.degToRad(+dreh.value); w.textContent = dreh.value + "°"; };
document.getElementById("schnitt").onchange = e => { ebenen.length = 0; if (e.target.checked) ebenen.push(ebene); };
addEventListener("resize", () => { cam.aspect = innerWidth/innerHeight; cam.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });
renderer.setAnimationLoop(() => { ctl.update(); renderer.render(scene, cam); });
</script></body></html>"""

ziel.write_text(HTML.replace("__DATEN__", json.dumps(daten)), encoding="utf-8")
print(f"gespeichert: {ziel} ({ziel.stat().st_size / 1e6:.1f} MB)")
