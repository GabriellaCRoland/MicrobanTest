"""Suche: Ausrichtung des Rollmotors (Winkel alpha um die Rollachse) und Absenkung der Sohle (delta).
Bewertet: Spitze runter (Nicken +), Rollen nach außen/innen, Überstand nach außen, Beinverlängerung."""
import numpy as np
from shapely.geometry import Polygon, box, LineString
from shapely.affinity import rotate, translate

WAND, SPIEL = 2.0, 1.0
P = np.array([15.5, -36.0, -144.62])
def rel(x0, x1, y0, y1, z0, z1): return np.array([x0-P[0], x1-P[0], y0-P[1], y1-P[1], z0-P[2], z1-P[2]])
KNIE = rel(13.5, 33.5, -50.5, -21.5, -107.9, -73.9)
NICK = rel(5.5, 25.5, -50.5, -21.5, -154.1, -120.1)
ROLL_X = rel(-23.0, 3.0, 0, 0, 0, 0)[:2]
SOHLE_OBEN = -18.0        # heute: Oberkante Fußplatte 18 mm unter der Rollachse (z −162,6)
SOHLE_HALB = 20.0         # halbe Sohlenbreite

def roll_yz(alpha):
    """Rollmotor im yz-Schnitt: 20 breit (quer zur langen Seite), 34 lang, Achse 9,5 vom Ende. alpha=0: lange Seite
    nach oben (+z), alpha=90: lange Seite nach außen (−y)."""
    r = box(-10, -9.5, 10, 24.5)                       # (y, z) bei alpha 0
    return rotate(r, alpha, origin=(0, 0))             # gegen Uhrzeigersinn: +z dreht nach −y

def spitze_runter(alpha):
    yz = roll_yz(alpha).buffer(WAND, join_style=2)
    y0, z0, y1, z1 = yz.bounds
    if min(y1, KNIE[3] + WAND + SPIEL) - max(y0, KNIE[2] - WAND - SPIEL) <= 0:
        return 180.0
    motor = box(ROLL_X[0] - WAND, z0, ROLL_X[1] + WAND, z1)
    nick = box(NICK[0] - WAND, NICK[4] - WAND, NICK[1] + WAND, NICK[5] + WAND)
    knie = box(KNIE[0] - WAND - SPIEL, KNIE[4] - WAND - SPIEL, KNIE[1] + WAND + SPIEL, KNIE[5] + WAND + SPIEL)
    for w in np.arange(0, 120.5, 0.5):
        if rotate(motor, -w, origin=(0, 0)).intersects(knie) or rotate(nick, -w, origin=(0, 0)).intersects(knie):
            return w
    return 120.0

def rollen(alpha, delta, richtung):
    """größter Rollwinkel (richtung +1 / −1), bis die Fußplatten-Oberkante (Linie, 2*SOHLE_HALB breit, delta tiefer)
    den Rollmotor oder Nickmotor (jeweils mit Wand + Spiel) berührt."""
    hindernis = roll_yz(alpha).buffer(WAND + SPIEL, join_style=2).union(
        box(NICK[2] - WAND - SPIEL, NICK[4] - WAND - SPIEL, NICK[3] + WAND + SPIEL, NICK[5]))
    platte = box(-SOHLE_HALB, SOHLE_OBEN - delta - 3, SOHLE_HALB, SOHLE_OBEN - delta)
    for w in np.arange(0, 90.5, 0.5):
        if rotate(platte, richtung * w, origin=(0, 0)).intersects(hindernis):
            return w
    return 90.0

def ueberstand(alpha):
    y0 = roll_yz(alpha).buffer(WAND, join_style=2).bounds[0]
    return max(0.0, -(y0) - SOHLE_HALB)          # wie weit der Motorblock außen über die Sohlenkante ragt

print(f"{'alpha':>5} {'delta':>5} | {'Spitze runter':>13} {'Rollen außen':>12} {'innen':>6} | {'Überstand':>9}")
ergebnis = []
for alpha in (0, 15, 30, 45, 60, 75, 90):
    for delta in (0, 2, 4, 6):
        sr = spitze_runter(alpha)
        ra, ri = rollen(alpha, delta, +1), rollen(alpha, delta, -1)
        ue = ueberstand(alpha)
        ergebnis.append((alpha, delta, sr, ra, ri, ue))
        print(f"{alpha:5d} {delta:5d} | {sr:12.1f}° {ra:11.1f}° {ri:5.1f}° | {ue:8.1f} mm")

print("\nLängeres Schienbein (Kniemotor um s höher), Sohle delta = 4 mm tiefer:")
print(f"{'alpha':>5} {'s':>4} | {'Spitze runter':>13} {'Rollen außen':>12} {'innen':>6} | {'Bein länger':>11}")
basis = KNIE.copy()
for alpha in (0, 75, 90):
    for s in (0, 5, 10, 15, 20):
        KNIE[:] = basis; KNIE[4] += s; KNIE[5] += s
        print(f"{alpha:5d} {s:4d} | {spitze_runter(alpha):12.1f}° {rollen(alpha, 4, +1):11.1f}° {rollen(alpha, 4, -1):5.1f}° | {s + 4:9d} mm")
KNIE[:] = basis
